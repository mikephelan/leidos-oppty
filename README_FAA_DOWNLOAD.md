# FAA Orders PDF Downloader

This script downloads FAA Orders as PDF files from the FAA website.

## Prerequisites

- Python 3.6 or higher
- Required packages (already installed):
  - requests
  - beautifulsoup4

## Usage

### Basic Usage

To download up to 200 FAA orders:

```bash
python3 download_faa_orders.py
```

### What the Script Does

1. **Fetches the order list** from the FAA website
2. **Extracts PDF links** from the page
3. **Downloads PDFs** with the following features:
   - Rate limiting (2 second delay between requests)
   - Automatic retry on failure
   - Skip already downloaded files
   - Sanitized filenames
   - Progress tracking

### Output

- PDFs are saved to the `faa_orders/` directory
- Files are named with a numeric prefix (001_, 002_, etc.) for easy sorting
- The script displays progress and a summary at the end

### Configuration

You can modify these settings in `download_faa_orders.py`:

- `MAX_DOWNLOADS`: Maximum number of PDFs to download (default: 200)
- `DELAY_BETWEEN_REQUESTS`: Seconds to wait between downloads (default: 2)
- `DOWNLOAD_DIR`: Directory to save PDFs (default: "faa_orders")

### Important Notes

1. **Be Respectful**: The script includes rate limiting to avoid overloading the FAA servers
2. **Check Terms of Service**: Ensure compliance with FAA website usage policies
3. **Resume Capability**: If interrupted, re-run the script - it will skip already downloaded files
4. **Internet Connection**: Requires stable internet connection
5. **Disk Space**: Ensure you have sufficient disk space (PDFs can be several MB each)

### Troubleshooting

**No PDFs found:**
- The website structure may have changed
- Check the URL is still valid
- You may need to update the scraping logic

**Download failures:**
- Check your internet connection
- The FAA server may be temporarily unavailable
- Some links may be broken or moved

**Permission errors:**
- Ensure you have write permissions in the current directory

### Example Output

```
======================================================================
FAA Orders PDF Downloader
======================================================================
Target: 200 orders
Delay between requests: 2 seconds

Created directory: faa_orders
Fetching order list from: https://www.faa.gov/...
Found 250 potential PDF links

Will attempt to download 200 PDFs

[1] Downloading: 001_Order_8900.1.pdf
      URL: https://www.faa.gov/...
      Success: 2,456,789 bytes
[2] Downloading: 002_Order_1050.1F.pdf
      URL: https://www.faa.gov/...
      Success: 1,234,567 bytes
...

======================================================================
Download Summary
======================================================================
Successful: 198
Failed: 2
Total: 200
Files saved to: /Users/mphelan/Documents/src/github/leidos-oppty/faa_orders
```

## Manual Execution

If you prefer to run the script manually:

1. Open Terminal
2. Navigate to this directory:
   ```bash
   cd /Users/mphelan/Documents/src/github/leidos-oppty
   ```
3. Run the script:
   ```bash
   python3 download_faa_orders.py
   ```

## Stopping the Script

Press `Ctrl+C` to stop the download at any time. You can resume later by running the script again.