#!/usr/bin/env python3

from eventlet import monkey_patch
monkey_patch()

from flask import Flask, render_template
from flask_session import Session
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect


db = SQLAlchemy()
csrf = CSRFProtect()
sess = Session()
socketio = SocketIO(manage_session=False)


def create_app():
    """Create Onitools aplication."""
    app = Flask(__name__)

    # App configuration
    app.config.from_object('onitools.app.default_settings')
    app.config.from_envvar('ONITOOLS_SETTINGS')

    # Initialize extensions.
    db.init_app(app)
    csrf.init_app(app)
    sess.init_app(app)
    socketio.init_app(app)

    # Blueprints.
    from .home import Home
    from .mobu import Mobu
    from .sozo import Sozo
    from .nado import Nado
    app.register_blueprint(Home)
    app.register_blueprint(Sozo, url_prefix='/sozo')
    app.register_blueprint(Mobu, url_prefix='/mobu')
    app.register_blueprint(Nado, url_prefix='/nado')

    # Define for all templates (navbar, etc.).
    @app.context_processor
    def inject_globals():
        return {
            'pages': ['Sozo', 'Mobu', 'Nado']
        }

    # Handle errors.
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    return app
