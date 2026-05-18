#!/usr/bin/env python3
"""
Process FAA Orders: extract text and find CFR references.

This script processes PDF files of FAA Orders, extracts text,
identifies CFR citations, and stores everything in the database.
"""
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

from order_processor.pdf_extractor import PDFExtractor
from order_processor.citation_parser import CitationParser
from order_processor.models import FAAOrder
from storage.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_order_pdf(
    pdf_path: str,
    order_number: str | None = None,
    db_path: str = "data/cfr_orders.db"
) -> bool:
    """
    Process a single FAA Order PDF.
    
    Args:
        pdf_path: Path to PDF file
        order_number: Optional order number (will be extracted if not provided)
        db_path: Path to database file
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Processing: {pdf_path}")
    
    try:
        # Extract text from PDF
        extractor = PDFExtractor()
        result = extractor.extract_with_metadata(pdf_path)
        
        text = result['text']
        metadata = result['metadata']
        
        logger.info(f"Extracted {len(text)} characters from {result['page_count']} pages")
        
        # Clean the text
        text = extractor.clean_text(text)
        
        # Extract order number if not provided
        if not order_number:
            order_number = extractor.extract_order_number(text)
            if not order_number:
                logger.warning("Could not extract order number from PDF")
                # Use filename as fallback
                order_number = Path(pdf_path).stem
        
        logger.info(f"Order number: {order_number}")
        
        # Parse CFR citations
        parser = CitationParser()
        references = parser.find_cfr_references(text)
        
        logger.info(f"Found {len(references)} CFR references")
        
        # Show most referenced sections
        if references:
            top_sections = parser.get_most_referenced_sections(references, top_n=5)
            logger.info("Most referenced sections:")
            for section, count in top_sections:
                logger.info(f"  §{section}: {count} times")
        
        # Create FAAOrder object
        order = FAAOrder(
            order_number=order_number,
            order_title=metadata.get('Title', f'FAA Order {order_number}'),
            file_path=pdf_path,
            extracted_text=text,
            cfr_references=references,
            metadata=metadata
        )
        
        # Store in database
        db = Database(db_path)
        try:
            order_id = db.store_faa_order(order)
            logger.info(f"Stored order in database (ID: {order_id})")
            return True
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {e}")
        return False


def process_orders_directory(
    directory: str,
    db_path: str = "data/cfr_orders.db",
    pattern: str = "*.pdf"
) -> tuple[int, int]:
    """
    Process all PDF files in a directory.
    
    Args:
        directory: Directory containing PDF files
        db_path: Path to database file
        pattern: File pattern to match (default: *.pdf)
        
    Returns:
        Tuple of (successful_count, failed_count)
    """
    dir_path = Path(directory)
    
    if not dir_path.exists():
        logger.error(f"Directory not found: {directory}")
        return 0, 0
    
    pdf_files = list(dir_path.glob(pattern))
    logger.info(f"Found {len(pdf_files)} PDF files in {directory}")
    
    successful = 0
    failed = 0
    
    for pdf_file in pdf_files:
        if process_order_pdf(str(pdf_file), db_path=db_path):
            successful += 1
        else:
            failed += 1
    
    return successful, failed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Process FAA Order PDFs and extract CFR references'
    )
    
    parser.add_argument(
        'input',
        help='PDF file or directory to process'
    )
    
    parser.add_argument(
        '--order-number',
        help='Order number (for single file processing)'
    )
    
    parser.add_argument(
        '--db-path',
        type=str,
        default='data/cfr_orders.db',
        help='Path to database file (default: data/cfr_orders.db)'
    )
    
    parser.add_argument(
        '--pattern',
        type=str,
        default='*.pdf',
        help='File pattern for directory processing (default: *.pdf)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    input_path = Path(args.input)
    
    try:
        if input_path.is_file():
            # Process single file
            success = process_order_pdf(
                str(input_path),
                order_number=args.order_number,
                db_path=args.db_path
            )
            return 0 if success else 1
            
        elif input_path.is_dir():
            # Process directory
            successful, failed = process_orders_directory(
                str(input_path),
                db_path=args.db_path,
                pattern=args.pattern
            )
            
            logger.info(f"\nProcessing complete:")
            logger.info(f"  Successful: {successful}")
            logger.info(f"  Failed: {failed}")
            
            return 0 if failed == 0 else 1
            
        else:
            logger.error(f"Input path not found: {args.input}")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())

# Made with Bob
