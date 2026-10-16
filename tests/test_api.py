import pytest
from fastapi.testclient import TestClient
from engine.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_api_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ONLINE"
    assert "telemetry" in data
    assert "config" in data


def test_api_matrix(client):
    res = client.get("/api/matrix")
    assert res.status_code == 200
    data = res.json()
    assert "currencies" in data
    assert "rates" in data


def test_api_orderbook(client):
    res = client.get("/api/orderbook/Binance/BTCUSDT")
    assert res.status_code == 200
    data = res.json()
    assert "depth" in data
    assert "slippage_curve" in data
    assert data["depth"]["symbol"] == "BTCUSDT"
    assert len(data["slippage_curve"]) > 0


def test_api_risk_and_kill_switch_toggle(client):
    # Initial status
    res = client.get("/api/risk")
    assert res.status_code == 200
    initial_halt = res.json()["kill_switch"]

    # Toggle kill switch ON
    res_post = client.post("/api/risk", json={"kill_switch": True})
    assert res_post.status_code == 200
    assert res_post.json()["kill_switch"] is True
    assert res_post.json()["status"] == "HALTED"

    # Simulate trade should be blocked
    res_sim = client.post("/api/simulate", json={"capital_usd": 5000.0})
    assert res_sim.status_code == 403

    # Toggle kill switch OFF
    res_off = client.post("/api/risk", json={"kill_switch": False})
    assert res_off.status_code == 200
    assert res_off.json()["kill_switch"] is False
    assert res_off.json()["status"] == "ACTIVE_MONITORING"
