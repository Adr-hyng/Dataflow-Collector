import asyncio
import logging
import os
import re
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser
from urllib.parse import urljoin
import time

from database import DatabaseManager
from roboflow_api import RoboflowAPI

logger = logging.getLogger(__name__)

class RoboflowScraper:
    def __init__(self, db_manager: DatabaseManager, roboflow_api: RoboflowAPI):
        self.db_manager = db_manager
        self.roboflow_api = roboflow_api
        self.base_url = "https://universe.roboflow.com"
        self.search_url = f"{self.base_url}/search"
        
    async def scrape_search_results(self, search_term: str, max_pages: int = 5) -> List[Dict]:
        """Scrape search results for a given search term using direct URL navigation"""
        async with async_playwright() as p:
            # Check for debug mode
            debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
            
            if debug_mode:
                browser = await p.chromium.launch(
                    headless=False,
                    slow_mo=1000,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--no-sandbox',
                        '--disable-dev-shm-usage'
                    ]
                )
            else:
                browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Set viewport and user agent
                await page.set_viewport_size({"width": 1920, "height": 1080})
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                })
                
                # Build and navigate to direct search URL
                query = search_term.replace(' ', '%20')
                search_url = f"{self.search_url}?q={query}"
                logger.info(f"Navigating to search URL: {search_url}")
                response = await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                if response:
                    logger.info(f"Search page status: {response.status}")
                await page.wait_for_selector('.projectCard', timeout=20000)
                await asyncio.sleep(2)
                
                all_projects = []
                page_count = 0
                
                while page_count < max_pages:
                    logger.info(f"Scraping page {page_count + 1}")
                    
                    # Get project cards on current page
                    projects = await self.extract_project_cards(page)
                    
                    if not projects:
                        logger.info("No more projects found")
                        break
                    
                    all_projects.extend(projects)
                    logger.info(f"Found {len(projects)} projects on page {page_count + 1}")
                    
                    # Try to go to next page via pagination if present
                    next_button = await page.query_selector('button[aria-label="Go to next page"], a[aria-label="Go to next page"], .pagination .next, a:has-text("Next")')
                    if next_button and await next_button.is_enabled():
                        await next_button.click()
                        await page.wait_for_load_state("domcontentloaded")
                        await asyncio.sleep(1.5)
                        page_count += 1
                    else:
                        break
                
                # Record search history
                self.db_manager.add_search_history(search_term, len(all_projects))
                
                logger.info(f"Total projects found: {len(all_projects)}")
                return all_projects
                
            except Exception as e:
                logger.error(f"Error during scraping: {e}")
                return []
            finally:
                await browser.close()
    
    async def extract_project_cards(self, page: Page) -> List[Dict]:
        """Extract project information from project cards on the current page"""
        try:
            # Wait for project cards to be present
            await page.wait_for_selector('.projectCard', timeout=10000)
            
            # Get all project cards
            cards = await page.query_selector_all('.projectCard')
            projects = []
            
            for card in cards:
                try:
                    project_data = await self.extract_single_project(page, card)
                    if project_data:
                        projects.append(project_data)
                except Exception as e:
                    logger.warning(f"Error extracting project card: {e}")
                    continue
            
            return projects
            
        except Exception as e:
            logger.error(f"Error extracting project cards: {e}")
            return []
    
    async def extract_single_project(self, page: Page, card) -> Optional[Dict]:
        """Extract data from a single project card"""
        try:
            # Get the main project link
            link_element = await card.query_selector('a.secondaryLink[href*="/"]')
            if not link_element:
                return None
            
            href = await link_element.get_attribute('href')
            if not href:
                return None
            
            # Construct full URL
            project_url = urljoin(self.base_url, href)
            
            # Extract workspace_id and project_id from URL
            # URL format: https://universe.roboflow.com/<workspace_id>/<project_id>
            url_parts = href.strip('/').split('/')
            if len(url_parts) < 2:
                logger.warning(f"Invalid project URL format: {href}")
                return None
            
            workspace_id = url_parts[-2]
            project_id = url_parts[-1]
            
            # Extract title
            title_element = await card.query_selector('h3.title-star a')
            title = await title_element.inner_text() if title_element else "Unknown"
            
            # Extract author
            author_element = await card.query_selector('.author a')
            author = await author_element.inner_text() if author_element else "Unknown"
            if author.startswith('by '):
                author = author[3:]
            
            # Extract image and model counts
            details_element = await card.query_selector('.details .flex')
            image_count = 0
            model_count = 0
            
            if details_element:
                details_text = await details_element.inner_text()
                
                # Extract numbers using regex
                image_match = re.search(r'(\d+)\s+images?', details_text)
                model_match = re.search(r'(\d+)\s+models?', details_text)
                
                if image_match:
                    image_count = int(image_match.group(1))
                if model_match:
                    model_count = int(model_match.group(1))
            
            # Extract classes
            class_elements = await card.query_selector_all('.classChip')
            classes = []
            for class_element in class_elements:
                class_name = await class_element.inner_text()
                if class_name:
                    classes.append(class_name.strip())
            
            project_data = {
                'project_url': project_url,
                'workspace_id': workspace_id,
                'project_id': project_id,
                'title': title.strip(),
                'author': author.strip(),
                'image_count': image_count,
                'model_count': model_count,
                'classes': classes
            }
            
            logger.debug(f"Extracted project: {title} by {author}")
            return project_data
            
        except Exception as e:
            logger.error(f"Error extracting single project: {e}")
            return None
    
    async def process_projects(self, projects: List[Dict]) -> int:
        """Process projects: skip if visited, try versioned download; if no version or requires direct, just record."""
        saved_count = 0
        downloaded_count = 0
        
        for project in projects:
            try:
                # Check if project already exists
                if not self.db_manager.project_exists(project['project_url']):
                    # Add to database
                    db_project = self.db_manager.add_project(project)
                    if db_project:
                        saved_count += 1
                        # Attempt versioned download via API helper
                        download_path = self.roboflow_api.download_dataset(
                            project['workspace_id'],
                            project['project_id']
                        )
                        if download_path:
                            self.db_manager.update_project_download_status(project['project_url'], download_path)
                            downloaded_count += 1
                            logger.info(f"Downloaded: {project['title']}")
                        else:
                            # No version or requires direct download; just keep recorded as undownloaded
                            logger.info(f"No version or direct-download required for {project['title']}. Recorded only.")
                        
                        # Small delay to be respectful to the API
                        await asyncio.sleep(1)
                else:
                    logger.info(f"Project already exists: {project['title']}")
                    
            except Exception as e:
                logger.error(f"Error processing project {project.get('title', 'Unknown')}: {e}")
                continue
        
        logger.info(f"Processed {len(projects)} projects, saved {saved_count} new projects, downloaded {downloaded_count} datasets")
        return saved_count
    
    async def run_search(self, search_term: str, max_pages: int = 5) -> Dict:
        """Run complete search and download process"""
        logger.info(f"Starting search for: {search_term}")
        
        # Scrape search results
        projects = await self.scrape_search_results(search_term, max_pages)
        
        if not projects:
            logger.warning("No projects found")
            return {'projects_found': 0, 'projects_saved': 0}
        
        # Process and save projects
        saved_count = await self.process_projects(projects)
        
        return {
            'projects_found': len(projects),
            'projects_saved': saved_count
        }
