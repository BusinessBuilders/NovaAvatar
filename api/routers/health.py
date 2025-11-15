"""Health check and monitoring endpoints."""

import os
import sys
import psutil
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
import redis

from database import get_db

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    checks: Dict[str, Any]


class DetailedHealthResponse(HealthResponse):
    """Detailed health check with system info."""
    system: Dict[str, Any]
    dependencies: Dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Basic health check endpoint.

    Returns service status and component health.
    """
    checks = {
        "database": await _check_database(db),
        "redis": _check_redis(),
        "disk": _check_disk(),
    }

    # Overall status is healthy if all checks pass
    all_healthy = all(check["status"] == "healthy" for check in checks.values())
    status = "healthy" if all_healthy else "unhealthy"

    return {
        "status": status,
        "timestamp": datetime.utcnow(),
        "version": _get_version(),
        "checks": checks,
    }


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check with system information.

    Includes CPU, memory, and dependency status.
    """
    checks = {
        "database": await _check_database(db),
        "redis": _check_redis(),
        "disk": _check_disk(),
        "memory": _check_memory(),
    }

    system_info = {
        "python_version": sys.version,
        "platform": sys.platform,
        "cpu_count": psutil.cpu_count(),
        "cpu_percent": psutil.cpu_percent(interval=1),
    }

    dependencies = {
        "torch": _check_torch(),
        "cuda": _check_cuda(),
    }

    all_healthy = all(check["status"] == "healthy" for check in checks.values())
    status = "healthy" if all_healthy else "unhealthy"

    return {
        "status": status,
        "timestamp": datetime.utcnow(),
        "version": _get_version(),
        "checks": checks,
        "system": system_info,
        "dependencies": dependencies,
    }


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Kubernetes readiness probe endpoint.

    Returns 200 if service is ready to accept traffic.
    """
    # Check critical dependencies
    db_status = await _check_database(db)

    if db_status["status"] != "healthy":
        return {"status": "not ready", "reason": "database unavailable"}, 503

    return {"status": "ready"}


@router.get("/health/live")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if service is alive (even if dependencies are down).
    """
    return {"status": "alive", "timestamp": datetime.utcnow()}


# Helper functions

async def _check_database(db: Session) -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "message": "Database connection OK",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Database error: {str(e)}",
        }


def _check_redis() -> Dict[str, Any]:
    """Check Redis connectivity."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    try:
        client = redis.from_url(redis_url, socket_connect_timeout=2)
        client.ping()
        return {
            "status": "healthy",
            "message": "Redis connection OK",
        }
    except Exception as e:
        return {
            "status": "degraded",
            "message": f"Redis unavailable: {str(e)}",
        }


def _check_disk() -> Dict[str, Any]:
    """Check disk space."""
    try:
        usage = psutil.disk_usage("/")
        percent_used = usage.percent

        if percent_used > 90:
            status = "unhealthy"
            message = f"Disk space critical: {percent_used}% used"
        elif percent_used > 80:
            status = "degraded"
            message = f"Disk space low: {percent_used}% used"
        else:
            status = "healthy"
            message = f"Disk space OK: {percent_used}% used"

        return {
            "status": status,
            "message": message,
            "percent_used": percent_used,
            "free_gb": usage.free / (1024**3),
        }
    except Exception as e:
        return {
            "status": "unknown",
            "message": f"Could not check disk: {str(e)}",
        }


def _check_memory() -> Dict[str, Any]:
    """Check memory usage."""
    try:
        memory = psutil.virtual_memory()
        percent_used = memory.percent

        if percent_used > 90:
            status = "unhealthy"
        elif percent_used > 80:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "status": status,
            "percent_used": percent_used,
            "available_gb": memory.available / (1024**3),
            "total_gb": memory.total / (1024**3),
        }
    except Exception as e:
        return {
            "status": "unknown",
            "message": f"Could not check memory: {str(e)}",
        }


def _check_torch() -> Dict[str, Any]:
    """Check PyTorch availability."""
    try:
        import torch
        return {
            "available": True,
            "version": torch.__version__,
        }
    except ImportError:
        return {
            "available": False,
            "message": "PyTorch not installed",
        }


def _check_cuda() -> Dict[str, Any]:
    """Check CUDA availability."""
    try:
        import torch
        if torch.cuda.is_available():
            return {
                "available": True,
                "version": torch.version.cuda,
                "device_count": torch.cuda.device_count(),
                "current_device": torch.cuda.current_device(),
                "device_name": torch.cuda.get_device_name(0),
            }
        else:
            return {
                "available": False,
                "message": "CUDA not available",
            }
    except Exception as e:
        return {
            "available": False,
            "message": f"Error checking CUDA: {str(e)}",
        }


def _get_version() -> str:
    """Get application version."""
    try:
        import tomli
        with open("pyproject.toml", "rb") as f:
            data = tomli.load(f)
            return data.get("project", {}).get("version", "unknown")
    except Exception:
        return "unknown"
