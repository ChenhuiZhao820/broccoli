#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Monica API Client Module

Provides functionality for interacting with Monica API.
"""

import time
import requests
import logging
from typing import Dict, Any, Tuple, Optional


class MonicaClient:
    """Monica API client class providing API call functionality"""
    
    def __init__(self, base_url: str, api_key: str, model: str):
        """
        Initialize Monica API client
        
        Args:
            base_url: API base URL
            api_key: API key
            model: Model name
        """
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger(__name__)
    
    def calculate_backoff_delay(self, attempt: int, base_delay: int, max_delay: int = 300) -> int:
        """
        Calculate exponential backoff delay time
        
        Args:
            attempt: Current attempt number (starting from 0)
            base_delay: Base delay time in seconds
            max_delay: Maximum delay time in seconds
            
        Returns:
            int: Delay time in seconds
        """
        # Exponential backoff: delay = base_delay * (2 ^ attempt)
        delay = base_delay * (2 ** attempt)
        # Limit maximum delay time
        return min(delay, max_delay)
    
    def complete(self, prompt: str, retry_attempts: int = 3, retry_delay: int = 5, 
                temperature: float = 0.7, max_tokens: int = 4000) -> str:
        """
        Call Monica API for text completion
        
        Args:
            prompt: Input prompt
            retry_attempts: Number of retry attempts
            retry_delay: Base retry delay in seconds
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            str: API response content
            
        Raises:
            Exception: When API call fails after all retry attempts
        """
        content, elapsed_time = self.call_api(prompt, retry_attempts, retry_delay, temperature, max_tokens)
        if content is None:
            raise Exception(f"Monica API call failed after {retry_attempts} attempts")
        return content
    
    def call_api(self, prompt: str, retry_attempts: int = 3, retry_delay: int = 5,
                temperature: float = 0.7, max_tokens: int = 4000) -> Tuple[Optional[str], float]:
        """
        Call Monica API with retry logic
        
        Args:
            prompt: Input prompt
            retry_attempts: Number of retry attempts
            retry_delay: Base retry delay in seconds
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Tuple[Optional[str], float]: API response content and elapsed time in seconds, 
                                       content is None if failed
        """
        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        url = f"{self.base_url}/chat/completions"
        
        start_time = time.time()
        
        for attempt in range(retry_attempts):
            try:
                self.logger.info(f"Calling Monica API (model: {self.model}, attempt: {attempt + 1}/{retry_attempts})")
                response = requests.post(url, headers=self.headers, json=data, verify=False, timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get('choices', [{}])[0].get('message', {}).get('content')
                    if content:
                        elapsed_time = time.time() - start_time
                        self.logger.info(f"API call successful, elapsed time: {elapsed_time:.2f}s")
                        return content, elapsed_time
                    else:
                        self.logger.error(f"API response missing content: {result}")
                        
                elif response.status_code == 429:
                    # Rate limit error, use exponential backoff
                    self.logger.warning(f"Hit API rate limit (429), will retry with exponential backoff")
                    
                elif response.status_code >= 500:
                    # Server error, use exponential backoff
                    self.logger.error(f"Server error (status code: {response.status_code}): {response.text}")
                    
                else:
                    # Other errors, may not need retry
                    self.logger.error(f"API call failed (status code: {response.status_code}): {response.text}")
                    if 400 <= response.status_code < 500:
                        # Client error, usually no need to retry
                        elapsed_time = time.time() - start_time
                        return None, elapsed_time
                
            except requests.exceptions.Timeout as e:
                self.logger.error(f"API call timeout: {e}")
            except requests.exceptions.ConnectionError as e:
                self.logger.error(f"API connection error: {e}")
            except Exception as e:
                self.logger.error(f"API call exception: {e}")
            
            if attempt < retry_attempts - 1:
                # Calculate exponential backoff delay
                backoff_delay = self.calculate_backoff_delay(attempt, retry_delay)
                self.logger.info(f"Will retry in {backoff_delay} seconds...")
                time.sleep(backoff_delay)
        
        elapsed_time = time.time() - start_time
        self.logger.error(f"API call still failed after {retry_attempts} attempts, total elapsed time: {elapsed_time:.2f}s")
        return None, elapsed_time