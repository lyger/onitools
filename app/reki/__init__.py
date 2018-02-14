#!/usr/bin/env python3

from flask import Blueprint

Reki = Blueprint('Reki', __name__, template_folder='templates',
                 static_folder='static')

from . import db, events, forms, views
