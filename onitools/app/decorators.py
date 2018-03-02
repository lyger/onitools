#!/usr/bin/env python3

from . import socketio


def async(f):
    def wrapper(*args, **kwargs):
        socketio.start_background_task(f, *args, **kwargs)
    return wrapper
