"""
Pytest configuration and shared fixtures for API tests.
"""

import copy
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Provides a TestClient for making HTTP requests to the API."""
    return TestClient(app)


@pytest.fixture
def mock_activities():
    """Provides a fresh copy of the activities database for each test.
    
    This ensures test isolation and prevents state from leaking between tests.
    """
    return copy.deepcopy(activities)


@pytest.fixture
def isolated_app(monkeypatch, mock_activities):
    """Provides an app with isolated activities data.
    
    Patches the module-level activities dict so tests don't affect each other.
    """
    monkeypatch.setattr("src.app.activities", mock_activities)
    return app
