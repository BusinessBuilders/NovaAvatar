"""Unit tests for ContentScraper service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.content_scraper import ContentScraper, ContentItem


@pytest.mark.unit
class TestContentScraper:
    """Test ContentScraper functionality."""

    @pytest.fixture
    def scraper(self):
        """Create ContentScraper instance."""
        return ContentScraper()

    @pytest.mark.asyncio
    async def test_scrape_rss_feed(self, scraper):
        """Test RSS feed scraping."""
        mock_feed = MagicMock()
        mock_feed.entries = [
            MagicMock(
                title="Test Article",
                summary="Test description",
                link="https://example.com/article",
                published_parsed=datetime.now().timetuple(),
            )
        ]

        with patch("feedparser.parse", return_value=mock_feed):
            items = await scraper._scrape_rss("https://example.com/rss")

            assert len(items) > 0
            assert items[0].title == "Test Article"
            assert items[0].url == "https://example.com/article"

    @pytest.mark.asyncio
    async def test_fetch_full_article(self, scraper):
        """Test full article fetching."""
        mock_html = """
        <html>
            <body>
                <article>
                    <p>This is test content.</p>
                </article>
            </body>
        </html>
        """

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            content = await scraper.fetch_full_article("https://example.com/article")

            assert content is not None
            assert len(content) > 0

    @pytest.mark.asyncio
    async def test_scrape_all_deduplication(self, scraper):
        """Test that duplicate items are removed."""
        # Mock multiple sources returning same item
        duplicate_item = ContentItem(
            title="Same Article",
            description="Same description",
            url="https://example.com/same",
            source_name="Source1",
        )

        scraper._scrape_rss = AsyncMock(return_value=[duplicate_item])
        scraper._scrape_reddit = AsyncMock(return_value=[duplicate_item])

        items = await scraper.scrape_all(max_items_per_source=5)

        # Should only have one item, not two duplicates
        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_search_term_filtering(self, scraper):
        """Test filtering by search term."""
        items = [
            ContentItem(
                title="AI Revolution",
                description="AI is changing everything",
                url="https://example.com/1",
                source_name="Test",
            ),
            ContentItem(
                title="Cooking Tips",
                description="How to cook pasta",
                url="https://example.com/2",
                source_name="Test",
            ),
        ]

        scraper._scrape_rss = AsyncMock(return_value=items)

        filtered = await scraper.scrape_all(search_term="AI", max_items_per_source=10)

        assert len(filtered) == 1
        assert "AI" in filtered[0].title
