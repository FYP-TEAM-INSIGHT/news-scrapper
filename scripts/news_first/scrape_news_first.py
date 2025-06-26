import requests
import json
import re
import hashlib
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Set
from dataclasses import dataclass

@dataclass
class NewsArticle:
    id: str  # encoded URL
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

def get_md5_hash(text: str) -> str:
    """Generate MD5 hash for the given text"""
    return hashlib.md5(text.encode()).hexdigest()

def load_existing_ids(category_name: str) -> Set[str]:
    """Load existing article IDs from the category folder"""
    data_dir = ensure_data_directory(category_name)
    existing_ids_file = data_dir / "existing_ids.json"
    
    if existing_ids_file.exists():
        try:
            with open(existing_ids_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except (json.JSONDecodeError, FileNotFoundError):
            return set()
    return set()

def save_existing_ids(category_name: str, ids: Set[str]):
    """Save article IDs to the existing_ids.json file"""
    data_dir = ensure_data_directory(category_name)
    existing_ids_file = data_dir / "existing_ids.json"
    
    with open(existing_ids_file, 'w', encoding='utf-8') as f:
        json.dump(list(ids), f, ensure_ascii=False, indent=2)

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
        
        # Generate article ID from URL
        article_id = get_md5_hash(article_url)
        
        article = NewsArticle(
            id=article_id,
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
        # Parse the timestamp to datetime object
        if 'T' in timestamp:
            # Handle ISO format like "2025-06-26T08:45:42"
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            # Handle other formats
            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
        
        # Create filename: YYYY-MM-DD_HH_MM_SS_{article_id}.json
        if article_id:
            return f"{dt.strftime('%Y-%m-%d_%H_%M_%S')}_{article_id}.json"
        else:
            return f"{dt.strftime('%Y-%m-%d_%H_%M_%S')}.json"
    except Exception:
        # Fallback to current timestamp if parsing fails
        current_time = datetime.now()
        if article_id:
            return f"{current_time.strftime('%Y-%m-%d_%H_%M_%S')}_{article_id}.json"
        else:
            return f"{current_time.strftime('%Y-%m-%d_%H_%M_%S')}.json"

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

def save_article_to_file(article: NewsArticle, category_id: int):
    """Save individual article to categorized file structure"""
    category_name = get_category_name(category_id)
    data_dir = ensure_data_directory(category_name)
    
    # Create filename based on timestamp and article ID
    filename = create_timestamp_filename(article.timestamp, article.id)
    file_path = data_dir / filename
    
    # Prepare article data
    article_data = {
        "id": article.id,
        "source": article.source,
        "headline": article.headline,
        "content": article.content,
        "timestamp": article.timestamp,
        "url": article.url
    }
    
    # Save to file
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(article_data, f, ensure_ascii=False, indent=2)
    
    print(f"Saved article to: {file_path}")
    return file_path

def save_articles_by_category(articles: List[NewsArticle], category_id: int):
    """Save all articles to individual files organized by category"""
    category_name = get_category_name(category_id)
    saved_files = []
    
    # Load existing IDs to avoid duplicates
    existing_ids = load_existing_ids(category_name)
    new_ids = set()
    new_articles_count = 0
    
    print(f"\nProcessing {len(articles)} articles for category: {category_name}")
    print(f"Found {len(existing_ids)} existing articles")
    
    for article in articles:
        # Skip if article already exists
        if article.id in existing_ids:
            print(f"Skipping existing article: {article.id}")
            continue
        
        # Save new article
        file_path = save_article_to_file(article, category_id)
        saved_files.append(file_path)
        new_ids.add(article.id)
        existing_ids.add(article.id)
        new_articles_count += 1
    
    # Update existing IDs file if we have new articles
    if new_ids:
        save_existing_ids(category_name, existing_ids)
    
    print(f"Saved {new_articles_count} new articles to: data/news_first/{category_name}/")
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
                saved_files = save_articles_by_category(articles, category_id)
                category_files.extend(saved_files)
                print(f"Processed {len(articles)} articles from page {page}")
            else:
                print(f"No articles to save for {category_name} page {page}")
        
        all_saved_files.extend(category_files)
        print(f"\nTotal new files saved for {category_name}: {len(category_files)}")
    
    print(f"\n{'='*50}")
    print(f"SUMMARY: Total new files saved across all categories: {len(all_saved_files)}")
    print(f"{'='*50}")
    
    return all_saved_files

def save_to_json(articles: List[NewsArticle], filename: str = "output.json"):
    """Save articles to JSON file"""
    articles_dict = {
        "newsArticles": [
            {
                "id": article.id,
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

def scrape_single_category(category_name: str, max_pages: int = 3):
    """Scrape a single category with specified pages"""
    if category_name not in CATEGORIES:
        print(f"Invalid category: {category_name}")
        print(f"Valid categories: {', '.join(CATEGORIES.keys())}")
        return []
    
    category_id = CATEGORIES[category_name]
    all_saved_files = []
    
    print(f"\n{'='*50}")
    print(f"Scraping category: {category_name.upper()} (ID: {category_id})")
    print(f"Pages: 1 to {max_pages}")
    print(f"{'='*50}")
    
    for page in range(1, max_pages + 1):
        print(f"\nFetching page {page} for {category_name}...")
        
        # Fetch data for this category and page
        api_data = fetch_news_data(category_id, page, 10)
        
        if not api_data:
            print(f"No data found for {category_name} page {page}")
            continue
        
        # Convert to articles
        articles = convert_to_news_articles(api_data)
        
        if articles:
            # Save articles to category folder
            saved_files = save_articles_by_category(articles, category_id)
            all_saved_files.extend(saved_files)
            print(f"Processed {len(articles)} articles from page {page}")
        else:
            print(f"No articles to save for {category_name} page {page}")
    
    print(f"\nTotal new files saved for {category_name}: {len(all_saved_files)}")
    return all_saved_files

def main():
    """Main function with command line argument support"""
    if len(sys.argv) < 2:
        print("Usage: python scrape_news_first.py <category> [max_pages]")
        print("Categories: local, sports, foreign, business, all")
        print("Example: python scrape_news_first.py sports 5")
        print("Example: python scrape_news_first.py all 3")
        return
    
    category = sys.argv[1].lower()
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    # Validate category
    valid_categories = list(CATEGORIES.keys()) + ["all"]
    if category not in valid_categories:
        print(f"Invalid category: {category}")
        print(f"Valid categories: {', '.join(valid_categories)}")
        return
    
    if category == "all":
        print(f"Scraping all categories with max_pages={max_pages}")
        fetch_and_save_all_categories(max_pages, 10)
    else:
        print(f"Scraping {category} category with max_pages={max_pages}")
        scrape_single_category(category, max_pages)

if __name__ == "__main__":
    main()

"""
Usage Examples:

1. Scrape a specific category with page limit:
   python scrape_news_first.py sports 5
   (This scrapes Sports category from page 1 to 5)

2. Scrape all categories:
   python scrape_news_first.py all 3
   (This scrapes all categories from page 1 to 3)

3. Use default page limit (3 pages):
   python scrape_news_first.py business
   (This scrapes Business category from page 1 to 3)

4. Command line format:
   python scrape_news_first.py <category> [max_pages]
   
   - category: local, sports, foreign, business, all
   - max_pages: Number of pages to scrape (default: 3)

5. Programmatic usage (import in other scripts):
   from scrape_news_first import scrape_single_category, fetch_and_save_all_categories
   scrape_single_category("sports", max_pages=10)
   fetch_and_save_all_categories(pages_per_category=5)

6. Available categories:
   - local (ID: 81)
   - sports (ID: 83) 
   - foreign (ID: 84)
   - business (ID: 85)
   - all (scrapes all categories above)

7. File structure created:
   data/
   └── news_first/
       ├── local/
       │   ├── existing_ids.json
       │   ├── 2025_06_26_08_45_42_7b6ce94562218b68be811a0051f8a5b3.json
       │   └── ...
       ├── sports/
       ├── foreign/
       └── business/

8. Each article JSON file contains:
   {
     "id": "md5_hash_of_url",
     "source": "News First",
     "headline": "Article title",
     "content": "Article content",
     "timestamp": "2025-06-26T08:45:42",
     "url": "https://sinhala.newsfirst.lk/article-url"
   }

9. The scraper automatically:
   - Skips already downloaded articles using existing_ids.json
   - Creates directory structure if it doesn't exist
   - Handles API errors and continues scraping
   - Uses MD5 hash of article URL as unique article ID
   - Cleans HTML content from articles
"""

