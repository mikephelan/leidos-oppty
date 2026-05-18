#!/usr/bin/env python3
"""
Script to download FAA Orders from the FAA website.
Downloads PDFs with rate limiting to be respectful of the server.
"""

import requests
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin
import sys

# Configuration
BASE_URL = "https://www.faa.gov/regulations_policies/orders_notices/index.cfm/go/document.list/?documentTypeID=2"
DOWNLOAD_DIR = "faa_orders"
MAX_DOWNLOADS = 200
DELAY_BETWEEN_REQUESTS = 2  # seconds - be respectful to the server

def create_download_directory():
    """Create directory for downloaded PDFs if it doesn't exist."""
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        print(f"Created directory: {DOWNLOAD_DIR}")

def get_order_links(url):
    """
    Scrape the FAA orders page and extract PDF download links.
    Returns a list of tuples: (order_name, pdf_url)
    """
    print(f"Fetching order list from: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching page: {e}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all PDF links - adjust selectors based on actual page structure
    pdf_links = []
    
    # Look for links containing 'pdf' or ending with .pdf
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '.pdf' in href.lower() or 'pdf' in href.lower():
            full_url = urljoin(url, href)
            # Get link text or use filename as name
            name = link.get_text(strip=True) or os.path.basename(href)
            pdf_links.append((name, full_url))
    
    print(f"Found {len(pdf_links)} potential PDF links")
    return pdf_links

def sanitize_filename(filename):
    """Remove or replace characters that are invalid in filenames."""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename

def download_pdf(name, url, index):
    """
    Download a single PDF file.
    Returns True if successful, False otherwise.
    """
    # Create a safe filename
    safe_name = sanitize_filename(name)
    if not safe_name.lower().endswith('.pdf'):
        safe_name += '.pdf'
    
    # Add index prefix for organization
    filename = f"{index:03d}_{safe_name}"
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    
    # Skip if already downloaded
    if os.path.exists(filepath):
        print(f"[{index}] Already exists: {filename}")
        return True
    
    print(f"[{index}] Downloading: {filename}")
    print(f"      URL: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()
        
        # Check if it's actually a PDF
        content_type = response.headers.get('content-type', '').lower()
        if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
            print(f"      Warning: Content-Type is {content_type}, may not be a PDF")
        
        # Write to file
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        file_size = os.path.getsize(filepath)
        print(f"      Success: {file_size:,} bytes")
        return True
        
    except requests.RequestException as e:
        print(f"      Error downloading: {e}")
        # Clean up partial download
        if os.path.exists(filepath):
            os.remove(filepath)
        return False

def main():
    """Main function to orchestrate the download process."""
    print("=" * 70)
    print("FAA Orders PDF Downloader")
    print("=" * 70)
    print(f"Target: {MAX_DOWNLOADS} orders")
    print(f"Delay between requests: {DELAY_BETWEEN_REQUESTS} seconds")
    print()
    
    # Create download directory
    create_download_directory()
    
    # Get list of PDF links
    pdf_links = get_order_links(BASE_URL)
    
    if not pdf_links:
        print("No PDF links found. The page structure may have changed.")
        print("Please check the URL and update the script if needed.")
        return
    
    # Limit to MAX_DOWNLOADS
    pdf_links = pdf_links[:MAX_DOWNLOADS]
    print(f"\nWill attempt to download {len(pdf_links)} PDFs")
    print()
    
    # Download each PDF
    successful = 0
    failed = 0
    
    for i, (name, url) in enumerate(pdf_links, 1):
        if download_pdf(name, url, i):
            successful += 1
        else:
            failed += 1
        
        # Rate limiting - be respectful to the server
        if i < len(pdf_links):
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Summary
    print()
    print("=" * 70)
    print("Download Summary")
    print("=" * 70)
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total: {successful + failed}")
    print(f"Files saved to: {os.path.abspath(DOWNLOAD_DIR)}")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user.")
        sys.exit(0)

# Made with Bob
