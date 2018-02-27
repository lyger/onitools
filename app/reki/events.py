#!/usr/bin/env python3

from flask_security import current_user
from flask_socketio import emit
from base64 import b64encode
from sqlalchemy.orm import load_only

from .. import db, socketio
from .db import RekiData

# Global storage.
active_rekis = {}


def validate_reki_id(f):
    def wrapper(*args, **kwargs):
        # reki_id = active_rekis.get(current_user.id, None)
        reki_id = active_rekis.get(1, None)

        if len(args) < 1 or not reki_id:
            return

        msg = args[0]

        if reki_id != msg.get('id', None):
            emit('wrong reki')
            return

        return f(*args, **kwargs)
    return wrapper


@socketio.on('init rid', namespace='/reki')
def initialize_rid():
    # reki_id = active_rekis.get(current_user.id, None)
    reki_id = active_rekis.get(1, None)

    if not reki_id:
        emit('wrong reki')
        return

    emit('send rid', {'rid': reki_id})


@socketio.on('init settings', namespace='/reki')
@validate_reki_id
def initialize_settings(msg):
    reki_id = msg['id']
    reki = RekiData.query.options(
        load_only('settings', 'world_data')).get(reki_id)

    emit('send settings', {'settings': reki.settings,
                           'world_data': reki.world_data})


@socketio.on('init map image', namespace='/reki')
@validate_reki_id
def initialize_map_image(msg):
    reki_id = msg['id']
    reki = RekiData.query.options(load_only('map_image')).get(reki_id)
    img_data = b64encode(reki.map_image).decode('utf-8')

    emit('send map image', {'data': img_data})
