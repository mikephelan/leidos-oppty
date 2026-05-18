# Strategy for Programmatically Defining FAA Rules from eCFR

## Overview

This document outlines the strategy for scraping, parsing, and structuring FAA regulations from the Electronic Code of Federal Regulations (eCFR) website and associating them with FAA Orders.

## 1. Understanding the Data Sources

### eCFR Structure (https://www.ecfr.gov/)
- **Title 14 - Aeronautics and Space** is the primary FAA regulatory title
- Organized hierarchically:
  - **Chapters** (e.g., Chapter I - Federal Aviation Administration)
  - **Subchapters** (e.g., Subchapter A - Definitions and General Requirements)
  - **Parts** (e.g., Part 91 - General Operating and Flight Rules)
  - **Subparts** (e.g., Subpart A - General)
  - **Sections** (e.g., §91.3 - Responsibility and authority of the pilot in command)

### FAA Orders
- Policy documents, procedures, and guidance
- Often reference specific CFR sections
- Downloaded from: https://www.faa.gov/regulations_policies/orders_notices/

## 2. Recommended Architecture

### A. Data Model (Object-Oriented Approach)

```python
# Core Classes Structure

class CFRTitle:
    - title_number: int
    - title_name: str
    - chapters: List[CFRChapter]
    - effective_date: datetime
    - source_url: str

class CFRChapter:
    - chapter_number: str
    - chapter_name: str
    - subchapters: List[CFRSubchapter]
    - parent_title: CFRTitle

class CFRSubchapter:
    - subchapter_letter: str
    - subchapter_name: str
    - parts: List[CFRPart]
    - parent_chapter: CFRChapter

class CFRPart:
    - part_number: int
    - part_name: str
    - subparts: List[CFRSubpart]
    - sections: List[CFRSection]
    - parent_subchapter: CFRSubchapter
    - authority: str  # Legal authority citation
    - source: str     # Federal Register citation

class CFRSubpart:
    - subpart_letter: str
    - subpart_name: str
    - sections: List[CFRSection]
    - parent_part: CFRPart

class CFRSection:
    - section_number: str  # e.g., "91.3"
    - section_title: str
    - content: str  # Full text content
    - paragraphs: List[CFRParagraph]
    - parent_subpart: CFRSubpart
    - cross_references: List[str]  # References to other sections
    - effective_date: datetime

class CFRParagraph:
    - paragraph_id: str  # e.g., "(a)", "(1)", "(i)"
    - content: str
    - parent_section: CFRSection
    - child_paragraphs: List[CFRParagraph]  # For nested structure

class FAAOrder:
    - order_number: str  # e.g., "8900.1"
    - order_title: str
    - effective_date: datetime
    - file_path: str
    - related_cfr_sections: List[CFRSection]  # Associated regulations
    - extracted_text: str  # Full text from PDF
    - cfr_references: List[str]  # Extracted CFR citations

class CFROrderMapping:
    - cfr_section: CFRSection
    - faa_order: FAAOrder
    - relationship_type: str  # "implements", "references", "clarifies", etc.
    - confidence_score: float  # For ML-based associations
    - extraction_method: str  # "explicit_citation", "semantic_match", etc.
```

### B. Database Schema (Alternative/Complementary Approach)

