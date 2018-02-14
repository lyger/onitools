#!/usr/bin/env python3

from eventlet import monkey_patch
monkey_patch()

from flask import Flask, render_template, request, url_for
from flask_mail import Mail
from flask_security import Security
from flask_session import Session
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_uploads import patch_request_class
from flask_wtf.csrf import CSRFProtect
from werkzeug.exceptions import default_exceptions


db = SQLAlchemy()
csrf = CSRFProtect()
mail = Mail()
security = Security()
sess = Session()
socketio = SocketIO(manage_session=False)


def create_app():
    """Create Onitools aplication."""
    app = Flask(__name__)

    # App configuration
    app.config.from_object('onitools.app.default_settings')
    app.config.from_envvar('ONITOOLS_SETTINGS')

    from .models import user_datastore

    # Initialize extensions.
    db.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    security.init_app(app, datastore=user_datastore)
    sess.init_app(app)
    socketio.init_app(app)

    # Blueprints.
    from .home import Home
    from .mobu import Mobu
    from .sozo import Sozo
    # from .nado import Nado
    from .reki import Reki
    app.register_blueprint(Home)
    app.register_blueprint(Sozo, url_prefix='/sozo')
    app.register_blueprint(Mobu, url_prefix='/mobu')
    # app.register_blueprint(Nado, url_prefix='/nado')
    app.register_blueprint(Reki, url_prefix='/reki')

    # Set a maximum request size of 20 MB.
    patch_request_class(app, size=20 * 1024 * 1024)

    @app.before_first_request
    def init_db():
        db.create_all()
        admin_role = user_datastore.find_or_create_role(
            'admin', description='')
        member_role = user_datastore.find_or_create_role(
            'member', description='')
        admin_user = user_datastore.get_user(1)
        user_datastore.add_role_to_user(admin_user, admin_role)
        db.session.commit()

    # Define for all templates (navbar, etc.).
    @app.context_processor
    def inject_globals():
        return {
            # 'pages': ['Sozo', 'Mobu', 'Nado', 'Reki']
            'pages': ['Sozo', 'Mobu', 'Reki']
        }

    # Handle errors.
    def handle_http_error(e):
        next_url = url_for('Home.main')
        try:
            message = 'Something went wrong.'
            if e.code == 401 or e.code == 403:
                message = 'You don\'t have permission to view this page.'
            elif e.code == 404 or e.code == 410:
                message = 'Sorry, we couldn\'t find what you were looking for.'
            elif e.code == 405 or e.code == 408:
                message = 'The server couldn\'t process your request.'
            elif e.code == 413:
                message = 'Request too large.'
                next_url = request.path

            return render_template('error.html',
                                   error_code=e.code,
                                   message=message,
                                   next_url=next_url), e.code
        except:
            message = 'Something went wrong. ' + \
                'Please contact the server administrator.'
            return render_template('error.html',
                                   error_code=500,
                                   message=message,
                                   next_url=next_url), 500

    for code in default_exceptions:
        app.errorhandler(code)(handle_http_error)

    return app
