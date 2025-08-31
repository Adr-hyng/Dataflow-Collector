#!/usr/bin/env python3
"""
Simple Roboflow Scraper Test Script
Runs without database - just tests the web scraping automation

CONFIGURATION:
- PROJECT_INDEX_TO_DOWNLOAD: Which project to download (0 = first, 1 = second, etc.)
- DOWNLOAD_TO_RESULTS: Where to save downloads (True = results/, False = test_results/downloads/)
"""

import asyncio
import logging
import os
import re
from pathlib import Path
import sys
from playwright.async_api import async_playwright
import time

# Try to import requests for fallback download methods
try:
    import requests
    print("✅ Requests package imported successfully")
except ImportError:
    print("❌ Requests package not found. Install with: pip install requests")
    requests = None

# Try to import roboflow package
try:
    from roboflow import Roboflow
    print("✅ Roboflow package imported successfully")
except ImportError:
    print("❌ Roboflow package not found. Install with: pip install roboflow")
    Roboflow = None

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Look for .env in src/, then in project root
    here = Path(__file__).parent
    candidate_paths = [here / '.env', here.parent / '.env']
    found = False
    for env_path in candidate_paths:
        print(f"🔍 Looking for .env file at: {env_path}")
        if env_path.exists():
            load_dotenv(env_path)
            print("✅ Loaded .env file")
            found = True
            break
    if not found:
        load_dotenv()
        print("⚠️  .env not found near script; attempted to load from CWD")
    # Debug: Check if API key was loaded
    api_key = os.getenv('ROBOFLOW_API_KEY')
    if api_key:
        print(f"🔑 API Key loaded: {api_key[:8]}...{api_key[-4:]}")
    else:
        print("⚠️  API Key not found in environment")
except ImportError:
    print("💡 Install python-dotenv to load .env files: pip install python-dotenv")

