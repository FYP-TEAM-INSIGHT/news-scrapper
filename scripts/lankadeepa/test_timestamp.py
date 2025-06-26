#!/usr/bin/env python3
"""Test script to verify timestamp extraction"""

from scrape_lankadeepa import LankadeepaNewscraper

def test_timestamp_extraction():
    scraper = LankadeepaNewscraper()
    
    # Test with the article we know has a date
    test_url = "https://www.lankadeepa.lk/latest_news/රජය-ඉන්ධන-බලශක්ති-මාෆියාවේ-ගොඳුරක්-වෙලා/1-674467"
    
    print(f"Testing timestamp extraction with: {test_url}")
    
    article = scraper.scrape_article(test_url)
    
    if article:
        print(f"✓ Article scraped successfully")
        print(f"Headline: {article.headline}")
        print(f"Extracted timestamp: {article.timestamp}")
        print(f"Content length: {len(article.content)} characters")
        
        # Test the Sinhala date parser directly
        test_dates = [
            "2025 ජුනි මස 22",
            "2024 දෙසැම්බර් මස 15", 
            "2025 ජනවාරි මස 01"
        ]
        
        print("\nTesting Sinhala date parser:")
        for date_str in test_dates:
            parsed = scraper.parse_sinhala_date(date_str)
            print(f"  '{date_str}' -> {parsed}")
    else:
        print("✗ Failed to scrape article")

if __name__ == "__main__":
    test_timestamp_extraction()
