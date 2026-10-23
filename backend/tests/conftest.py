import pytest
from backend.app import create_app
from backend.database import init_db

@pytest.fixture
def app_ctx():
    app = create_app({"TESTING": True})
    with app.app_context():
        init_db()
        yield app

@pytest.fixture
def client(app_ctx):
    with app_ctx.test_client() as c:
        yield c
