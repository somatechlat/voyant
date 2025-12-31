"""
Voyant Scraper - LLM Selector Generation

AI-driven CSS/XPath selector generation using LLM providers.
"""
from typing import Dict, Any, List, Optional
import json
import os
import httpx


SELECTOR_PROMPT = """You are an expert web scraping assistant. Analyze the HTML and generate precise CSS or XPath selectors for data extraction.

USER REQUEST: {user_prompt}

HTML CONTENT (truncated):
```html
{html_content}
```

OUTPUT FORMAT (JSON only, no markdown):
{{
    "selectors": [
        {{
            "field": "<field_name>",
            "selector": "<css_or_xpath_selector>",
            "type": "css" | "xpath",
            "multiple": true | false
        }}
    ],
    "confidence": 0.0-1.0,
    "notes": "<any relevant notes>"
}}

Generate selectors that are:
1. Specific enough to target the right elements
2. Robust to minor HTML changes
3. Prefer id > class > tag hierarchy
"""


class LLMSelectorGenerator:
    """
    LLM-based selector generator for intelligent data extraction.
    
    Supports:
    - OpenAI GPT-4
    - Anthropic Claude
    - Ollama local models
    """
    
    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.provider = provider
        self.api_key = api_key or os.environ.get(f"{provider.upper()}_API_KEY")
        
        # Default models
        self.model = model or {
            "openai": "gpt-4-turbo-preview",
            "anthropic": "claude-3-sonnet-20240229",
            "ollama": "llama2"
        }.get(provider, "gpt-4")
    
    async def generate_selectors(
        self,
        html: str,
        user_prompt: str,
        max_html_length: int = 50000
    ) -> Dict[str, Any]:
        """
        Generate selectors using LLM.
        
        Args:
            html: Page HTML content
            user_prompt: What to extract (e.g., "product name and price")
            max_html_length: Max HTML chars to send to LLM
            
        Returns:
            Dict with selectors, confidence, notes
        """
        # Truncate HTML if needed
        if len(html) > max_html_length:
            html = html[:max_html_length] + "\n... [truncated]"
        
        prompt = SELECTOR_PROMPT.format(
            user_prompt=user_prompt,
            html_content=html
        )
        
        if self.provider == "openai":
            return await self._call_openai(prompt)
        elif self.provider == "anthropic":
            return await self._call_anthropic(prompt)
        elif self.provider == "ollama":
            return await self._call_ollama(prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    async def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a web scraping expert. Output only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2000
                },
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
    
    async def _call_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Call Anthropic API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": 2000,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            content = data["content"][0]["text"]
            return json.loads(content)
    
    async def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Call Ollama local API."""
        ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()
            return json.loads(data["response"])


class SelectorEngine:
    """
    Unified selector engine for CSS and XPath queries.
    """
    
    @staticmethod
    def extract_css(html: str, selector: str, multiple: bool = False) -> List[str]:
        """Extract using CSS selector."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        elements = soup.select(selector)
        
        if multiple:
            return [el.get_text(strip=True) for el in elements]
        elif elements:
            return [elements[0].get_text(strip=True)]
        return []
    
    @staticmethod
    def extract_xpath(html: str, xpath: str, multiple: bool = False) -> List[str]:
        """Extract using XPath selector."""
        from lxml import etree
        tree = etree.HTML(html)
        elements = tree.xpath(xpath)
        
        results = []
        for el in elements:
            if isinstance(el, str):
                results.append(el.strip())
            elif hasattr(el, 'text') and el.text:
                results.append(el.text.strip())
            else:
                results.append(etree.tostring(el, encoding='unicode', method='text').strip())
        
        if multiple:
            return results
        return results[:1] if results else []
    
    @staticmethod
    def apply_selectors(
        html: str, 
        selectors: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Apply a list of selectors to HTML.
        
        Args:
            html: HTML content
            selectors: List of selector definitions
            
        Returns:
            Dict mapping field names to extracted values
        """
        results = {}
        
        for sel in selectors:
            field = sel["field"]
            selector = sel["selector"]
            sel_type = sel.get("type", "css")
            multiple = sel.get("multiple", False)
            
            if sel_type == "css":
                values = SelectorEngine.extract_css(html, selector, multiple)
            else:
                values = SelectorEngine.extract_xpath(html, selector, multiple)
            
            results[field] = values if multiple else (values[0] if values else None)
        
        return results
