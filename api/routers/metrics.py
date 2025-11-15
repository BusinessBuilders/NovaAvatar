"""Prometheus metrics endpoint."""

from fastapi import APIRouter, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CollectorRegistry,
    CONTENT_TYPE_LATEST,
)

router = APIRouter(tags=["Metrics"])

# Create registry
registry = CollectorRegistry()

# Define metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=registry,
)

video_generation_total = Counter(
    "video_generation_total",
    "Total video generation requests",
    ["status"],
    registry=registry,
)

video_generation_duration_seconds = Histogram(
    "video_generation_duration_seconds",
    "Video generation duration in seconds",
    registry=registry,
)

active_jobs = Gauge(
    "active_jobs",
    "Number of active video generation jobs",
    registry=registry,
)

queue_size = Gauge(
    "queue_size",
    "Number of jobs in review queue",
    registry=registry,
)

gpu_memory_used_bytes = Gauge(
    "gpu_memory_used_bytes",
    "GPU memory used in bytes",
    ["device"],
    registry=registry,
)

gpu_utilization_percent = Gauge(
    "gpu_utilization_percent",
    "GPU utilization percentage",
    ["device"],
    registry=registry,
)

scraper_items_total = Counter(
    "scraper_items_total",
    "Total items scraped",
    ["source"],
    registry=registry,
)

api_key_requests_total = Counter(
    "api_key_requests_total",
    "Total requests per API key",
    ["api_key_name"],
    registry=registry,
)


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus format.
    """
    # Update GPU metrics if available
    _update_gpu_metrics()

    # Generate metrics
    metrics_output = generate_latest(registry)

    return Response(
        content=metrics_output,
        media_type=CONTENT_TYPE_LATEST,
    )


def _update_gpu_metrics():
    """Update GPU-related metrics."""
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                # Memory usage
                allocated = torch.cuda.memory_allocated(i)
                gpu_memory_used_bytes.labels(device=str(i)).set(allocated)

                # Utilization (requires nvidia-ml-py3)
                try:
                    import pynvml
                    pynvml.nvmlInit()
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_utilization_percent.labels(device=str(i)).set(util.gpu)
                except Exception:
                    pass  # nvidia-ml-py3 not installed
    except Exception:
        pass  # PyTorch not available or no GPU