# Import database from same directory
from database import DatabaseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleRoboflowScraper:
    def __init__(self):
        self.results_dir = Path("test_results")
        self.results_dir.mkdir(exist_ok=True)
        # Configuration
        try:
            self.MAX_PROJECTS = int(os.getenv('MAX_PROJECTS', '5'))
        except Exception:
            self.MAX_PROJECTS = 5
        try:
            self.MAX_PAGES = int(os.getenv('MAX_PAGES', '1'))
        except Exception:
            self.MAX_PAGES = 1
        self.DOWNLOAD_ROOT = Path("downloads")
        self.DOWNLOAD_ROOT.mkdir(exist_ok=True)
        self.db = DatabaseManager()
        
        # Debug mode - bypasses database checks
        self.DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        if self.DEBUG_MODE:
            logger.info("🐛 DEBUG MODE ENABLED - Will download all projects regardless of database status")

    async def scrape_projects(self, search_term, max_pages=None):
        logger.info(f"🔍 Starting search for: {search_term}")
        if max_pages is None:
            max_pages = self.MAX_PAGES
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(
                    headless=False,
                    slow_mo=600,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--no-sandbox',
                        '--disable-dev-shm-usage'
                    ]
                )
                page = await browser.new_page()
                await page.set_viewport_size({"width": 1366, "height": 768})
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                search_url = f"https://universe.roboflow.com/search?q={search_term.replace(' ', '%20')}"
                logger.info(f"🔍 Navigating directly to search URL: {search_url}")
                response = await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                if response:
                    logger.info(f"✅ Search page loaded with status: {response.status}")
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                await page.screenshot(path=self.results_dir / "01_search_results_page.png")
                try:
                    await page.wait_for_selector('.projectCard', timeout=15000)
                except Exception as e:
                    logger.warning(f"⚠️  Project cards not found immediately: {e}")
                await asyncio.sleep(2.5)
                await page.screenshot(path=self.results_dir / "02_results_loaded.png")
                projects = await self._extract_projects(page)
                logger.info(f"📈 TOTAL PROJECTS EXTRACTED: {len(projects)}")
                projects = projects[: self.MAX_PROJECTS]
                for project in projects:
                    full_url = project.get('full_url') or ''
                    if not full_url:
                        continue
                    
                    # In DEBUG_MODE, skip all database operations
                    if self.DEBUG_MODE:
                        logger.info(f"🐛 DEBUG MODE: Downloading project without database check: {full_url}")
                    else:
                        # Normal mode: check if project already exists in database
                        if self.db.project_exists(full_url):
                            logger.info(f"⏭️  Skipping already recorded: {full_url}")
                            continue
                    
                    success_path = await self._download_project_by_meta(project)
                    if success_path:
                        # Only add to database if not in DEBUG_MODE
                        if not self.DEBUG_MODE:
                            record = {
                                'project_url': full_url,
                                'workspace_id': self._workspace_from_link(project.get('redirection_link', '')),
                                'project_id': self._project_from_link(project.get('redirection_link', '')),
                                'title': project.get('title', ''),
                                'author': self._workspace_from_link(project.get('redirection_link', '')),
                                'image_count': self._parse_image_count(project.get('image_count', '0')),
                                'downloaded': True,
                                'download_path': str(success_path)
                            }
                            self.db.add_project(record)
                        else:
                            logger.info(f"🐛 DEBUG MODE: Successfully downloaded {full_url} (not recorded in database)")
                    
                    # Add a small delay between downloads to ensure proper processing
                    await asyncio.sleep(1)
                
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"❌ Error during scraping: {e}")
                try:
                    await page.screenshot(path=self.results_dir / "error.png")
                except Exception:
                    pass
            finally:
                logger.info("🔒 Closing browser...")
                await browser.close()

    async def _extract_projects(self, page):
        projects = []
        try:
            await page.wait_for_selector('.projectCard', timeout=10000)
            project_cards = await page.query_selector_all('.projectCard')
            for i, card in enumerate(project_cards[:20]):
                try:
                    card_id = await card.get_attribute('id')
                    if not card_id or not card_id.startswith('dataset_'):
                        continue
                    project_id = card_id.replace('dataset_', '')
                    title_link = await card.query_selector('h3.title-star a.secondaryLink')
                    if title_link:
                        href = await title_link.get_attribute('href') or ''
                        title_text = await title_link.text_content() or ''
                    else:
                        href = ''
                        title_text = f"Project {project_id}"
                    image_count_elem = await card.query_selector('.details span')
                    image_count_text = await image_count_elem.text_content() if image_count_elem else 'Unknown'
                    author_elem = await card.query_selector('.author a')
                    workspace_id = (await author_elem.text_content()) if author_elem else 'Unknown'
                    full_url = f"https://universe.roboflow.com{href}" if href.startswith('/') else href
                    projects.append({
                        'title': title_text.strip(),
                        'workspace_id': workspace_id.strip(),
                        'project_id': project_id,
                        'redirection_link': href,
                        'full_url': full_url,
                        'image_count': image_count_text,
                        'card_id': card_id
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Error finding project cards: {e}")
        return projects

    async def _download_project_by_meta(self, project):
        logger.info("🚀 Attempting to download project...")
        try:
            redirection_link = project['redirection_link']
            if redirection_link.startswith('/'):
                parts = redirection_link[1:].split('/')
                if len(parts) >= 2:
                    workspace_id = parts[0]
                    project_id = parts[1]
                    api_key = os.getenv('ROBOFLOW_API_KEY')
                    if not api_key:
                        logger.warning("⚠️  ROBOFLOW_API_KEY not set; skipping download")
                        return None
                    return await self._download_dataset(workspace_id, project_id, api_key)
        except Exception as e:
            logger.error(f"❌ Error preparing download: {e}")
        return None

    def _workspace_from_link(self, redirection_link: str) -> str:
        if redirection_link.startswith('/'):
            parts = redirection_link[1:].split('/')
            if len(parts) >= 2:
                return parts[0]
        return ''

    def _project_from_link(self, redirection_link: str) -> str:
        if redirection_link.startswith('/'):
            parts = redirection_link[1:].split('/')
            if len(parts) >= 2:
                return parts[1]
        return ''

    def _parse_image_count(self, text: str) -> int:
        m = re.search(r"(\d+)", text or '')
        return int(m.group(1)) if m else 0

    async def _download_dataset(self, workspace_id, project_id, api_key):
        # Ensure all necessary imports are available
        import os
        import shutil
        import glob
        
        logger.info(f"📥 Downloading dataset for {workspace_id}/{project_id}...")
        download_dir = self.DOWNLOAD_ROOT / f"{workspace_id}_{project_id}"
        download_dir.mkdir(parents=True, exist_ok=True)
        
        download_successful = False
        
        # First, get project information to determine the best export format
        project_type = None
        available_formats = []
        
        try:
            import requests
            project_url = f"https://api.roboflow.com/{workspace_id}/{project_id}?api_key={api_key}"
            logger.info(f"🔍 Fetching project info from: {project_url}")
            
            response = requests.get(project_url)
            if response.status_code == 200:
                project_data = response.json()
                logger.info(f"✅ Project info retrieved successfully")
                
                # Extract project type
                if 'project' in project_data and 'type' in project_data['project']:
                    project_type = project_data['project']['type']
                    logger.info(f"🎯 Project type: {project_type}")
                    
                else:
                    logger.warning(f"⚠️  Could not determine project type, using fallback formats")
                    available_formats = []
                    
            else:
                logger.warning(f"⚠️  Failed to get project info (HTTP {response.status_code}), using fallback formats")
                available_formats = []
                
        except Exception as e:
            logger.warning(f"⚠️  Error fetching project info: {e}, using fallback formats")
            available_formats = []
        
        # Determine the best format to try based on project type and available formats
        if project_type == "object-detection":
            # Priority order for object detection - only valid formats based on Roboflow error messages
            preferred_formats = ['darknet', 'coco', 'yolov8', 'yolov5', 'yolov5pytorch', 'yolov7pytorch', 'yolov4pytorch', 'voc', 'tensorflow', 'tfrecord', 'yolov8-obb', 'yolov9', 'yolov11', 'yolov12', 'mt-yolov6', 'retinanet', 'benchmarker']
        elif project_type == "single-label-classification":
            # Priority order for single-label classification
            preferred_formats = ['folder', 'clip', 'multiclass', 'coco', 'darknet']
        elif project_type == "multi-label-classification":
            # Priority order for multi-label classification
            preferred_formats = ['folder', 'multiclass', 'coco', 'darknet']
        elif project_type == "instance-segmentation":
            # Priority order for instance segmentation
            preferred_formats = ['coco', 'folder', 'darknet']
        elif project_type == "semantic-segmentation":
            # Priority order for semantic segmentation
            preferred_formats = ['png-mask-semantic', 'coco-segmentation', 'coco', 'folder']
        elif project_type == "keypoint-detection":
            # Priority order for keypoint detection
            preferred_formats = ['coco', 'folder', 'darknet']
        else:
            # Fallback for unknown project types
            preferred_formats = ['darknet', 'coco', 'yolov8', 'yolov5']
        
        # Filter preferred formats to only include available ones, then add fallbacks
        if available_formats:
            # First try available formats in preferred order
            formats_to_try = [fmt for fmt in preferred_formats if fmt in available_formats]
        else:
            # If no available formats, use preferred formats as fallback
            formats_to_try = preferred_formats
        
        logger.info(f"🎯 Will try formats in this order: {formats_to_try}")
        
        # Try downloading with determined formats
        try:
            rf = Roboflow(api_key=api_key)
            project = rf.workspace(workspace_id).project(project_id)
            try:
                version = project.version(1)
                dataset = version.download(model_format=formats_to_try[0])
                download_successful = True
                # for fmt in formats_to_try:
                #     try:
                #         logger.info(f"🔄 Trying format: {fmt}")
                #         dataset = version.download(location=download_dir)
                #     except Exception as e:
                #         error_msg = str(e)
                #         if "invalid format" in error_msg.lower() or "invalid for project type" in error_msg.lower():
                #             logger.info(f"ℹ️  Format {fmt} not supported for this project type, skipping...")
                #         else:
                #             logger.warning(f"⚠️  Format {fmt} failed: {e}")
                #         continue
            except Exception as e:
                logger.warning(f"⚠️  Version download failed: {e}")
        except Exception as e:
            logger.warning(f"⚠️  Roboflow package download failed: {e}")
        
        if download_successful:
            logger.info(f"🎉 Successfully downloaded dataset for {workspace_id}/{project_id}")
            return download_dir
        else:
            logger.warning(f"❌ No supported download method succeeded for {workspace_id}/{project_id}")
            return None

async def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║              Simple Roboflow Scraper Test                    ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    scraper = SimpleRoboflowScraper()
    search_term = os.getenv('SEARCH_TERM') or input("🔍 Enter search term (or press Enter for 'plastic bottle'): ").strip() or "plastic bottle"
    print(f"🚀 Starting test with search term: '{search_term}'")
    await scraper.scrape_projects(search_term)
    print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(main())


