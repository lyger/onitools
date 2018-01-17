#!/usr/bin/env python3

from flask import Flask, render_template
from flask_session import Session
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy


socketio = SocketIO()
db = SQLAlchemy()


def create_app():
    """Create Onitools aplication."""
    app = Flask(__name__)

    # App configuration
    app.config.from_object('onitools.app.default_settings')
    app.config.from_envvar('ONITOOLS_SETTINGS')

    # Initialize extensions.
    socketio.init_app(app)
    db.init_app(app)
    Session(app)

    # Blueprints.
    from .home import Home
    from .mobu import Mobu
    from .sozo import Sozo
    app.register_blueprint(Home)
    app.register_blueprint(Sozo, url_prefix='/sozo')
    app.register_blueprint(Mobu, url_prefix='/mobu')

    # Define for all templates (navbar, etc.).
    @app.context_processor
    def inject_globals():
        return {
            'pages': ['Sozo', 'Mobu']
        }

    # Handle errors.
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html')

    return app
