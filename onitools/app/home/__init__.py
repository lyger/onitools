#!/usr/bin/env python3

from flask import Blueprint

Home = Blueprint('Home', __name__, template_folder='templates',
                 static_folder='static')

from . import events, views
