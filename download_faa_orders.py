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

def get_document_info_links(url):
    """
    Scrape the FAA orders listing page and extract document information page links.
    Returns a list of tuples: (order_name, info_page_url)
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
    
    # Find all document information links
    doc_links = []
    
    # Look for links to document.information pages
    for link in soup.find_all('a', href=True):
        href = link['href']
        if 'document.information' in href and 'documentID' in href:
            full_url = urljoin(url, href)
            # Get link text as the order name
            name = link.get_text(strip=True)
            if name and full_url not in [url for _, url in doc_links]:
                doc_links.append((name, full_url))
    
    print(f"Found {len(doc_links)} document information pages")
    return doc_links

def get_pdf_url_from_info_page(info_url):
    """
    Visit a document information page and extract the PDF download URL.
    Returns the PDF URL or None if not found.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(info_url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"      Error fetching info page: {e}")
        return None
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Look for PDF links in the document information page
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.endswith('.pdf'):
            # Make sure it's an absolute URL
            pdf_url = urljoin(info_url, href)
            return pdf_url
    
    return None

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
    
    # Step 1: Get list of document information page links
    doc_info_links = get_document_info_links(BASE_URL)
    
    if not doc_info_links:
        print("No document information links found. The page structure may have changed.")
        print("Please check the URL and update the script if needed.")
        return
    
    # Limit to MAX_DOWNLOADS
    doc_info_links = doc_info_links[:MAX_DOWNLOADS]
    print(f"\nWill attempt to process {len(doc_info_links)} orders")
    print()
    
    # Step 2: Visit each document info page to get PDF URLs and download
    successful = 0
    failed = 0
    skipped = 0
    
    for i, (name, info_url) in enumerate(doc_info_links, 1):
        print(f"[{i}] Processing: {name}")
        print(f"      Info page: {info_url}")
        
        # Get the PDF URL from the document information page
        pdf_url = get_pdf_url_from_info_page(info_url)
        
        if not pdf_url:
            print(f"      Warning: No PDF link found on info page")
            skipped += 1
        else:
            print(f"      PDF URL: {pdf_url}")
            if download_pdf(name, pdf_url, i):
                successful += 1
            else:
                failed += 1
        
        # Rate limiting - be respectful to the server
        if i < len(doc_info_links):
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Summary
    print()
    print("=" * 70)
    print("Download Summary")
    print("=" * 70)
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Skipped (no PDF): {skipped}")
    print(f"Total processed: {successful + failed + skipped}")
    print(f"Files saved to: {os.path.abspath(DOWNLOAD_DIR)}")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user.")
        sys.exit(0)

# Made with Bob
