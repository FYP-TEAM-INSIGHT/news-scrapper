#!/usr/bin/env python3
"""
Lankadeepa News Scraper

This script scrapes news articles from Lankadeepa website.
Usage: python scrape_lankadeepa.py [category] [pages]

Examples:
- python scrape_lankadeepa.py politics 3
- python scrape_lankadeepa.py latest-news 2
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
import time
import sys


@dataclass
class NewsArticle:
    id: str  # encoded URL
    source: str
    headline: str
    content: str
    timestamp: str
    url: str


class LankadeepaNewscraper:
    def __init__(self, base_url="https://www.lankadeepa.lk"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def encode_url(self, url):
        """Encode URL to create a unique ID"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def get_category_page(self, category, page_offset=0):
        """Get the category page HTML"""
        # Map category names to their actual URLs
        category_urls = {
            'politics': 'politics/13',
            'latest-news': 'latest-news/1', 
            'news': 'news/101',
            'foreign': 'sports/14',
            'local': 'local/16',
            'business': 'ft'
        }
        
        # Get the base category URL
        category_url = category_urls.get(category, category)
        
        if page_offset == 0:
            url = f"{self.base_url}/{category_url}"
        else:
            url = f"{self.base_url}/{category_url}/{page_offset}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching category page {url}: {e}")
            return None
    
    def extract_article_urls_with_timestamps(self, html_content):
        """Extract article URLs and timestamps from category page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        articles_data = []
        
        # Focus on the main content area to avoid sidebar articles
        main_content = soup.find('div', class_='col-md-10 col-lg-9 p-b-20 leftcol')
        if not main_content:
            # Fallback to other possible main content selectors
            main_content = soup.find('div', class_='col-md-12') or soup.find('div', class_='col-lg-9')
        if not main_content:
            main_content = soup  # Final fallback to entire page
        
        # Find all article containers in the main content area
        article_containers = main_content.find_all('div', class_='flex-wr-sb-s p-t-20 p-b-15 how-bor2 row')
        
        for container in article_containers:
            # Extract URL from the link
            link = container.find('a', href=True)
            if not link:
                continue
                
            href = link.get('href', '')
            
            # Filter for valid Lankadeepa article URLs
            if not (href.startswith('https://www.lankadeepa.lk/') and 
                    any(category in href for category in ['latest_news', 'news', 'politics', 'sports', 'foreign', 'local', 'business'])):
                continue
                
            # Additional filtering to avoid pagination and other non-article links
            if any(skip in href for skip in ['page=', 'category=', '/you_may_also_like/']):
                continue
            
            # Extract timestamp from the same container
            timestamp = None
            timestamp_span = container.find('span', class_='f1-s-4 cl8 hov-cl10 trans-03 timec')
            if timestamp_span:
                timestamp_text = timestamp_span.get_text(strip=True)
                timestamp = self.parse_sinhala_date(timestamp_text)
                
            # Only add if we haven't seen this URL before
            if href not in [item['url'] for item in articles_data]:
                articles_data.append({
                    'url': href,
                    'timestamp': timestamp
                })
        
        return articles_data
    
    def extract_article_urls(self, html_content):
        """Extract article URLs from category page (backward compatibility)"""
        articles_data = self.extract_article_urls_with_timestamps(html_content)
        return [item['url'] for item in articles_data]
    
    def parse_sinhala_date(self, date_text):
        """Parse Sinhala date format to ISO timestamp"""
        try:
            # Map Sinhala month names to numbers
            sinhala_months = {
                'ජනවාරි': '01', 'පෙබරවාරි': '02', 'මාර්තු': '03', 'අප්‍රේල්': '04',
                'මැයි': '05', 'ජුනි': '06', 'ජූලි': '07', 'අගෝස්තු': '08',
                'සැප්තැම්බර්': '09', 'ඔක්තෝබර්': '10', 'නොවැම්බර්': '11', 'දෙසැම්බර්': '12'
            }
            
            # Extract parts from format like "2025 ජුනි මස 22"
            parts = date_text.strip().split()
            if len(parts) >= 4:
                year = parts[0]
                month_sinhala = parts[1]
                day = parts[3]
                
                # Convert Sinhala month to number
                month_num = sinhala_months.get(month_sinhala, '01')
                
                # Create ISO format timestamp
                timestamp = f"{year}-{month_num}-{day.zfill(2)}T00:00:00"
                return timestamp
        except Exception as e:
            print(f"Warning: Could not parse date '{date_text}': {e}")
        
        # Fallback to current timestamp
        return datetime.now().isoformat()
    
    def scrape_article(self, url, pre_extracted_timestamp=None):
        """Scrape a single article"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract headline - it's usually in h3 with specific class
            headline = ""
            headline_elem = soup.find('h3', class_='f1-l-3')
            if not headline_elem:
                # Try alternative selectors
                headline_elem = soup.find('h1') or soup.find('h2') or soup.find('h3')
            if headline_elem:
                headline = headline_elem.get_text(strip=True)
            
            # Use pre-extracted timestamp if available, otherwise try to extract from page
            if pre_extracted_timestamp:
                timestamp = pre_extracted_timestamp
            else:
                # Extract publication timestamp from the page (fallback method)
                timestamp = datetime.now().isoformat()  # Default fallback
                
                # Look for the date in the header section
                header_div = soup.find('div', class_='header p-b-20')
                if header_div:
                    # Find the link with the date information
                    date_links = header_div.find_all('a', class_='f1-s-4')
                    for link in date_links:
                        text = link.get_text(strip=True)
                        # Check if this contains a Sinhala date pattern
                        if any(month in text for month in ['ජනවාරි', 'පෙබරවාරි', 'මාර්තු', 'අප්‍රේල්', 'මැයි', 'ජුනි', 'ජූලි', 'අගෝස්තු', 'සැප්තැම්බර්', 'ඔක්තෝබර්', 'නොවැම්බර්', 'දෙසැම්බර්']):
                            # Extract just the date part (remove author info)
                            if 'මස' in text:
                                date_part = text.split('මස')[0] + 'මස ' + text.split('මස')[1].strip().split()[0]
                                timestamp = self.parse_sinhala_date(date_part)
                                break
            
            # Extract content - look for the main content area
            content = ""
            content_div = soup.find('div', class_='header inner-content')
            if not content_div:
                # Try alternative selectors
                content_div = soup.find('div', class_='inner-content') or soup.find('div', class_='content')
            
            if content_div:
                # Get all paragraphs
                paragraphs = content_div.find_all('p')
                content_parts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    # Filter out unwanted content
                    if (text and 
                        len(text) > 30 and  # Must be substantial text
                        not text.startswith('(') and  # Skip attribution in parentheses
                        not text.startswith('&nbsp;') and  # Skip HTML entities
                        'script' not in text.lower() and  # Skip script tags
                        'advertisement' not in text.lower() and  # Skip ads
                        'googletag' not in text.lower()):  # Skip Google ads
                        content_parts.append(text)
                content = '\n\n'.join(content_parts)
            
            # If we still don't have content, try a more general approach
            if not content:
                # Look for any div containing substantial text
                text_divs = soup.find_all('div')
                for div in text_divs:
                    text = div.get_text(strip=True)
                    if len(text) > 200 and headline and headline.lower() in text.lower():
                        paragraphs = div.find_all('p')
                        if paragraphs:
                            content_parts = []
                            for p in paragraphs:
                                p_text = p.get_text(strip=True)
                                if len(p_text) > 30:
                                    content_parts.append(p_text)
                            content = '\n\n'.join(content_parts)
                            break
            
            # Create article object
            article = NewsArticle(
                id=self.encode_url(url),
                source="Lankadeepa",
                headline=headline,
                content=content,
                timestamp=timestamp,
                url=url
            )
            
            return article
            
        except requests.RequestException as e:
            print(f"Error scraping article {url}: {e}")
            return None
    
    def load_existing_ids(self, category):
        """Load existing article IDs to avoid duplicates"""
        # Go up two directories to reach root, then data/lankadeepa
        ids_file = f"../../data/lankadeepa/{category}/existing_ids.json"
        if os.path.exists(ids_file):
            with open(ids_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()
    
    def save_existing_ids(self, category, ids):
        """Save existing article IDs"""
        # Go up two directories to reach root, then data/lankadeepa
        os.makedirs(f"../../data/lankadeepa/{category}", exist_ok=True)
        ids_file = f"../../data/lankadeepa/{category}/existing_ids.json"
        with open(ids_file, 'w', encoding='utf-8') as f:
            json.dump(list(ids), f, ensure_ascii=False, indent=2)
    
    def save_article(self, article, category):
        """Save article to JSON file"""
        # Go up two directories to reach root, then data/lankadeepa
        os.makedirs(f"../../data/lankadeepa/{category}", exist_ok=True)
        
        # Use article's publication timestamp for filename
        try:
            # Parse the ISO timestamp and format for filename
            from datetime import datetime as dt
            pub_date = dt.fromisoformat(article.timestamp.replace('T', ' ').replace('Z', ''))
            timestamp_str = pub_date.strftime("%Y-%m-%d_%H_%M_%S")
        except Exception:
            # Fallback to current time if parsing fails
            timestamp_str = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        
        filename = f"../../data/lankadeepa/{category}/{timestamp_str}_{article.id}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(asdict(article), f, ensure_ascii=False, indent=2)
    
    def scrape_category(self, category, num_pages=1):
        """Scrape articles from a category with pagination"""
        all_articles_data = []
        
        # Step 1: Extract article URLs and timestamps from all pages
        print(f"Step 1: Extracting article URLs and timestamps from {num_pages} page(s) of {category}...")
        
        for page in range(num_pages):
            page_offset = page * 30  # Each page has 30 articles
            print(f"  Fetching page {page + 1} (offset: {page_offset})...")
            
            html = self.get_category_page(category, page_offset)
            if html:
                articles_data = self.extract_article_urls_with_timestamps(html)
                all_articles_data.extend(articles_data)
                print(f"    Found {len(articles_data)} articles with timestamps")
                time.sleep(1)  # Be polite to the server
            else:
                print(f"    Failed to fetch page {page + 1}")
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_articles_data = []
        for article_data in all_articles_data:
            if article_data['url'] not in seen_urls:
                seen_urls.add(article_data['url'])
                unique_articles_data.append(article_data)
        
        print(f"  Total unique articles found: {len(unique_articles_data)}")
        
        # Save URLs to step-01-output.json for compatibility
        urls_only = [item['url'] for item in unique_articles_data]
        with open("step-01-output.json", 'w', encoding='utf-8') as f:
            json.dump(urls_only, f, ensure_ascii=False, indent=2)
        print("  URLs saved to step-01-output.json")
        
        # Step 2: Check existing IDs to avoid duplicates
        print("\nStep 2: Loading existing article IDs...")
        existing_ids = self.load_existing_ids(category)
        print(f"  Found {len(existing_ids)} existing articles")
        
        # Step 3: Scrape new articles
        print("\nStep 3: Scraping articles...")
        new_articles = 0
        skipped_articles = 0
        
        for i, article_data in enumerate(unique_articles_data, 1):
            url = article_data['url']
            timestamp = article_data['timestamp']
            url_id = self.encode_url(url)
            
            if url_id in existing_ids:
                skipped_articles += 1
                print(f"  [{i}/{len(unique_articles_data)}] Skipping existing article: {url}")
                continue
            
            print(f"  [{i}/{len(unique_articles_data)}] Scraping: {url}")
            if timestamp:
                print(f"    Using extracted timestamp: {timestamp}")
            
            # Pass the pre-extracted timestamp to avoid parsing it from individual page
            article = self.scrape_article(url, pre_extracted_timestamp=timestamp)
            
            if article and article.headline and article.content:
                self.save_article(article, category)
                existing_ids.add(article.id)
                new_articles += 1
                print(f"    ✓ Saved: {article.headline[:60]}...")
            else:
                print("    ✗ Failed to scrape or empty content")
            
            time.sleep(2)  # Be polite to the server
        
        # Step 4: Save updated IDs
        print("\nStep 4: Updating existing IDs...")
        self.save_existing_ids(category, existing_ids)
        
        print("\nScraping completed!")
        print(f"  New articles: {new_articles}")
        print(f"  Skipped articles: {skipped_articles}")
        print(f"  Total processed: {len(unique_articles_data)}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scrape_lankadeepa.py [category] [pages]")
        print("Example: python scrape_lankadeepa.py politics 3")
        print("Available categories: politics, latest-news, news, etc.")
        sys.exit(1)
    
    category = sys.argv[1]
    num_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    scraper = LankadeepaNewscraper()
    scraper.scrape_category(category, num_pages)


if __name__ == "__main__":
    main()


"""
USAGE EXAMPLES:

1. Scrape politics category (1 page, ~30 articles):
   python scrape_lankadeepa.py politics

2. Scrape politics category (3 pages, ~90 articles):
   python scrape_lankadeepa.py politics 3

3. Scrape latest news (2 pages):
   python scrape_lankadeepa.py latest-news 2

4. Scrape general news:
   python scrape_lankadeepa.py news

AVAILABLE CATEGORIES:
- politics     : Political news (maps to /politics/13)
- latest-news  : Latest news (maps to /latest-news/1)
- business     : Business news (maps to /ft)
- news         : General news (maps to /news/101)
- foreign      : Foreign news (maps to /sports/14)
- local        : Local news (maps to /local/16)

OUTPUT:
- Articles are saved to: ../../data/lankadeepa/{category}/
- Filename format: YYYY-MM-DD_HH_MM_SS_{article_id}.json (uses article publication date)
- Existing article IDs are tracked in: existing_ids.json
- URL extraction results saved to: step-01-output.json

FEATURES:
- Automatic duplicate detection and skipping
- Pagination support
- Polite scraping with delays
- UTF-8 encoding support for Sinhala text
- Robust content extraction with fallback methods
- Article ID generation using URL hashing
- Publication timestamp extraction from Sinhala date format

NOTES:
- Each page typically contains 30 articles
- The scraper adds 2-second delays between article requests
- Articles are filtered to avoid sidebar content and pagination links
- Content extraction focuses on main article text while filtering ads and scripts
- Timestamps are extracted from article publication date in Sinhala format (e.g., "2025 ජුනි මස 22")
- Filenames use the actual publication date, not the scraping date
"""