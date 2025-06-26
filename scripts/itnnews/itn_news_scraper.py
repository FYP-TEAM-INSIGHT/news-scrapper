import requests
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup
import time
import urllib.parse

@dataclass
class NewsArticle:
    source: str
    headline: str
    content: str
    timestamp: str
    url: str

# Category definitions for ITN News
CATEGORIES = {
    'local': 'local',
    'world': 'world', 
    'business': 'business',
    'sports': 'sports',
    'entertainment': 'entertainment'
}

class ITNNewsScraper:
    def __init__(self, delay_between_requests: float = 2.0):
        self.base_url = "https://www.itnnews.lk"
        self.delay = delay_between_requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove any remaining HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        return text

    def extract_article_links_from_category_page(self, category: str, page: int = 1) -> List[Dict[str, Any]]:
        """Extract article links and basic info from category page"""
        url = f"{self.base_url}/{category}/"
        if page > 1:
            url += f"page/{page}/"
        
        try:
            print(f"Fetching category page: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = []
            
            # Find article containers
            article_containers = soup.find_all('div', {'class': re.compile(r'p-wrap.*p-grid.*p-box')})
            
            for container in article_containers:
                try:
                    # Extract data-pid (article ID)
                    article_id = container.get('data-pid')
                    if not article_id:
                        continue
                    
                    # Extract article URL
                    link_elem = container.find('a', {'class': 'p-url'})
                    if not link_elem:
                        # Try alternative link structure
                        link_elem = container.find('a', href=True)
                    
                    if not link_elem:
                        continue
                    
                    article_url = link_elem.get('href')
                    if not article_url.startswith('http'):
                        article_url = self.base_url + article_url
                    
                    # Extract headline
                    title_elem = container.find('h3', {'class': 'entry-title'})
                    headline = ""
                    if title_elem:
                        headline = self.clean_text(title_elem.get_text())
                    
                    # Extract summary/excerpt
                    summary_elem = container.find('p', {'class': 'entry-summary'})
                    summary = ""
                    if summary_elem:
                        summary = self.clean_text(summary_elem.get_text())
                    
                    # Extract date if available
                    date_elem = container.find('time')
                    date_str = ""
                    if date_elem:
                        date_str = date_elem.get('datetime', '')
                        if not date_str:
                            date_str = self.clean_text(date_elem.get_text())
                    
                    articles.append({
                        'id': article_id,
                        'url': article_url,
                        'headline': headline,
                        'summary': summary,
                        'date': date_str,
                        'category': category
                    })
                    
                except Exception as e:
                    print(f"Error extracting article info: {e}")
                    continue
            
            print(f"Found {len(articles)} articles on page {page}")
            return articles
            
        except Exception as e:
            print(f"Error fetching category page {url}: {e}")
            return []

    def scrape_individual_article(self, article_url: str, article_info: Dict[str, Any]) -> Optional[NewsArticle]:
        """Scrape content from individual article page"""
        try:
            print(f"Scraping article: {article_url}")
            response = self.session.get(article_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract headline
            headline = article_info.get('headline', '')
            if not headline:
                # Try to get from page
                title_elem = soup.find('h1', {'class': re.compile(r's-title')})
                if title_elem:
                    headline = self.clean_text(title_elem.get_text())
            
            # Extract content
            content = ""
            # Look for main content area
            content_areas = [
                soup.find('div', {'class': re.compile(r'single-content')}),
                soup.find('div', {'class': re.compile(r'entry-content')}),
                soup.find('div', {'class': re.compile(r'post-content')}),
                soup.find('article'),
            ]
            
            for content_area in content_areas:
                if content_area:
                    # Remove unwanted elements
                    for unwanted in content_area.find_all(['script', 'style', 'nav', 'aside', 'footer', 'header']):
                        unwanted.decompose()
                    
                    # Extract paragraphs
                    paragraphs = content_area.find_all('p')
                    content_parts = []
                    for p in paragraphs:
                        text = self.clean_text(p.get_text())
                        if text and len(text) > 20:  # Filter out very short paragraphs
                            content_parts.append(text)
                    
                    content = ' '.join(content_parts)
                    if content:
                        break
            
            # Extract timestamp
            timestamp = article_info.get('date', '')
            if not timestamp:
                # Try to extract from page
                time_elem = soup.find('time')
                if time_elem:
                    timestamp = time_elem.get('datetime', '') or self.clean_text(time_elem.get_text())
            
            # Format timestamp
            if timestamp:
                timestamp = self.format_timestamp(timestamp)
            
            if not headline or not content:
                print(f"Missing essential data for {article_url}: headline={bool(headline)}, content={bool(content)}")
                return None
            
            return NewsArticle(
                source="ITN News",
                headline=headline,
                content=content,
                timestamp=timestamp,
                url=article_url
            )
            
        except Exception as e:
            print(f"Error scraping article {article_url}: {e}")
            return None

    def format_timestamp(self, timestamp_str: str) -> str:
        """Format timestamp to standard format"""
        if not timestamp_str:
            return ""
        
        try:
            # Handle ISO format with timezone
            if 'T' in timestamp_str and '+' in timestamp_str:
                # Parse ISO format: 2025-06-24T22:13:33+05:30
                dt = datetime.fromisoformat(timestamp_str.replace('+05:30', ''))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Handle Sinhala date format
            if 'ජූනි' in timestamp_str or 'මැයි' in timestamp_str or 'අප්‍රේල්' in timestamp_str:
                # For now, return as-is, could implement Sinhala date parsing later
                return timestamp_str
            
            return timestamp_str
            
        except Exception:
            return timestamp_str

    def scrape_category(self, category: str, max_pages: int = 3, articles_per_page: int = 20) -> List[NewsArticle]:
        """Scrape articles from a category"""
        all_articles = []
        
        for page in range(1, max_pages + 1):
            print(f"\n--- Scraping {category} page {page} ---")
            
            # Get article links from category page
            article_links = self.extract_article_links_from_category_page(category, page)
            
            if not article_links:
                print(f"No articles found on page {page}, stopping")
                break
            
            # Limit articles per page if specified
            if articles_per_page and len(article_links) > articles_per_page:
                article_links = article_links[:articles_per_page]
            
            # Scrape individual articles
            for i, article_info in enumerate(article_links, 1):
                print(f"Processing article {i}/{len(article_links)} on page {page}")
                
                article = self.scrape_individual_article(article_info['url'], article_info)
                if article:
                    all_articles.append(article)
                
                # Rate limiting
                time.sleep(self.delay)
            
            print(f"Completed page {page}, total articles: {len(all_articles)}")
            
            # Break if we didn't get enough articles (likely end of content)
            if len(article_links) < 10:  # Assuming normal pages have more articles
                print("Reached end of available content")
                break
        
        return all_articles

    def create_timestamp_filename(self, timestamp: str, article_id: str = None) -> str:
        """Create a filename based on timestamp"""
        try:
            # Create a safe filename from timestamp
            safe_timestamp = re.sub(r'[^\w\-]', '_', timestamp)
            if article_id:
                return f"{safe_timestamp}_{article_id}.json"
            else:
                return f"{safe_timestamp}.json"
        except Exception:
            # Fallback
            current_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            if article_id:
                return f"{current_time}_{article_id}.json"
            else:
                return f"{current_time}.json"

    def ensure_data_directory(self, category_name: str) -> Path:
        """Create data directory structure"""
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent
        data_dir = project_root / "data" / "itnnews" / category_name
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def save_article_to_file(self, article: NewsArticle, category: str, article_id: str = None):
        """Save individual article to file"""
        data_dir = self.ensure_data_directory(category)
        
        filename = self.create_timestamp_filename(article.timestamp, article_id)
        file_path = data_dir / filename
        
        article_data = {
            "source": article.source,
            "headline": article.headline,
            "content": article.content,
            "timestamp": article.timestamp,
            "url": article.url,
            "category": category,
            "saved_at": datetime.now().isoformat()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(article_data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved: {file_path}")
        return file_path

    def save_articles_to_json(self, articles: List[NewsArticle], filename: str = "itn_output.json"):
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
    """Main function"""
    scraper = ITNNewsScraper(delay_between_requests=2.0)
    
    print("ITN News Scraper")
    print("=" * 50)
    print("Choose an option:")
    print("1. Scrape single category")
    print("2. Scrape all categories")
    print("3. Scrape all categories and save to organized folders")
    
    try:
        choice = input("\nEnter your choice (1-3): ").strip()
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return
    
    if choice == "1":
        # Single category
        print("\nAvailable categories:")
        for i, (key, value) in enumerate(CATEGORIES.items(), 1):
            print(f"{i}. {key}")
        
        try:
            cat_choice = int(input("Select category number: ")) - 1
            category = list(CATEGORIES.keys())[cat_choice]
        except (ValueError, IndexError):
            print("Invalid choice, using 'local'")
            category = 'local'
        
        max_pages = int(input("Number of pages to scrape (default 2): ") or 2)
        
        print(f"\nScraping {category} category...")
        articles = scraper.scrape_category(category, max_pages=max_pages)
        
        if articles:
            scraper.save_articles_to_json(articles, f"itn_{category}_output.json")
            print(f"\nScraping completed! Found {len(articles)} articles.")
        else:
            print("No articles found.")
    
    elif choice == "2":
        # All categories to single JSON
        all_articles = []
        
        for category in CATEGORIES.keys():
            print(f"\n{'='*30}")
            print(f"Scraping category: {category.upper()}")
            print(f"{'='*30}")
            
            articles = scraper.scrape_category(category, max_pages=2)
            all_articles.extend(articles)
            
            print(f"Found {len(articles)} articles in {category}")
        
        if all_articles:
            scraper.save_articles_to_json(all_articles, "itn_all_categories_output.json")
            print(f"\nAll scraping completed! Total articles: {len(all_articles)}")
        else:
            print("No articles found.")
    
    elif choice == "3":
        # All categories to organized folders
        print("\nScraping all categories and saving to organized folders...")
        
        for category in CATEGORIES.keys():
            print(f"\n{'='*40}")
            print(f"Processing category: {category.upper()}")
            print(f"{'='*40}")
            
            articles = scraper.scrape_category(category, max_pages=2, articles_per_page=15)
            
            # Save each article to organized folder
            for i, article in enumerate(articles):
                scraper.save_article_to_file(article, category, str(i))
            
            print(f"Saved {len(articles)} articles for {category}")
        
        print("\nAll categories completed!")
    
    else:
        print("Invalid choice. Please run again and select 1, 2, or 3.")

if __name__ == "__main__":
    main()