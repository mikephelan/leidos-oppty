"""
PDF text extraction for FAA Orders.
"""
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import re

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logging.warning("pdfplumber not available, falling back to PyPDF2")

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract text from PDF files."""
    
    def __init__(self, prefer_pdfplumber: bool = True):
        """
        Initialize PDF extractor.
        
        Args:
            prefer_pdfplumber: Prefer pdfplumber over PyPDF2 if available
        """
        self.prefer_pdfplumber = prefer_pdfplumber and PDFPLUMBER_AVAILABLE
        
        if not PDFPLUMBER_AVAILABLE and not PYPDF2_AVAILABLE:
            raise ImportError("Neither pdfplumber nor PyPDF2 is available. Install at least one.")
    
    def extract_text(self, pdf_path: str) -> str:
        """
        Extract all text from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text as string
        """
        if self.prefer_pdfplumber:
            return self._extract_with_pdfplumber(pdf_path)
        else:
            return self._extract_with_pypdf2(pdf_path)
    
    def extract_with_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text and metadata from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with 'text', 'metadata', and 'page_count'
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        result = {
            'text': '',
            'metadata': {},
            'page_count': 0,
            'file_size': path.stat().st_size
        }
        
        if self.prefer_pdfplumber:
            result.update(self._extract_with_pdfplumber_metadata(pdf_path))
        else:
            result.update(self._extract_with_pypdf2_metadata(pdf_path))
        
        return result
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """Extract text using pdfplumber."""
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError("pdfplumber is not available")
        
        try:
            text_parts = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            return '\n\n'.join(text_parts)
        except Exception as e:
            logger.error(f"Error extracting text with pdfplumber from {pdf_path}: {e}")
            raise
    
    def _extract_with_pdfplumber_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text and metadata using pdfplumber."""
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError("pdfplumber is not available")
        
        try:
            text_parts = []
            metadata = {}
            
            with pdfplumber.open(pdf_path) as pdf:
                metadata = pdf.metadata or {}
                page_count = len(pdf.pages)
                
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            return {
                'text': '\n\n'.join(text_parts),
                'metadata': metadata,
                'page_count': page_count
            }
        except Exception as e:
            logger.error(f"Error extracting with pdfplumber from {pdf_path}: {e}")
            raise
    
    def _extract_with_pypdf2(self, pdf_path: str) -> str:
        """Extract text using PyPDF2."""
        if not PYPDF2_AVAILABLE:
            raise ImportError("PyPDF2 is not available")
        
        try:
            text_parts = []
            reader = PdfReader(pdf_path)
            
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            return '\n\n'.join(text_parts)
        except Exception as e:
            logger.error(f"Error extracting text with PyPDF2 from {pdf_path}: {e}")
            raise
    
    def _extract_with_pypdf2_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text and metadata using PyPDF2."""
        if not PYPDF2_AVAILABLE:
            raise ImportError("PyPDF2 is not available")
        
        try:
            text_parts = []
            reader = PdfReader(pdf_path)
            
            metadata = reader.metadata or {}
            page_count = len(reader.pages)
            
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            return {
                'text': '\n\n'.join(text_parts),
                'metadata': {k: str(v) for k, v in metadata.items()},
                'page_count': page_count
            }
        except Exception as e:
            logger.error(f"Error extracting with PyPDF2 from {pdf_path}: {e}")
            raise
    
    def extract_order_number(self, text: str) -> Optional[str]:
        """
        Extract FAA order number from text.
        
        Args:
            text: Text to search
            
        Returns:
            Order number if found, None otherwise
        """
        # Common patterns for FAA order numbers
        patterns = [
            r'Order\s+(\d+\.\d+[A-Z]*)',  # Order 8900.1
            r'FAA\s+Order\s+(\d+\.\d+[A-Z]*)',  # FAA Order 8900.1
            r'Order\s+No\.\s+(\d+\.\d+[A-Z]*)',  # Order No. 8900.1
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted text by removing extra whitespace and formatting issues.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove multiple spaces
        text = re.sub(r' +', ' ', text)
        
        # Remove multiple newlines (keep max 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove page numbers (common pattern)
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        
        # Remove headers/footers (lines with only page numbers or dates)
        text = re.sub(r'\n\s*\d{1,3}\s*\n', '\n', text)
        
        return text.strip()

# Made with Bob
