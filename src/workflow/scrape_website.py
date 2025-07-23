#!/usr/bin/env python3
"""
Website Scraping Entry Point

Main script for executing competition website scraping workflows.
Reads configuration, executes scraping, and saves structured results.
"""

import json
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
# Add src directory to path for imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent  # Go up from workflow/ to src/
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

try:
    from scraper.web_scraper import WebScraper, ScrapingResult
except ImportError as e:
    print(f"Error importing scraper module: {e}")
    print("Make sure web_scraper.py is in src/scraper/ directory")
    sys.exit(1)


class CompetitionScraper:
    """Main orchestrator for competition website scraping workflow."""
    
    def __init__(self, competition_name: str, target_url: str, config_path: str = "src/scraper/scraper_config.json"):
        self.competition_name = competition_name
        self.target_url = target_url
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.setup_logging()
        
    def load_config(self) -> Dict[str, Any]:
        """Load scraping configuration from JSON file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.logger = logging.getLogger(__name__)
            self.logger.info(f"Configuration loaded from {self.config_path}")
            return config
        except FileNotFoundError:
            print(f"Configuration file not found: {self.config_path}")
            print("Please ensure scraper_config.json exists in the config directory")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in configuration file: {e}")
            sys.exit(1)
    
    def setup_logging(self) -> None:
        """Configure logging based on config settings."""
        log_level = self.config.get('logging', {}).get('level', 'INFO')
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/scraper.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_target_url(self) -> str:
        """Return the target URL provided during initialization."""
        return self.target_url
    
    def get_scraper_config(self) -> Dict[str, Any]:
        """Extract scraper-specific configuration."""
        return self.config.get('scraper_settings', {})
    
    def get_output_directory(self) -> Path:
        """Determine output directory for scraped data."""
        output_dir = Path(self.config.get('output_directory', 'input')) / self.competition_name / 'competition_info'
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    def save_scraping_result(self, result: ScrapingResult, output_dir: Path) -> None:
        """Save scraping results to structured files."""
        
        # Save main content as text file
        content_file = output_dir / 'scraped_content.txt'
        with open(content_file, 'w', encoding='utf-8') as f:
            f.write(result.content or "No content extracted")
        
        # Save metadata as JSON
        metadata = {
            'url': result.url,
            'success': result.success,
            'title': result.title,
            'meta_description': result.meta_description,
            'scraping_method': result.scraping_method,
            'timestamp': result.timestamp,
            'error_message': result.error_message,
            'links_count': len(result.links or []),
            'images_count': len(result.images or []),
            'content_length': len(result.content or '')
        }
        
        metadata_file = output_dir / 'scraping_metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Save links and images if available
        if result.links:
            links_file = output_dir / 'extracted_links.json'
            with open(links_file, 'w', encoding='utf-8') as f:
                json.dump(result.links, f, indent=2, ensure_ascii=False)
        
        if result.images:
            images_file = output_dir / 'extracted_images.json'
            with open(images_file, 'w', encoding='utf-8') as f:
                json.dump(result.images, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Scraping results saved to {output_dir}")
    
    def execute_scraping(self) -> bool:
        """Execute the complete scraping workflow."""
        try:
            # Get configuration
            target_url = self.get_target_url()
            scraper_config = self.get_scraper_config()
            output_dir = self.get_output_directory()
            
            self.logger.info(f"Starting scraping workflow for: {target_url}")
            self.logger.info(f"Output directory: {output_dir}")
            
            # Execute scraping
            with WebScraper(scraper_config) as scraper:
                result = scraper.scrape_url(target_url)
            
            # Save results
            self.save_scraping_result(result, output_dir)
            
            if result.success:
                self.logger.info(" Scraping completed successfully")
                print(f" Successfully scraped content from {target_url}")
                print(f" Results saved to: {output_dir}")
                return True
            else:
                self.logger.error(f" Scraping failed: {result.error_message}")
                print(f" Scraping failed: {result.error_message}")
                return False
                
        except Exception as e:
            self.logger.error(f"Unexpected error in scraping workflow: {e}")
            print(f" Scraping workflow failed: {e}")
            return False


def get_user_inputs() -> tuple[str, str]:
    """Prompt user for competition name and target URL."""
    print("Competition Website Scraper")
    print("=" * 30)
    
    while True:
        competition_name = input("Enter competition name: ").strip()
        if competition_name:
            break
        print(" Competition name cannot be empty. Please try again.")
    
    while True:
        target_url = input("Enter competition website URL: ").strip()
        if target_url:
            # Basic URL validation
            if not (target_url.startswith('http://') or target_url.startswith('https://')):
                target_url = 'https://' + target_url
            break
        print(" URL cannot be empty. Please try again.")
    
    print(f"\n Competition: {competition_name}")
    print(f" URL: {target_url}")
    
    confirm = input("\nProceed with scraping? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Scraping cancelled.")
        sys.exit(0)
    
    return competition_name, target_url


def main():
    """Main entry point for the scraping script."""
    
    # Ensure required directories exist
    for directory in ['config', 'logs', 'input']:
        Path(directory).mkdir(exist_ok=True)
    
    # Check if configuration file exists
    config_file = Path("src/scraper/scraper_config.json")
    if not config_file.exists():
        print(f" Configuration file not found: {config_file}")
        print("Please create the configuration file before running the scraper.")
        return False
    
    # Get user inputs
    competition_name, target_url = get_user_inputs()
    
    # Execute scraping workflow
    scraper = CompetitionScraper(competition_name, target_url)
    success = scraper.execute_scraping()
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)