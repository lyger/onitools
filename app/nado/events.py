#!/usr/bin/env python3

from flask import current_app, request, session
from flask_socketio import emit
from collections import defaultdict
from datetime import datetime, timedelta
from numpy import random
from os import path
from subprocess import Popen, PIPE, DEVNULL
from threading import Lock

from .. import socketio
from ..decorators import async
from .learn import permanent_generators

NUM_PER_GENERATOR = 1000
REQUEST_MORE_THRESHOLD = 500
MAX_QUEUE = 5000  # To limit memory usage.
VOTE_THRESHOLD = 2
ADD_QUEUE_THRESHOLD = 50

BUSY_SIGNAL = "<BUSY>"

CUSTOM_TIME_LIMIT = timedelta(minutes=10)
CUSTOM_MAX_DATA = 200
CUSTOM_MAX_RUNNING = 3
custom_running = 0


def fmt_plural(str, num):
    return ('{} ' + str + '{}').format(num, '' if num == 1 else 's')


class NameManager:

    def __init__(self):
        self.queue = []
        self.lock = Lock()
        self.candidates = defaultdict(int)
        self.toadd = []

    def get_names(self, num, seen=set()):
        num = max(1, num)
        with self.lock:
            ret = []

            # Randomly sneak in a candidate for extra training data, if any.
            if len(self.candidates) > 0:
                n_sample = min(len(self.candidates), num, random.randint(3))
                sample = random.choice([k for k in self.candidates.keys()],
                                       size=n_sample, replace=False)
                ret.extend(s for s in sample if s not in seen)
                num -= len(ret)

            ret.extend(self.queue[:num])
            self.queue = self.queue[num:]

            do_request_more = len(self.queue) < REQUEST_MORE_THRESHOLD

            random.shuffle(ret)

        if len(ret) < num:
            return BUSY_SIGNAL, False

        return ret, do_request_more

    def add_names(self, names):
        with self.lock:
            self.queue.extend(names)
            self.queue = self.queue[:MAX_QUEUE]

    def add_candidate(self, cand):
        with self.lock:
            self.candidates[cand] = 0

    def vote(self, name, up=True):
        with self.lock:
            if up:
                self.candidates[name] += 1
            else:
                self.candidates[name] -= 1

            if self.candidates[name] > VOTE_THRESHOLD:
                self.toadd.append(name)
                del self.candidates[name]
            elif self.candidates[name] < -VOTE_THRESHOLD:
                del self.candidates[name]

            while name in self.queue:
                self.queue.remove(name)

        return len(self.toadd)

    def clear_add_queue(self):
        with self.lock:
            self.toadd = []


__managers = {category: {genname: NameManager() for genname in genlist}
              for category, genlist in permanent_generators.generators.items()}


def validate_message(f):
    def wrapper(msg, *args, **kwargs):
        cat = msg.get('category', None)
        gen = msg.get('generator', None)
        if cat not in __managers or gen not in __managers[cat]:
            emit('invalid')
            return None

        return f(msg, *args, **kwargs)

    return wrapper


def add_names_to_manager(category, generator, new_data):
    __managers[category][generator].add_names(new_data)


@socketio.on('vote', namespace='/nado')
@validate_message
def vote(msg):
    cat = msg.get('category', None)
    gen = msg.get('generator', None)
    name = msg.get('name', None)
    up = msg.get('up', False)

    seen = session.get('nado_names_seen', {})
    seen[name] = True
    session['nado_names_seen'] = seen

    mngr = __managers[cat][gen]
    add_queue = mngr.vote(name, up)

    if add_queue >= ADD_QUEUE_THRESHOLD:
        print('Adding:', mngr.toadd, 'to', cat, gen)
        permanent_generators.add_data(cat, gen, mngr.toadd)
        mngr.clear_add_queue()


@socketio.on('send names', namespace='/nado')
@validate_message
def send_names(msg):
    cat = msg.get('category', None)
    gen = msg.get('generator', None)
    num = msg.get('number', 0)

    seen = session.get('nado_names_seen', {})

    names, more = __managers[cat][gen].get_names(num, seen)

    if names == BUSY_SIGNAL:
        emit('busy')
        return

    emit('names sent', {'category': cat, 'generator': gen, 'names': names})

    if more:
        permanent_generators.request_more_data(cat, gen,
                                               NUM_PER_GENERATOR,
                                               add_names_to_manager)


@socketio.on('add suggestion', namespace='/nado')
@validate_message
def add_suggestion(msg):
    cat = msg.get('category', None)
    gen = msg.get('generator', None)
    name = msg.get('name', '')

    seen = session.get('nado_names_seen', {})
    seen[name] = True
    session['nado_names_seen'] = seen

    if len(name) > 0:
        __managers[cat][gen].add_candidate(name)


# Since socketio is async already, no need to spawn new thread.
@socketio.on('train custom', namespace='/nado')
def train_custom(msg):
    global custom_running

    # Check if too many generators are running server-side.
    if custom_running >= CUSTOM_MAX_RUNNING:
        emit('custom error', {'message': 'Sorry! The server is under heavy ' +
                              'load. Please try again later'})

    # Check if the user has used the generator already.
    last_used = session.get('nado_custom_last_used', datetime.min)
    now = datetime.today()
    since_used = now - last_used

    if since_used < CUSTOM_TIME_LIMIT:
        seconds = (CUSTOM_TIME_LIMIT - since_used).seconds
        minutes = round(seconds / 60)

        msg_time = fmt_plural('minute', minutes) if minutes > 0 \
            else fmt_plural('second', seconds)

        emit('custom error',
             {'message': 'Please wait {} '.format(msg_time) +
              'before using again.'})
        return

    words = list(set(msg.get('examples', [])))[:CUSTOM_MAX_DATA]

    if len(words) < 100:
        emit('custom error',
             {'message': 'Error! Not enough examples provided. ' +
              'Please refresh and try again.'})
        return

    n_epochs = 750
    n_gen = 200

    session['nado_custom_last_used'] = now

    run_temp_generator(words, request.sid)


@async
def run_temp_generator(words, sid):
    global custom_running

    n_epochs = 750
    n_gen = 200

    script = path.join(path.dirname(__file__),
                       'learn', 'temp_generator.py')

    custom_running += 1

    try:
        p = Popen(['python3', script, str(n_epochs), str(n_gen)],
                  stdin=PIPE, stdout=PIPE, stderr=DEVNULL)

        for w in words:
            p.stdin.write((w + '\n').encode())

        genned = []
        training = True
        pct = 0

        p.stdin.close()

        for stat in iter(p.stdout.readline, b''):
            stat = stat.decode().strip()
            if len(stat) < 1:
                continue

            if training:
                if stat == 'END':
                    training = False
                    continue

                stat = (int(stat) * 100) // n_epochs
                if stat > pct:
                    socketio.emit('custom progress', {'progress': stat},
                                  namespace='/nado', room=sid)

                pct = stat
            else:
                genned.append(stat)
        p.stdout.close()

        socketio.emit('custom results', {'results': genned},
                      namespace='/nado', room=sid)

    except Exception as e:
        print(e)
        socketio.emit('custom error',
                      {'message': 'Error! Something went wrong during ' +
                       'training. Please refresh and try again.'},
                      namespace='/nado', room=sid)

    finally:
        p.terminate()
        custom_running = max(0, custom_running - 1)

permanent_generators.start(NUM_PER_GENERATOR + REQUEST_MORE_THRESHOLD,
                           add_names_to_manager)
