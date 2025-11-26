"""Seed endpoint to populate the database with sample data."""

import logging
from typing import Awaitable, Callable

from fastapi import APIRouter, Depends, status

from seed_data import seed_database

logger = logging.getLogger(__name__)
router = APIRouter()

SeedRunner = Callable[[], Awaitable[None]]


def get_seed_runner() -> SeedRunner:
    """Provide the seed runner. Kept as a dependency for easy test overrides."""
    return seed_database


@router.post(
    "/seed",
    status_code=status.HTTP_200_OK,
    summary="Run database seed",
    tags=["seed"],
)
async def run_seed(seed_runner: SeedRunner = Depends(get_seed_runner)):
    """
    Run the database seed script.

    This endpoint is intentionally unauthenticated for deployment convenience.
    """
    logger.warning("Running seed endpoint without authentication. Use with caution.")
    await seed_runner()
    return {"detail": "Database seeded successfully"}
