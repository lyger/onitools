#!/usr/bin/env python3

from flask import current_app, request, session
from flask_security import current_user
from flask_socketio import emit
from base64 import b64encode

from .. import socketio
from ..decorators import async

# Global storage.
active_rekis = {}


def validate_reki_id(f):
    def wrapper(msg, *args, **kwargs):
        reki_id = active_rekis.get(current_user.id, None)

        if not reki_id:
            return

        if reki_id != msg.id:
            emit('wrong canvas')
            return

        return f(msg, *args, **kwargs)
    return wrapper


@socketio.on('initialize', namespace='/reki')
@validate_reki_id
def initialize(msg):
    pass
