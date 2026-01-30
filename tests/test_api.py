"""
Tests for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    activities.clear()
    activities.update({
        "Soccer Team": {
            "description": "Join the school soccer team and compete in regional matches",
            "schedule": "Mondays and Wednesdays, 4:00 PM - 6:00 PM",
            "max_participants": 25,
            "participants": ["alex@mergington.edu", "sarah@mergington.edu"]
        },
        "Basketball Club": {
            "description": "Practice basketball skills and play friendly matches",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
            "max_participants": 15,
            "participants": ["james@mergington.edu", "emily@mergington.edu"]
        },
        "Art Studio": {
            "description": "Explore painting, drawing, and mixed media art techniques",
            "schedule": "Wednesdays, 3:30 PM - 5:30 PM",
            "max_participants": 18,
            "participants": ["lily@mergington.edu", "noah@mergington.edu"]
        },
    })
    yield


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for the activities endpoint"""

    def test_get_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Soccer Team" in data
        assert "Basketball Club" in data
        assert "Art Studio" in data

    def test_activities_structure(self, client):
        """Test that activity data has correct structure"""
        response = client.get("/activities")
        data = response.json()
        soccer = data["Soccer Team"]
        assert "description" in soccer
        assert "schedule" in soccer
        assert "max_participants" in soccer
        assert "participants" in soccer
        assert isinstance(soccer["participants"], list)


class TestSignupEndpoint:
    """Tests for the signup endpoint"""

    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Soccer Team/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]

        # Verify student was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Soccer Team"]["participants"]

    def test_signup_duplicate(self, client):
        """Test that duplicate signup is rejected"""
        response = client.post(
            "/activities/Soccer Team/signup?email=alex@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()

    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_signup_updates_participants_list(self, client):
        """Test that signup adds student to participants list"""
        email = "newparticipant@mergington.edu"
        initial_count = len(activities["Soccer Team"]["participants"])
        
        client.post(f"/activities/Soccer Team/signup?email={email}")
        
        new_count = len(activities["Soccer Team"]["participants"])
        assert new_count == initial_count + 1
        assert email in activities["Soccer Team"]["participants"]


class TestUnregisterEndpoint:
    """Tests for the unregister endpoint"""

    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        response = client.delete(
            "/activities/Soccer Team/unregister?email=alex@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "alex@mergington.edu" in data["message"]

        # Verify student was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "alex@mergington.edu" not in activities_data["Soccer Team"]["participants"]

    def test_unregister_not_signed_up(self, client):
        """Test that unregistering a non-participant is rejected"""
        response = client.delete(
            "/activities/Soccer Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"].lower()

    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_unregister_removes_from_participants_list(self, client):
        """Test that unregister removes student from participants list"""
        email = "alex@mergington.edu"
        initial_count = len(activities["Soccer Team"]["participants"])
        assert email in activities["Soccer Team"]["participants"]
        
        client.delete(f"/activities/Soccer Team/unregister?email={email}")
        
        new_count = len(activities["Soccer Team"]["participants"])
        assert new_count == initial_count - 1
        assert email not in activities["Soccer Team"]["participants"]


class TestActivityCapacity:
    """Tests for activity capacity management"""

    def test_multiple_signups(self, client):
        """Test multiple students can sign up for same activity"""
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(f"/activities/Soccer Team/signup?email={email}")
            assert response.status_code == 200
        
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        participants = activities_data["Soccer Team"]["participants"]
        
        for email in emails:
            assert email in participants

    def test_spots_available_calculation(self, client):
        """Test that available spots decrease with signups"""
        activities_response = client.get("/activities")
        initial_data = activities_response.json()
        initial_participants = len(initial_data["Soccer Team"]["participants"])
        max_participants = initial_data["Soccer Team"]["max_participants"]
        initial_spots = max_participants - initial_participants
        
        # Sign up one student
        client.post("/activities/Soccer Team/signup?email=newstudent@mergington.edu")
        
        activities_response = client.get("/activities")
        new_data = activities_response.json()
        new_participants = len(new_data["Soccer Team"]["participants"])
        new_spots = max_participants - new_participants
        
        assert new_spots == initial_spots - 1
