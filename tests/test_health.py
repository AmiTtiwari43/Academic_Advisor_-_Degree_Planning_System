import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_check_endpoint():
    """
    Verify the health check endpoint returns HTTP 200, status 'ok', and expected payload structure.
    """
    client = APIClient()
    response = client.get("/api/health/")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "academic-advisor-system"
    assert "version" in data
    assert "timestamp" in data


def test_health_check_unauthenticated():
    """
    Verify the health check endpoint is accessible without authentication headers or session.
    """
    client = APIClient()
    response = client.get("/api/health/")
    assert response.status_code == 200
