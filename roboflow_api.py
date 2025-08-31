import os
import requests
import logging
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any
import time

logger = logging.getLogger(__name__)

class RoboflowAPI:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('ROBOFLOW_API_KEY')
        self.base_url = "https://api.roboflow.com"
        # Use absolute path to ensure it works in Docker
        self.results_dir = Path("/home/appuser/results")
        self.results_dir.mkdir(exist_ok=True, parents=True)
        
        if not self.api_key:
            logger.warning("No Roboflow API key provided. Dataset downloads will be skipped.")
    
    def download_dataset(self, workspace_id: str, project_id: str, format: str = "yolov8") -> Optional[str]:
        """
        Download a dataset from Roboflow
        
        Args:
            workspace_id: The workspace ID from the project URL
            project_id: The project ID from the project URL
            format: Dataset format (yolov8, coco, pascal, etc.)
        
        Returns:
            Path to downloaded dataset or None if failed
        """
        if not self.api_key:
            logger.warning("No API key available, skipping download")
            return None
        
        try:
            # Create project directory
            project_dir = self.results_dir / f"{workspace_id}_{project_id}"
            project_dir.mkdir(exist_ok=True)
            
            # Check if already downloaded
            dataset_path = project_dir / f"{project_id}_{format}.zip"
            if dataset_path.exists():
                logger.info(f"Dataset already exists: {dataset_path}")
                return str(dataset_path)
            
            # Get project info first
            project_info = self.get_project_info(workspace_id, project_id)
            if not project_info:
                logger.error(f"Could not get project info for {workspace_id}/{project_id}")
                return None
            
            # Try to get the latest version
            versions = project_info.get('versions', [])
            if not versions:
                logger.error(f"No versions found for project {workspace_id}/{project_id}")
                return None
            
            # Get the latest version (highest version number)
            latest_version = max(versions, key=lambda x: x.get('id', 0))
            version_id = latest_version.get('id')
            
            if not version_id:
                logger.error(f"Could not determine version ID for {workspace_id}/{project_id}")
                return None
            
            # Download URL
            download_url = f"{self.base_url}/{workspace_id}/{project_id}/{version_id}/{format}"
            
            logger.info(f"Downloading dataset: {workspace_id}/{project_id} (version {version_id})")
            
            # Make the download request
            response = requests.get(
                download_url,
                params={'key': self.api_key},
                stream=True,
                timeout=300  # 5 minutes timeout
            )
            
            if response.status_code == 200:
                # Save the dataset
                with open(dataset_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                logger.info(f"Successfully downloaded dataset to: {dataset_path}")
                
                # Try to extract the zip file
                try:
                    extract_dir = project_dir / f"{project_id}_{format}"
                    extract_dir.mkdir(exist_ok=True)
                    
                    with zipfile.ZipFile(dataset_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    
                    logger.info(f"Successfully extracted dataset to: {extract_dir}")
                    return str(extract_dir)
                    
                except zipfile.BadZipFile:
                    logger.warning(f"Downloaded file is not a valid zip: {dataset_path}")
                    return str(dataset_path)
                
            elif response.status_code == 404:
                logger.error(f"Dataset not found: {workspace_id}/{project_id}")
                return None
            elif response.status_code == 401:
                logger.error("Invalid API key or unauthorized access")
                return None
            else:
                logger.error(f"Failed to download dataset: HTTP {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Network error downloading dataset {workspace_id}/{project_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading dataset {workspace_id}/{project_id}: {e}")
            return None
    
    def get_project_info(self, workspace_id: str, project_id: str) -> Optional[Dict[Any, Any]]:
        """Get project information from Roboflow API"""
        if not self.api_key:
            return None
        
        try:
            url = f"{self.base_url}/{workspace_id}/{project_id}"
            response = requests.get(
                url,
                params={'key': self.api_key},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get project info: HTTP {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Network error getting project info {workspace_id}/{project_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting project info {workspace_id}/{project_id}: {e}")
            return None
    
    def test_api_key(self) -> bool:
        """Test if the API key is valid"""
        if not self.api_key:
            return False
        
        try:
            # Test with a simple API call
            response = requests.get(
                f"{self.base_url}/",
                params={'key': self.api_key},
                timeout=10
            )
            return response.status_code in [200, 404]  # 404 is ok, means key works but endpoint doesn't exist
        except:
            return False
