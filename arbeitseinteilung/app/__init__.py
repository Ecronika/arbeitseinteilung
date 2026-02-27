import eventlet
eventlet.monkey_patch()

import logging
from flask import Flask
from flask_socketio import SocketIO
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s – %(message)s',
)

socketio = SocketIO()


def create_app():
    app = Flask(__name__)

    if os.environ.get('USE_REVERSE_PROXY', '').lower() == 'true':
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        raise RuntimeError("SECRET_KEY environment variable is missing. It is mandatory for secure operations.")
    app.config['SECRET_KEY'] = secret_key
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
    allowed_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:8090')
    socketio.init_app(app, cors_allowed_origins=allowed_origins, async_mode='eventlet')

    # ─── HTTP-Sicherheitsheader ───────────────────────────────────────────────
    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    return app
