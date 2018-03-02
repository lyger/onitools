#!/usr/bin/env python3

from app import socketio, create_app
import warnings

if __name__ == "__main__":
    app = create_app()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        socketio.run(app)
