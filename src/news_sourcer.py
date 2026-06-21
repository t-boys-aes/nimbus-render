import os
import json
import requests
from bs4 import BeautifulSoup
import urllib.parse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TEMP_DIR = "temp"
NEWS_DATA_PATH = os.path.join(TEMP_DIR, "news_data.json")

def fetch_trending_articles(query_str="(geopolitics OR finance OR economy) sourcelang:english", max_records=5):
    """Query GDELT Doc API to get recent trending articles."""
    logger.info(f"Querying GDELT DOC API with query: {query_str}")
    encoded_query = urllib.parse.quote(query_str)
    url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={encoded_query}&mode=artlist&format=json&maxrecords={max_records}"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        # GDELT occasionally returns empty content or invalid JSON if no articles match
        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error("GDELT response is not valid JSON. Content:")
            logger.error(response.text[:200])
            return []
            
        articles = data.get("articles", [])
        logger.info(f"Found {len(articles)} candidate articles from GDELT.")
        return articles
    except Exception as e:
        logger.error(f"Error fetching from GDELT: {e}")
        return []

def fetch_google_news_rss(query_str="geopolitics OR finance OR economy"):
    """Query Google News RSS to get recent articles."""
    logger.info("Querying Google News RSS as fallback...")
    import xml.etree.ElementTree as ET
    encoded_query = urllib.parse.quote(query_str)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Parse XML using ElementTree
        root = ET.fromstring(response.content)
        items = root.findall(".//item")
        
        articles = []
        for item in items[:5]:
            title_el = item.find("title")
            link_el = item.find("link")
            title = title_el.text if title_el is not None else "News Update"
            link = link_el.text if link_el is not None else ""
            articles.append({
                "title": title,
                "url": link
            })
            
        logger.info(f"Found {len(articles)} candidate articles from Google News RSS.")
        return articles
    except Exception as e:
        logger.error(f"Error fetching from Google News RSS: {e}")
        return []

def scrape_article_text(url: str) -> str:
    """Scrape the full text of an article, removing HTML tags and scripts."""
    logger.info(f"Attempting to scrape article: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "header", "footer", "nav", "aside"]):
            script.decompose()
            
        # Extract text content
        paragraphs = soup.find_all("p")
        text_content = "\n".join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
        
        # Clean up whitespace
        lines = (line.strip() for line in text_content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = "\n".join(chunk for chunk in chunks if chunk)
        
        return clean_text
    except Exception as e:
        logger.warning(f"Failed to scrape {url}: {e}")
        return ""

def source_news(query_str="(geopolitics OR finance OR economy) sourcelang:english", override_url=None):
    """Main entry point to fetch and scrape the best article, saving results to json."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    if override_url:
        logger.info(f"Using manual override URL: {override_url}")
        article_text = scrape_article_text(override_url)
        if not article_text:
            raise ValueError(f"Failed to scrape text from manual URL: {override_url}")
        
        news_data = {
            "title": "Manual Override Article",
            "url": override_url,
            "text": article_text,
            "source": "manual"
        }
    else:
        articles = fetch_trending_articles(query_str)
        source_name = "GDELT"
        if not articles:
            articles = fetch_google_news_rss("geopolitics OR finance OR economy")
            source_name = "Google News RSS"
            
        if not articles:
            raise ValueError("No articles returned from GDELT or Google News RSS.")
            
        news_data = None
        for art in articles:
            title = art.get("title", "")
            url = art.get("url", "")
            
            # Scrape full text
            text = scrape_article_text(url)
            
            # Require at least 800 characters of content to make a good script
            if len(text) > 800:
                logger.info(f"Successfully sourced article: '{title}' ({len(text)} characters)")
                news_data = {
                    "title": title,
                    "url": url,
                    "text": text,
                    "source": source_name
                }
                break
            else:
                logger.warning(f"Article text too short ({len(text)} chars), trying next...")
                
        if not news_data:
            # Fallback: if all scrapes fail, use the first article's title/metadata
            logger.warning("All scraping attempts failed or were too short. Using fallback article metadata.")
            first_art = articles[0]
            news_data = {
                "title": first_art.get("title", "Geopolitics Update"),
                "url": first_art.get("url", ""),
                "text": f"Title: {first_art.get('title', '')}.",
                "source": f"{source_name}_fallback"
            }
            
    with open(NEWS_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(news_data, f, indent=4, ensure_ascii=False)
        
    logger.info(f"Saved news data to {NEWS_DATA_PATH}")
    return news_data

if __name__ == "__main__":
    logger.info("Running news sourcer standalone test...")
    try:
        res = source_news()
        print(f"Title: {res['title']}")
        print(f"URL: {res['url']}")
        print(f"Text Length: {len(res['text'])} characters")
    except Exception as e:
        logger.error(f"Sourcing test failed: {e}")