```sql
-- For persistent storage and querying

CREATE TABLE cfr_titles (
    id INTEGER PRIMARY KEY,
    title_number INTEGER,
    title_name TEXT,
    effective_date DATE,
    source_url TEXT
);

CREATE TABLE cfr_parts (
    id INTEGER PRIMARY KEY,
    part_number INTEGER,
    part_name TEXT,
    chapter_id INTEGER,
    authority TEXT,
    source TEXT,
    FOREIGN KEY (chapter_id) REFERENCES cfr_chapters(id)
);

CREATE TABLE cfr_sections (
    id INTEGER PRIMARY KEY,
    section_number TEXT,
    section_title TEXT,
    content TEXT,
    part_id INTEGER,
    subpart_id INTEGER,
    effective_date DATE,
    FOREIGN KEY (part_id) REFERENCES cfr_parts(id),
    FOREIGN KEY (subpart_id) REFERENCES cfr_subparts(id)
);

CREATE TABLE faa_orders (
    id INTEGER PRIMARY KEY,
    order_number TEXT UNIQUE,
    order_title TEXT,
    effective_date DATE,
    file_path TEXT,
    extracted_text TEXT
);

CREATE TABLE cfr_order_mappings (
    id INTEGER PRIMARY KEY,
    cfr_section_id INTEGER,
    faa_order_id INTEGER,
    relationship_type TEXT,
    confidence_score REAL,
    extraction_method TEXT,
    FOREIGN KEY (cfr_section_id) REFERENCES cfr_sections(id),
    FOREIGN KEY (faa_order_id) REFERENCES faa_orders(id)
);

CREATE TABLE cfr_cross_references (
    id INTEGER PRIMARY KEY,
    source_section_id INTEGER,
    target_section_id INTEGER,
    reference_type TEXT,
    FOREIGN KEY (source_section_id) REFERENCES cfr_sections(id),
    FOREIGN KEY (target_section_id) REFERENCES cfr_sections(id)
);
```

## 3. Implementation Strategy

### Phase 1: eCFR Data Extraction

**Tools & Libraries:**
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `lxml` - Fast XML/HTML processing
- `selenium` (optional) - For JavaScript-heavy pages

**Approach:**

1. **API-First Strategy** (Recommended)
   - eCFR provides an API: https://www.ecfr.gov/developers/documentation/api/v1
   - Endpoints available for:
     - `/title/{title_number}` - Get title structure
     - `/title/{title_number}/part/{part_number}` - Get specific part
     - `/title/{title_number}/section/{section_number}` - Get specific section
   - Returns JSON or XML format
   - Much more reliable than web scraping

2. **Web Scraping Fallback**
   - Use if API is insufficient
   - Parse HTML structure of eCFR pages
   - Extract hierarchical structure
   - Handle pagination and navigation

**Example API Usage:**
```python
import requests

def fetch_cfr_part(title_number, part_number):
    """Fetch a CFR part using the eCFR API"""
    base_url = "https://www.ecfr.gov/api/versioner/v1"
    endpoint = f"/full/{year}/{month}/{day}/title-{title_number}.json"
    # Or use structure endpoint for hierarchy
    response = requests.get(f"{base_url}{endpoint}")
    return response.json()
```

### Phase 2: FAA Order Text Extraction

**Tools & Libraries:**
- `PyPDF2` or `pdfplumber` - PDF text extraction
- `pdfminer.six` - Advanced PDF parsing
- `pytesseract` - OCR for scanned PDFs (if needed)

**Approach:**
1. Extract text from downloaded PDFs
2. Parse document structure (sections, paragraphs)
3. Identify CFR citations using regex patterns
4. Store extracted text and metadata

**CFR Citation Patterns:**
```python
import re

CFR_PATTERNS = [
    r'\b14\s+CFR\s+(?:§\s*)?(\d+)\.(\d+)',  # 14 CFR §91.3
    r'\b14\s+C\.F\.R\.\s+(?:§\s*)?(\d+)\.(\d+)',  # 14 C.F.R. §91.3
    r'§\s*(\d+)\.(\d+)',  # §91.3 (when context is clear)
    r'Part\s+(\d+)',  # Part 91
]

def extract_cfr_references(text):
    """Extract all CFR references from text"""
    references = []
    for pattern in CFR_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        references.extend(matches)
    return references
```

### Phase 3: Association & Mapping

**Strategies for Linking Orders to CFR Sections:**

1. **Explicit Citation Matching** (High Confidence)
   - Parse CFR citations in order text
   - Direct mapping to CFR sections
   - Confidence: 95-100%

2. **Keyword/Topic Matching** (Medium Confidence)
   - Extract key terms from both sources
   - Use TF-IDF or similar for similarity
   - Confidence: 60-80%

3. **Semantic Similarity** (ML-Based)
   - Use embeddings (e.g., sentence-transformers)
   - Calculate cosine similarity
   - Confidence: 70-90%

