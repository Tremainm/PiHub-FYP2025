from fastapi.testclient import TestClient
from app.main import app
import pytest

# Every test function that takes client as a param gets a new 'TestClient(app)'
# Ensures isolation: one test doesn't leak state into another (cookies, headers, auth, etc.)
@pytest.fixture
def client():
    return TestClient(app)
