"""
Shared test fixtures for Argus OSINT tests.
"""
import asyncio
import pytest
import sys
import os

# Ensure argus package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "argus"))


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
