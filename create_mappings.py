#!/usr/bin/env python3
"""
Create mappings between CFR sections and FAA Orders.

This script analyzes the CFR references found in FAA Orders and creates
explicit mappings in the database with confidence scores.
"""
import argparse
import logging
import sys
from typing import List, Dict, Any

from storage.database import Database
from order_processor.models import CFROrderMapping

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_explicit_mappings(db_path: str = "data/cfr_orders.db") -> int:
    """
    Create mappings based on explicit CFR citations in orders.
    
    Args:
        db_path: Path to database file
        
    Returns:
        Number of mappings created
    """
    logger.info("Creating explicit CFR-Order mappings...")
    
    db = Database(db_path)
    mappings_created = 0
    
    try:
        # Get all orders with CFR references
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT o.order_number, o.order_title
            FROM faa_orders o
            JOIN order_cfr_references r ON o.id = r.order_id
        """)
        
        orders = cursor.fetchall()
        logger.info(f"Found {len(orders)} orders with CFR references")
        
        for order_row in orders:
            order_number = order_row[0]
            
            # Get all CFR references for this order
            cursor.execute("""
                SELECT cfr_section, context, confidence
                FROM order_cfr_references r
                JOIN faa_orders o ON r.order_id = o.id
                WHERE o.order_number = ?
            """, (order_number,))
            
            references = cursor.fetchall()
            
            for ref_row in references:
                cfr_section = ref_row[0]
                context = ref_row[1]
                confidence = ref_row[2]
                
                try:
                    # Create mapping
                    db.create_mapping(
                        cfr_section_number=cfr_section,
                        order_number=order_number,
                        relationship_type='references',
                        confidence_score=confidence,
                        extraction_method='explicit_citation',
                        context=context
                    )
                    mappings_created += 1
                    
                except ValueError as e:
                    # CFR section might not be in database yet
                    logger.debug(f"Skipping {cfr_section} for {order_number}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error creating mapping for {cfr_section}: {e}")
                    continue
        
        logger.info(f"Created {mappings_created} explicit mappings")
        return mappings_created
        
    finally:
        db.close()


def analyze_mapping_statistics(db_path: str = "data/cfr_orders.db"):
    """
    Analyze and display mapping statistics.
    
    Args:
        db_path: Path to database file
    """
    logger.info("\nMapping Statistics:")
    logger.info("=" * 60)
    
    db = Database(db_path)
    
    try:
        cursor = db.conn.cursor()
        
        # Total mappings
        cursor.execute("SELECT COUNT(*) FROM cfr_order_mappings")
        total_mappings = cursor.fetchone()[0]
        logger.info(f"Total mappings: {total_mappings}")
        
        # Mappings by relationship type
        cursor.execute("""
            SELECT relationship_type, COUNT(*) as count
            FROM cfr_order_mappings
            GROUP BY relationship_type
            ORDER BY count DESC
        """)
        logger.info("\nMappings by relationship type:")
        for row in cursor.fetchall():
            logger.info(f"  {row[0]}: {row[1]}")
        
        # Average confidence score
        cursor.execute("SELECT AVG(confidence_score) FROM cfr_order_mappings")
        avg_confidence = cursor.fetchone()[0]
        logger.info(f"\nAverage confidence score: {avg_confidence:.3f}")
        
        # Most referenced CFR sections
        cursor.execute("""
            SELECT s.section_number, s.section_title, COUNT(*) as ref_count
            FROM cfr_order_mappings m
            JOIN cfr_sections s ON m.cfr_section_id = s.id
            GROUP BY s.section_number
            ORDER BY ref_count DESC
            LIMIT 10
        """)
        logger.info("\nTop 10 most referenced CFR sections:")
        for row in cursor.fetchall():
            logger.info(f"  §{row[0]}: {row[2]} orders - {row[1]}")
        
        # Orders with most CFR references
        cursor.execute("""
            SELECT o.order_number, o.order_title, COUNT(*) as ref_count
            FROM cfr_order_mappings m
            JOIN faa_orders o ON m.faa_order_id = o.id
            GROUP BY o.order_number
            ORDER BY ref_count DESC
            LIMIT 10
        """)
        logger.info("\nTop 10 orders with most CFR references:")
        for row in cursor.fetchall():
            logger.info(f"  {row[0]}: {row[2]} sections - {row[1]}")
        
    finally:
        db.close()


def export_mappings_to_json(
    db_path: str = "data/cfr_orders.db",
    output_file: str = "data/mappings/cfr_order_mappings.json"
):
    """
    Export mappings to JSON file.
    
    Args:
        db_path: Path to database file
        output_file: Output JSON file path
    """
    import json
    from pathlib import Path
    
    logger.info(f"Exporting mappings to {output_file}")
    
    db = Database(db_path)
    
    try:
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT 
                s.section_number,
                s.section_title,
                o.order_number,
                o.order_title,
                m.relationship_type,
                m.confidence_score,
                m.extraction_method,
                m.context
            FROM cfr_order_mappings m
            JOIN cfr_sections s ON m.cfr_section_id = s.id
            JOIN faa_orders o ON m.faa_order_id = o.id
            ORDER BY s.section_number, m.confidence_score DESC
        """)
        
        mappings = []
        for row in cursor.fetchall():
            mappings.append({
                'cfr_section': row[0],
                'cfr_title': row[1],
                'order_number': row[2],
                'order_title': row[3],
                'relationship_type': row[4],
                'confidence_score': row[5],
                'extraction_method': row[6],
                'context': row[7]
            })
        
        # Ensure output directory exists
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Write JSON
        with open(output_file, 'w') as f:
            json.dump(mappings, f, indent=2)
        
        logger.info(f"Exported {len(mappings)} mappings to {output_file}")
        
    finally:
        db.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Create and analyze CFR-Order mappings'
    )
    
    parser.add_argument(
        '--db-path',
        type=str,
        default='data/cfr_orders.db',
        help='Path to database file (default: data/cfr_orders.db)'
    )
    
    parser.add_argument(
        '--create',
        action='store_true',
        help='Create explicit mappings from citations'
    )
    
    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Analyze and display mapping statistics'
    )
    
    parser.add_argument(
        '--export',
        type=str,
        help='Export mappings to JSON file'
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
        if args.create:
            mappings_created = create_explicit_mappings(args.db_path)
            logger.info(f"\nSuccessfully created {mappings_created} mappings")
        
        if args.analyze:
            analyze_mapping_statistics(args.db_path)
        
        if args.export:
            export_mappings_to_json(args.db_path, args.export)
        
        if not (args.create or args.analyze or args.export):
            parser.print_help()
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())

# Made with Bob
