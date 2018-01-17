#!/usr/bin/env python3

from flask import Blueprint

Mobu = Blueprint('Mobu', __name__, template_folder='templates',
                 static_folder='static')

from . import main
