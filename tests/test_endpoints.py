"""
Tests for FastAPI endpoints: root, get_activities, signup, unregister.
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities
import copy


@pytest.fixture
def client_with_fresh_data(monkeypatch):
    """Provides a TestClient with fresh, isolated activities data per test."""
    fresh_activities = copy.deepcopy(activities)
    monkeypatch.setattr("src.app.activities", fresh_activities)
    return TestClient(app)


class TestRoot:
    """Tests for GET / endpoint."""

    def test_root_redirects_to_static_index(self, client_with_fresh_data):
        """Verify root path redirects to /static/index.html."""
        response = client_with_fresh_data.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint."""

    def test_get_activities_returns_all_activities(self, client_with_fresh_data):
        """Verify /activities returns all activities with correct structure."""
        response = client_with_fresh_data.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        # Verify it's a dict (activities keyed by name)
        assert isinstance(data, dict)
        # Verify at least the expected activities are present
        expected_activities = [
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Basketball Team",
            "Tennis Club",
            "Art Club",
            "Drama Club",
            "Debate Team",
            "Science Club",
        ]
        for activity_name in expected_activities:
            assert activity_name in data

    def test_get_activities_has_correct_structure(self, client_with_fresh_data):
        """Verify each activity has required fields."""
        response = client_with_fresh_data.get("/activities")
        data = response.json()
        
        # Check first activity has all required fields
        first_activity = next(iter(data.values()))
        assert "description" in first_activity
        assert "schedule" in first_activity
        assert "max_participants" in first_activity
        assert "participants" in first_activity
        assert isinstance(first_activity["participants"], list)


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint."""

    def test_signup_adds_participant_successfully(self, client_with_fresh_data):
        """Verify valid signup adds participant to activity."""
        activity_name = "Chess Club"
        email = "newstudent@mergington.edu"
        
        response = client_with_fresh_data.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]
        
        # Verify participant was added
        updated = client_with_fresh_data.get("/activities").json()
        assert email in updated[activity_name]["participants"]

    def test_signup_duplicate_email_returns_400(self, client_with_fresh_data):
        """Verify duplicate signup returns 400 error."""
        activity_name = "Chess Club"
        # michael@mergington.edu is already signed up
        email = "michael@mergington.edu"
        
        response = client_with_fresh_data.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_invalid_activity_returns_404(self, client_with_fresh_data):
        """Verify signup for nonexistent activity returns 404."""
        response = client_with_fresh_data.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_signup_response_message_format(self, client_with_fresh_data):
        """Verify signup response has correct message format."""
        response = client_with_fresh_data.post(
            "/activities/Chess Club/signup",
            params={"email": "alice@mergington.edu"}
        )
        
        assert response.status_code == 200
        message = response.json()["message"]
        assert "alice@mergington.edu" in message
        assert "Chess Club" in message


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint."""

    def test_unregister_removes_participant_successfully(self, client_with_fresh_data):
        """Verify valid unregister removes participant from activity."""
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already signed up
        
        response = client_with_fresh_data.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]
        
        # Verify participant was removed
        updated = client_with_fresh_data.get("/activities").json()
        assert email not in updated[activity_name]["participants"]

    def test_unregister_not_found_returns_400(self, client_with_fresh_data):
        """Verify unregister for participant not signed up returns 400."""
        activity_name = "Chess Club"
        email = "nosuchstudent@mergington.edu"
        
        response = client_with_fresh_data.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_unregister_invalid_activity_returns_404(self, client_with_fresh_data):
        """Verify unregister from nonexistent activity returns 404."""
        response = client_with_fresh_data.delete(
            "/activities/Nonexistent Club/unregister",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_unregister_response_message_format(self, client_with_fresh_data):
        """Verify unregister response has correct message format."""
        response = client_with_fresh_data.delete(
            "/activities/Chess Club/unregister",
            params={"email": "michael@mergington.edu"}
        )
        
        assert response.status_code == 200
        message = response.json()["message"]
        assert "michael@mergington.edu" in message
        assert "Chess Club" in message

    def test_unregister_decrements_participant_count(self, client_with_fresh_data):
        """Verify participant count decreases after unregister."""
        activity_name = "Programming Class"
        email = "emma@mergington.edu"
        
        # Get initial count
        initial = client_with_fresh_data.get("/activities").json()
        initial_count = len(initial[activity_name]["participants"])
        
        # Unregister
        client_with_fresh_data.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )
        
        # Get updated count
        updated = client_with_fresh_data.get("/activities").json()
        updated_count = len(updated[activity_name]["participants"])
        
        assert updated_count == initial_count - 1


class TestStateIsolation:
    """Tests to ensure test isolation and no cross-test state pollution."""

    def test_signup_then_unregister_isolation(self, client_with_fresh_data):
        """Verify modifications in one test don't affect isolation in next."""
        # Sign up
        client_with_fresh_data.post(
            "/activities/Tennis Club/signup",
            params={"email": "newuser@mergington.edu"}
        )
        
        # Unregister
        response = client_with_fresh_data.delete(
            "/activities/Tennis Club/unregister",
            params={"email": "newuser@mergington.edu"}
        )
        
        assert response.status_code == 200
        
        # Verify state is clean for next iteration
        final = client_with_fresh_data.get("/activities").json()
        assert "newuser@mergington.edu" not in final["Tennis Club"]["participants"]
