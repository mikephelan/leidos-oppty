"""
Database interface for storing and retrieving CFR and FAA Order data.
"""
import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from cfr_scraper.models import CFRPart, CFRSection, CFRSubpart
from order_processor.models import FAAOrder, CFRReference, CFROrderMapping

logger = logging.getLogger(__name__)


class Database:
    """SQLite database interface for CFR and FAA Orders."""
    
    def __init__(self, db_path: str = "data/cfr_orders.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: sqlite3.Connection
        self._ensure_db_directory()
        self._initialize_db()
    
    def _ensure_db_directory(self):
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def _initialize_db(self):
        """Initialize database with schema."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Read and execute schema
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, 'r') as f:
            schema = f.read()
        
        self.conn.executescript(schema)
        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    # CFR Part operations
    def store_cfr_part(self, part: CFRPart) -> int:
        """
        Store a CFR part and its sections in the database.
        
        Args:
            part: CFRPart object to store
            
        Returns:
            Part ID in database
        """
        cursor = self.conn.cursor()
        
        # Insert or update part
        cursor.execute("""
            INSERT INTO cfr_parts (part_number, part_name, title_number, authority, source)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(title_number, part_number) DO UPDATE SET
                part_name = excluded.part_name,
                authority = excluded.authority,
                source = excluded.source,
                updated_at = CURRENT_TIMESTAMP
        """, (part.part_number, part.part_name, part.title_number, part.authority, part.source))
        
        part_id = cursor.lastrowid
        if part_id == 0:
            # Get existing part_id
            cursor.execute("""
                SELECT id FROM cfr_parts WHERE title_number = ? AND part_number = ?
            """, (part.title_number, part.part_number))
            part_id = cursor.fetchone()[0]
        
        # Store sections
        for section in part.sections:
            self._store_cfr_section(section, part_id)
        
        self.conn.commit()
        logger.info(f"Stored CFR Part {part.part_number} with {len(part.sections)} sections")
        return part_id
    
    def _store_cfr_section(self, section: CFRSection, part_id: int):
        """Store a CFR section."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO cfr_sections (section_number, section_title, content, part_id, effective_date)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(part_id, section_number) DO UPDATE SET
                section_title = excluded.section_title,
                content = excluded.content,
                effective_date = excluded.effective_date,
                updated_at = CURRENT_TIMESTAMP
        """, (
            section.section_number,
            section.section_title,
            section.content,
            part_id,
            section.effective_date.isoformat() if section.effective_date else None
        ))
    
    def get_cfr_section(self, section_number: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a CFR section by section number.
        
        Args:
            section_number: Section number (e.g., "91.3")
            
        Returns:
            Section data as dictionary or None
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, p.part_number, p.part_name, p.title_number
            FROM cfr_sections s
            JOIN cfr_parts p ON s.part_id = p.id
            WHERE s.section_number = ?
        """, (section_number,))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_cfr_part_sections(self, title_number: int, part_number: int) -> List[Dict[str, Any]]:
        """
        Get all sections for a CFR part.
        
        Args:
            title_number: CFR title number
            part_number: Part number
            
        Returns:
            List of section dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*
            FROM cfr_sections s
            JOIN cfr_parts p ON s.part_id = p.id
            WHERE p.title_number = ? AND p.part_number = ?
            ORDER BY s.section_number
        """, (title_number, part_number))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # FAA Order operations
    def store_faa_order(self, order: FAAOrder) -> int:
        """
        Store an FAA Order in the database.
        
        Args:
            order: FAAOrder object to store
            
        Returns:
            Order ID in database
        """
        cursor = self.conn.cursor()
        
        metadata_json = json.dumps(order.metadata) if order.metadata else None
        
        cursor.execute("""
            INSERT INTO faa_orders (order_number, order_title, effective_date, file_path, extracted_text, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(order_number) DO UPDATE SET
                order_title = excluded.order_title,
                effective_date = excluded.effective_date,
                file_path = excluded.file_path,
                extracted_text = excluded.extracted_text,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
        """, (
            order.order_number,
            order.order_title,
            order.effective_date.isoformat() if order.effective_date else None,
            order.file_path,
            order.extracted_text,
            metadata_json
        ))
        
        order_id = cursor.lastrowid
        if order_id == 0:
            cursor.execute("SELECT id FROM faa_orders WHERE order_number = ?", (order.order_number,))
            order_id = cursor.fetchone()[0]
        
        # Store CFR references
        for ref in order.cfr_references:
            self._store_cfr_reference(ref, order_id)
        
        self.conn.commit()
        logger.info(f"Stored FAA Order {order.order_number} with {len(order.cfr_references)} references")
        return order_id
    
    def _store_cfr_reference(self, reference: CFRReference, order_id: int):
        """Store a CFR reference from an order."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO order_cfr_references 
            (order_id, cfr_section, part_number, section_number, context, page_number, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id,
            reference.cfr_section,
            reference.part_number,
            reference.section_number,
            reference.context,
            reference.page_number,
            reference.confidence
        ))
    
    def get_faa_order(self, order_number: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an FAA Order by order number.
        
        Args:
            order_number: Order number (e.g., "8900.1")
            
        Returns:
            Order data as dictionary or None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM faa_orders WHERE order_number = ?", (order_number,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        order_dict = dict(row)
        if order_dict.get('metadata'):
            order_dict['metadata'] = json.loads(order_dict['metadata'])
        
        return order_dict
    
    # Mapping operations
    def create_mapping(
        self,
        cfr_section_number: str,
        order_number: str,
        relationship_type: str,
        confidence_score: float,
        extraction_method: str,
        context: Optional[str] = None
    ) -> int:
        """
        Create a mapping between a CFR section and an FAA Order.
        
        Args:
            cfr_section_number: CFR section number
            order_number: FAA order number
            relationship_type: Type of relationship
            confidence_score: Confidence score (0-1)
            extraction_method: Method used to extract the mapping
            context: Optional context text
            
        Returns:
            Mapping ID
        """
        cursor = self.conn.cursor()
        
        # Get CFR section ID
        cursor.execute("""
            SELECT id FROM cfr_sections WHERE section_number = ?
        """, (cfr_section_number,))
        section_row = cursor.fetchone()
        if not section_row:
            raise ValueError(f"CFR section {cfr_section_number} not found")
        section_id = section_row[0]
        
        # Get order ID
        cursor.execute("""
            SELECT id FROM faa_orders WHERE order_number = ?
        """, (order_number,))
        order_row = cursor.fetchone()
        if not order_row:
            raise ValueError(f"FAA Order {order_number} not found")
        order_id = order_row[0]
        
        # Create mapping
        cursor.execute("""
            INSERT INTO cfr_order_mappings 
            (cfr_section_id, faa_order_id, relationship_type, confidence_score, extraction_method, context)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(cfr_section_id, faa_order_id, relationship_type) DO UPDATE SET
                confidence_score = excluded.confidence_score,
                extraction_method = excluded.extraction_method,
                context = excluded.context
        """, (section_id, order_id, relationship_type, confidence_score, extraction_method, context))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_mappings_for_section(self, section_number: str) -> List[Dict[str, Any]]:
        """Get all order mappings for a CFR section."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT m.*, o.order_number, o.order_title, s.section_number, s.section_title
            FROM cfr_order_mappings m
            JOIN cfr_sections s ON m.cfr_section_id = s.id
            JOIN faa_orders o ON m.faa_order_id = o.id
            WHERE s.section_number = ?
            ORDER BY m.confidence_score DESC
        """, (section_number,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_mappings_for_order(self, order_number: str) -> List[Dict[str, Any]]:
        """Get all CFR section mappings for an order."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT m.*, o.order_number, o.order_title, s.section_number, s.section_title
            FROM cfr_order_mappings m
            JOIN cfr_sections s ON m.cfr_section_id = s.id
            JOIN faa_orders o ON m.faa_order_id = o.id
            WHERE o.order_number = ?
            ORDER BY s.section_number
        """, (order_number,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # Search operations
    def search_cfr_sections(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Full-text search of CFR sections.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching sections
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, p.part_number, p.part_name
            FROM cfr_sections_fts fts
            JOIN cfr_sections s ON fts.rowid = s.id
            JOIN cfr_parts p ON s.part_id = p.id
            WHERE cfr_sections_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_faa_orders(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Full-text search of FAA Orders.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching orders
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT o.*
            FROM faa_orders_fts fts
            JOIN faa_orders o ON fts.rowid = o.id
            WHERE faa_orders_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        
        return [dict(row) for row in cursor.fetchall()]

# Made with Bob