4. **Manual Curation** (Ground Truth)
   - Subject matter expert review
   - Create training data for ML models
   - Confidence: 100%

### Phase 4: Rule Definition as Code

**Approach 1: Declarative JSON/YAML**
```yaml
# cfr_rules/part_91/section_91_3.yaml
section: "91.3"
title: "Responsibility and authority of the pilot in command"
part: 91
subpart: "A"
content: |
  (a) The pilot in command of an aircraft is directly responsible for, 
  and is the final authority as to, the operation of that aircraft.
  (b) In an in-flight emergency requiring immediate action, the pilot 
  in command may deviate from any rule of this part to the extent 
  required to meet that emergency.
  (c) Each pilot in command who deviates from a rule under paragraph 
  (b) of this section shall, upon the request of the Administrator, 
  send a written report of that deviation to the Administrator.
related_orders:
  - order: "8900.1"
    relationship: "implements"
    confidence: 0.95
cross_references:
  - "91.123"
  - "91.13"
effective_date: "2024-01-01"
```

**Approach 2: Python Domain-Specific Language (DSL)**
```python
# cfr_rules/part_91.py
from cfr_framework import Section, Rule, Requirement

section_91_3 = Section(
    number="91.3",
    title="Responsibility and authority of the pilot in command",
    rules=[
        Rule(
            id="91.3.a",
            text="The pilot in command is directly responsible for aircraft operation",
            requirements=[
                Requirement("pilot_in_command", "must_be_responsible"),
                Requirement("pilot_in_command", "has_final_authority")
            ]
        ),
        Rule(
            id="91.3.b",
            text="May deviate in emergency",
            conditions=["in_flight_emergency", "immediate_action_required"],
            allows=["deviation_from_rules"]
        ),
        Rule(
            id="91.3.c",
            text="Must report deviations",
            triggers=["deviation_under_91.3.b", "administrator_request"],
            requires=["written_report"]
        )
    ]
)
```

**Approach 3: Graph Database (Neo4j)**
```cypher
// Create CFR Section node
CREATE (s:CFRSection {
    number: '91.3',
    title: 'Responsibility and authority of the pilot in command',
    part: 91,
    content: '...'
})

// Create FAA Order node
CREATE (o:FAAOrder {
    number: '8900.1',
    title: 'Flight Standards Information Management System'
})

// Create relationship
CREATE (o)-[:IMPLEMENTS {confidence: 0.95}]->(s)

// Create cross-reference
MATCH (s1:CFRSection {number: '91.3'})
MATCH (s2:CFRSection {number: '91.123'})
CREATE (s1)-[:REFERENCES]->(s2)
```

## 4. Recommended Technology Stack

### Core Components
1. **Data Extraction**: Python with requests, BeautifulSoup, eCFR API
2. **PDF Processing**: pdfplumber or PyPDF2
3. **Storage**: 
   - SQLite (lightweight, embedded)
   - PostgreSQL (production-grade)
   - Neo4j (graph relationships)
4. **NLP/ML**: 
   - spaCy (entity recognition)
   - sentence-transformers (semantic similarity)
   - scikit-learn (classification)
5. **API/Interface**: FastAPI or Flask
6. **Version Control**: Git with DVC for data versioning

### Project Structure
```
leidos-oppty/
├── cfr_scraper/
│   ├── __init__.py
│   ├── api_client.py       # eCFR API client
│   ├── scraper.py          # Web scraping fallback
│   ├── parser.py           # Parse CFR structure
│   └── models.py           # Data models
├── order_processor/
│   ├── __init__.py
│   ├── pdf_extractor.py    # Extract text from PDFs
│   ├── citation_parser.py  # Find CFR references
│   └── models.py           # Order data models
├── mapping_engine/
│   ├── __init__.py
│   ├── explicit_matcher.py # Citation-based matching
│   ├── semantic_matcher.py # ML-based matching
│   └── confidence_scorer.py
├── storage/
│   ├── __init__.py
│   ├── database.py         # Database interface
│   └── schema.sql          # Database schema
├── rules_engine/
│   ├── __init__.py
│   ├── rule_loader.py      # Load rules from storage
│   ├── rule_validator.py   # Validate rule compliance
│   └── query_engine.py     # Query rules
├── api/
│   ├── __init__.py
│   └── endpoints.py        # REST API
├── data/
│   ├── cfr_raw/           # Raw eCFR data
│   ├── orders_raw/        # Raw order PDFs
│   ├── processed/         # Processed data
│   └── mappings/          # CFR-Order mappings
├── tests/
│   └── ...
├── download_faa_orders.py  # Existing script
├── download_cfr_data.py    # New: Download CFR data
├── process_orders.py       # New: Extract text from PDFs
├── create_mappings.py      # New: Link orders to CFR
└── requirements.txt
```

