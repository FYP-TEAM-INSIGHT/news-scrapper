import requests
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class NewsArticle:
    source: str
    headline: str
    content: str
    timestamp: str
    url: str

# Category definitions
CATEGORIES = {
    'local': 81,
    'sports': 83,
    'foreign': 84,
    'business': 85
}

def clean_html_content(html_content: str) -> str:
    """Remove HTML tags and decode HTML entities from content"""
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', html_content)
    # Replace common HTML entities
    clean_text = clean_text.replace('&nbsp;', ' ')
    clean_text = clean_text.replace('&amp;', '&')
    clean_text = clean_text.replace('&lt;', '<')
    clean_text = clean_text.replace('&gt;', '>')
    clean_text = clean_text.replace('&quot;', '"')
    # Remove extra whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def format_timestamp(date_string: str) -> str:
    """Convert the API date format to a standard timestamp"""
    try:
        # Parse the date string (e.g., "03-06-2025T8:11 AM")
        date_part = date_string.split('T')[0]
        time_part = date_string.split('T')[1] if 'T' in date_string else ''
        
        # Convert to standard format
        day, month, year = date_part.split('-')
        formatted_date = f"{year}-{month}-{day}"
        
        if time_part:
            # Handle time parsing
            time_clean = time_part.replace(' AM', '').replace(' PM', '')
            if ':' in time_clean:
                formatted_timestamp = f"{formatted_date} {time_clean}"
            else:
                formatted_timestamp = formatted_date
        else:
            formatted_timestamp = formatted_date
            
        return formatted_timestamp
    except Exception:
        return date_string

def fetch_news_data(category_id: int = 83, page: int = 2, count: int = 5) -> Dict[str, Any]:
    """Fetch news data from News First API"""
    url = f"https://apisinhala.newsfirst.lk/post/categoryPostPagination/{category_id}/{page}/{count}/"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return {}

def convert_to_news_articles(api_data: Dict[str, Any]) -> List[NewsArticle]:
    """Convert API response to list of NewsArticle objects"""
    articles = []
    
    if 'postResponseDto' not in api_data:
        return articles
    
    for post in api_data['postResponseDto']:
        # Extract and clean content
        content = ""
        if 'content' in post and 'rendered' in post['content']:
            content = clean_html_content(post['content']['rendered'])
        elif 'excerpt' in post and 'rendered' in post['excerpt']:
            content = clean_html_content(post['excerpt']['rendered'])
        
        # Extract headline
        headline = ""
        if 'title' in post and 'rendered' in post['title']:
            headline = clean_html_content(post['title']['rendered'])
        elif 'short_title' in post:
            headline = post['short_title']
        
        # Format timestamp
        timestamp = format_timestamp(post.get('date', ''))
        
        # Construct full URL
        base_url = "https://sinhala.newsfirst.lk/"
        article_url = base_url + post.get('post_url', '')
        
        article = NewsArticle(
            source="News First",
            headline=headline,
            content=content,
            timestamp=timestamp,
            url=article_url
        )
        
        articles.append(article)
    
    return articles

def create_timestamp_filename(timestamp: str, article_id: str = None) -> str:
    """Create a filename based on timestamp for better sorting"""
    try:
        # Remove spaces and special characters from timestamp
        clean_timestamp = re.sub(r'[^\w\-]', '_', timestamp)
        # Add article ID if provided for uniqueness
        if article_id:
            return f"{clean_timestamp}_{article_id}.json"
        else:
            return f"{clean_timestamp}.json"
    except Exception:
        # Fallback to current timestamp if parsing fails
        from datetime import datetime
        current_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        if article_id:
            return f"{current_time}_{article_id}.json"
        else:
            return f"{current_time}.json"

def ensure_data_directory(category_name: str) -> Path:
    """Create data directory structure if it doesn't exist"""
    # Get the project root (go up from scripts/news_first to project root)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    data_dir = project_root / "data" / "news_first" / category_name
    
    # Create directory if it doesn't exist
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_category_name(category_id: int) -> str:
    """Get category name from category ID"""
    for name, id_val in CATEGORIES.items():
        if id_val == category_id:
            return name
    return 'unknown'

def save_article_to_file(article: NewsArticle, category_id: int, article_id: str = None):
    """Save individual article to categorized file structure"""
    category_name = get_category_name(category_id)
    data_dir = ensure_data_directory(category_name)
    
    # Create filename based on timestamp
    filename = create_timestamp_filename(article.timestamp, article_id)
    file_path = data_dir / filename
    
    # Prepare article data
    article_data = {
        "source": article.source,
        "headline": article.headline,
        "content": article.content,
        "timestamp": article.timestamp,
        "url": article.url,
        "category": category_name,
        "category_id": category_id,
        "saved_at": datetime.now().isoformat()
    }
    
    # Save to file
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(article_data, f, ensure_ascii=False, indent=2)
    
    print(f"Saved article to: {file_path}")
    return file_path

