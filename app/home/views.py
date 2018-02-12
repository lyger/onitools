#!/usr/bin/env python3

from flask import flash, redirect, render_template, request, session, url_for
from flask_security import current_user, login_required

from . import Home


@Home.route('/')
def main():
    return render_template('index.html')


@Home.route('/profile')
@login_required
def profile():
    # NOT YET IMPLEMENTED
    return render_template('profile.html')
