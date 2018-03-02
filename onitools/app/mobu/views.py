#!/usr/bin/env python3

from flask import flash, redirect, render_template, request, session, url_for
import re

from . import Mobu

__valid_name_re = re.compile(r'[A-Za-z0-9_]+')


@Mobu.context_processor
def inject_globals():
    return {
        'active_page': 'Mobu'
    }


@Mobu.route('/', methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        encounter_name = request.form['mobuName']
        if not __valid_name_re.fullmatch(encounter_name):
            flash('Invalid encounter name.', 'error')
            return render_template('mobu_index.html')

        return redirect(url_for('.run_app', encounter_name=encounter_name))

    return render_template('mobu_index.html')


@Mobu.route('/run')
@Mobu.route('/run/<encounter_name>')
def run_app(encounter_name=None):
    if not encounter_name:
        flash('Please enter an encounter name', 'error')
        return redirect(url_for('.main'))
    return render_template('mobu_app.html')