def save_articles_by_category(articles: List[NewsArticle], category_id: int, api_data: Dict[str, Any] = None):
    """Save all articles to individual files organized by category"""
    category_name = get_category_name(category_id)
    saved_files = []
    
    print(f"\nSaving {len(articles)} articles to category: {category_name}")
    
    for i, article in enumerate(articles):
        # Try to get article ID from original API data for uniqueness
        article_id = None
        if api_data and 'postResponseDto' in api_data:
            if i < len(api_data['postResponseDto']):
                article_id = api_data['postResponseDto'][i].get('id', str(i))
        
        if not article_id:
            article_id = str(i)
        
        file_path = save_article_to_file(article, category_id, article_id)
        saved_files.append(file_path)
    
    print(f"All articles saved to: data/news_first/{category_name}/")
    return saved_files

def fetch_and_save_all_categories(pages_per_category: int = 2, articles_per_page: int = 10):
    """Fetch and save articles for all categories"""
    all_saved_files = []
    
    for category_name, category_id in CATEGORIES.items():
        print(f"\n{'='*50}")
        print(f"Processing category: {category_name.upper()} (ID: {category_id})")
        print(f"{'='*50}")
        
        category_files = []
        for page in range(1, pages_per_category + 1):
            print(f"\nFetching page {page} for {category_name}...")
            
            # Fetch data for this category and page
            api_data = fetch_news_data(category_id, page, articles_per_page)
            
            if not api_data:
                print(f"No data found for {category_name} page {page}")
                continue
            
            # Convert to articles
            articles = convert_to_news_articles(api_data)
            
            if articles:
                # Save articles to category folder
                saved_files = save_articles_by_category(articles, category_id, api_data)
                category_files.extend(saved_files)
                print(f"Saved {len(articles)} articles from page {page}")
            else:
                print(f"No articles to save for {category_name} page {page}")
        
        all_saved_files.extend(category_files)
        print(f"\nTotal files saved for {category_name}: {len(category_files)}")
    
    print(f"\n{'='*50}")
    print(f"SUMMARY: Total files saved across all categories: {len(all_saved_files)}")
    print(f"{'='*50}")
    
    return all_saved_files

def save_to_json(articles: List[NewsArticle], filename: str = "output.json"):
    """Save articles to JSON file"""
    articles_dict = {
        "newsArticles": [
            {
                "source": article.source,
                "headline": article.headline,
                "content": article.content,
                "timestamp": article.timestamp,
                "url": article.url
            }
            for article in articles
        ]
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(articles_dict, f, ensure_ascii=False, indent=2)
    
    print(f"Data saved to {filename}")

def main():
    """Main function to execute the news scraping process"""
    print("News First Scraper")
    print("=" * 50)
    print("Choose an option:")
    print("1. Fetch single category (original behavior)")
    print("2. Fetch and save all categories to organized folders")
    print("3. Fetch all categories and also save to output.json")
    
    try:
        choice = input("\nEnter your choice (1-3): ").strip()
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return
    
    if choice == "1":
        # Original behavior - single category
        print("\nFetching single category data...")
        api_data = fetch_news_data(category_id=83, page=2, count=5)
        
        if not api_data:
            print("Failed to fetch data from API")
            return
        
        print(f"Fetched {len(api_data.get('postResponseDto', []))} articles")
        
        articles = convert_to_news_articles(api_data)
        print(f"Converted {len(articles)} articles")
        
        save_to_json(articles, "output.json")
        
        print("\nArticles Summary:")
        for i, article in enumerate(articles, 1):
            print(f"{i}. {article.headline[:100]}...")
    
    elif choice == "2":
        # New behavior - all categories to organized folders
        print("\nFetching all categories and saving to organized folders...")
        pages_per_category = 2
        articles_per_page = 10
        
        try:
            pages_per_category = int(input(f"Pages per category (default {pages_per_category}): ") or pages_per_category)
            articles_per_page = int(input(f"Articles per page (default {articles_per_page}): ") or articles_per_page)
        except ValueError:
            print("Using default values...")
        
        all_saved_files = fetch_and_save_all_categories(pages_per_category, articles_per_page)
        print(f"\nCompleted! Total files created: {len(all_saved_files)}")
    
    else:
        print("Invalid choice. Please run again and select 1, 2.")

if __name__ == "__main__":
    main()

