#!/usr/bin/env python3

from flask import flash, redirect, render_template, request, session, url_for

from . import Mobu


@Mobu.context_processor
def inject_globals():
    return {
        'active_page': 'Mobu'
    }


@Mobu.route('/')
def main():
    return render_template('mobu_index.html')


@Mobu.route('/run')
def run_app():
    return render_template('mobu_app.html')
