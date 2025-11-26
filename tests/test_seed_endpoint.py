"""Tests for the public seed endpoint."""

import pytest

from app.api.v1.endpoints.seed import run_seed


async def _fake_seed_runner():
    _fake_seed_runner.called = True


@pytest.mark.asyncio
async def test_seed_endpoint_uses_runner():
    """Ensure the seed endpoint executes the provided runner."""
    _fake_seed_runner.called = False

    response = await run_seed(seed_runner=_fake_seed_runner)

    assert response["detail"] == "Database seeded successfully"
    assert _fake_seed_runner.called is True
