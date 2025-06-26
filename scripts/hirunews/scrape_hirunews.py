import requests
import json
import os
import hashlib
from datetime import datetime
from dataclasses import dataclass
from typing import List, Set
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

class HiruNewsScraper:
    def __init__(self):
        self.base_url = "https://hirunews.lk/api/fetch_news.php"
        self.base_article_url = "https://hirunews.lk/"
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "hirunews")
        self.categories = ["Sports", "International", "Entertainment", "Business", "Local"]
        
    def get_md5_hash(self, text: str) -> str:
        """Generate MD5 hash for the given text"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def load_existing_ids(self, category: str) -> Set[str]:
        """Load existing article IDs from the category folder"""
        category_dir = os.path.join(self.data_dir, category.lower())
        existing_ids_file = os.path.join(category_dir, "existing_ids.json")
        
        if os.path.exists(existing_ids_file):
            try:
                with open(existing_ids_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except (json.JSONDecodeError, FileNotFoundError):
                return set()
        return set()
    
    def save_existing_ids(self, category: str, ids: Set[str]):
        """Save article IDs to the existing_ids.json file"""
        category_dir = os.path.join(self.data_dir, category.lower())
        os.makedirs(category_dir, exist_ok=True)
        
        existing_ids_file = os.path.join(category_dir, "existing_ids.json")
        with open(existing_ids_file, 'w', encoding='utf-8') as f:
            json.dump(list(ids), f, ensure_ascii=False, indent=2)
    
    def fetch_news_from_api(self, category: str, page: int = 1) -> List[dict]:
        """Fetch news articles from the Hiru News API"""
        try:
            params = {
                "page": page,
                "category": category
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching news for {category}, page {page}: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response for {category}, page {page}: {e}")
            return []
    
    def parse_article(self, article_data: dict, category: str) -> NewsArticle:
        """Parse article data from API response into NewsArticle object"""
        seourltitle = article_data.get("seourltitle", "")
        article_id = self.get_md5_hash(seourltitle)
        
        # Parse timestamp
        timestamp_str = article_data.get("sinhala_added_date", "")
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            timestamp = datetime.now()
        
        return NewsArticle(
            id=article_id,
            source="hirunews",
            headline=article_data.get("sinhala_title", ""),
            content=article_data.get("sinhala_story", ""),
            timestamp=timestamp.isoformat(),
            url=f"{self.base_article_url}{seourltitle}"
        )
    
    def save_article(self, article: NewsArticle, category: str):
        """Save article as JSON file with the specified naming convention"""
        category_dir = os.path.join(self.data_dir, category.lower())
        os.makedirs(category_dir, exist_ok=True)
        
        # Parse timestamp for filename
        try:
            dt = datetime.fromisoformat(article.timestamp.replace('Z', '+00:00'))
        except ValueError:
            dt = datetime.now()
        
        # Create filename: YYYY-MM-DD_HH_MM_SS_{article_id}.json
        filename = f"{dt.strftime('%Y-%m-%d_%H_%M_%S')}_{article.id}.json"
        filepath = os.path.join(category_dir, filename)
        
        # Convert article to dictionary
        article_dict = {
            "id": article.id,
            "source": article.source,
            "headline": article.headline,
            "content": article.content,
            "timestamp": article.timestamp,
            "url": article.url,
            "category": category
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(article_dict, f, ensure_ascii=False, indent=2)
        
        print(f"Saved article: {filename}")
    
    def scrape_category(self, category: str, max_pages: int = 5):
        """Scrape articles for a specific category"""
        print(f"Scraping {category} category...")
        
        existing_ids = self.load_existing_ids(category)
        new_ids = set()
        total_new_articles = 0
        
        for page in range(1, max_pages + 1):
            print(f"Fetching page {page} for {category}...")
            
            articles_data = self.fetch_news_from_api(category, page)
            
            if not articles_data:
                print(f"No articles found on page {page} for {category}")
                break
            
            page_new_articles = 0
            
            for article_data in articles_data:
                try:
                    article = self.parse_article(article_data, category)
                    
                    # Skip if article already exists
                    if article.id in existing_ids:
                        print(f"Skipping existing article: {article.id}")
                        continue
                    
                    # Save new article
                    self.save_article(article, category)
                    new_ids.add(article.id)
                    existing_ids.add(article.id)
                    page_new_articles += 1
                    total_new_articles += 1
                    
                except Exception as e:
                    print(f"Error processing article: {e}")
                    continue
            
            print(f"Found {page_new_articles} new articles on page {page}")
            
            # If no new articles found on this page, likely no more new content
            if page_new_articles == 0:
                print(f"No new articles on page {page}, stopping pagination for {category}")
                break
            
            # Add delay between requests to be respectful
            time.sleep(1)
        
        # Update existing IDs file
        if new_ids:
            self.save_existing_ids(category, existing_ids)
        
        print(f"Completed {category}: {total_new_articles} new articles saved")
        return total_new_articles
    
    def scrape_all_categories(self, max_pages: int = 5):
        """Scrape articles from all categories"""
        print("Starting Hiru News scraping...")
        
        total_articles = 0
        for category in self.categories:
            try:
                new_articles = self.scrape_category(category, max_pages)
                total_articles += new_articles
                print(f"Completed {category}: {new_articles} new articles")
                
                # Add delay between categories
                time.sleep(2)
                
            except Exception as e:
                print(f"Error scraping {category}: {e}")
                continue
        
        print(f"Scraping completed! Total new articles: {total_articles}")
        return total_articles

def main():
    """Main function to run the scraper with command line arguments"""
    if len(sys.argv) < 2:
        print("Usage: python scrape_hirunews.py <category> [max_pages]")
        print("Categories: Sports, International, Entertainment, Business, Local, all")
        print("Example: python scrape_hirunews.py Sports 5")
        print("Example: python scrape_hirunews.py all 3")
        return
    
    category = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    scraper = HiruNewsScraper()
    
    # Validate category
    valid_categories = ["Sports", "International", "Entertainment", "Business", "Local", "all"]
    if category not in valid_categories:
        print(f"Invalid category: {category}")
        print(f"Valid categories: {', '.join(valid_categories)}")
        return
    
    if category.lower() == "all":
        print(f"Scraping all categories with max_pages={max_pages}")
        scraper.scrape_all_categories(max_pages=max_pages)
    else:
        print(f"Scraping {category} category with max_pages={max_pages}")
        scraper.scrape_category(category, max_pages=max_pages)

if __name__ == "__main__":
    main()

"""
Usage Examples:

