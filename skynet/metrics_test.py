import pytest
from fastapi.testclient import TestClient

from skynet import readiness
from skynet.metrics import metrics


@pytest.fixture
def client():
    yield TestClient(metrics)
    readiness.set_ready(False)


class TestHealthz:
    def test_unhealthy_until_main_app_started(self, client):
        # Also the state after a failed startup: the flag is only set once the
        # main app's startup has completed.
        readiness.set_ready(False)

        response = client.get('/healthz')

        assert response.status_code == 503
        assert response.json() == {'status': 'starting'}

    def test_healthy_once_main_app_started(self, client):
        readiness.set_ready(True)

        response = client.get('/healthz')

        assert response.status_code == 200
        assert response.json() == {'status': 'ok'}
