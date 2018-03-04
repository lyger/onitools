#!/usr/bin/env python3

from datetime import datetime  # May delete later
from flask import request, session
from flask_socketio import emit, join_room
from sqlalchemy.orm import load_only

from .. import socketio, db
from .db import CanvasData

UNDO_MODE = 8
NULL_MODE = -1
active_canvases = {}
sid_connections = {}


def validate_cid(f):
    def wrapper(data, *args, **kwargs):
        cid = data.get('cid', None)

        if not cid:
            return

        if cid not in active_canvases:
            emit('reload')
            return

        return f(cid, data, *args, **kwargs)

    return wrapper


class CanvasHandler:

    def __init__(self, canvas_id):
        canvas = CanvasData.query.options(load_only('data')).get(canvas_id)
        self.data = canvas.data or []
        self.cid = canvas_id
        self.clients = set()
        self.clientdata = {}
        self.alive = True
        db.session.close()

    def addClient(self, client):
        self.clients.add(client)
        self.clientdata[client] = []

    def removeClient(self, client):
        self.clients.discard(client)
        self.clientdata.pop(client, None)
        return len(self.clients)

    def push(self, client, obj):
        obj["id"] = len(self.data)
        self.data.append(obj)
        self.clientdata[client].append(obj['id'])

    def undo(self, client):
        to_undo = self.clientdata[client].pop()
        self.data[to_undo]['mode'] += UNDO_MODE
        return to_undo

    def redo(self, client, objid):
        self.clientdata[client].append(objid)
        obj = self.data[objid]
        obj['mode'] -= UNDO_MODE
        return obj

    def commit(self):
        canvas = CanvasData.query.get(self.cid)
        canvas.data = self.data
        db.session.add(canvas)
        db.session.commit()
        db.session.close()


@socketio.on('connect', namespace='/sozo')
def acknowledge_connect():
    sid_connections[request.sid] = [1, set()]


@socketio.on('disconnect', namespace='/sozo')
def client_leave():
    sid_connections[request.sid][0] -= 1
    if sid_connections[request.sid][0] < 1:
        sid_connections[request.sid][0] = 0
        for cid in sid_connections[request.sid][1]:
            handler = active_canvases[cid]
            if handler.removeClient(request.sid) == 0:
                handler.commit()
                active_canvases.pop(cid, None)
        sid_connections.pop(request.sid, None)


@socketio.on('init canvas', namespace='/sozo')
@validate_cid
def initialize_canvas(cid, data):
    join_room(cid)

    sid_connections[request.sid][1].add(cid)

    active_canvases[cid].addClient(request.sid)

    if len(active_canvases[cid].data) > 0:
        emit('loading')
        for obj in active_canvases[cid].data:
            if obj['mode'] < UNDO_MODE:
                emit('draw update', obj)
            else:
                # Don't waste bandwidth sending undone objects until needed
                emit('draw update', {'id': obj['id'], 'mode': NULL_MODE})
    emit('done loading')


@socketio.on('draw action', namespace='/sozo')
@validate_cid
def draw_to_canvas(cid, data):
    obj = data['obj']
    active_canvases[cid].push(request.sid, obj)
    emit('draw update', obj, room=cid)
    emit('draw confirm', {'id': obj['id']})


@socketio.on('undo', namespace='/sozo')
@validate_cid
def undo_from_client(cid, data):
    to_undo = active_canvases[cid].undo(request.sid)
    emit('undo update', {'id': to_undo}, room=cid)
    emit('undo confirm', {'id': to_undo})


@socketio.on('redo', namespace='/sozo')
@validate_cid
def redo_from_client(cid, data):
    obj = active_canvases[cid].redo(request.sid, data['id'])
    emit('redo update', obj, room=cid)
    emit('redo confirm', {'id': obj['id']})


@socketio.on('resend', namespace='/sozo')
@validate_cid
def resend_from(cid, data):
    ctop = data['from']
    for obj in active_canvases[cid].data[ctop:]:
        emit('draw update', obj, room=cid)
