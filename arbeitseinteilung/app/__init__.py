"""Flask application factory für Arbeitseinteilung.

Erstellt und konfiguriert die Flask-App mit SocketIO,
Datenbank-Initialisierung und HTTP-Sicherheitsheadern.
"""

import logging
import os

import eventlet  # noqa: E402  (muss vor allen anderen Imports stehen)
eventlet.monkey_patch()

from flask import Flask  # noqa: E402
from flask_socketio import SocketIO  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s – %(message)s',
)

socketio = SocketIO()


def create_app() -> Flask:
    """Erstelle und konfiguriere die Flask-Anwendung.

    Returns:
        Flask: Die vollständig konfigurierte Flask-App-Instanz.

    Raises:
        RuntimeError: Wenn SECRET_KEY nicht als Umgebungsvariable gesetzt ist.
    """
    app = Flask(__name__)

    if os.environ.get('USE_REVERSE_PROXY', '').lower() == 'true':
        from werkzeug.middleware.proxy_fix import ProxyFix  # noqa: PLC0415
        app.wsgi_app = ProxyFix(  # type: ignore[method-assign]
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
        )

    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY environment variable is missing. "
            "It is mandatory for secure operations."
        )
    app.config['SECRET_KEY'] = secret_key
    app.config['DATABASE_PATH'] = os.environ.get(
        'DATABASE_PATH',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'arbeitseinteilung.db')
    )

    from .database import init_db  # noqa: PLC0415
    with app.app_context():
        init_db(app)

    from .routes import bp  # noqa: PLC0415
    app.register_blueprint(bp)

    from . import sockets as _sockets  # noqa: PLC0415, F401
    _ = _sockets  # Registriert Socket-Handler als Seiteneffekt
    allowed_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:8090')
    socketio.init_app(app, cors_allowed_origins=allowed_origins, async_mode='eventlet')

    @app.after_request
    def security_headers(response):
        """Füge HTTP-Sicherheitsheader zu jeder Antwort hinzu."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    return app
