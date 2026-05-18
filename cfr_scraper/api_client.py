"""
eCFR API Client for fetching Code of Federal Regulations data.
"""
import requests
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from .models import CFRTitle, CFRPart, CFRSection
import time

logger = logging.getLogger(__name__)


class ECFRClient:
    """Client for interacting with the eCFR API."""
    
    BASE_URL = "https://www.ecfr.gov/api/versioner/v1"
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the eCFR API client.
        
        Args:
            cache_dir: Optional directory for caching API responses
        """
        self.cache_dir = cache_dir
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FAA-Rules-Scraper/1.0'
        })
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make a request to the eCFR API with error handling and rate limiting.
        
        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            
        Returns:
            JSON response as dictionary
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Rate limiting - be respectful
            time.sleep(0.5)
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            raise
    
    def fetch_title_structure(self, title_number: int, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch the structure of a CFR title.
        
        Args:
            title_number: CFR title number (e.g., 14 for Aeronautics)
            date: Optional date in YYYY-MM-DD format (defaults to current)
            
        Returns:
            Title structure data
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        endpoint = f"/structure/{date}/title-{title_number}.json"
        return self._make_request(endpoint)
    
    def fetch_part(self, title_number: int, part_number: int, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific CFR part.
        
        Args:
            title_number: CFR title number
            part_number: Part number within the title
            date: Optional date in YYYY-MM-DD format
            
        Returns:
            Part data including all sections, or None if not found
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        endpoint = f"/full/{date}/title-{title_number}.json"
        data = self._make_request(endpoint)
        
        # Extract the specific part from the full title data
        return self._extract_part_from_title(data, part_number)
    
    def fetch_section(self, title_number: int, section_number: str, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific CFR section.
        
        Args:
            title_number: CFR title number
            section_number: Section number (e.g., "91.3")
            date: Optional date in YYYY-MM-DD format
            
        Returns:
            Section data, or None if not found
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Parse section number to get part
        part_number = int(section_number.split('.')[0])
        
        endpoint = f"/full/{date}/title-{title_number}.json"
        data = self._make_request(endpoint)
        
        return self._extract_section_from_title(data, section_number)
    
    def _extract_part_from_title(self, title_data: Dict[str, Any], part_number: int) -> Optional[Dict[str, Any]]:
        """Extract a specific part from title data."""
        # Navigate through the structure to find the part
        # This is a simplified version - actual structure may vary
        try:
            content_data = title_data.get('content', [])
            for item in content_data:
                if item.get('type') == 'part' and item.get('identifier') == str(part_number):
                    return item
            return None
        except Exception as e:
            logger.error(f"Error extracting part {part_number}: {e}")
            return None
    
    def _extract_section_from_title(self, title_data: Dict[str, Any], section_number: str) -> Optional[Dict[str, Any]]:
        """Extract a specific section from title data."""
        try:
            content_data = title_data.get('content', [])
            for item in content_data:
                if item.get('type') == 'section' and item.get('identifier') == section_number:
                    return item
            return None
        except Exception as e:
            logger.error(f"Error extracting section {section_number}: {e}")
            return None
    
    def parse_part_to_model(self, part_data: Dict[str, Any], title_number: int) -> CFRPart:
        """
        Parse API response data into a CFRPart model.
        
        Args:
            part_data: Raw part data from API
            title_number: CFR title number
            
        Returns:
            CFRPart object
        """
        part_number = int(part_data.get('identifier', '0'))
        part_name = part_data.get('label', '')
        
        part = CFRPart(
            part_number=part_number,
            part_name=part_name,
            title_number=title_number,
            authority=part_data.get('authority', ''),
            source=part_data.get('source', '')
        )
        
        # Parse sections
        sections_data = part_data.get('children', [])
        for section_data in sections_data:
            if section_data.get('type') == 'section':
                section = self._parse_section(section_data, part_number)
                if section:
                    part.sections.append(section)
        
        return part
    
    def _parse_section(self, section_data: Dict[str, Any], part_number: int) -> Optional[CFRSection]:
        """Parse section data into CFRSection model."""
        try:
            section_number = section_data.get('identifier', '')
            section_title = section_data.get('label', '')
            content = section_data.get('content', '')
            
            section = CFRSection(
                section_number=section_number,
                section_title=section_title,
                content=content,
                part_number=part_number
            )
            
            return section
        except Exception as e:
            logger.error(f"Error parsing section: {e}")
            return None
    
    def fetch_title_14_parts(self, part_range: Optional[tuple] = None) -> List[CFRPart]:
        """
        Fetch multiple parts from Title 14 (Aeronautics and Space).
        
        Args:
            part_range: Optional tuple (start, end) for part numbers to fetch
            
        Returns:
            List of CFRPart objects
        """
        if part_range is None:
            part_range = (1, 199)  # Common FAA parts
        
        parts = []
        for part_num in range(part_range[0], part_range[1] + 1):
            try:
                logger.info(f"Fetching Title 14, Part {part_num}")
                part_data = self.fetch_part(14, part_num)
                if part_data:
                    part = self.parse_part_to_model(part_data, 14)
                    parts.append(part)
            except Exception as e:
                logger.warning(f"Could not fetch Part {part_num}: {e}")
                continue
        
        return parts

# Made with Bob