1. Run the scraper for a specific category:
   python scrape_hirunews.py Sports 5
   (This will scrape Sports category from page 1 to 5)

2. Run the scraper for all categories:
   python scrape_hirunews.py all 3
   (This will scrape all categories from page 1 to 3)

3. Run with default page limit (3 pages):
   python scrape_hirunews.py International
   (This will scrape International category from page 1 to 3)

4. Command line format:
   python scrape_hirunews.py <category> [max_pages]
   
   - category: Sports, International, Entertainment, Business, Local, all
   - max_pages: Number of pages to scrape (default: 3)

5. Programmatic usage (import in other scripts):
   from scrape_hirunews import HiruNewsScraper
   scraper = HiruNewsScraper()
   scraper.scrape_category("Sports", max_pages=10)

6. Available categories:
   - Sports
   - International
   - Entertainment
   - Business
   - Local
   - all (scrapes all categories)

7. File structure created:
   data/
   └── hirunews/
       ├── sports/
       │   ├── existing_ids.json
       │   ├── 2025-06-26_08_45_42_7b6ce94562218b68be811a0051f8a5b3.json
       │   └── ...
       ├── international/
       ├── entertainment/
       ├── business/
       └── local/

8. Each article JSON file contains:
   {
     "id": "md5_hash_of_seourltitle",
     "source": "hirunews",
     "headline": "Article title in Sinhala",
     "content": "Article content in Sinhala",
     "timestamp": "2025-06-26T08:45:42",
     "url": "https://hirunews.lk/sports/408388/article-url",
     "category": "sports"
   }

9. The scraper automatically:
   - Skips already downloaded articles using existing_ids.json
   - Creates directory structure if it doesn't exist
   - Handles API errors and continues scraping
   - Adds delays between requests to be respectful to the server
   - Uses MD5 hash of seourltitle as unique article ID
"""

