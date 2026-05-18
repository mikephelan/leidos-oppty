"""
Data models for FAA Orders.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class CFRReference:
    """Represents a CFR reference found in an order."""
    cfr_section: str  # e.g., "91.3"
    part_number: int  # e.g., 91
    section_number: str  # e.g., "3"
    context: str  # Surrounding text
    page_number: Optional[int] = None
    confidence: float = 1.0  # Confidence in the extraction
    
    def to_dict(self):
        return {
            'cfr_section': self.cfr_section,
            'part_number': self.part_number,
            'section_number': self.section_number,
            'context': self.context,
            'page_number': self.page_number,
            'confidence': self.confidence
        }


@dataclass
class FAAOrder:
    """Represents an FAA Order document."""
    order_number: str  # e.g., "8900.1"
    order_title: str
    file_path: str
    effective_date: Optional[datetime] = None
    extracted_text: Optional[str] = None
    cfr_references: List[CFRReference] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self):
        return {
            'order_number': self.order_number,
            'order_title': self.order_title,
            'file_path': self.file_path,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'extracted_text': self.extracted_text,
            'cfr_references': [ref.to_dict() for ref in self.cfr_references],
            'metadata': self.metadata
        }
    
    def add_cfr_reference(self, reference: CFRReference):
        """Add a CFR reference to this order."""
        self.cfr_references.append(reference)
    
    def get_unique_cfr_sections(self) -> List[str]:
        """Get unique CFR sections referenced in this order."""
        return list(set(ref.cfr_section for ref in self.cfr_references))


@dataclass
class CFROrderMapping:
    """Represents a mapping between a CFR section and an FAA Order."""
    cfr_section: str  # e.g., "91.3"
    order_number: str  # e.g., "8900.1"
    relationship_type: str  # "implements", "references", "clarifies", etc.
    confidence_score: float  # 0.0 to 1.0
    extraction_method: str  # "explicit_citation", "semantic_match", etc.
    context: Optional[str] = None  # Context from the order
    created_at: Optional[datetime] = None
    
    def to_dict(self):
        return {
            'cfr_section': self.cfr_section,
            'order_number': self.order_number,
            'relationship_type': self.relationship_type,
            'confidence_score': self.confidence_score,
            'extraction_method': self.extraction_method,
            'context': self.context,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Made with Bob
