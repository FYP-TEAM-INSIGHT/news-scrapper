#!/usr/bin/env python3
"""Test script to scrape a single article"""

from scrape_lankadeepa import LankadeepaNewscraper

def test_single_article():
    scraper = LankadeepaNewscraper()
    
    # Test with the article from the webpage we fetched earlier
    test_url = "https://www.lankadeepa.lk/latest_news/රජය-ඉන්ධන-බලශක්ති-මාෆියාවේ-ගොඳුරක්-වෙලා/1-674467"
    
    print(f"Testing article scraping with URL: {test_url}")
    
    article = scraper.scrape_article(test_url)
    
    if article:
        print(f"✓ Successfully scraped article")
        print(f"Headline: {article.headline}")
        print(f"Content length: {len(article.content)} characters")
        print(f"Content preview: {article.content[:300]}...")
        print(f"Article ID: {article.id}")
    else:
        print("✗ Failed to scrape article")

if __name__ == "__main__":
    test_single_article()
