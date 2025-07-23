#!/usr/bin/env python3
"""
Workflow Execution Module

Orchestrates the complete competition application automation workflow:
1. Web scraping
2. Content parsing
3. LLM-powered application generation
"""

import yaml
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add src directory to path
current_dir = Path(__file__).parent
src_dir = current_dir / 'src'
sys.path.insert(0, str(src_dir))

try:
    from scraper.web_scraper import WebScraper
    from scraper.content_parser import ContentParser, MonicaAIClient
    from api.monica_client import MonicaClient
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)


class WorkflowExecutor:
    """Main orchestrator for the complete application workflow."""
    
    def __init__(self, config_path: str = "src/workflow/workflow_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.setup_logging()
        
    def load_config(self) -> Dict[str, Any]:
        """Load workflow configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            print(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Invalid YAML in configuration file: {e}")
            sys.exit(1)
    
    def setup_logging(self) -> None:
        """Configure logging."""
        log_level = self.config.get('logging', {}).get('level', 'INFO')
        
        # Ensure logs directory exists
        Path('logs').mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/workflow.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_user_inputs(self) -> tuple[str, str]:
        """Get competition name and URL from user."""
        print("Competition Application Automation Workflow")
        print("=" * 45)
        
        while True:
            competition_name = input("Enter competition name: ").strip()
            if competition_name:
                break
            print("❌ Competition name cannot be empty.")
        
        while True:
            target_url = input("Enter competition website URL: ").strip()
            if target_url:
                if not (target_url.startswith('http://') or target_url.startswith('https://')):
                    target_url = 'https://' + target_url
                break
            print("❌ URL cannot be empty.")
        
        print(f"\n📋 Competition: {competition_name}")
        print(f"🌐 URL: {target_url}")
        
        confirm = input("\nProceed with workflow? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("Workflow cancelled.")
            sys.exit(0)
        
        return competition_name, target_url
    
    def execute_scraping(self, competition_name: str, target_url: str) -> bool:
        """Execute web scraping step."""
        self.logger.info("Step 1: Executing web scraping")
        
        try:
            scraper_config = self.config.get('scraper_settings', {})
            
            # Create output directory
            output_dir = Path(self.config['paths']['input_base']) / competition_name / 'competition_info'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Execute scraping
            with WebScraper(scraper_config) as scraper:
                result = scraper.scrape_url(target_url)
            
            if not result.success:
                self.logger.error(f"Scraping failed: {result.error_message}")
                return False
            
            # Save results manually to competition_info directory
            content_file = output_dir / 'scraped_content.txt'
            with open(content_file, 'w', encoding='utf-8') as f:
                f.write(result.content or "No content extracted")
            
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
            import json
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            self.logger.info("✅ Scraping completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Scraping step failed: {e}")
            return False
    
    def execute_parsing(self, competition_name: str) -> bool:
        """Execute content parsing step."""
        self.logger.info("Step 2: Executing content parsing")
        
        try:
            # Read scraped content
            input_dir = Path(self.config['paths']['input_base']) / competition_name / 'competition_info'
            content_file = input_dir / 'scraped_content.txt'
            
            if not content_file.exists():
                self.logger.error(f"Scraped content not found: {content_file}")
                return False
            
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Initialize parser with Monica AI client
            llm_config = self.config.get('llm_settings', {})
            llm_client = MonicaAIClient(
                api_key=llm_config['api_key'],
                base_url=llm_config['base_url'],
                model=llm_config['model']
            )
            parser = ContentParser(llm_client=llm_client)
            
            # Parse content
            parsed_info = parser.parse_content(content)
            
            # Save parsed information
            parser.save_to_competition_dir(parsed_info, competition_name, self.config['paths']['input_base'])
            
            self.logger.info("✅ Content parsing completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Parsing step failed: {e}")
            return False
    
    def load_prompt_template(self) -> str:
        """Load the prompt template from markdown file."""
        prompt_path = Path(self.config['paths']['prompt_template'])
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"Prompt template not found: {prompt_path}")
            raise
    
    def load_reference_docs(self, competition_name: str) -> Dict[str, str]:
        """Load reference documentation and parsed competition info."""
        docs = {}
        
        # Load parsed competition info
        parsed_info_path = Path(self.config['paths']['input_base']) / competition_name / 'competition_info' / 'parsed_competition_info.json'
        if parsed_info_path.exists():
            with open(parsed_info_path, 'r', encoding='utf-8') as f:
                import json
                docs['competition_info'] = json.load(f)
        
        # Load scraped content
        content_path = Path(self.config['paths']['input_base']) / competition_name / 'competition_info' / 'scraped_content.txt'
        if content_path.exists():
            with open(content_path, 'r', encoding='utf-8') as f:
                docs['scraped_content'] = f.read()
        
        # Load reference documentation from multiple files
        reference_docs = self.config.get('reference_docs', {})
        for category, file_list in reference_docs.items():
            category_content = []
            for file_path in file_list:
                full_path = Path(file_path)
                if full_path.exists():
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            category_content.append(f"## {full_path.name}\n{content}")
                    except Exception as e:
                        self.logger.warning(f"Failed to read {file_path}: {e}")
                else:
                    self.logger.warning(f"Reference file not found: {file_path}")
            
            if category_content:
                docs[f'reference_{category}'] = '\n\n'.join(category_content)
        
        return docs
    
    def execute_application_generation(self, competition_name: str) -> bool:
        """Execute LLM-powered application generation step."""
        self.logger.info("Step 3: Executing application generation")
        
        try:
            # Load prompt template
            prompt_template = self.load_prompt_template()
            
            # Load reference documents
            reference_docs = self.load_reference_docs(competition_name)
            
            # Construct final prompt
            final_prompt = self.construct_final_prompt(prompt_template, reference_docs, competition_name)
            
            # Execute LLM call (placeholder for now)
            application_content = self.call_llm_for_application(final_prompt)
            
            # Save output
            output_dir = Path(self.config['paths']['output_base']) / competition_name
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / f"{competition_name}_application.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(application_content)
            
            self.logger.info(f"✅ Application generated and saved to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Application generation failed: {e}")
            return False
    
    def construct_final_prompt(self, template: str, reference_docs: Dict[str, str], competition_name: str) -> str:
        # 替换基本占位符
        prompt = template.replace("{COMPETITION_NAME}", competition_name)
        prompt = prompt.replace("{TIMESTAMP}", datetime.now().isoformat())
        
        # 构建参考数据字符串
        reference_data = ""
        for key, content in reference_docs.items():
            reference_data += f"\n## {key}\n{content}\n"
        
        prompt = prompt.replace("{reference_data}", reference_data)
        prompt = prompt.replace("{history_data}", "")  # 暂时为空
        
        return prompt
    
    def call_llm_for_application(self, prompt: str) -> str:
        """Call Monica AI to generate application content."""
        self.logger.info(f"Calling Monica AI for application generation with prompt length: {len(prompt)}")
        
        try:
            # Get LLM configuration
            llm_config = self.config.get('llm_settings', {})
            
            # Create Monica client using your custom implementation
            monica_client = MonicaClient(
                base_url=llm_config.get('base_url', 'https://openapi.monica.im/v1'),
                api_key=llm_config.get('api_key'),
                model=llm_config.get('model', 'gpt-4.1')
            )
            
            # Call the API with configuration parameters
            application_content = monica_client.complete(
                prompt=prompt,
                temperature=llm_config.get('temperature', 0.7),
                max_tokens=llm_config.get('max_tokens', 4000),
                retry_attempts=3,
                retry_delay=5
            )
            
            self.logger.info(f"Successfully generated application content ({len(application_content)} characters)")
            return application_content
            
        except Exception as e:
            self.logger.error(f"Failed to generate application content: {e}")
            # Return a fallback message instead of crashing
            return f"""# Application Generation Failed

An error occurred while generating the application content: {str(e)}

**Original prompt length:** {len(prompt)} characters
**Error timestamp:** {datetime.now().isoformat()}

Please check the logs for more details and verify your Monica AI configuration.

---
*Competition Application Automation System*
"""
    
    def execute_complete_workflow(self) -> bool:
        """Execute the complete workflow."""
        try:
            # Get user inputs
            competition_name, target_url = self.get_user_inputs()
            
            print(f"\n🚀 Starting workflow for {competition_name}")
            
            # Step 1: Web scraping
            if not self.execute_scraping(competition_name, target_url):
                print("❌ Workflow failed at scraping step")
                return False
            print("✅ Step 1: Web scraping completed")
            
            # Step 2: Content parsing
            if not self.execute_parsing(competition_name):
                print("❌ Workflow failed at parsing step")
                return False
            print("✅ Step 2: Content parsing completed")
            
            # Step 3: Application generation
            if not self.execute_application_generation(competition_name):
                print("❌ Workflow failed at application generation step")
                return False
            print("✅ Step 3: Application generation completed")
            
            print(f"\n🎉 Workflow completed successfully!")
            print(f"📁 Output saved to: output/{competition_name}/")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            print(f"❌ Workflow failed: {e}")
            return False


def main():
    """Main entry point."""
    
    # Ensure required directories exist
    for directory in ['logs', 'input', 'output']:
        Path(directory).mkdir(exist_ok=True)
    
    # Check configuration file
    config_file = Path('src/workflow/workflow_config.yaml')
    if not config_file.exists():
        print(f"❌ Configuration file not found: {config_file}")
        return False
    
    # Execute workflow
    executor = WorkflowExecutor()
    success = executor.execute_complete_workflow()
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)