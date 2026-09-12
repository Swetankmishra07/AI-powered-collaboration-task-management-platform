def test_database_health(client):
    response = client.get("/health/database")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
    }


def test_redis_health_is_disabled_without_configuration(client):
    response = client.get("/health/redis")

    assert response.status_code == 200
    assert response.json() == {
        "status": "disabled",
        "redis": "not_configured",
    }