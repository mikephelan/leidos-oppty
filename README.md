# FAA Rules and Orders Database

A comprehensive system for scraping, parsing, and structuring FAA regulations from the Electronic Code of Federal Regulations (eCFR) and associating them with FAA Orders.

## Overview

This project implements the strategy outlined in `STRATEGY_FAA_RULES.md` to:

1. **Download CFR Data**: Fetch Title 14 (Aeronautics and Space) regulations from the eCFR API
2. **Process FAA Orders**: Extract text from PDF files and identify CFR citations
3. **Create Mappings**: Link CFR sections to FAA Orders with confidence scores
4. **Query and Search**: Provide tools to search and analyze the relationships

## Project Structure

```
leidos-oppty/
├── cfr_scraper/              # CFR data extraction
│   ├── __init__.py
│   ├── api_client.py         # eCFR API client
│   ├── models.py             # CFR data models
│   └── parser.py             # Parse CFR structure
├── order_processor/          # FAA Order processing
│   ├── __init__.py
│   ├── pdf_extractor.py      # Extract text from PDFs
│   ├── citation_parser.py    # Find CFR references
│   └── models.py             # Order data models
├── storage/                  # Database layer
│   ├── __init__.py
│   ├── database.py           # Database interface
│   └── schema.sql            # Database schema
├── data/                     # Data storage
│   ├── cfr_raw/             # Raw eCFR data
│   ├── orders_raw/          # Raw order PDFs
│   ├── processed/           # Processed data
│   └── mappings/            # CFR-Order mappings
├── download_faa_orders.py    # Download FAA Orders
├── download_cfr_data.py      # Download CFR data
├── process_orders.py         # Process order PDFs
├── create_mappings.py        # Create CFR-Order mappings
└── requirements.txt          # Python dependencies
```

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd leidos-oppty
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database (automatic on first run):
```bash
python download_cfr_data.py --help
```

## Usage

### 1. Download FAA Orders

First, download FAA Order PDFs:

```bash
python download_faa_orders.py
```

This will download orders to the `faa_orders/` directory.

### 2. Download CFR Data

Download CFR regulations from the eCFR API:

```bash
# Download all common FAA parts (1-199)
python download_cfr_data.py

# Download a specific part
python download_cfr_data.py --part 91

# Download a custom range
python download_cfr_data.py --start-part 61 --end-part 99
```

Options:
- `--title`: CFR title number (default: 14)
- `--part`: Download a specific part
- `--start-part`: Start of part range (default: 1)
- `--end-part`: End of part range (default: 199)
- `--db-path`: Database file path (default: data/cfr_orders.db)
- `--verbose`: Enable verbose logging

### 3. Process FAA Orders

Extract text and CFR references from order PDFs:

```bash
# Process a single PDF
python process_orders.py faa_orders/001_Order_8900.1.pdf

# Process all PDFs in a directory
python process_orders.py faa_orders/

# Specify order number manually
python process_orders.py faa_orders/001_Order_8900.1.pdf --order-number 8900.1
```

Options:
- `input`: PDF file or directory to process
- `--order-number`: Order number (for single file)
- `--db-path`: Database file path
- `--pattern`: File pattern for directory (default: *.pdf)
- `--verbose`: Enable verbose logging

### 4. Create Mappings

Create explicit mappings between CFR sections and FAA Orders:

```bash
# Create mappings from citations
python create_mappings.py --create

# Analyze mapping statistics
python create_mappings.py --analyze

# Export mappings to JSON
python create_mappings.py --export data/mappings/cfr_order_mappings.json

# Do all three
python create_mappings.py --create --analyze --export data/mappings/mappings.json
```

## Database Schema

The system uses SQLite with the following main tables:

