"""
Content Scraper Service
Scrapes content from RSS feeds, Reddit, and NewsAPI for avatar video generation.
"""

import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import feedparser
import praw
from newsapi import NewsApiClient
import httpx
from loguru import logger
from pydantic import BaseModel, Field


class ContentItem(BaseModel):
    """Represents a single piece of content for video generation."""

    title: str
    description: str
    source: str  # 'rss', 'reddit', 'newsapi'
    source_name: str  # Actual source (e.g., 'CNN', 'r/technology')
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    score: float = 0.0  # Trending/relevance score
    category: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ContentScraper:
    """Scrapes content from multiple sources."""

    def __init__(
        self,
        reddit_client_id: Optional[str] = None,
        reddit_client_secret: Optional[str] = None,
        reddit_user_agent: str = "NovaAvatar:v1.0",
        newsapi_key: Optional[str] = None,
        rss_feeds: Optional[List[str]] = None
    ):
        self.reddit_client_id = reddit_client_id or os.getenv("REDDIT_CLIENT_ID")
        self.reddit_client_secret = reddit_client_secret or os.getenv("REDDIT_CLIENT_SECRET")
        self.newsapi_key = newsapi_key or os.getenv("NEWSAPI_KEY")

        # Default RSS feeds if none provided
        self.rss_feeds = rss_feeds or [
            "http://rss.cnn.com/rss/cnn_topstories.rss",
            "http://feeds.bbci.co.uk/news/rss.xml",
            "https://www.npr.org/rss/rss.php?id=1001",
            "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
            "https://feeds.feedburner.com/TechCrunch/",
        ]

        # Initialize clients
        self._init_clients()

    def _init_clients(self):
        """Initialize API clients."""
        # Reddit client
        if self.reddit_client_id and self.reddit_client_secret:
            try:
                self.reddit = praw.Reddit(
                    client_id=self.reddit_client_id,
                    client_secret=self.reddit_client_secret,
                    user_agent=self.reddit_user_agent
                )
                logger.info("Reddit client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Reddit client: {e}")
                self.reddit = None
        else:
            logger.warning("Reddit credentials not provided")
            self.reddit = None

        # NewsAPI client
        if self.newsapi_key:
            try:
                self.newsapi = NewsApiClient(api_key=self.newsapi_key)
                logger.info("NewsAPI client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize NewsAPI client: {e}")
                self.newsapi = None
        else:
            logger.warning("NewsAPI key not provided")
            self.newsapi = None

    async def scrape_rss(self, max_items: int = 10) -> List[ContentItem]:
        """Scrape content from RSS feeds."""
        items = []

        for feed_url in self.rss_feeds:
            try:
                logger.info(f"Scraping RSS feed: {feed_url}")
                feed = feedparser.parse(feed_url)

                for entry in feed.entries[:max_items]:
                    # Extract published date
                    published_at = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_at = datetime(*entry.published_parsed[:6])

                    item = ContentItem(
                        title=entry.get('title', 'No title'),
                        description=entry.get('summary', entry.get('description', '')),
                        source='rss',
                        source_name=feed.feed.get('title', feed_url),
                        url=entry.get('link'),
                        published_at=published_at,
                        score=0.0,  # RSS doesn't provide scores
                    )
                    items.append(item)

            except Exception as e:
                logger.error(f"Error scraping RSS feed {feed_url}: {e}")

        logger.info(f"Scraped {len(items)} items from RSS feeds")
        return items

    async def scrape_reddit(
        self,
        subreddits: List[str] = None,
        time_filter: str = "day",
        max_items: int = 10
    ) -> List[ContentItem]:
        """Scrape trending posts from Reddit."""
        if not self.reddit:
            logger.warning("Reddit client not initialized")
            return []

        items = []
        subreddits = subreddits or ['news', 'worldnews', 'technology', 'science']

        for subreddit_name in subreddits:
            try:
                logger.info(f"Scraping Reddit: r/{subreddit_name}")
                subreddit = self.reddit.subreddit(subreddit_name)

                for post in subreddit.hot(limit=max_items):
                    # Skip stickied posts
                    if post.stickied:
                        continue

                    # Calculate score (normalize by time to prefer recent posts)
                    age_hours = (datetime.now().timestamp() - post.created_utc) / 3600
                    score = post.score / (age_hours + 2) ** 1.5  # Reddit's hot algorithm

                    item = ContentItem(
                        title=post.title,
                        description=post.selftext[:500] if post.selftext else "",
                        source='reddit',
                        source_name=f"r/{subreddit_name}",
                        url=f"https://reddit.com{post.permalink}",
                        published_at=datetime.fromtimestamp(post.created_utc),
                        score=score,
                        category=subreddit_name,
                    )
                    items.append(item)

            except Exception as e:
                logger.error(f"Error scraping Reddit r/{subreddit_name}: {e}")

        logger.info(f"Scraped {len(items)} items from Reddit")
        return items

    async def scrape_newsapi(
        self,
        query: Optional[str] = None,
        category: Optional[str] = 'general',
        max_items: int = 10
    ) -> List[ContentItem]:
        """Scrape news from NewsAPI."""
        if not self.newsapi:
            logger.warning("NewsAPI client not initialized")
            return []

        items = []

        try:
            logger.info(f"Scraping NewsAPI - category: {category}, query: {query}")

            # Get top headlines
            if query:
                response = self.newsapi.get_everything(
                    q=query,
                    language='en',
                    sort_by='popularity',
                    page_size=max_items
                )
            else:
                response = self.newsapi.get_top_headlines(
                    category=category,
                    language='en',
                    page_size=max_items
                )

            for article in response.get('articles', []):
                # Parse published date
                published_at = None
                if article.get('publishedAt'):
                    try:
                        published_at = datetime.fromisoformat(
                            article['publishedAt'].replace('Z', '+00:00')
                        )
                    except:
                        pass

                item = ContentItem(
                    title=article.get('title', 'No title'),
                    description=article.get('description', article.get('content', '')),
                    source='newsapi',
                    source_name=article.get('source', {}).get('name', 'Unknown'),
                    url=article.get('url'),
                    published_at=published_at,
                    score=0.0,  # NewsAPI doesn't provide scores
                    category=category,
                )
                items.append(item)

        except Exception as e:
            logger.error(f"Error scraping NewsAPI: {e}")

        logger.info(f"Scraped {len(items)} items from NewsAPI")
        return items

    async def scrape_all(
        self,
        max_items_per_source: int = 10,
        reddit_subreddits: Optional[List[str]] = None,
        newsapi_category: str = 'general'
    ) -> List[ContentItem]:
        """Scrape content from all available sources."""
        all_items = []

        # Scrape RSS
        rss_items = await self.scrape_rss(max_items=max_items_per_source)
        all_items.extend(rss_items)

        # Scrape Reddit
        reddit_items = await self.scrape_reddit(
            subreddits=reddit_subreddits,
            max_items=max_items_per_source
        )
        all_items.extend(reddit_items)

        # Scrape NewsAPI
        newsapi_items = await self.scrape_newsapi(
            category=newsapi_category,
            max_items=max_items_per_source
        )
        all_items.extend(newsapi_items)

        # Sort by score (for ranked sources) and published date
        all_items.sort(
            key=lambda x: (x.score, x.published_at or datetime.min),
            reverse=True
        )

        # Deduplicate by title similarity
        all_items = self._deduplicate(all_items)

        logger.info(f"Total scraped items after deduplication: {len(all_items)}")
        return all_items

    def _deduplicate(self, items: List[ContentItem]) -> List[ContentItem]:
        """Remove duplicate items based on title similarity."""
        unique_items = []
        seen_titles = set()

        for item in items:
            # Normalize title for comparison
            normalized = item.title.lower().strip()

            # Check if similar title already exists
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique_items.append(item)

        return unique_items


# Example usage
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv

    load_dotenv()

    async def main():
        scraper = ContentScraper()
        items = await scraper.scrape_all(max_items_per_source=5)

        print(f"\nFound {len(items)} items:\n")
        for i, item in enumerate(items[:10], 1):
            print(f"{i}. [{item.source_name}] {item.title}")
            print(f"   {item.description[:100]}...")
            print()

    asyncio.run(main())
