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
    # Load .env from current directory explicitly
    env_path = Path(__file__).parent / '.env'
    print(f"🔍 Looking for .env file at: {env_path}")
    
    if env_path.exists():
        print("✅ .env file found")
        load_dotenv(env_path)
        print("✅ Loaded .env file")
    else:
        print("⚠️  .env file not found at expected location")
        # Try current working directory
        load_dotenv()
        print("✅ Attempted to load .env from current directory")
    
    # Debug: Check if API key was loaded
    api_key = os.getenv('ROBOFLOW_API_KEY')
    if api_key:
        print(f"🔑 API Key loaded: {api_key[:8]}...{api_key[-4:]}")
    else:
        print("⚠️  API Key not found in .env file")
        
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
        self.PROJECT_INDEX_TO_DOWNLOAD = 10 # 0 = first project, 1 = second, etc.
        self.DOWNLOAD_TO_RESULTS = True     # True = download to results/, False = download to test_results/downloads/
        
    async def scrape_projects(self, search_term, max_pages=2):
        """Simple scraping without database storage"""
        logger.info(f"🔍 Starting search for: {search_term}")
        
        async with async_playwright() as p:
            try:
                # Launch browser with visible window for debugging
                browser = await p.chromium.launch(
                    headless=False,  # Show browser window
                    slow_mo=1000,    # Slow down for visibility
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--no-sandbox',
                        '--disable-dev-shm-usage'
                    ]
                )
                
                page = await browser.new_page()
                
                # Set viewport and user agent
                await page.set_viewport_size({"width": 1366, "height": 768})
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                
                # Build the search URL directly
                search_url = f"https://universe.roboflow.com/search?q={search_term.replace(' ', '%20')}"
                logger.info(f"🔍 Navigating directly to search URL: {search_url}")
                
                # Navigate directly to the search results page
                response = await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                
                if response:
                    logger.info(f"✅ Search page loaded with status: {response.status}")
                
                # Wait for DOM to be ready
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                logger.info("✅ DOM content loaded")
                
                # Get page title and URL
                title = await page.title()
                current_url = page.url
                logger.info(f"📄 Page title: {title}")
                logger.info(f"🌐 Current URL: {current_url}")
                
                # Take screenshot of search results page
                await page.screenshot(path=self.results_dir / "01_search_results_page.png")
                logger.info("📸 Search results page screenshot saved")
                
                # Wait for search results to fully load
                logger.info("⏳ Waiting for search results to fully load...")
                
                # Wait for project cards to appear
                try:
                    await page.wait_for_selector('.projectCard', timeout=15000)
                    logger.info("✅ Project cards found")
                except Exception as e:
                    logger.warning(f"⚠️  Project cards not found immediately: {e}")
                
                # Additional wait for any dynamic content to settle
                await asyncio.sleep(3)
                
                # Take another screenshot after waiting
                await page.screenshot(path=self.results_dir / "02_results_loaded.png")
                logger.info("📸 Results loaded screenshot saved")
                
                # Extract project information from the search results
                projects = await self._extract_projects(page)
                logger.info(f"📊 Found {len(projects)} projects")
                
                # Verify that we actually got search results
                if projects:
                    first_project = projects[0]
                    logger.info(f"🔍 First project title: '{first_project['title']}'")
                    logger.info(f"🔍 First project workspace: '{first_project['workspace_id']}'")
                    
                    # Check if this looks like a search result for our term
                    search_term_lower = search_term.lower()
                    title_lower = first_project['title'].lower()
                    workspace_lower = first_project['workspace_id'].lower()
                    
                    if (search_term_lower in title_lower or 
                        search_term_lower in workspace_lower or
                        any(word in title_lower for word in search_term_lower.split())):
                        logger.info("✅ Search results verified - found relevant projects!")
                    else:
                        logger.warning("⚠️  Search results may not be correct - projects don't seem to match search term")
                else:
                    logger.warning("⚠️  No projects found after search")
                
                # Display summary of extracted projects
                logger.info("📊 EXTRACTED PROJECTS SUMMARY:")
                logger.info("=" * 60)
                
                for i, project in enumerate(projects[:5]):  # Limit to first 5 for testing
                    logger.info(f"📋 PROJECT {i+1}:")
                    logger.info(f"   🏷️  Title: {project['title']}")
                    logger.info(f"   👤 Workspace: {project['workspace_id']}")
                    logger.info(f"   🆔 Project ID: {project['project_id']}")
                    logger.info(f"   🔗 Redirection Link: {project['redirection_link']}")
                    logger.info(f"   🌐 Full URL: {project['full_url']}")
                    logger.info(f"   🖼️  Image Count: {project['image_count']}")
                    logger.info(f"   🃏 Card ID: {project['card_id']}")
                    logger.info("   " + "="*60)
                
                # Also show total count
                logger.info(f"📈 TOTAL PROJECTS EXTRACTED: {len(projects)}")
                logger.info("=" * 60)
                
                # Try to download the specified project using Roboflow API
                if projects:
                    # Check if the specified project index exists
                    if self.PROJECT_INDEX_TO_DOWNLOAD < len(projects):
                        selected_project = projects[self.PROJECT_INDEX_TO_DOWNLOAD]
                        logger.info(f"🎯 Selected project {self.PROJECT_INDEX_TO_DOWNLOAD + 1} for download: '{selected_project['title']}'")
                        await self._download_first_project(selected_project)
                    else:
                        logger.warning(f"⚠️  Project index {self.PJECT_INDEX_TO_DOWNLOAD} not available. Only {len(projects)} projects found.")
                        logger.info(f"💡 Available indices: 0 to {len(projects) - 1}")
                        # Fallback to first project
                        logger.info("🔄 Falling back to first project...")
                        await self._download_first_project(projects[0])
                
                # Wait for manual inspection
                logger.info("⏰ Waiting 30 seconds for you to inspect the browser...")
                logger.info("👀 You can now manually interact with the page")
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Error during scraping: {e}")
                await page.screenshot(path=self.results_dir / "error.png")
                logger.info("📸 Error screenshot saved")
                
            finally:
                logger.info("🔒 Closing browser...")
                await browser.close()
    

    
    async def _extract_projects(self, page):
        """Extract project information from the page"""
        projects = []
        
        try:
            # Wait for project cards to load
            await page.wait_for_selector('.projectCard', timeout=10000)
            
            # Find all project cards
            project_cards = await page.query_selector_all('.projectCard')
            logger.info(f"🔍 Found {len(project_cards)} project cards")
            
            for i, card in enumerate(project_cards[:20]):  # Limit to first 10
                try:
                    logger.info(f"🔍 Processing card {i+1}...")
                    
                    # Extract project ID from card ID
                    card_id = await card.get_attribute('id')
                    if card_id and card_id.startswith('dataset_'):
                        project_id = card_id.replace('dataset_', '')
                        logger.info(f"   📋 Project ID: {project_id}")
                        
                        # Find the project title link (the redirection link you want)
                        title_link = await card.query_selector('h3.title-star a.secondaryLink')
                        if title_link:
                            href = await title_link.get_attribute('href')
                            title_text = await title_link.text_content()
                            logger.info(f"   🔗 Redirection Link: {href}")
                            logger.info(f"   📝 Project Title: {title_text}")
                        else:
                            logger.warning(f"   ❌ No title link found for card {i+1}")
                            href = "No link found"
                            title_text = f"Project {project_id}"
                        
                        # Find the number of images
                        image_count_elem = await card.query_selector('.details span')
                        if image_count_elem:
                            image_count_text = await image_count_elem.text_content()
                            logger.info(f"   🖼️  Image Count: {image_count_text}")
                        else:
                            logger.warning(f"   ❌ No image count found for card {i+1}")
                            image_count_text = "Unknown"
                        
                        # Find workspace/author info
                        author_elem = await card.query_selector('.author a')
                        if author_elem:
                            workspace_id = await author_elem.text_content()
                            logger.info(f"   👤 Workspace: {workspace_id}")
                        else:
                            logger.warning(f"   ❌ No workspace info found for card {i+1}")
                            workspace_id = "Unknown"
                        
                        # Build the full URL
                        if href.startswith('/'):
                            full_url = f"https://universe.roboflow.com{href}"
                        else:
                            full_url = href
                        
                        projects.append({
                            'title': title_text.strip() if title_text else f"Project {project_id}",
                            'workspace_id': workspace_id.strip() if workspace_id else "unknown",
                            'project_id': project_id,
                            'redirection_link': href,
                            'full_url': full_url,
                            'image_count': image_count_text,
                            'card_id': card_id
                        })
                        
                        logger.info(f"   ✅ Card {i+1} processed successfully")
                        logger.info("   " + "="*50)
                        
                except Exception as e:
                    logger.error(f"❌ Error processing card {i+1}: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Error finding project cards: {e}")
        
        return projects
    
    async def _download_first_project(self, project):
        """Download the first project using Roboflow API"""
        logger.info("🚀 Attempting to download first project...")
        
        try:
            # Extract workspace_id and project_id from the redirection link
            redirection_link = project['redirection_link']
            logger.info(f"🔗 Analyzing redirection link: {redirection_link}")
            
            # Parse the URL to extract workspace_id and project_id
            # Example: /csproject-lqqy2/plastic-bottle-biyfl
            # workspace_id = csproject-lqqy2, project_id = plastic-bottle-biyfl
            
            if redirection_link.startswith('/'):
                # Remove leading slash and split by /
                parts = redirection_link[1:].split('/')
                if len(parts) >= 2:
                    workspace_id = parts[0]
                    project_id = parts[1]
                    
                    logger.info(f"🏷️  Extracted workspace_id: {workspace_id}")
                    logger.info(f"🆔 Extracted project_id: {project_id}")
                    
                    # Check if we have API key
                    api_key = os.getenv('ROBOFLOW_API_KEY')
                    if not api_key:
                        logger.warning("⚠️  ROBOFLOW_API_KEY not found in environment variables")
                        logger.info("💡 To download datasets, set ROBOFLOW_API_KEY environment variable")
                        logger.info("💡 Example: set ROBOFLOW_API_KEY=your_key_here")
                        return
                    
                    # Download the dataset
                    await self._download_dataset(workspace_id, project_id, api_key)
                else:
                    logger.error("❌ Could not parse redirection link format")
            else:
                logger.error("❌ Redirection link is not in expected format")
                
        except Exception as e:
            logger.error(f"❌ Error preparing download: {e}")
    
    async def _download_dataset(self, workspace_id, project_id, api_key):
        """Download dataset using official Roboflow package or fallback methods"""
        logger.info(f"📥 Downloading dataset for {workspace_id}/{project_id}...")
        
        # Create download directory based on configuration
        if self.DOWNLOAD_TO_RESULTS:
            # Download to main results/ folder
            download_dir = Path("results") / f"{workspace_id}_{project_id}"
            logger.info("📁 Downloading to main results/ folder")
        else:
            # Download to test_results/downloads/ folder
            download_dir = self.results_dir / "downloads" / f"{workspace_id}_{project_id}"
            logger.info("📁 Downloading to test_results/downloads/ folder")
        
        download_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Download directory: {download_dir}")
        
        # Method 1: Try official Roboflow package with version
        if Roboflow:
            try:
                logger.info("🔄 Method 1: Trying official Roboflow package with version...")
                await self._download_with_roboflow_package(workspace_id, project_id, api_key, download_dir)
                return
            except Exception as e:
                logger.warning(f"⚠️  Official Roboflow package method failed: {e}")
                logger.info("🔄 Falling back to alternative methods...")
        
        # Method 2: Try direct project download without version
        try:
            logger.info("🔄 Method 2: Trying direct project download without version...")
            await self._download_direct_project(workspace_id, project_id, api_key, download_dir)
            return
        except Exception as e:
            logger.warning(f"⚠️  Direct project download failed: {e}")
        
        logger.error("❌ All download methods failed")
        logger.info("💡 This project might not support dataset downloads or have restricted access")
    
    async def _download_with_roboflow_package(self, workspace_id, project_id, api_key, download_dir):
        """Download using official Roboflow package with version"""
        try:
            # Initialize Roboflow client
            rf = Roboflow(api_key=api_key)
            logger.info("🔑 Roboflow client initialized")
            
            # Get project
            project = rf.workspace(workspace_id).project(project_id)
            logger.info(f"📋 Project: {project.name}")
            
            # Try to get version 1 first
            try:
                version = project.version(1)
                logger.info(f"📦 Version: {version.version}")
                
                # Try popular formats
                popular_formats = ['yolov8', 'yolov5', 'darknet', 'coco', 'folder', 'multiclass']
                
                for format_name in popular_formats:
                    try:
                        logger.info(f"🔄 Attempting to download in {format_name} format...")
                        dataset_path = version.download(format_name)
                        
                        if dataset_path and os.path.exists(dataset_path):
                            logger.info(f"✅ Successfully downloaded in {format_name} format!")
                            logger.info(f"📁 Downloaded to: {dataset_path}")
                            return
                    except Exception as e:
                        logger.warning(f"⚠️  Format {format_name} failed: {e}")
                        continue
                
                logger.warning("⚠️  All version formats failed, trying without version...")
                
            except Exception as e:
                logger.warning(f"⚠️  Version 1 not available: {e}")
                logger.info("🔄 Trying direct project download...")
            
            # Try direct project download without version
            if hasattr(project, 'download'):
                for format_name in ['yolov8', 'yolov5', 'darknet', 'coco', 'folder']:
                    try:
                        logger.info(f"🔄 Trying direct project download in {format_name} format...")
                        dataset_path = project.download(format_name)
                        
                        if dataset_path and os.path.exists(dataset_path):
                            logger.info(f"✅ Successfully downloaded in {format_name} format!")
                            logger.info(f"📁 Downloaded to: {dataset_path}")
                            return
                    except Exception as e:
                        logger.warning(f"⚠️  Direct {format_name} format failed: {e}")
                        continue
            
            raise Exception("No working download method found with Roboflow package")
            
        except Exception as e:
            raise Exception(f"Roboflow package download failed: {e}")
    
    async def _download_direct_project(self, workspace_id, project_id, api_key, download_dir):
        """Try to download dataset directly from project without version"""
        pass
