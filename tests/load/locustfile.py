"""
Locust load testing for NovaAvatar API.

Usage:
    # Web UI
    locust -f tests/load/locustfile.py --host=http://localhost:8000

    # Headless
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
        --users 10 --spawn-rate 2 --run-time 60s --headless
"""

from locust import HttpUser, task, between, tag
import random


class NovaAvatarUser(HttpUser):
    """Simulated NovaAvatar API user."""

    # Wait between 1-5 seconds between tasks
    wait_time = between(1, 5)

    # API key for authentication
    api_key = "test_api_key_12345"  # Change to your test API key

    def on_start(self):
        """Called when a user starts."""
        self.client.headers.update({"X-API-Key": self.api_key})

    @tag("health")
    @task(10)
    def health_check(self):
        """Check health endpoint (most frequent)."""
        self.client.get("/health")

    @tag("health")
    @task(5)
    def liveness_check(self):
        """Check liveness probe."""
        self.client.get("/health/live")

    @tag("health")
    @task(3)
    def readiness_check(self):
        """Check readiness probe."""
        self.client.get("/health/ready")

    @tag("metrics")
    @task(2)
    def get_metrics(self):
        """Get Prometheus metrics."""
        self.client.get("/metrics")

    @tag("scraper")
    @task(1)
    def scrape_content(self):
        """Scrape content (least frequent, most expensive)."""
        payload = {
            "max_items": random.randint(1, 5),
            "sources": []
        }
        with self.client.post(
            "/api/scrape",
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Got status {response.status_code}")

    @tag("jobs")
    @task(5)
    def list_jobs(self):
        """List all jobs."""
        self.client.get("/api/jobs")

    @tag("jobs")
    @task(3)
    def get_job_status(self):
        """Get status of a random job."""
        # Generate a random UUID (will likely 404, but tests the endpoint)
        import uuid
        job_id = str(uuid.uuid4())
        with self.client.get(
            f"/api/jobs/{job_id}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @tag("queue")
    @task(2)
    def get_review_queue(self):
        """Get review queue."""
        self.client.get("/api/queue")


class StressTestUser(HttpUser):
    """Aggressive user for stress testing."""

    wait_time = between(0.1, 0.5)  # Very short wait time
    api_key = "test_api_key_12345"

    def on_start(self):
        """Called when a user starts."""
        self.client.headers.update({"X-API-Key": self.api_key})

    @task
    def rapid_health_checks(self):
        """Rapidly hit health endpoint."""
        self.client.get("/health")

    @task
    def rapid_metrics_checks(self):
        """Rapidly hit metrics endpoint."""
        self.client.get("/metrics")
