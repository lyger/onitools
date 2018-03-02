#!/usr/bin/env python3

from flask import flash, redirect, render_template, request, session, url_for
from flask_security import current_user, login_required
from werkzeug.security import generate_password_hash, \
    check_password_hash

from . import Sozo
from .util import int_to_shortstring
from .db import db, CanvasData
from .events import active_canvases, CanvasHandler


@Sozo.context_processor
def inject_globals():
    return {
        'active_page': 'Sozo'
    }


@Sozo.before_request
def initialize_session_vars():
    if 'validated_canvases' not in session:
        session['validated_canvases'] = []


@Sozo.route('/', methods=['GET', 'POST'])
def main():
    if request.method == 'GET':
        return render_template('sozo_index.html')

    elif request.method == 'POST':
        canvas_name = request.form['name'][:60]
        canvas_pass = request.form['pass']

        if len(canvas_name) < 1:
            flash('Please provide a canvas name.', 'error')
            return render_template('sozo_index.html')

        metaopts = {
            'backgroundColor': request.form['background'],
            'truew': request.form['width'],
            'trueh': request.form['height']
        }

        canvas = CanvasData(name=canvas_name, metaopts=metaopts)

        if current_user.is_authenticated:
            current_user.sozo_canvases.append(canvas)
            db.session.add(current_user)

        db.session.add(canvas)
        db.session.commit()

        canvas.stringid = int_to_shortstring(canvas.id)

        if len(canvas_pass) > 0:
            canvas.passhash = generate_password_hash(canvas_pass)
            session['validated_canvases'].append(canvas.stringid)

        db.session.commit()

        return redirect(url_for('.show_canvas', stringid=canvas.stringid))


@Sozo.route('/canvas/<stringid>', methods=['GET', 'POST'])
def show_canvas(stringid):
    canvas = CanvasData.query.filter_by(stringid=stringid).first()
    if not canvas:
        flash('Sorry, that canvas does not exist.', 'error')
        return redirect(url_for('.main'))

    if canvas.passhash:
        # Passphrase form submitted.
        if request.method == 'POST':
            canvas_pass = request.form['pass']
            if check_password_hash(canvas.passhash, canvas_pass):
                session['validated_canvases'].append(stringid)
            else:
                flash('Passphrase incorrect.', 'error')

        if stringid not in session['validated_canvases']:
            return render_template('sozo_canvas_pass.html',
                                   canvas_name=canvas.name,
                                   stringid=stringid)

    if stringid not in active_canvases:
        active_canvases[stringid] = CanvasHandler(canvas.id)

    return render_template('sozo_canvas.html',
                           canvas_name=canvas.name,
                           metaopts=canvas.metaopts)


@Sozo.route('/delete', methods=['POST'])
@login_required
def delete(stringid=None):
    next_url = request.args.get('next', url_for('.main'))
    stringid = request.form.get('SozoID', None)

    if stringid:
        canvas = CanvasData.query.filter_by(stringid=stringid).first()

        if canvas and canvas.user_id == current_user.id:
            db.session.delete(canvas)
            db.session.commit()

    return redirect(next_url)


@Sozo.route('/rename', methods=['POST'])
@login_required
def rename(stringid=None):
    next_url = request.args.get('next', url_for('.main'))
    stringid = request.form.get('SozoID', None)

    if stringid:
        canvas = CanvasData.query.filter_by(stringid=stringid).first()

        if canvas and canvas.user_id == current_user.id:
            new_name = request.form.get('newSozoName', 'Canvas')
            if len(new_name.strip()) > 0:
                canvas.name = new_name
                db.session.add(canvas)
                db.session.commit()

    return redirect(next_url)