async def main():
    """Main function"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║              Simple Roboflow Scraper Test                    ║")
    print("║                                                              ║")
    print("║  This will test the web scraping automation without         ║")
    print("║  database storage - just to see how it works                ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    
    # Show current configuration
    scraper = SimpleRoboflowScraper()
    print("🔧 CURRENT CONFIGURATION:")
    print(f"   📥 Project to download: Index {scraper.PROJECT_INDEX_TO_DOWNLOAD} (0 = first, 1 = second, etc.)")
    print(f"   📁 Download location: {'results/ folder' if scraper.DOWNLOAD_TO_RESULTS else 'test_results/downloads/ folder'}")
    print("💡 To change these settings, edit the variables in the SimpleRoboflowScraper.__init__ method")
    print()
    
    # Get search term from user or use default
    search_term = input("🔍 Enter search term (or press Enter for 'plastic bottle'): ").strip()
    if not search_term:
        search_term = "plastic bottle"
    
    print(f"🚀 Starting test with search term: '{search_term}'")
    print("📺 A browser window will open shortly...")
    print()
    
    await scraper.scrape_projects(search_term, max_pages=2)
    
    print()
    print("✅ Test completed!")
    print(f"📁 Check the 'test_results' folder for screenshots")
    print("📝 This was just a test - no data was stored or downloaded")

if __name__ == "__main__":
    asyncio.run(main())
