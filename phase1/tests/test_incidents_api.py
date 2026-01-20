
import pytest
from fastapi.testclient import TestClient
from services.api.main import app
from services.autopilot.repository import AutopilotRepository
from datetime import datetime
from uuid import uuid4

client = TestClient(app)

import services.api.routes.incidents as incidents_module

@pytest.fixture
def mock_repo(mocker):
    # Mock the get_autopilot_repository dependency
    mock = mocker.Mock(spec=AutopilotRepository)
    # Patch directly on the imported module object
    mocker.patch.object(incidents_module, 'get_autopilot_repository', return_value=mock)
    return mock

def test_list_alerts_empty(mock_repo):
    mock_repo.list_incidents.return_value = []
    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    assert response.json() == []

def test_list_alerts_with_data(mock_repo):
    # Mock incident object
    class MockIncident:
        def __init__(self):
            self.id = "inc_1"
            self.severity = "warning"
            self.category = "system"
            self.title = "Test Incident"
            self.description = "Something happened"
            self.run_id = "run_1"
            self.created_at = datetime.now()
            self.resolved = False
            self.resolved_at = None
            self.resolution_note = None

    mock_repo.list_incidents.return_value = [MockIncident()]
    
    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "inc_1"
    assert data[0]["severity"] == "warning"

def test_resolve_alert(mock_repo):
    class MockIncident:
        def __init__(self):
            self.id = "inc_1"
            self.resolved_at = datetime.now()
            
    mock_repo.resolve_incident.return_value = MockIncident()
    
    response = client.post("/api/v1/alerts/inc_1/resolve?note=Fixed")
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    mock_repo.resolve_incident.assert_called_with("inc_1", note="Fixed")