- **cfr_titles**: CFR title information
- **cfr_parts**: CFR parts (e.g., Part 91)
- **cfr_sections**: Individual CFR sections (e.g., §91.3)
- **faa_orders**: FAA Order documents
- **order_cfr_references**: CFR citations found in orders
- **cfr_order_mappings**: Explicit mappings with confidence scores

Full-text search is enabled for both CFR sections and FAA Orders.

## Data Models

### CFR Models

- `CFRTitle`: Top-level CFR title
- `CFRChapter`: Chapter within a title
- `CFRSubchapter`: Subchapter within a chapter
- `CFRPart`: Part within a subchapter (e.g., Part 91)
- `CFRSubpart`: Subpart within a part
- `CFRSection`: Individual section (e.g., §91.3)
- `CFRParagraph`: Paragraph within a section

### Order Models

- `FAAOrder`: FAA Order document
- `CFRReference`: CFR citation found in an order
- `CFROrderMapping`: Mapping between CFR section and order

## Examples

### Query CFR Section

```python
from storage.database import Database

db = Database()

# Get a specific section
section = db.get_cfr_section("91.3")
print(f"§{section['section_number']}: {section['section_title']}")

# Search CFR sections
results = db.search_cfr_sections("pilot in command")
for result in results:
    print(f"§{result['section_number']}: {result['section_title']}")

db.close()
```

### Query FAA Order

```python
from storage.database import Database

db = Database()

# Get an order
order = db.get_faa_order("8900.1")
print(f"Order {order['order_number']}: {order['order_title']}")

# Get mappings for an order
mappings = db.get_mappings_for_order("8900.1")
for mapping in mappings:
    print(f"  References §{mapping['section_number']}")

db.close()
```

### Process a New Order

```python
from order_processor.pdf_extractor import PDFExtractor
from order_processor.citation_parser import CitationParser
from order_processor.models import FAAOrder
from storage.database import Database

# Extract text
extractor = PDFExtractor()
result = extractor.extract_with_metadata("path/to/order.pdf")

# Find CFR references
parser = CitationParser()
references = parser.find_cfr_references(result['text'])

# Create order object
order = FAAOrder(
    order_number="8900.1",
    order_title="Flight Standards Information Management System",
    file_path="path/to/order.pdf",
    extracted_text=result['text'],
    cfr_references=references
)

# Store in database
db = Database()
order_id = db.store_faa_order(order)
db.close()
```

## API Reference

### ECFRClient

```python
from cfr_scraper.api_client import ECFRClient

client = ECFRClient()

# Fetch a specific part
part_data = client.fetch_part(title_number=14, part_number=91)

# Fetch a specific section
section_data = client.fetch_section(title_number=14, section_number="91.3")

# Fetch multiple parts
parts = client.fetch_title_14_parts(part_range=(61, 99))
```

### Database

```python
from storage.database import Database

db = Database("data/cfr_orders.db")

# Store CFR part
db.store_cfr_part(part)

# Store FAA order
db.store_faa_order(order)

# Create mapping
db.create_mapping(
    cfr_section_number="91.3",
    order_number="8900.1",
    relationship_type="references",
    confidence_score=0.95,
    extraction_method="explicit_citation"
)

# Search
results = db.search_cfr_sections("emergency")
results = db.search_faa_orders("pilot")

db.close()
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
black .
flake8 .
```

## Future Enhancements

See `STRATEGY_FAA_RULES.md` for the complete roadmap. Planned features include:

- **Phase 3**: Semantic similarity matching using ML
- **Phase 4**: Rules engine for compliance validation
- **Phase 5**: REST API and web interface

## Resources

- [eCFR API Documentation](https://www.ecfr.gov/developers/documentation/api/v1)
- [eCFR Website](https://www.ecfr.gov/)
- [FAA Orders](https://www.faa.gov/regulations_policies/orders_notices/)
- [Title 14 CFR](https://www.ecfr.gov/current/title-14)

## License

[Add license information]

## Contributing

[Add contribution guidelines]

## Contact

[Add contact information]
