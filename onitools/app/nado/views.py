#!/usr/bin/env python3

from flask import flash, redirect, render_template, request, session, url_for

from . import Nado
from .learn.permanent_generators import generators

genList = [{'category': cat, 'generators': gens}
           for cat, gens in generators.items()]


@Nado.context_processor
def inject_globals():
    return {
        'active_page': 'Nado'
    }


@Nado.route('/', methods=['GET'])
def main():
    return render_template('nado_index.html', generators=genList)
