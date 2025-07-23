"""
Web Scraper Module for Competition Information Extraction

This module provides comprehensive web scraping capabilities for extracting
competition information from various websites. It handles both static and
dynamic content, implements anti-detection measures, and provides robust
error handling for reliable data extraction.

Author: Competition Application Automation System
Version: 1.0
"""

import requests
import time
import random
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
import json
from datetime import datetime

try:
    from bs4 import BeautifulSoup
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, WebDriverException
except ImportError as e:
    print(f"Required dependencies not installed: {e}")
    print("Please install: pip install beautifulsoup4 selenium requests")


@dataclass
class ScrapingResult:
    """
    Data class to encapsulate the results of a web scraping operation.
    
    This structure helps us maintain clean interfaces between different
    parts of the scraping pipeline and makes it easier to handle errors
    and partial results gracefully.
    """
    url: str
    success: bool
    content: Optional[str] = None
    title: Optional[str] = None
    meta_description: Optional[str] = None
    links: Optional[List[str]] = None
    images: Optional[List[str]] = None
    error_message: Optional[str] = None
    scraping_method: Optional[str] = None  # 'static' or 'dynamic'
    timestamp: Optional[str] = None


class WebScraper:
    """
    A comprehensive web scraper that can handle both static and dynamic content.
    
    This class implements a multi-layered approach to web scraping:
    1. First attempts fast static scraping for simple HTML pages
    2. Falls back to Selenium-based dynamic scraping for JavaScript-heavy sites
    3. Implements various anti-detection measures to avoid being blocked
    4. Provides detailed logging and error handling for debugging
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the web scraper with configuration options.
        
        Args:
            config: Dictionary containing scraper configuration such as
                   timeouts, user agents, and retry settings
        """
        # Set up default configuration that works well for most websites
        self.config = config or {}
        self.request_delay = self.config.get('request_delay', (2, 5))  # Random delay range
        self.timeout = self.config.get('timeout', 15)
        self.max_retries = self.config.get('max_retries', 3)
        self.user_agents = self.config.get('user_agents', self._get_default_user_agents())
        
        # Set up logging to track scraping operations and debug issues
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize session for connection reuse and cookie persistence
        self.session = requests.Session()
        
        # Selenium driver will be initialized on-demand to save resources
        self.driver = None
    
    def _get_default_user_agents(self) -> List[str]:
        """
        Returns a list of realistic user agent strings to rotate between requests.
        
        Using different user agents helps avoid detection as a bot, since
        real users access websites from various browsers and devices.
        """
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Safari/17.2'
        ]
    
    def _get_random_headers(self) -> Dict[str, str]:
        """
        Generate realistic HTTP headers with randomized user agent.
        
        This method creates headers that mimic real browser requests,
        including Accept headers and language preferences that make
        our requests less distinguishable from human traffic.
        """
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def _random_delay(self) -> None:
        """
        Implement a random delay between requests to appear more human-like.
        
        The delay prevents overwhelming the target server and reduces
        the likelihood of being detected as automated traffic.
        """
        if isinstance(self.request_delay, tuple):
            delay = random.uniform(self.request_delay[0], self.request_delay[1])
        else:
            delay = self.request_delay
        
        time.sleep(delay)
    
    def scrape_static_content(self, url: str) -> ScrapingResult:
        """
        Scrape content using traditional HTTP requests and BeautifulSoup parsing.
        
        This method is fast and resource-efficient for websites that serve
        their content directly in HTML without requiring JavaScript execution.
        It's our first choice for most scraping operations.
        
        Args:
            url: The URL to scrape
            
        Returns:
            ScrapingResult object containing the scraped content and metadata
        """
        self.logger.info(f"Starting static scraping for: {url}")
        
        for attempt in range(self.max_retries):
            try:
                # Add delay between requests to be respectful to the server
                if attempt > 0:
                    self._random_delay()
                
                # Make the request with randomized headers
                response = self.session.get(
                    url,
                    headers=self._get_random_headers(),
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                # Check if the request was successful
                response.raise_for_status()
                
                # Parse the HTML content
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract comprehensive information from the page
                content = self._extract_content_from_soup(soup)
                title = soup.find('title')
                title_text = title.get_text().strip() if title else None
                
                # Extract meta description for additional context
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                meta_description = meta_desc.get('content', '').strip() if meta_desc else None
                
                # Extract all links for potential follow-up scraping
                links = [urljoin(url, link.get('href', '')) 
                        for link in soup.find_all('a', href=True)]
                
                # Extract image URLs that might contain useful visual information
                images = [urljoin(url, img.get('src', '')) 
                         for img in soup.find_all('img', src=True)]
                
                self.logger.info(f"Successfully scraped {len(content)} characters from {url}")
                
                return ScrapingResult(
                    url=url,
                    success=True,
                    content=content,
                    title=title_text,
                    meta_description=meta_description,
                    links=links[:50],  # Limit to first 50 links to avoid overwhelming data
                    images=images[:20],  # Limit to first 20 images
                    scraping_method='static',
                    timestamp=datetime.now().isoformat()
                )
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Static scraping attempt {attempt + 1} failed for {url}: {e}")
                if attempt == self.max_retries - 1:
                    return ScrapingResult(
                        url=url,
                        success=False,
                        error_message=f"Static scraping failed after {self.max_retries} attempts: {str(e)}",
                        scraping_method='static',
                        timestamp=datetime.now().isoformat()
                    )
            
            except Exception as e:
                self.logger.error(f"Unexpected error during static scraping: {e}")
                return ScrapingResult(
                    url=url,
                    success=False,
                    error_message=f"Unexpected error: {str(e)}",
                    scraping_method='static',
                    timestamp=datetime.now().isoformat()
                )
    
    def _extract_content_from_soup(self, soup: BeautifulSoup) -> str:
        """
        Extract meaningful text content from parsed HTML.
        
        This method focuses on extracting the actual content while filtering
        out navigation elements, advertisements, and other non-essential parts
        that might confuse the LLM during analysis.
        """
        # Remove script and style elements that don't contain useful content
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Try to find main content areas first
        main_content_selectors = [
            'main', 'article', '.content', '#content', '.main-content',
            '.entry-content', '.post-content', '[role="main"]'
        ]
        
        main_content = None
        for selector in main_content_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    main_content = element
                    break
            except:
                continue
        
        # If no main content area found, use the entire body
        if not main_content:
            main_content = soup.find('body') or soup
        
        # Extract text and clean it up
        text = main_content.get_text(separator=' ', strip=True)
        
        # Clean up excessive whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        cleaned_text = '\n'.join(lines)
        
        return cleaned_text
    
    def _initialize_selenium_driver(self) -> webdriver.Chrome:
        """
        Initialize a Selenium Chrome driver with optimized settings.
        
        The driver is configured to be stealthy and efficient, with settings
        that help avoid detection while minimizing resource usage.
        """
        if self.driver and self._is_driver_alive():
            return self.driver
        
        options = Options()
        
        # Configure Chrome options for stealth and efficiency
        options.add_argument('--headless')  # Run without GUI for efficiency
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Set a realistic user agent
        options.add_argument(f'--user-agent={random.choice(self.user_agents)}')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            # Remove automation indicators
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return self.driver
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
    
    def _is_driver_alive(self) -> bool:
        """Check if the Selenium driver is still responsive."""
        try:
            self.driver.current_url
            return True
        except:
            return False
    
    def scrape_dynamic_content(self, url: str) -> ScrapingResult:
        """
        Scrape content from JavaScript-heavy websites using Selenium.
        
        This method is used when static scraping fails or when we detect
        that a website requires JavaScript execution to display its content.
        It's more resource-intensive but can handle modern web applications.
        
        Args:
            url: The URL to scrape
            
        Returns:
            ScrapingResult object containing the scraped content and metadata
        """
        self.logger.info(f"Starting dynamic scraping for: {url}")
        
        try:
            driver = self._initialize_selenium_driver()
            
            # Navigate to the page
            driver.get(url)
            
            # Wait for the page to load completely
            # We use multiple strategies to detect when content is ready
            WebDriverWait(driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait for dynamic content to load
            time.sleep(3)
            
            # Try to detect if there are loading indicators and wait for them to disappear
            loading_selectors = ['.loading', '.spinner', '[data-loading="true"]', '.loader']
            for selector in loading_selectors:
                try:
                    WebDriverWait(driver, 5).until_not(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                except TimeoutException:
                    pass  # Loading indicator might not exist, which is fine
            
            # Get the fully rendered HTML
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract content using the same method as static scraping
            content = self._extract_content_from_soup(soup)
            
            # Get page title
            title = driver.title
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            meta_description = meta_desc.get('content', '').strip() if meta_desc else None
            
            # Extract links and images
            current_url = driver.current_url  # Might be different due to redirects
            links = [urljoin(current_url, link.get('href', '')) 
                    for link in soup.find_all('a', href=True)]
            images = [urljoin(current_url, img.get('src', '')) 
                     for img in soup.find_all('img', src=True)]
            
            self.logger.info(f"Successfully scraped {len(content)} characters using dynamic method")
            
            return ScrapingResult(
                url=url,
                success=True,
                content=content,
                title=title,
                meta_description=meta_description,
                links=links[:50],
                images=images[:20],
                scraping_method='dynamic',
                timestamp=datetime.now().isoformat()
            )
            
        except TimeoutException:
            error_msg = f"Page load timeout for {url}"
            self.logger.error(error_msg)
            return ScrapingResult(
                url=url,
                success=False,
                error_message=error_msg,
                scraping_method='dynamic',
                timestamp=datetime.now().isoformat()
            )
            
        except WebDriverException as e:
            error_msg = f"WebDriver error for {url}: {str(e)}"
            self.logger.error(error_msg)
            return ScrapingResult(
                url=url,
                success=False,
                error_message=error_msg,
                scraping_method='dynamic',
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            error_msg = f"Unexpected error during dynamic scraping: {str(e)}"
            self.logger.error(error_msg)
            return ScrapingResult(
                url=url,
                success=False,
                error_message=error_msg,
                scraping_method='dynamic',
                timestamp=datetime.now().isoformat()
            )
    
    def scrape_url(self, url: str, force_dynamic: bool = False) -> ScrapingResult:
        """
        Main scraping method that intelligently chooses between static and dynamic approaches.
        
        This method implements our two-tier strategy:
        1. Try static scraping first (faster, more efficient)
        2. Fall back to dynamic scraping if static fails or produces insufficient content
        
        Args:
            url: The URL to scrape
            force_dynamic: If True, skip static scraping and use Selenium directly
            
        Returns:
            ScrapingResult object with the scraped content
        """
        self.logger.info(f"Beginning scraping workflow for: {url}")
        
        # Validate the URL format
        parsed_url = urlparse(url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            return ScrapingResult(
                url=url,
                success=False,
                error_message="Invalid URL format",
                timestamp=datetime.now().isoformat()
            )
        
        # If dynamic scraping is forced, skip static attempt
        if force_dynamic:
            self.logger.info("Dynamic scraping forced, skipping static attempt")
            return self.scrape_dynamic_content(url)
        
        # Try static scraping first
        static_result = self.scrape_static_content(url)
        
        # Evaluate if static scraping was successful and sufficient
        if static_result.success and self._is_content_sufficient(static_result.content):
            self.logger.info("Static scraping successful and content appears sufficient")
            return static_result
        
        # Static scraping failed or content was insufficient, try dynamic
        self.logger.info("Static scraping insufficient, attempting dynamic scraping")
        dynamic_result = self.scrape_dynamic_content(url)
        
        # Return the better result (dynamic if it worked, otherwise static with error info)
        if dynamic_result.success:
            return dynamic_result
        else:
            # Both methods failed, return the static result with additional error info
            static_result.error_message = f"Both static and dynamic scraping failed. Static: {static_result.error_message}, Dynamic: {dynamic_result.error_message}"
            return static_result
    
    def _is_content_sufficient(self, content: Optional[str]) -> bool:
        """
        Evaluate whether scraped content contains enough information for analysis.
        
        This heuristic helps determine when static scraping has successfully
        captured the meaningful content vs. when we need to try dynamic scraping.
        """
        if not content:
            return False
        
        # Content should be reasonably substantial
        if len(content.strip()) < 500:
            return False
        
        # Look for indicators of successful content extraction
        competition_keywords = [
            'competition', 'apply', 'application', 'deadline', 'prize', 'eligibility',
            'requirements', 'submit', 'participants', 'winner', 'startup', 'innovation',
            'entrepreneur', 'funding', 'investment', 'accelerator'
        ]
        
        content_lower = content.lower()
        keyword_matches = sum(1 for keyword in competition_keywords if keyword in content_lower)
        
        # Content should contain at least a few relevant keywords
        return keyword_matches >= 3
    
    def scrape_multiple_urls(self, urls: List[str]) -> List[ScrapingResult]:
        """
        Scrape multiple URLs with proper delays and error handling.
        
        This method is useful when a competition's information is spread
        across multiple pages (main page, FAQ, application guidelines, etc.)
        """
        results = []
        
        for i, url in enumerate(urls):
            self.logger.info(f"Scraping URL {i+1}/{len(urls)}: {url}")
            
            result = self.scrape_url(url)
            results.append(result)
            
            # Add delay between requests except for the last one
            if i < len(urls) - 1:
                self._random_delay()
        
        return results
    
    def close(self) -> None:
        """
        Clean up resources, particularly the Selenium driver.
        
        This method should be called when scraping is complete to free up
        system resources and properly close browser instances.
        """
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Selenium driver closed successfully")
            except Exception as e:
                self.logger.warning(f"Error closing Selenium driver: {e}")
            finally:
                self.driver = None
        
        # Close the requests session
        self.session.close()
    
    def __enter__(self):
        """Context manager entry - allows using 'with' statement."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup happens automatically."""
        self.close()


if __name__ == "__main__":
    # This module is designed to be imported and used by scrape_competition.py
    print("WebScraper module loaded successfully. Use scrape_website.py to execute scraping workflows.")