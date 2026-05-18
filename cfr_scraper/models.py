"""
Data models for CFR (Code of Federal Regulations) structure.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class CFRParagraph:
    """Represents a paragraph within a CFR section."""
    paragraph_id: str  # e.g., "(a)", "(1)", "(i)"
    content: str
    parent_section: Optional['CFRSection'] = None
    child_paragraphs: List['CFRParagraph'] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'paragraph_id': self.paragraph_id,
            'content': self.content,
            'child_paragraphs': [p.to_dict() for p in self.child_paragraphs]
        }


@dataclass
class CFRSection:
    """Represents a section within a CFR part."""
    section_number: str  # e.g., "91.3"
    section_title: str
    content: str
    part_number: int
    subpart_letter: Optional[str] = None
    paragraphs: List[CFRParagraph] = field(default_factory=list)
    cross_references: List[str] = field(default_factory=list)
    effective_date: Optional[datetime] = None
    
    def to_dict(self):
        return {
            'section_number': self.section_number,
            'section_title': self.section_title,
            'content': self.content,
            'part_number': self.part_number,
            'subpart_letter': self.subpart_letter,
            'paragraphs': [p.to_dict() for p in self.paragraphs],
            'cross_references': self.cross_references,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None
        }


@dataclass
class CFRSubpart:
    """Represents a subpart within a CFR part."""
    subpart_letter: str  # e.g., "A", "B"
    subpart_name: str
    part_number: int
    sections: List[CFRSection] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'subpart_letter': self.subpart_letter,
            'subpart_name': self.subpart_name,
            'part_number': self.part_number,
            'sections': [s.to_dict() for s in self.sections]
        }


@dataclass
class CFRPart:
    """Represents a part within a CFR title."""
    part_number: int
    part_name: str
    title_number: int
    chapter_number: Optional[str] = None
    subchapter_letter: Optional[str] = None
    authority: Optional[str] = None
    source: Optional[str] = None
    subparts: List[CFRSubpart] = field(default_factory=list)
    sections: List[CFRSection] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'part_number': self.part_number,
            'part_name': self.part_name,
            'title_number': self.title_number,
            'chapter_number': self.chapter_number,
            'subchapter_letter': self.subchapter_letter,
            'authority': self.authority,
            'source': self.source,
            'subparts': [s.to_dict() for s in self.subparts],
            'sections': [s.to_dict() for s in self.sections]
        }


@dataclass
class CFRSubchapter:
    """Represents a subchapter within a CFR chapter."""
    subchapter_letter: str
    subchapter_name: str
    chapter_number: str
    parts: List[CFRPart] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'subchapter_letter': self.subchapter_letter,
            'subchapter_name': self.subchapter_name,
            'chapter_number': self.chapter_number,
            'parts': [p.to_dict() for p in self.parts]
        }


@dataclass
class CFRChapter:
    """Represents a chapter within a CFR title."""
    chapter_number: str
    chapter_name: str
    title_number: int
    subchapters: List[CFRSubchapter] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'chapter_number': self.chapter_number,
            'chapter_name': self.chapter_name,
            'title_number': self.title_number,
            'subchapters': [s.to_dict() for s in self.subchapters]
        }


@dataclass
class CFRTitle:
    """Represents a title in the Code of Federal Regulations."""
    title_number: int
    title_name: str
    effective_date: Optional[datetime] = None
    source_url: Optional[str] = None
    chapters: List[CFRChapter] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'title_number': self.title_number,
            'title_name': self.title_name,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'source_url': self.source_url,
            'chapters': [c.to_dict() for c in self.chapters]
        }

# Made with Bob
