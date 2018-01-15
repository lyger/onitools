from flask import Blueprint

Sozo = Blueprint('Sozo', __name__, template_folder='templates',
                 static_folder='static')

from . import db, events, main, util
