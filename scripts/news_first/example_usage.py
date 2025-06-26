#!/usr/bin/env python3
"""
Example usage of the News First scraper functions
"""

from news_first import fetch_news_data, convert_to_news_articles, save_to_json

def example_basic_usage():
    """Basic example of fetching and saving news data"""
    print("Example 1: Basic usage")
    
    # Fetch data
    api_data = fetch_news_data()
    
    # Convert to articles
    articles = convert_to_news_articles(api_data)
    
    # Save to file
    save_to_json(articles, "example_output.json")
    
    print(f"Fetched {len(articles)} articles and saved to example_output.json")

def example_custom_parameters():
    """Example with custom parameters"""
    print("\nExample 2: Custom parameters")
    
    # Fetch more articles from page 1
    api_data = fetch_news_data(category_id=83, page=1, count=10)
    
    # Convert and save
    articles = convert_to_news_articles(api_data)
    save_to_json(articles, "custom_output.json")
    
    print(f"Fetched {len(articles)} articles with custom parameters")

def example_process_existing_data():
    """Example of processing existing JSON data"""
    print("\nExample 3: Process existing data")
    
    import json
    
    # Load existing data.json file
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        
        # Convert to articles
        articles = convert_to_news_articles(existing_data)
        
        # Save processed data
        save_to_json(articles, "processed_existing_data.json")
        
        print(f"Processed existing data: {len(articles)} articles")
        
        # Print first article as example
        if articles:
            print(f"\nFirst article headline: {articles[0].headline}")
            
    except FileNotFoundError:
        print("data.json file not found")

if __name__ == "__main__":
    example_basic_usage()
    example_custom_parameters()
    example_process_existing_data()
