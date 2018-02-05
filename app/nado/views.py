#!/usr/bin/env python3

from flask import flash, redirect, render_template, request, session, url_for

from . import Nado
from .learn.permanent_generators import generators


@Nado.context_processor
def inject_globals():
    return {
        'active_page': 'Nado'
    }


@Nado.route('/', methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        train_data = request.form['nadoData']
    return render_template('nado_index.html', generators=generators)


# @Nado.route('/custom', methods=['GET', 'POST'])
# def custom():
#     if request.method == 'POST':
#         train_data = request.form['nadoData']
#     return render_template('nado_custom.html')
