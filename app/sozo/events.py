#!/usr/bin/env python3

from datetime import datetime  # May delete later
from flask import request, session
from flask_socketio import emit, join_room
from sqlalchemy.orm.attributes import flag_modified

from .. import socketio, db

UNDO_MODE = 8
NULL_MODE = -1
active_canvases = {}
sid_connections = {}


def log(*msg):
    print(datetime.today().strftime("%y-%m-%d %H:%M:%S"), *msg)


class CanvasHandler:

    def __init__(self, canvas):
        self.data = canvas.data or []
        self.canvas = canvas
        self.clients = set()
        self.clientdata = {}
        self.alive = True

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
        self.canvas.data = self.data
        flag_modified(self.canvas, 'data')
        db.session.add(self.canvas)
        db.session.commit()


@socketio.on('connect', namespace='/sozo')
def acknowledge_connect():
    log("CONNECT:", request.sid)
    sid_connections[request.sid] = [1, set()]


@socketio.on('disconnect', namespace='/sozo')
def client_leave():
    log("LEAVE:", request.sid)
    sid_connections[request.sid][0] -= 1
    if sid_connections[request.sid][0] < 1:
        sid_connections[request.sid][0] = 0
        for cid in sid_connections[request.sid][1]:
            handler = active_canvases[cid]
            if handler.removeClient(request.sid) == 0:
                handler.commit()
                active_canvases.pop(cid, None)
                log('Removed', cid, 'from memory.')
        sid_connections.pop(request.sid, None)


@socketio.on('init canvas', namespace='/sozo')
def initialize_canvas(data):
    cid = data['cid']
    join_room(cid)

    # Due to browser behavior (back button, etc.) the page may be loaded
    # despite the canvas not being active on server.
    if cid not in active_canvases:
        emit('reload')
        return

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
def draw_to_canvas(data):
    cid = data['cid']
    obj = data['obj']
    active_canvases[cid].push(request.sid, obj)
    emit('draw update', obj, room=cid)
    emit('draw confirm', {'id': obj['id']})


@socketio.on('undo', namespace='/sozo')
def undo_from_client(data):
    cid = data['cid']
    to_undo = active_canvases[cid].undo(request.sid)
    emit('undo update', {'id': to_undo}, room=cid)
    emit('undo confirm', {'id': to_undo})


@socketio.on('redo', namespace='/sozo')
def redo_from_client(data):
    cid = data['cid']
    obj = active_canvases[cid].redo(request.sid, data['id'])
    emit('redo update', obj, room=cid)
    emit('redo confirm', {'id': obj['id']})


@socketio.on('resend', namespace='/sozo')
def resend_from(data):
    cid = data['cid']
    ctop = data['from']
    for obj in active_canvases[cid].data[ctop:]:
        emit('draw update', obj, room=cid)
