from flask import Flask
from flask_socketio import SocketIO
import os

socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY', 'arbeitseinteilung-secret-2024'
    )
    app.config['DATABASE_PATH'] = os.environ.get(
        'DATABASE_PATH',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'arbeitseinteilung.db')
    )

    from .database import init_db
    with app.app_context():
        init_db(app)

    from .routes import bp
    app.register_blueprint(bp)

    from . import sockets  # noqa: F401
    socketio.init_app(app, cors_allowed_origins='*', async_mode='eventlet')

    return app
