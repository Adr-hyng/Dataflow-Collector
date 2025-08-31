#!/usr/bin/env python3
"""
Roboflow Universe Dataset Scraper

A robust web scraper that searches Roboflow Universe for datasets,
extracts project information, and downloads datasets using the Roboflow API.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from database import DatabaseManager
from roboflow_api import RoboflowAPI
from scraper import RoboflowScraper

# Load environment variables
load_dotenv()

# Setup logging
def setup_logging():
    """Setup logging configuration"""
    log_dir = Path("/home/appuser/logs")
    log_dir.mkdir(exist_ok=True, parents=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "scraper.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_search_terms():
    """Get search terms from environment variable or user input"""
    # Check for environment variable first
    env_search_terms = os.getenv('SEARCH_TERMS')
    if env_search_terms:
        return [term.strip() for term in env_search_terms.split(',')]
    
    # Interactive input if running interactively
    if sys.stdin.isatty():
        print("Enter search terms (comma-separated):")
        user_input = input().strip()
        if user_input:
            return [term.strip() for term in user_input.split(',')]
    
    # Default search terms
    return ["bottle", "object detection"]

async def main():
    """Main entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Roboflow Universe Scraper")
    
    try:
        # Initialize components
        logger.info("Initializing database connection...")
        db_manager = DatabaseManager()
        
        logger.info("Initializing Roboflow API...")
        roboflow_api = RoboflowAPI()
        
        # Test API key if provided
        if roboflow_api.api_key:
            if roboflow_api.test_api_key():
                logger.info("Roboflow API key is valid")
            else:
                logger.warning("Roboflow API key appears to be invalid")
        else:
            logger.warning("No Roboflow API key provided - datasets will not be downloaded")
        
        # Initialize scraper
        scraper = RoboflowScraper(db_manager, roboflow_api)
        
        # Get search terms
        search_terms = get_search_terms()
        logger.info(f"Search terms: {search_terms}")
        
        # Get configuration
        max_pages = int(os.getenv('MAX_PAGES', '3'))
        
        # Process each search term
        total_found = 0
        total_saved = 0
        
        for search_term in search_terms:
            logger.info(f"Processing search term: {search_term}")
            
            try:
                result = await scraper.run_search(search_term, max_pages)
                total_found += result['projects_found']
                total_saved += result['projects_saved']
                
                logger.info(f"Search '{search_term}' completed: {result['projects_found']} found, {result['projects_saved']} saved")
                
                # Small delay between searches
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing search term '{search_term}': {e}")
                continue
        
        logger.info(f"Scraping completed. Total: {total_found} projects found, {total_saved} projects saved")
        
        # Download any remaining undownloaded projects
        if roboflow_api.api_key:
            logger.info("Checking for undownloaded projects...")
            undownloaded = db_manager.get_undownloaded_projects()
            
            if undownloaded:
                logger.info(f"Found {len(undownloaded)} undownloaded projects, attempting download...")
                
                for project in undownloaded:
                    try:
                        download_path = roboflow_api.download_dataset(
                            project.workspace_id,
                            project.project_id
                        )
                        
                        if download_path:
                            db_manager.update_project_download_status(
                                project.project_url,
                                download_path
                            )
                            logger.info(f"Downloaded: {project.title}")
                        
                        # Rate limiting
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error downloading {project.title}: {e}")
                        continue
            else:
                logger.info("All projects have been downloaded")
        
        logger.info("Scraper finished successfully")
        
    except KeyboardInterrupt:
        logger.info("Scraper interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
