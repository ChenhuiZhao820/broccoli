"""
Content Parser Module for Competition Information Extraction

This module provides LLM-powered intelligent parsing of scraped competition content
to extract structured information for application workflow optimization.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import re


@dataclass
class ParsedCompetitionInfo:
    """Structured representation of parsed competition information."""
    
    # Basic competition details
    name: Optional[str] = None
    organizer: Optional[str] = None
    partners: Optional[List[str]] = None
    application_status: Optional[str] = None
    deadline: Optional[str] = None
    
    # Target participants
    target_description: Optional[str] = None
    eligibility_criteria: Optional[List[str]] = None
    
    # Competition focus
    stage_preference: Optional[str] = None
    industry_focus: Optional[List[str]] = None
    innovation_type: Optional[str] = None
    
    # Benefits and prizes
    prize_fund: Optional[str] = None
    benefits: Optional[List[str]] = None
    support_offered: Optional[List[str]] = None
    
    # Evaluation criteria
    explicit_criteria: Optional[List[str]] = None
    implied_preferences: Optional[List[str]] = None
    
    # Metadata
    confidence_score: Optional[float] = None
    parsing_timestamp: Optional[str] = None
    raw_content_length: Optional[int] = None


class ContentParser:
    """LLM-powered parser for extracting structured competition information."""
    
    def __init__(self, llm_client=None, config: Optional[Dict] = None):
        """
        Initialize the content parser.
        
        Args:
            llm_client: LLM client instance (OpenAI, Anthropic, etc.)
            config: Parser configuration settings
        """
        self.llm_client = llm_client
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
    
    def generate_extraction_prompt(self, content: str) -> str:
        """Generate the prompt template for competition information extraction."""
        
        prompt = f"""## Task: Extract structured competition information from website content

### Input Content:
{content}

### Extraction Requirements:
Please analyze the above content and extract the following structured information in JSON format:

{{
  "competition_basic_info": {{
    "name": "Competition name (or null if not found)",
    "organizer": "Main organizing body (or null if not found)",
    "partners": ["Partner 1", "Partner 2"] or null,
    "application_status": "Current status: open/closed/upcoming (or null if unclear)",
    "deadline": "Application deadline in any format found (or null if not mentioned)"
  }},
  "target_participants": {{
    "description": "Overall description of target participants (or null)",
    "criteria": ["Eligibility criterion 1", "Eligibility criterion 2"] or null
  }},
  "competition_focus": {{
    "stage_preference": "Preferred project stage: idea/MVP/prototype/seed/etc (or null)",
    "industry_focus": ["Industry 1", "Industry 2"] or null,
    "innovation_type": "Type of innovation preferred (or null)"
  }},
  "benefits_and_prizes": {{
    "prize_fund": "Total prize amount with currency (or null if not mentioned)",
    "benefits": ["Benefit 1", "Benefit 2"] or null,
    "support_offered": ["Support type 1", "Support type 2"] or null
  }},
  "evaluation_criteria": {{
    "explicit_criteria": ["Stated evaluation criterion 1", "Criterion 2"] or null,
    "implied_preferences": ["Inferred preference 1", "Preference 2"] or null
  }}
}}

### Extraction Guidelines:
1. Extract information exactly as presented in the source text
2. Use null for any field where information is not clearly available
3. For dates, preserve the original format found in the text
4. For monetary amounts, include the currency symbol/code as written
5. Focus on explicit information; only infer when patterns are very clear
6. If multiple pieces of similar information exist, include the most comprehensive
7. Maintain original terminology and phrasing where possible