## 5. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Set up project structure
- [ ] Implement eCFR API client
- [ ] Create data models
- [ ] Set up database schema
- [ ] Download sample CFR data (Title 14, Parts 1-99)

### Phase 2: Data Extraction (Week 2-3)
- [ ] Implement PDF text extraction
- [ ] Parse CFR citations from orders
- [ ] Store extracted data in database
- [ ] Create data validation pipeline

### Phase 3: Mapping & Association (Week 3-4)
- [ ] Implement explicit citation matcher
- [ ] Build keyword-based matcher
- [ ] Integrate semantic similarity (optional)
- [ ] Create confidence scoring system

### Phase 4: Rules Engine (Week 4-5)
- [ ] Design rule representation format
- [ ] Implement rule loader
- [ ] Create query interface
- [ ] Build validation engine

### Phase 5: API & Interface (Week 5-6)
- [ ] Build REST API
- [ ] Create documentation
- [ ] Add search functionality
- [ ] Implement export features

## 6. Key Considerations

### Legal & Compliance
- **Copyright**: eCFR content is public domain (U.S. government work)
- **Terms of Service**: Review eCFR API terms
- **Attribution**: Cite sources appropriately
- **Updates**: CFR is updated regularly; implement versioning

### Technical Challenges
- **Volume**: Title 14 has 1000+ sections
- **Complexity**: Nested hierarchical structure
- **Ambiguity**: Some order-CFR relationships are implicit
- **Updates**: Both CFR and orders change over time
- **PDF Quality**: Some orders may be scanned images (OCR needed)

### Best Practices
- **Incremental Processing**: Process in batches
- **Caching**: Cache API responses
- **Error Handling**: Robust error handling for network/parsing issues
- **Logging**: Comprehensive logging for debugging
- **Testing**: Unit tests for parsers and matchers
- **Documentation**: Document data model and relationships

## 7. Quick Start Example

```python
# Example: Fetch and store a CFR section
from cfr_scraper import ECFRClient
from storage import Database

# Initialize
client = ECFRClient()
db = Database('cfr_orders.db')

# Fetch CFR Part 91
part_91 = client.fetch_part(title=14, part=91)

# Store in database
db.store_cfr_part(part_91)

# Process an order
from order_processor import PDFExtractor, CitationParser

extractor = PDFExtractor()
text = extractor.extract('faa_orders/001_Order_8900.1.pdf')

parser = CitationParser()
citations = parser.find_cfr_references(text)

# Create mappings
for citation in citations:
    db.create_mapping(
        order_id='8900.1',
        cfr_section=citation.section,
        relationship='references',
        confidence=citation.confidence
    )
```

## 8. Next Steps

1. **Review this strategy** with stakeholders
2. **Prioritize features** based on project requirements
3. **Set up development environment**
4. **Start with Phase 1** implementation
5. **Iterate based on feedback**

## Resources

- eCFR API Documentation: https://www.ecfr.gov/developers/documentation/api/v1
- eCFR Website: https://www.ecfr.gov/
- FAA Orders: https://www.faa.gov/regulations_policies/orders_notices/
- Title 14 CFR: https://www.ecfr.gov/current/title-14

---

**Document Version**: 1.0  
**Last Updated**: 2026-05-18  
**Author**: Bob (AI Assistant)