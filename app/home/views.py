#!/usr/bin/env python3

from flask import abort, Blueprint, current_app, flash, redirect, \
    render_template, request, session, url_for

from . import Home


@Home.route('/')
def main():
    return render_template('index.html')