### Output Format:
Respond with ONLY the JSON object, no additional text or explanation."""

        return prompt
    
    def parse_with_llm(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Use LLM to parse content and extract structured information.
        
        Args:
            content: Raw scraped content to parse
            
        Returns:
            Parsed information as dictionary or None if parsing fails
        """
        if not self.llm_client:
            self.logger.error("No LLM client configured for parsing")
            return None
        
        try:
            prompt = self.generate_extraction_prompt(content)
            
            # Call LLM API (implementation depends on your LLM client)
            response = self.llm_client.complete(prompt)
            
            # Parse JSON response
            parsed_data = json.loads(response.strip())
            
            self.logger.info("Successfully parsed content with LLM")
            return parsed_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            return None
        except Exception as e:
            self.logger.error(f"LLM parsing failed: {e}")
            return None
    
    def parse_with_rules(self, content: str) -> Dict[str, Any]:
        """
        Fallback rule-based parsing for basic information extraction.
        
        This method provides a backup when LLM parsing is unavailable,
        using regex patterns and keyword matching.
        """
        self.logger.info("Using rule-based parsing as fallback")
        
        parsed = {
            "competition_basic_info": {},
            "target_participants": {},
            "competition_focus": {},
            "benefits_and_prizes": {},
            "evaluation_criteria": {}
        }
        
        content_lower = content.lower()
        
        # Extract prize information
        prize_patterns = [
            r'£([\d,]+)',
            r'\$([\d,]+)',
            r'€([\d,]+)',
            r'([\d,]+)\s*pounds?',
            r'prize.*?([\d,]+)',
            r'funding.*?([\d,]+)'
        ]
        
        for pattern in prize_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                parsed["benefits_and_prizes"]["prize_fund"] = match.group(0)
                break
        
        # Extract deadline information
        deadline_patterns = [
            r'deadline.*?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'apply.*?by.*?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'close.*?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})'
        ]
        
        for pattern in deadline_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                parsed["competition_basic_info"]["deadline"] = match.group(1)
                break
        
        # Detect application status
        if any(phrase in content_lower for phrase in ['applications closed', 'deadline passed', 'no longer accepting']):
            parsed["competition_basic_info"]["application_status"] = "closed"
        elif any(phrase in content_lower for phrase in ['applications open', 'now accepting', 'apply now']):
            parsed["competition_basic_info"]["application_status"] = "open"
        elif any(phrase in content_lower for phrase in ['coming soon', 'opening soon', 'applications will open']):
            parsed["competition_basic_info"]["application_status"] = "upcoming"
        
        # Extract benefits
        benefits = []
        benefit_keywords = [
            'mentorship', 'networking', 'funding', 'investment', 'support',
            'guidance', 'resources', 'exposure', 'recognition', 'accelerator'
        ]
        
        for keyword in benefit_keywords:
            if keyword in content_lower:
                benefits.append(keyword.capitalize())
        
        if benefits:
            parsed["benefits_and_prizes"]["benefits"] = benefits[:5]  # Limit to top 5
        
        # Extract stage preferences
        stage_keywords = {
            'idea': ['idea stage', 'early idea', 'concept'],
            'mvp': ['mvp', 'minimum viable product', 'prototype'],
            'seed': ['seed stage', 'early stage', 'startup'],
            'growth': ['scaling', 'growth stage', 'expansion']
        }
        
        for stage, keywords in stage_keywords.items():
            if any(kw in content_lower for kw in keywords):
                parsed["competition_focus"]["stage_preference"] = stage
                break
        
        return parsed
    
    def validate_parsed_data(self, parsed_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score for parsed data based on completeness and quality.
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0
        total_weight = 0.0
        
        # Scoring weights for different information types
        weights = {
            "competition_basic_info": {
                "name": 0.15,
                "organizer": 0.10,
                "application_status": 0.15,
                "deadline": 0.20
            },
            "benefits_and_prizes": {
                "prize_fund": 0.15,
                "benefits": 0.10
            },
            "target_participants": {
                "criteria": 0.10
            },
            "competition_focus": {
                "stage_preference": 0.05
            }
        }
        
        for section, fields in weights.items():
            if section in parsed_data:
                for field, weight in fields.items():
                    total_weight += weight
                    if field in parsed_data[section] and parsed_data[section][field]:
                        score += weight
        
        return min(score / total_weight if total_weight > 0 else 0.0, 1.0)
    
    def parse_content(self, content: str) -> ParsedCompetitionInfo:
        """
        Main method to parse competition content using available methods.
        
        Args:
            content: Raw scraped content
            
        Returns:
            ParsedCompetitionInfo object with extracted data
        """
        self.logger.info(f"Starting content parsing for {len(content)} characters")
        
        # Try LLM parsing first
        parsed_data = None
        if self.llm_client:
            parsed_data = self.parse_with_llm(content)
        
        # Fallback to rule-based parsing
        if not parsed_data:
            self.logger.info("LLM parsing unavailable, using rule-based fallback")
            parsed_data = self.parse_with_rules(content)
        
        # Calculate confidence score
        confidence = self.validate_parsed_data(parsed_data)
        
        # Convert to structured object
        result = self._dict_to_parsed_info(parsed_data)
        result.confidence_score = confidence
        result.parsing_timestamp = datetime.now().isoformat()
        result.raw_content_length = len(content)
        
        self.logger.info(f"Parsing completed with confidence score: {confidence:.2f}")
        return result
    
    def _dict_to_parsed_info(self, data: Dict[str, Any]) -> ParsedCompetitionInfo:
        """Convert parsed dictionary to ParsedCompetitionInfo object."""
        
        basic = data.get("competition_basic_info", {})
        target = data.get("target_participants", {})
        focus = data.get("competition_focus", {})
        benefits = data.get("benefits_and_prizes", {})
        criteria = data.get("evaluation_criteria", {})
        
        return ParsedCompetitionInfo(
            name=basic.get("name"),
            organizer=basic.get("organizer"),
            partners=basic.get("partners"),
            application_status=basic.get("application_status"),
            deadline=basic.get("deadline"),
            
            target_description=target.get("description"),
            eligibility_criteria=target.get("criteria"),
            
            stage_preference=focus.get("stage_preference"),
            industry_focus=focus.get("industry_focus"),
            innovation_type=focus.get("innovation_type"),
            
            prize_fund=benefits.get("prize_fund"),
            benefits=benefits.get("benefits"),
            support_offered=benefits.get("support_offered"),
            
            explicit_criteria=criteria.get("explicit_criteria"),
            implied_preferences=criteria.get("implied_preferences")
        )
    
    def save_parsed_info(self, parsed_info: ParsedCompetitionInfo, output_path: str) -> None:
        """Save parsed information to JSON file."""
        
        # Convert to dictionary for JSON serialization
        data = {
            "competition_basic_info": {
                "name": parsed_info.name,
                "organizer": parsed_info.organizer,
                "partners": parsed_info.partners,
                "application_status": parsed_info.application_status,
                "deadline": parsed_info.deadline
            },
            "target_participants": {
                "description": parsed_info.target_description,
                "criteria": parsed_info.eligibility_criteria
            },
            "competition_focus": {
                "stage_preference": parsed_info.stage_preference,
                "industry_focus": parsed_info.industry_focus,
                "innovation_type": parsed_info.innovation_type
            },
            "benefits_and_prizes": {
                "prize_fund": parsed_info.prize_fund,
                "benefits": parsed_info.benefits,
                "support_offered": parsed_info.support_offered
            },
            "evaluation_criteria": {
                "explicit_criteria": parsed_info.explicit_criteria,
                "implied_preferences": parsed_info.implied_preferences
            },
            "metadata": {
                "confidence_score": parsed_info.confidence_score,
                "parsing_timestamp": parsed_info.parsing_timestamp,
                "raw_content_length": parsed_info.raw_content_length
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Parsed information saved to {output_path}")
    
    def save_to_competition_dir(self, parsed_info: ParsedCompetitionInfo, competition_name: str, base_dir: str = 'input') -> None:
        """Save parsed info to standardized competition directory structure."""
        from pathlib import Path
        
        output_dir = Path(base_dir) / competition_name / 'competition_info'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / 'parsed_competition_info.json'
        self.save_parsed_info(parsed_info, str(output_path))


class MonicaAIClient:
    """Monica AI client for LLM-powered content parsing."""
    
    def __init__(self, api_key: str, base_url: str = "https://openapi.monica.im/v1", model: str = "gpt-4.1"):
        from api.monica_client import MonicaClient
        self.client = MonicaClient(base_url, api_key, model)
        self.logger = logging.getLogger(__name__)
    
    def complete(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        """Send completion request to Monica AI."""
        try:
            return self.client.complete(prompt, temperature=temperature, max_tokens=max_tokens)
        except Exception as e:
            self.logger.error(f"Monica AI API call failed: {e}")
            raise

