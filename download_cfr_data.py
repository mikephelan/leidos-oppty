#!/usr/bin/env python3
"""
Download CFR data from eCFR API and store in database.

This script fetches Title 14 (Aeronautics and Space) CFR data from the
eCFR API and stores it in the local SQLite database.
"""
import argparse
import logging
import sys
from pathlib import Path

from cfr_scraper.api_client import ECFRClient
from storage.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_cfr_parts(
    title_number: int,
    part_range: tuple,
    db_path: str = "data/cfr_orders.db"
):
    """
    Download CFR parts and store in database.
    
    Args:
        title_number: CFR title number (e.g., 14 for Aeronautics)
        part_range: Tuple of (start_part, end_part)
        db_path: Path to database file
    """
    logger.info(f"Starting CFR download for Title {title_number}, Parts {part_range[0]}-{part_range[1]}")
    
    # Initialize API client and database
    client = ECFRClient()
    db = Database(db_path)
    
    try:
        # Fetch parts
        parts = client.fetch_title_14_parts(part_range)
        
        logger.info(f"Successfully fetched {len(parts)} parts")
        
        # Store in database
        for part in parts:
            try:
                part_id = db.store_cfr_part(part)
                logger.info(f"Stored Part {part.part_number} (ID: {part_id})")
            except Exception as e:
                logger.error(f"Error storing Part {part.part_number}: {e}")
                continue
        
        logger.info("CFR download complete!")
        
    except Exception as e:
        logger.error(f"Error during CFR download: {e}")
        raise
    finally:
        db.close()


def download_specific_part(
    title_number: int,
    part_number: int,
    db_path: str = "data/cfr_orders.db"
):
    """
    Download a specific CFR part.
    
    Args:
        title_number: CFR title number
        part_number: Part number to download
        db_path: Path to database file
    """
    logger.info(f"Downloading Title {title_number}, Part {part_number}")
    
    client = ECFRClient()
    db = Database(db_path)
    
    try:
        # Fetch the part
        part_data = client.fetch_part(title_number, part_number)
        
        if not part_data:
            logger.error(f"Part {part_number} not found")
            return
        
        # Parse and store
        part = client.parse_part_to_model(part_data, title_number)
        part_id = db.store_cfr_part(part)
        
        logger.info(f"Successfully stored Part {part_number} (ID: {part_id})")
        
    except Exception as e:
        logger.error(f"Error downloading Part {part_number}: {e}")
        raise
    finally:
        db.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Download CFR data from eCFR API'
    )
    
    parser.add_argument(
        '--title',
        type=int,
        default=14,
        help='CFR title number (default: 14 for Aeronautics)'
    )
    
    parser.add_argument(
        '--part',
        type=int,
        help='Download a specific part number'
    )
    
    parser.add_argument(
        '--start-part',
        type=int,
        default=1,
        help='Start part number for range download (default: 1)'
    )
    
    parser.add_argument(
        '--end-part',
        type=int,
        default=199,
        help='End part number for range download (default: 199)'
    )
    
    parser.add_argument(
        '--db-path',
        type=str,
        default='data/cfr_orders.db',
        help='Path to database file (default: data/cfr_orders.db)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        if args.part:
            # Download specific part
            download_specific_part(args.title, args.part, args.db_path)
        else:
            # Download range of parts
            part_range = (args.start_part, args.end_part)
            download_cfr_parts(args.title, part_range, args.db_path)
        
        logger.info("Download completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())

# Made with Bob
