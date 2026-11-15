def test_health_liveness(client):
    """Test GET /health returns UP."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert "service" in data


def test_health_readiness(client):
    """Test GET /health/ready returns status and dependency checks."""
    response = client.get("/health/ready")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "dependencies" in data
    assert "database" in data["dependencies"]
    assert "rabbitmq" in data["dependencies"]


def test_actuator_health(client):
    """Test GET /actuator/health for Spring Cloud Gateway / Eureka compatibility."""
    response = client.get("/actuator/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"


def test_notifications_ping(client):
    """Test GET /api/notifications/ping preserves existing skeleton contract."""
    response = client.get("/api/notifications/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "notification"


def test_list_notifications_empty(client):
    """Test GET /api/notifications returns empty list initially."""
    response = client.get("/api/notifications")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "notifications" in data
    assert isinstance(data["notifications"], list)


def test_trigger_test_notification_endpoint(client):
    """Test POST /api/notifications/test sends simulated email and logs it."""
    payload = {
        "to_email": "candidate.test@esprit.tn",
        "template_name": "application_created.html",
        "custom_data": {"jobTitle": "Développeur Cloud Python"}
    }
    response = client.post("/api/notifications/test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["recipient"] == "candidate.test@esprit.tn"
    assert data["mode"] == "SIMULATED"

