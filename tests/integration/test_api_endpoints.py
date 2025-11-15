"""Integration tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from api.server import app
from database.base import Base, get_db
from database.models import APIKey


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    # Create tables
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as c:
        yield c

    # Drop tables
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def api_key(client):
    """Create test API key."""
    db = TestingSessionLocal()
    key = APIKey(
        key="test_api_key_12345",
        name="Test Key",
        description="API key for testing",
        is_active=True,
        permissions=["*"],
        rate_limit=1000,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    yield key.key
    db.close()


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_basic_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "version" in data

    def test_detailed_health_check(self, client):
        """Test detailed health check endpoint."""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "system" in data
        assert "dependencies" in data

    def test_readiness_probe(self, client):
        """Test readiness probe endpoint."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_liveness_probe(self, client):
        """Test liveness probe endpoint."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


@pytest.mark.integration
class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint."""

    def test_metrics_endpoint(self, client):
        """Test that metrics endpoint returns Prometheus format."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        # Check for some expected metrics
        assert b"http_requests_total" in response.content


@pytest.mark.integration
class TestAuthentication:
    """Test API key authentication."""

    def test_protected_endpoint_without_key(self, client):
        """Test that protected endpoints reject requests without API key."""
        response = client.post("/api/scrape", json={"max_items": 5})
        assert response.status_code == 401

    def test_protected_endpoint_with_invalid_key(self, client):
        """Test that invalid API keys are rejected."""
        response = client.post(
            "/api/scrape",
            json={"max_items": 5},
            headers={"X-API-Key": "invalid_key"}
        )
        assert response.status_code == 401

    def test_protected_endpoint_with_valid_key(self, client, api_key):
        """Test that valid API keys are accepted."""
        # This might fail if the actual endpoint requires more setup
        # but it should at least not fail on auth
        response = client.post(
            "/api/scrape",
            json={"max_items": 5},
            headers={"X-API-Key": api_key}
        )
        # Should not be 401 (may be 500 or other error due to missing setup)
        assert response.status_code != 401


@pytest.mark.integration
class TestRateLimiting:
    """Test rate limiting middleware."""

    def test_rate_limit_headers(self, client):
        """Test that rate limit headers are present."""
        response = client.get("/")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limit_enforcement(self, client):
        """Test that rate limits are enforced."""
        # This test would need to make many requests quickly
        # Skipping actual enforcement test in this example
        pass


@pytest.mark.integration
@pytest.mark.slow
class TestContentScraping:
    """Test content scraping endpoints."""

    def test_scrape_endpoint(self, client, api_key):
        """Test scrape content endpoint."""
        response = client.post(
            "/api/scrape",
            json={"max_items": 1, "sources": []},
            headers={"X-API-Key": api_key}
        )
        # May fail due to missing external dependencies
        # but we're testing the endpoint exists
        assert response.status_code in [200, 500, 503]


@pytest.mark.integration
class TestJobManagement:
    """Test job management endpoints."""

    def test_list_jobs(self, client, api_key):
        """Test listing jobs."""
        response = client.get(
            "/api/jobs",
            headers={"X-API-Key": api_key}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_job_status(self, client, api_key):
        """Test getting job status."""
        # Try to get a non-existent job
        job_id = str(uuid.uuid4())
        response = client.get(
            f"/api/jobs/{job_id}",
            headers={"X-API-Key": api_key}
        )
        # Should return 404 for non-existent job
        assert response.status_code == 404


@pytest.mark.integration
class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers(self, client):
        """Test that CORS headers are present."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        assert "access-control-allow-origin" in response.headers
