#!/usr/bin/env python3

from flask import Blueprint

Nado = Blueprint('Nado', __name__, template_folder='templates',
                 static_folder='static')

from . import events, views
