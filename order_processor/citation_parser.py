"""
Parse CFR citations from FAA Order text.
"""
import re
import logging
from typing import List, Optional, Tuple
from .models import CFRReference

logger = logging.getLogger(__name__)


class CitationParser:
    """Parse CFR citations from text."""
    
    # Regex patterns for different CFR citation formats
    CFR_PATTERNS = [
        # 14 CFR §91.3 or 14 CFR 91.3
        (r'14\s+CFR\s+(?:§\s*)?(\d+)\.(\d+)(?:\(([a-z0-9]+)\))?', 'explicit_title'),
        
        # 14 C.F.R. §91.3 or 14 C.F.R. 91.3
        (r'14\s+C\.F\.R\.\s+(?:§\s*)?(\d+)\.(\d+)(?:\(([a-z0-9]+)\))?', 'explicit_title'),
        
        # §91.3 or § 91.3 (when context is clear it's Title 14)
        (r'§\s*(\d+)\.(\d+)(?:\(([a-z0-9]+)\))?', 'section_symbol'),
        
        # Part 91, section 91.3
        (r'[Pp]art\s+(\d+),?\s+[Ss]ection\s+(\d+)\.(\d+)', 'part_section'),
        
        # section 91.3 (when part is clear from context)
        (r'[Ss]ection\s+(\d+)\.(\d+)(?:\(([a-z0-9]+)\))?', 'section_only'),
    ]
    
    def __init__(self, default_title: int = 14):
        """
        Initialize citation parser.
        
        Args:
            default_title: Default CFR title number (14 for FAA)
        """
        self.default_title = default_title
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), pattern_type)
            for pattern, pattern_type in self.CFR_PATTERNS
        ]
    
    def find_cfr_references(
        self,
        text: str,
        context_window: int = 100
    ) -> List[CFRReference]:
        """
        Find all CFR references in text.
        
        Args:
            text: Text to search for CFR references
            context_window: Number of characters to include as context
            
        Returns:
            List of CFRReference objects
        """
        references = []
        seen_refs = set()  # Track unique references
        
        for pattern, pattern_type in self.compiled_patterns:
            for match in pattern.finditer(text):
                try:
                    ref = self._create_reference(match, text, pattern_type, context_window)
                    
                    # Avoid duplicates
                    ref_key = (ref.cfr_section, ref.context[:50])
                    if ref_key not in seen_refs:
                        references.append(ref)
                        seen_refs.add(ref_key)
                        
                except Exception as e:
                    logger.warning(f"Error parsing reference at position {match.start()}: {e}")
                    continue
        
        return references
    
    def _create_reference(
        self,
        match: re.Match,
        text: str,
        pattern_type: str,
        context_window: int
    ) -> CFRReference:
        """Create a CFRReference from a regex match."""
        
        # Extract part and section numbers based on pattern type
        if pattern_type in ['explicit_title', 'section_symbol', 'section_only']:
            part_num = int(match.group(1))
            section_num = match.group(2)
        elif pattern_type == 'part_section':
            part_num = int(match.group(1))
            section_num = match.group(3)
        else:
            raise ValueError(f"Unknown pattern type: {pattern_type}")
        
        # Build section identifier
        cfr_section = f"{part_num}.{section_num}"
        
        # Extract context
        start = max(0, match.start() - context_window)
        end = min(len(text), match.end() + context_window)
        context = text[start:end].strip()
        
        # Determine confidence based on pattern type
        confidence = self._calculate_confidence(pattern_type, match, text)
        
        return CFRReference(
            cfr_section=cfr_section,
            part_number=part_num,
            section_number=section_num,
            context=context,
            confidence=confidence
        )
    
    def _calculate_confidence(
        self,
        pattern_type: str,
        match: re.Match,
        text: str
    ) -> float:
        """
        Calculate confidence score for a CFR reference.
        
        Args:
            pattern_type: Type of pattern that matched
            match: Regex match object
            text: Full text
            
        Returns:
            Confidence score between 0 and 1
        """
        # Base confidence by pattern type
        confidence_map = {
            'explicit_title': 1.0,  # "14 CFR §91.3" is unambiguous
            'section_symbol': 0.95,  # "§91.3" is very likely CFR
            'part_section': 0.9,     # "Part 91, section 91.3" is clear
            'section_only': 0.7,     # "section 91.3" needs context
        }
        
        base_confidence = confidence_map.get(pattern_type, 0.5)
        
        # Adjust based on context
        context_start = max(0, match.start() - 50)
        context_end = min(len(text), match.end() + 50)
        context = text[context_start:context_end].lower()
        
        # Boost confidence if aviation-related terms are nearby
        aviation_terms = ['aircraft', 'pilot', 'flight', 'aviation', 'faa', 'airspace']
        if any(term in context for term in aviation_terms):
            base_confidence = min(1.0, base_confidence + 0.05)
        
        return base_confidence
    
    def extract_part_numbers(self, text: str) -> List[int]:
        """
        Extract all CFR part numbers mentioned in text.
        
        Args:
            text: Text to search
            
        Returns:
            List of unique part numbers
        """
        part_pattern = re.compile(r'[Pp]art\s+(\d+)', re.IGNORECASE)
        parts = set()
        
        for match in part_pattern.finditer(text):
            try:
                part_num = int(match.group(1))
                # Filter to reasonable CFR part numbers (1-1999)
                if 1 <= part_num <= 1999:
                    parts.add(part_num)
            except ValueError:
                continue
        
        return sorted(list(parts))
    
    def group_references_by_part(
        self,
        references: List[CFRReference]
    ) -> dict[int, List[CFRReference]]:
        """
        Group CFR references by part number.
        
        Args:
            references: List of CFR references
            
        Returns:
            Dictionary mapping part numbers to lists of references
        """
        grouped = {}
        for ref in references:
            if ref.part_number not in grouped:
                grouped[ref.part_number] = []
            grouped[ref.part_number].append(ref)
        
        return grouped
    
    def get_most_referenced_sections(
        self,
        references: List[CFRReference],
        top_n: int = 10
    ) -> List[Tuple[str, int]]:
        """
        Get the most frequently referenced CFR sections.
        
        Args:
            references: List of CFR references
            top_n: Number of top sections to return
            
        Returns:
            List of (section_number, count) tuples
        """
        section_counts = {}
        for ref in references:
            section_counts[ref.cfr_section] = section_counts.get(ref.cfr_section, 0) + 1
        
        # Sort by count descending
        sorted_sections = sorted(
            section_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_sections[:top_n]
    
    def validate_section_format(self, section_number: str) -> bool:
        """
        Validate that a section number is in correct format.
        
        Args:
            section_number: Section number to validate (e.g., "91.3")
            
        Returns:
            True if valid format, False otherwise
        """
        pattern = re.compile(r'^\d+\.\d+$')
        return bool(pattern.match(section_number))

# Made with Bob
