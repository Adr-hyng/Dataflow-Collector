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
        # Configuration variables - easily change these
        self.PROJECT_INDEX_TO_DOWNLOAD = 0
        self.DOWNLOAD_TO_RESULTS = True

    async def scrape_projects(self, search_term, max_pages=1):
        logger.info(f"🔍 Starting search for: {search_term}")
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
                if projects:
                    idx = min(self.PROJECT_INDEX_TO_DOWNLOAD, len(projects)-1)
                    await self._download_first_project(projects[idx])
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

    async def _download_first_project(self, project):
        logger.info("🚀 Attempting to download first project...")
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
                        return
                    await self._download_dataset(workspace_id, project_id, api_key)
        except Exception as e:
            logger.error(f"❌ Error preparing download: {e}")

    async def _download_dataset(self, workspace_id, project_id, api_key):
        logger.info(f"📥 Downloading dataset for {workspace_id}/{project_id}...")
        download_dir = Path("results") / f"{workspace_id}_{project_id}"
        download_dir.mkdir(parents=True, exist_ok=True)
        if Roboflow:
            try:
                rf = Roboflow(api_key=api_key)
                project = rf.workspace(workspace_id).project(project_id)
                try:
                    version = project.version(1)
                    for fmt in ['yolov8', 'yolov5', 'darknet', 'coco', 'folder']:
                        try:
                            path = version.download(fmt)
                            if path and os.path.exists(path):
                                logger.info(f"✅ Downloaded in {fmt}: {path}")
                                return
                        except Exception:
                            continue
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"Roboflow package download failed: {e}")
        logger.warning("No supported download method succeeded.")

async def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║              Simple Roboflow Scraper Test                    ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    scraper = SimpleRoboflowScraper()
    search_term = os.getenv('SEARCH_TERM') or input("🔍 Enter search term (or press Enter for 'plastic bottle'): ").strip() or "plastic bottle"
    print(f"🚀 Starting test with search term: '{search_term}'")
    await scraper.scrape_projects(search_term, max_pages=1)
    print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(main())


