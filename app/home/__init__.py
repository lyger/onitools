from flask import Blueprint

Home = Blueprint('Home', __name__, template_folder='templates',
                 static_folder='static')

from . import main, events
