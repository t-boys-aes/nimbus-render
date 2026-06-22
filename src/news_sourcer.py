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
USED_NEWS_LOG_PATH = "used_news_log.json"

def load_used_news_log() -> list:
    """Load the list of processed article URLs."""
    if os.path.exists(USED_NEWS_LOG_PATH):
        try:
            with open(USED_NEWS_LOG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.warning(f"Failed to read used news log: {e}")
    return []

def save_used_news_log(log_data: list):
    """Save the list of processed article URLs."""
    try:
        # Keep only the last 200 URLs to avoid infinite growth
        trimmed_log = log_data[-200:]
        with open(USED_NEWS_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(trimmed_log, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to write used news log: {e}")


def fetch_trending_articles(query_str="(geopolitics OR macroeconomics OR 'global finance' OR 'foreign policy') sourcelang:english", max_records=10):
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

def fetch_google_news_rss(query_str="geopolitics OR macroeconomics OR 'global finance' OR 'foreign policy'"):
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
        for item in items[:12]:
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
    
    # Decode Google News URL if needed
    if "news.google.com" in url:
        logger.info(f"Detected Google News URL, attempting to decode: {url}")
        try:
            from googlenewsdecoder import gnewsdecoder
            decoded = gnewsdecoder(url)
            if decoded.get("status"):
                decoded_url = decoded.get("decoded_url")
                logger.info(f"Successfully decoded Google News URL to: {decoded_url}")
                url = decoded_url
            else:
                logger.warning(f"Failed to decode Google News URL using library: {decoded.get('message')}")
        except Exception as e:
            logger.warning(f"Could not import or use googlenewsdecoder: {e}")
            
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

def extract_search_query_from_article(title: str, text_snippet: str) -> str:
    """Use Gemini to extract a highly focused search query for finding related articles."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "" or "your_gemini_api_key" in api_key:
        import re
        # Basic fallback: extract main words (capitalized or significant words)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', title)
        # remove common filler words
        fillers = {'with', 'from', 'that', 'this', 'have', 'about', 'news', 'update', 'economy', 'geopolitics', 'finance'}
        keywords = [w for w in words if w.lower() not in fillers]
        if len(keywords) >= 2:
            return " ".join(keywords[:3])
        return "geopolitics"

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = f"""
        Analyze this news article title and text snippet. Generate a focused, short search query (2-4 words max) that can be used on Google News to find articles that are directly related to, or expand on, the exact same event, topic, or conflict.
        
        CRITICAL RULES:
        1. Do not use generic terms like 'geopolitics' or 'news'.
        2. Identify and ignore metaphorical, idiomatic, or figurative language in the title (e.g., if the title says 'explosion of debt' or 'running off a cliff', do NOT search for physical 'explosion' or 'cliff'. Search for 'US debt crisis' or 'consumer credit' instead).
        3. Focus only on the core countries, entities, financial indicators, or geopolitical events.
        
        Article Title: {title}
        Snippet: {text_snippet[:400]}
        
        Respond ONLY with the raw search query string. Do not include any explanation, quotes, or markdown.
        Example output: US Iran sanctions drones
        """
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        query = response.text.strip().strip('"').strip("'")
        logger.info(f"Extracted focused search query for related news: '{query}'")
        return query
    except Exception as e:
        logger.warning(f"Failed to extract search query using Gemini: {e}")
        # Basic fallback
        import re
        words = re.findall(r'\b[a-zA-Z]{4,}\b', title)
        keywords = [w for w in words if w.lower() not in {'with', 'from', 'that', 'this', 'have', 'about'}]
        if len(keywords) >= 2:
            return " ".join(keywords[:3])
        return "geopolitics"

def source_news(query_str="(geopolitics OR macroeconomics OR 'global finance' OR 'foreign policy') sourcelang:english", override_url=None):
    """Main entry point to fetch and scrape the best article, saving results to json."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    used_news = load_used_news_log()
    
    if override_url:
        logger.info(f"Using manual override URL: {override_url}")
        
        # Add override url to used news log to ensure consistency
        if override_url not in used_news:
            used_news.append(override_url)
            save_used_news_log(used_news)
            
        article_text = scrape_article_text(override_url)
        if not article_text:
            raise ValueError(f"Failed to scrape text from manual URL: {override_url}")
        
        main_article = {
            "title": "Manual Override Article",
            "url": override_url,
            "text": article_text
        }
        articles_data = [main_article]
        source_name = "manual"
        
        # Try to find related articles even for manual override to make it rich
        focused_query = extract_search_query_from_article("Manual Override", article_text)
        logger.info(f"Searching related news for manual override using query: '{focused_query}'")
        related_articles = fetch_google_news_rss(focused_query)
        
        for art in related_articles:
            url = art.get("url", "")
            if url == override_url:
                continue
            text = scrape_article_text(url)
            if len(text) > 800:
                logger.info(f"Sourced related article for manual override: '{art.get('title')}'")
                articles_data.append({
                    "title": art.get("title", ""),
                    "url": url,
                    "text": text
                })
                if len(articles_data) >= 3:
                    break
                    
        news_data = {
            "title": main_article["title"],
            "url": main_article["url"],
            "text": main_article["text"],
            "source": source_name,
            "articles": articles_data
        }
    else:
        # Phase 1: Find the main article (from general geopolitics/finance feed)
        logger.info("Phase 1: Sourcing the main geopolitical/financial article...")
        articles = fetch_trending_articles(query_str)
        source_name = "GDELT"
        if not articles:
            articles = fetch_google_news_rss("geopolitics OR macroeconomics OR 'global finance' OR 'foreign policy'")
            source_name = "Google News RSS"
            
        if not articles:
            raise ValueError("No articles returned from GDELT or Google News RSS.")
            
        main_article = None
        remaining_candidates = []
        
        for art in articles:
            title = art.get("title", "")
            url = art.get("url", "")
            
            # Deduplicate: check if already used
            if url in used_news:
                logger.info(f"Skipping already used news article: '{title}' ({url})")
                continue
                
            # Scrape full text
            text = scrape_article_text(url)
            if len(text) > 800:
                logger.info(f"Successfully sourced Main Article: '{title}' ({len(text)} characters)")
                main_article = {
                    "title": title,
                    "url": url,
                    "text": text
                }
                # Add to used news log and save immediately
                used_news.append(url)
                save_used_news_log(used_news)
                
                # Keep track of the index where we stopped so we don't re-scrape the same article
                start_idx = articles.index(art) + 1
                remaining_candidates = articles[start_idx:]
                break
            else:
                logger.warning(f"Article text too short ({len(text)} chars) for '{title}', trying next candidate...")
                
        if not main_article:
            # Check if all candidates were skipped due to deduplication
            unprocessed_candidates = [art for art in articles if art.get("url") not in used_news]
            if not unprocessed_candidates:
                msg = "No new, unprocessed articles found in the news feed. Halting pipeline to prevent duplicate video generation."
                logger.error(msg)
                raise ValueError(msg)
                
            # Fallback if no article could be scraped at all but we have unprocessed ones
            logger.warning("All scraping attempts for main article failed. Using fallback article metadata from first unprocessed candidate.")
            fallback_art = unprocessed_candidates[0]
            main_article = {
                "title": fallback_art.get("title", "Geopolitics Update"),
                "url": fallback_art.get("url", ""),
                "text": f"Title: {fallback_art.get('title', '')}."
            }
            # Add fallback to used news log and save
            used_news.append(main_article["url"])
            save_used_news_log(used_news)
            
            articles_data = [main_article]
            news_data = {
                "title": main_article["title"],
                "url": main_article["url"],
                "text": main_article["text"],
                "source": f"{source_name}_fallback",
                "articles": articles_data
            }
        else:
            articles_data = [main_article]
            
            # Phase 2: Extract focused query from main article
            logger.info("Phase 2: Extracting focused search terms from the Main Article...")
            focused_query = extract_search_query_from_article(main_article["title"], main_article["text"])
            
            # Phase 3: Fetch related articles using the focused query
            logger.info(f"Phase 3: Fetching related articles using focused query: '{focused_query}'")
            related_candidates = fetch_trending_articles(focused_query)
            if not related_candidates:
                related_candidates = fetch_google_news_rss(focused_query)
                
            # Phase 4: Scrape related articles
            logger.info("Phase 4: Scraping related articles to build narrative depth...")
            # We combine the focused query results first, then fallback to original feed if not enough
            all_candidates = related_candidates + remaining_candidates
            
            # Remove duplicates based on URL
            seen_urls = {main_article["url"]}
            
            for art in all_candidates:
                url = art.get("url", "")
                if url in seen_urls or not url:
                    continue
                seen_urls.add(url)
                
                title = art.get("title", "")
                text = scrape_article_text(url)
                
                if len(text) > 800:
                    logger.info(f"Successfully sourced related article: '{title}' ({len(text)} characters)")
                    articles_data.append({
                        "title": title,
                        "url": url,
                        "text": text
                    })
                    if len(articles_data) >= 3:
                        break
                else:
                    logger.warning(f"Related article text too short ({len(text)} chars) for '{title}', trying next...")
            
            news_data = {
                "title": main_article["title"],
                "url": main_article["url"],
                "text": main_article["text"],
                "source": source_name,
                "articles": articles_data
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
