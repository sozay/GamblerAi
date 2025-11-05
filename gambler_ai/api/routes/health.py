"""
Health check endpoints.
"""

from datetime import datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "GamblerAI API",
    }


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "GamblerAI API",
        "version": "0.1.0",
        "docs": "/docs",
    }
