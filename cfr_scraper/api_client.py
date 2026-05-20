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
            'User-Agent': 'FAA-Rules-Scraper/1.0',
            'Accept': 'application/json'
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
    
    def _get_latest_available_date(self, title_number: int) -> str:
        """
        Get the latest available date for a CFR title.
        
        The eCFR API uses January 1st dates for structure/full endpoints.
        We'll try the current year first, then fall back to previous years.
        
        Args:
            title_number: CFR title number
            
        Returns:
            Date string in YYYY-MM-DD format
        """
        current_year = datetime.now().year
        
        # Try current year and previous years
        for year in [current_year, current_year - 1, current_year - 2]:
            date_str = f"{year}-01-01"
            try:
                # Test if this date works with the structure endpoint
                endpoint = f"/structure/{date_str}/title-{title_number}.json"
                test_url = f"{self.BASE_URL}{endpoint}"
                response = self.session.get(test_url, timeout=10)
                
                if response.status_code == 200:
                    logger.info(f"Using date {date_str} for Title {title_number}")
                    return date_str
            except Exception:
                continue
        
        # Fallback to a known good date
        fallback = "2024-01-01"
        logger.warning(f"Could not determine latest date for title {title_number}, using fallback: {fallback}")
        return fallback
    
    def fetch_title_structure(self, title_number: int, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch the structure of a CFR title.
        
        Args:
            title_number: CFR title number (e.g., 14 for Aeronautics)
            date: Optional date in YYYY-MM-DD format (defaults to latest available)
            
        Returns:
            Title structure data
        """
        # Use the latest available date by not specifying a date
        # The eCFR API will return the most recent version
        if date is None:
            # Query for latest available date first
            date = self._get_latest_available_date(title_number)
        
        endpoint = f"/structure/{date}/title-{title_number}.json"
        return self._make_request(endpoint)
    
    def fetch_part(self, title_number: int, part_number: int, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific CFR part from the structure endpoint.
        
        The eCFR API v1 structure endpoint includes section text, so we can use it directly
        without needing to fetch the full content (which is too large for Title 14).
        
        Args:
            title_number: CFR title number
            part_number: Part number within the title
            date: Optional date in YYYY-MM-DD format (defaults to latest available)
            
        Returns:
            Part data including all sections, or None if not found
        """
        if date is None:
            # Get the latest available date for this title
            date = self._get_latest_available_date(title_number)
        
        # Fetch the structure which includes section text
        try:
            structure_endpoint = f"/structure/{date}/title-{title_number}.json"
            structure_data = self._make_request(structure_endpoint)
            
            # Find and extract the part from the structure
            part_structure = self._extract_part_from_full_title(structure_data, part_number)
            if not part_structure:
                logger.info(f"Part {part_number} not found in Title {title_number} structure")
                return None
            
            logger.info(f"Found Part {part_number} with structure data")
            
            # The structure data already contains the text content we need
            return part_structure
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"Part {part_number} not found (may not exist)")
                return None
            raise
    
    def fetch_section(self, title_number: int, section_number: str, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific CFR section.
        
        Args:
            title_number: CFR title number
            section_number: Section number (e.g., "91.3")
            date: Optional date in YYYY-MM-DD format (defaults to latest available)
            
        Returns:
            Section data, or None if not found
        """
        if date is None:
            # Get the latest available date for this title
            date = self._get_latest_available_date(title_number)
        
        # Parse section number to get part
        part_number = int(section_number.split('.')[0])
        
        endpoint = f"/full/{date}/title-{title_number}.json"
        data = self._make_request(endpoint)
        
        return self._extract_section_from_title(data, section_number)
    
    def _find_part_path(self, structure_data: Dict[str, Any], part_number: int, current_path: str = "") -> Optional[str]:
        """
        Find the API path to a specific part in the structure.
        Returns a path like '/chapter-I/subchapter-A' or '/chapter-I'
        """
        node_type = structure_data.get('type', '')
        identifier = structure_data.get('identifier', '')
        
        # Build current path based on node type
        if node_type == 'chapter':
            current_path += f"/chapter-{identifier}"
        elif node_type == 'subchapter':
            current_path += f"/subchapter-{identifier}"
        elif node_type == 'part':
            # Check if this is the part we're looking for
            part_id = identifier.replace('part-', '').split('-')[-1]
            try:
                if int(part_id) == part_number:
                    return current_path  # Return path to parent (chapter/subchapter)
            except (ValueError, AttributeError):
                pass
        
        # Recursively search children
        for child in structure_data.get('children', []):
            result = self._find_part_path(child, part_number, current_path)
            if result is not None:
                return result
        
        return None
    
    def _fetch_part_by_sections(self, title_number: int, part_number: int, date: str, part_structure: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Build part data by fetching individual sections.
        This is the most reliable method for the eCFR API.
        """
        logger.info(f"Building Part {part_number} from individual sections")
        
        # Extract section identifiers from structure
        sections = self._extract_children_recursive(part_structure, 'section')
        
        if not sections:
            logger.warning(f"No sections found in Part {part_number}")
            return None
        
        logger.info(f"Found {len(sections)} sections in Part {part_number}")
        
        # Create a part data structure
        part_data = {
            'type': 'part',
            'identifier': str(part_number),
            'label': part_structure.get('label', f'Part {part_number}'),
            'reserved': part_structure.get('reserved', {}),
            'children': []
        }
        
        # Fetch each section individually
        for i, section_struct in enumerate(sections, 1):
            section_id = section_struct.get('identifier', '')
            if section_id:
                try:
                    # The section identifier format is like "14.91.1" - we need just the section part
                    # Format: title-{title}.{part}.{section}
                    section_endpoint = f"/full/{date}/title-{title_number}/section-{section_id}.json"
                    logger.debug(f"Fetching section {i}/{len(sections)}: {section_id}")
                    section_data = self._make_request(section_endpoint)
                    part_data['children'].append(section_data)
                except Exception as e:
                    logger.warning(f"Could not fetch section {section_id}: {e}")
                    # Add the structure data as fallback
                    part_data['children'].append(section_struct)
                    continue
        
        logger.info(f"Successfully built Part {part_number} with {len(part_data['children'])} sections")
        return part_data if part_data['children'] else None
    
    def _extract_part_from_full_title(self, title_data: Dict[str, Any], part_number: int) -> Optional[Dict[str, Any]]:
        """Extract a specific part from full title data."""
        def search_for_part(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            # Check if this node is the part we're looking for
            if node.get('type') == 'part':
                identifier = node.get('identifier', '')
                # identifier might be "91" or "part-91"
                part_id = identifier.replace('part-', '').split('-')[-1]
                try:
                    if int(part_id) == part_number:
                        return node
                except (ValueError, AttributeError):
                    pass
            
            # Recursively search children
            for child in node.get('children', []):
                result = search_for_part(child)
                if result:
                    return result
            return None
        
        return search_for_part(title_data)
    
    def _extract_children_recursive(self, node: Dict[str, Any], target_type: str = 'section') -> List[Dict[str, Any]]:
        """
        Recursively extract children of a specific type from a node.
        
        Args:
            node: The node to search
            target_type: The type of children to extract (e.g., 'section', 'part')
            
        Returns:
            List of matching children
        """
        results = []
        
        # Check if this node matches
        if node.get('type') == target_type:
            results.append(node)
        
        # Recursively check children
        children = node.get('children', [])
        for child in children:
            results.extend(self._extract_children_recursive(child, target_type))
        
        return results
    
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
        # Extract part number from identifier or label
        identifier = part_data.get('identifier', '')
        if identifier:
            # identifier might be like "14" or "part-91"
            part_number = int(identifier.replace('part-', '').split('-')[-1])
        else:
            part_number = 0
        
        part_name = part_data.get('label', '').replace('PART ', '').strip()
        
        # Handle reserved field which can be a dict or boolean
        reserved_data = part_data.get('reserved', {})
        if isinstance(reserved_data, dict):
            authority = reserved_data.get('authority', '')
            source = reserved_data.get('source', '')
        else:
            authority = ''
            source = ''
        
        part = CFRPart(
            part_number=part_number,
            part_name=part_name,
            title_number=title_number,
            authority=authority,
            source=source
        )
        
        # Recursively extract all sections from the part structure
        sections_data = self._extract_children_recursive(part_data, 'section')
        
        for section_data in sections_data:
            section = self._parse_section(section_data, part_number)
            if section:
                part.sections.append(section)
        
        logger.info(f"Parsed Part {part_number} with {len(part.sections)} sections")
        
        return part
    
    def _parse_section(self, section_data: Dict[str, Any], part_number: int) -> Optional[CFRSection]:
        """Parse section data into CFRSection model."""
        try:
            # Extract section number from identifier (e.g., "14.91.1" -> "91.1")
            identifier = section_data.get('identifier', '')
            section_number = identifier.split('.')[-2] + '.' + identifier.split('.')[-1] if '.' in identifier else identifier
            
            # Get label and remove section prefix
            section_title = section_data.get('label', '').replace('§', '').strip()
            
            # Extract text content from the structure
            content_parts = []
            
            # Get direct text content
            if 'text' in section_data:
                content_parts.append(section_data['text'])
            
            # Get content from children (paragraphs, etc.)
            children = section_data.get('children', [])
            for child in children:
                if 'text' in child:
                    content_parts.append(child['text'])
            
            content = '\n\n'.join(content_parts)
            
            section = CFRSection(
                section_number=section_number,
                section_title=section_title,
                content=content,
                part_number=part_number
            )
            
            return section
        except Exception as e:
            logger.error(f"Error parsing section: {e}")
            logger.debug(f"Section data: {section_data}")
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
