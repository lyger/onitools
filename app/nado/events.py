#!/usr/bin/env python3

from flask import request, session, current_app
from flask_socketio import emit
from collections import defaultdict
from numpy import random
from threading import Lock

from .. import socketio
from .learn import permanent_generators

NUM_PER_GENERATOR = 1000
REQUEST_MORE_THRESHOLD = 500
MAX_QUEUE = 5000  # To limit memory usage.
VOTE_THRESHOLD = 2
ADD_QUEUE_THRESHOLD = 50

BUSY_SIGNAL = "<BUSY>"


class NameManager:

    def __init__(self):
        self.queue = []
        self.lock = Lock()
        self.candidates = defaultdict(int)
        self.toadd = []

    def get_names(self, num):
        num = max(1, num)
        with self.lock:
            ret = []

            # Randomly sneak in a candidate for extra training data, if any.
            if len(self.candidates) > 0:
                n_sample = min(len(self.candidates), num, random.randint(3))
                sample = random.choice([k for k in self.candidates.keys()],
                                       size=n_sample, replace=False)
                with current_app.app_context():
                    ret.extend(s for s in sample
                               if ('seen_names' not in session) or
                               (s not in session['seen_names']))
                num -= n_sample

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

    if 'seen_names' not in session:
        session['seen_names'] = []

    session['seen_names'].append(name)

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

    names, more = __managers[cat][gen].get_names(num)

    if names == BUSY_SIGNAL:
        emit('busy')
        return

    emit('names sent', {'category': cat, 'generator': gen, 'names': names})

    if more:
        permanent_generators.request_more_data(cat, gen,
                                               NUM_PER_GENERATOR,
                                               add_names_to_manager)


@socketio.on('add custom', namespace='/nado')
@validate_message
def add_custom(msg):
    cat = msg.get('category', None)
    gen = msg.get('generator', None)
    name = msg.get('name', 0)

    if len(name) > 0:
        __managers[cat][gen].add_candidate(name)

permanent_generators.start(NUM_PER_GENERATOR + REQUEST_MORE_THRESHOLD,
                           add_names_to_manager)
