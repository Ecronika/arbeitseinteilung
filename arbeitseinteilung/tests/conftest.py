import pytest
import os
import tempfile
from app import create_app, socketio
from app.database import get_db, init_db

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    os.environ['DATABASE_PATH'] = db_path
    os.environ['SECRET_KEY'] = 'test-secret'
    
    app = create_app()
    app.config.update({
        "TESTING": True,
    })

    yield app

    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def socket_client(app):
    return socketio.test_client(app)
