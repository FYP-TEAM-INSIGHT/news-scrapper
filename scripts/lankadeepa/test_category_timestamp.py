#!/usr/bin/env python3
"""Test script to verify timestamp extraction from category pages"""

from scrape_lankadeepa import LankadeepaNewscraper

def test_category_timestamp_extraction():
    scraper = LankadeepaNewscraper()
    
    # Test extracting URLs and timestamps from the politics category
    print("Testing timestamp extraction from category page...")
    
    # Get category page HTML
    html = scraper.get_category_page('politics', 0)
    if not html:
        print("Failed to fetch category page")
        return
    
    # Extract articles data with timestamps
    articles_data = scraper.extract_article_urls_with_timestamps(html)
    
    print(f"Extracted {len(articles_data)} articles with timestamps:")
    for i, article in enumerate(articles_data[:5], 1):  # Show first 5
        print(f"{i}. URL: {article['url']}")
        print(f"   Timestamp: {article['timestamp']}")
        print()
    
    # Test scraping a single article with pre-extracted timestamp
    if articles_data:
        print("Testing single article scraping with pre-extracted timestamp...")
        test_article = articles_data[0]
        url = test_article['url']
        timestamp = test_article['timestamp']
        
        print(f"URL: {url}")
        print(f"Pre-extracted timestamp: {timestamp}")
        
        article = scraper.scrape_article(url, pre_extracted_timestamp=timestamp)
        
        if article:
            print(f"✓ Article scraped successfully")
            print(f"  Headline: {article.headline}")
            print(f"  Final timestamp: {article.timestamp}")
            print(f"  Content length: {len(article.content)} characters")
        else:
            print("✗ Failed to scrape article")

if __name__ == "__main__":
    test_category_timestamp_extraction()
