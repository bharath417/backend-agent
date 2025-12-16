import pytest
from unittest.mock import MagicMock
from main import app as flask_app

@pytest.fixture
def app():
    yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def mock_bq_client(mocker):
    """Mocks the BigQuery client."""
    mock_client = MagicMock()
    mocker.patch('main.bq_client', mock_client)
    return mock_client