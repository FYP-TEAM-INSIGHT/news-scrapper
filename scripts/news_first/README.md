# News First Scraper

This script fetches news articles from the News First Sinhala API and converts them into a structured JSON format.

## Features

- Fetches news data from News First API
- Cleans HTML content and removes HTML tags
- Formats timestamps in a standardized format
- Converts data to NewsArticle objects
- Saves output in JSON format with proper structure

## Usage

### Basic Usage
```python
python news_first.py
```

### Customizing Parameters
You can modify the parameters in the `main()` function:

```python
# Fetch different categories, pages, or article counts
api_data = fetch_news_data(category_id=83, page=1, count=10)
```

### Parameters:
- `category_id`: Category ID for different news types (default: 83 for Local News)
- `page`: Page number for pagination (default: 2)
- `count`: Number of articles to fetch per page (default: 5)

## Output Format

The script generates an `output.json` file with the following structure:

```json
{
  "newsArticles": [
    {
      "source": "News First",
      "headline": "Article headline",
      "content": "Clean article content without HTML tags",
      "timestamp": "2025-06-03 8:11",
      "url": "https://sinhala.newsfirst.lk/article-url"
    }
  ]
}
```

## Functions

- `fetch_news_data()`: Fetches data from the API
- `clean_html_content()`: Removes HTML tags and entities
- `format_timestamp()`: Converts API date format to standard format
- `convert_to_news_articles()`: Converts API response to NewsArticle objects
- `save_to_json()`: Saves articles to JSON file

## Dependencies

- requests: For making HTTP requests to the API

Install dependencies:
```bash
pip install -r requirements.txt
```

## Error Handling

The script includes error handling for:
- API request failures
- Date parsing errors
- Missing or malformed data fields
