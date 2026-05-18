# Quick Start Guide

Get up and running with the FAA Rules and Orders Database in 5 minutes.

## Prerequisites

- Python 3.10+
- pip

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Basic Workflow

### Step 1: Download CFR Data

Download a few CFR parts to get started:

```bash
# Download Part 91 (General Operating and Flight Rules)
python download_cfr_data.py --part 91

# Or download a range of parts
python download_cfr_data.py --start-part 91 --end-part 95
```

**Expected output:**
```
INFO - Starting CFR download for Title 14, Parts 91-95
INFO - Successfully fetched 5 parts
INFO - Stored Part 91 (ID: 1)
INFO - CFR download complete!
```

### Step 2: Download FAA Orders

Download FAA Order PDFs (if not already done):

```bash
python download_faa_orders.py
```

This creates a `faa_orders/` directory with PDF files.

### Step 3: Process Orders

Extract text and find CFR references:

```bash
# Process all orders in the directory
python process_orders.py faa_orders/

# Or process a single order
python process_orders.py faa_orders/001_Order_8900.1.pdf
```

**Expected output:**
```
INFO - Processing: faa_orders/001_Order_8900.1.pdf
INFO - Extracted 150000 characters from 500 pages
INFO - Order number: 8900.1
INFO - Found 45 CFR references
INFO - Most referenced sections:
INFO -   §91.3: 5 times
INFO -   §91.123: 3 times
INFO - Stored order in database (ID: 1)
```

### Step 4: Create Mappings

Link CFR sections to orders:

```bash
python create_mappings.py --create --analyze
```

**Expected output:**
```
INFO - Creating explicit CFR-Order mappings...
INFO - Found 10 orders with CFR references
INFO - Created 120 explicit mappings

Mapping Statistics:
==================================================
Total mappings: 120
Mappings by relationship type:
  references: 120
Average confidence score: 0.950
```

## Verify Installation

Check that everything is working:

```python
from storage.database import Database

db = Database()

# Check CFR sections
sections = db.get_cfr_part_sections(14, 91)
print(f"Found {len(sections)} sections in Part 91")

# Check orders
cursor = db.conn.cursor()
cursor.execute("SELECT COUNT(*) FROM faa_orders")
order_count = cursor.fetchone()[0]
print(f"Found {order_count} FAA orders")

db.close()
```

## Common Tasks

### Search for a CFR Section

```python
from storage.database import Database

db = Database()
section = db.get_cfr_section("91.3")
print(f"§{section['section_number']}: {section['section_title']}")
print(section['content'])
db.close()
```

### Find Orders Referencing a Section

```python
from storage.database import Database

db = Database()
mappings = db.get_mappings_for_section("91.3")
print(f"Found {len(mappings)} orders referencing §91.3:")
for m in mappings:
    print(f"  - {m['order_number']}: {m['order_title']}")
db.close()
```

### Search CFR Content

```python
from storage.database import Database

db = Database()
results = db.search_cfr_sections("emergency deviation")
for result in results[:5]:
    print(f"§{result['section_number']}: {result['section_title']}")
db.close()
```

### Export Mappings

```bash
python create_mappings.py --export data/mappings/all_mappings.json
```

## Next Steps

1. **Explore the data**: Use the database queries to explore CFR sections and orders
2. **Add more data**: Download additional CFR parts and process more orders
3. **Analyze relationships**: Use the mapping statistics to understand CFR-Order relationships
4. **Build on top**: Use the data models and database to build your own tools

## Troubleshooting

### "Module not found" errors

Make sure you've installed all dependencies:
```bash
pip install -r requirements.txt
```

### Database errors

The database is created automatically. If you have issues, delete it and start fresh:
```bash
rm data/cfr_orders.db
python download_cfr_data.py --part 91
```

### PDF extraction issues

Some PDFs may be scanned images. The system will try to extract text but may fail. Check the logs for details.

### API rate limiting

The eCFR API has rate limits. The client includes automatic delays, but if you hit limits, wait a few minutes and try again.

## Getting Help

- See `README.md` for full documentation
- See `STRATEGY_FAA_RULES.md` for the complete project strategy
- Check the code comments for detailed API documentation

## Example: Complete Workflow

Here's a complete example from start to finish:

```bash
# 1. Install
pip install -r requirements.txt

# 2. Download CFR data (Part 91 only for quick start)
python download_cfr_data.py --part 91

# 3. Process orders (assuming you have PDFs)
python process_orders.py faa_orders/

# 4. Create mappings
python create_mappings.py --create --analyze

# 5. Export results
python create_mappings.py --export data/mappings/mappings.json
```

That's it! You now have a working database of CFR sections, FAA orders, and their relationships.