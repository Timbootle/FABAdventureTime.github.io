#!/usr/bin/env python3
import sys
import json
import os
import re
from urllib.request import urlopen, urlretrieve, Request
from urllib.error import URLError, HTTPError
import subprocess

def extract_og_image(html):
    # Try to find og:image or twitter:image meta tags
    m = re.search(r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r'name=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if m:
        return m.group(1)
    # Try common meta tag format
    m = re.search(r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:image["\']', html, re.IGNORECASE)
    if m:
        return m.group(1)
    return None

def download_and_optimize(page_url, dest_path):
    print(f"Processing: {page_url} -> {dest_path}")
    headers = { 'User-Agent': 'github-actions-image-fetcher/1.0' }
    req = Request(page_url, headers=headers)
    try:
        with urlopen(req, timeout=30) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Failed to download page {page_url}: {e}")
        return False

    img_url = extract_og_image(html)
    if not img_url:
        # Try finding first img src on the page as fallback
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html)
        if m:
            img_url = m.group(1)

    if not img_url:
        print(f"No image URL found on page {page_url}")
        return False

    # Normalize protocol-relative URLs
    if img_url.startswith('//'):
        img_url = 'https:' + img_url

    # Ensure destination directory exists
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    try:
        print(f"Downloading image {img_url}")
        urlretrieve(img_url, dest_path)
    except Exception as e:
        print(f"Failed to download image {img_url}: {e}")
        return False

    # Optimize / resize using ImageMagick
    try:
        # Resize to max width 1600px, keep aspect ratio, set quality ~80
        subprocess.run(["convert", dest_path, "-resize", "1600x>", "-quality", "80", dest_path], check=True)
    except Exception as e:
        print(f"ImageMagick processing failed for {dest_path}: {e}")
        return False

    print(f"Saved optimized image to {dest_path}")
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_images.py <sources.json>")
        sys.exit(1)
    srcfile = sys.argv[1]
    with open(srcfile, 'r', encoding='utf-8') as f:
        data = json.load(f)
    images = data.get('images', [])
    any_failed = False
    for item in images:
        dest = item.get('dest')
        page = item.get('page')
        credit = item.get('credit')
        ok = download_and_optimize(page, dest)
        if not ok:
            print(f"Failed processing {page} -> {dest} ({credit})")
            any_failed = True
    if any_failed:
        sys.exit(2)

if __name__ == '__main__':
    main()
