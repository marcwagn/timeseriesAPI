import pytest

from src.main import app
from src.services.timeseries_service import TimeSeriesService
from src.api.v1.timeseries import get_timeseries_service


@pytest.fixture
async def timeseries_client(client, db_session):
    """HTTP client with the timeseries service dependency overridden."""
    async def override():
        try:
            yield TimeSeriesService(db_session)
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_timeseries_service] = override
    yield client


class TestCreateTimeseries:
    async def test_success(self, timeseries_client):
        response = await timeseries_client.post("/timeseries/", json={
            "name": "temperature",
            "data": [
                {"timestamp": "01.01.2024 12:00", "value": 22.5, "status": "V"}
            ],
        })
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "temperature"
        assert body["data_count"] == 1

    async def test_no_data(self, timeseries_client):
        response = await timeseries_client.post("/timeseries/", json={
            "name": "empty_series",
            "data": [],
        })
        assert response.status_code == 201
        assert response.json()["data_count"] == 0

    async def test_invalid_payload(self, timeseries_client):
        response = await timeseries_client.post("/timeseries/", json={})
        assert response.status_code == 422

    async def test_duplicate_name(self, timeseries_client):
        payload = {"name": "duplicate", "data": []}
        first = await timeseries_client.post("/timeseries/", json=payload)
        second = await timeseries_client.post("/timeseries/", json=payload)
        assert second.status_code == 201
        assert second.json()["id"] == first.json()["id"]


class TestGetTimeseries:
    async def test_success(self, timeseries_client):
        create = await timeseries_client.post("/timeseries/", json={
            "name": "wind_speed",
            "data": [
                {"timestamp": "15.03.2024 09:00", "value": 5.5, "status": "W"},
                {"timestamp": "15.03.2024 10:00", "value": 6.1, "status": "W"},
            ],
        })
        timeseries_id = create.json()["id"]

        response = await timeseries_client.get(f"/timeseries/{timeseries_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "wind_speed"
        assert body["data_count"] == 2

    async def test_not_found(self, timeseries_client):
        response = await timeseries_client.get("/timeseries/99999")
        assert response.status_code == 404
