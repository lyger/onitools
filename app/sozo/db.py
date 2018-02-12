#!/usr/bin/env python3

from .. import db


class CanvasData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stringid = db.Column(db.String(10))
    name = db.Column(db.String(60), nullable=False)
    passhash = db.Column(db.String(100))
    metaopts = db.Column(db.PickleType, nullable=False)
    data = db.Column(db.PickleType)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
