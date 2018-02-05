#!/usr/bin/env python3

from .character_lstm import dy, np, WordGenerator, train
from collections import OrderedDict
from os import path
from threading import Lock
from time import sleep
import pathlib

from ...decorators import async

generators = OrderedDict([
    ('Town names',
        [
            'English',
            'German',
            'French',
            'Norse'
        ]),
    ('Character names',
        [
            'Anglo-Saxon',
            'Dutch',
            'German',
            'Misc'
        ]),
    ('Monster names',
        [
            'Angels',
            'Demons',
            'Misc'
        ])
])

EMB_DIM = 10
HID_DIM = 20
LAYERS = 1

EPSILON = 5e-3
MIN_EPOCHS = 200
MAX_EXTRA_EPOCHS = 2000
GEN_PER = 100

SLEEP_TIME = 3 * 60 * 60

ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

__models = {}

_dynet_lock = Lock()


def __P(*args):
    return path.join(path.dirname(__file__),
                     *[s.replace(' ', '_') for s in args])


def __create_file_structure():
    for category in generators:
        pathlib.Path(__P('data', category)).mkdir(parents=True, exist_ok=True)
        pathlib.Path(__P('model', category)).mkdir(parents=True, exist_ok=True)


def _vocab_from_data(data):
    # Ensure that all standard English leters are valid.
    vocab = set(list(ALPHABET))
    for w in data:
        vocab.update(list(w))
    return ''.join([c for c in sorted(vocab)])


class __ModelWrapper:

    def __init__(self, data_path, model_path):
        self.pc = dy.ParameterCollection()
        self.model_path = model_path
        self.data_path = data_path
        self.lock = Lock()

        with open(data_path, 'r') as dfile:
            self.data = [l.strip() for l in dfile]
            self.data = [l for l in self.data if len(l) > 0]

        self.length_limit = min(max(len(l) for l in self.data), 50)

        vocab_path = model_path + '.vocab'

        if pathlib.Path(vocab_path).is_file():
            with open(vocab_path, 'r') as vfile:
                vocab = vfile.readline().rstrip()
            model_exists = True
        else:
            vocab = _vocab_from_data(self.data)
            with open(vocab_path, 'w') as vfile:
                vfile.write(vocab + '\n')

        self.generator = WordGenerator(vocab,
                                       EMB_DIM,
                                       HID_DIM,
                                       LAYERS,
                                       self.pc)

        if pathlib.Path(model_path + '.meta').is_file():
            self.generator.load(model_path)
            self.has_new_data = False
        else:
            self.has_new_data = True
            self.train_loop()

    def save_all(self):
        '''Save both the model and the data.'''
        with self.lock:
            self.generator.save(self.model_path)
            with open(self.data_path, 'w') as ofile:
                for n in self.data:
                    ofile.write(n + '\n')

    def train_loop(self):
        with self.lock, _dynet_lock:
            trainer = dy.AdadeltaTrainer(self.pc)

            last_loss = train(self.generator, trainer, self.data, MIN_EPOCHS)

            extra_loops = MAX_EXTRA_EPOCHS // 50

            for _ in range(extra_loops):
                next_loss = train(self.generator, trainer, self.data, 50)

                if last_loss - next_loss < EPSILON:
                    break

                last_loss = next_loss

            self.has_new_data = False

        self.save_all()

    def generate(self, num):
        genned = []

        with self.lock, _dynet_lock:
            # Since data could increase, we will allow some duplicates.
            skip = set(np.random.choice(self.data,
                                        size=min(len(self.data), 200),
                                        replace=False))
            for _ in range(max(2, 2 * num // GEN_PER)):
                for n in self.generator.generate(GEN_PER,
                                                 limit=self.length_limit,
                                                 beam=2):
                    if n not in skip:
                        genned.append(n)
                        skip.add(n)
                if len(genned) >= num:
                    break

        return genned

    def extend_data(self, new_data):
        with self.lock:
            self.data.extend(new_data)
            self.has_new_data = True


# def __load_models():
#     models = {}
#     for category, genlist in generators.items():
#         models[category] = {}
#         for gen in genlist:
#             model_path = __P('model', category, gen)
#             data_path = __P('data', category, gen) + '.txt'

#             models[category][gen] = __ModelWrapper(data_path, model_path)
#     return models


@async
def request_more_data(category, generator, num, callback):
    callback(category, generator, __models[category][generator].generate(num))


@async
def add_data(category, generator, new_data):
    __models[category][generator].extend_data(new_data)


@async
def start(num, callback):
    dyparams = dy.DynetParams()
    dyparams.set_mem(250)

    dyparams.init()

    __create_file_structure()

    # __models.update(__load_models())
    for category, genlist in generators.items():
        __models[category] = {}
        for genname in genlist:
            model_path = __P('model', category, genname)
            data_path = __P('data', category, genname) + '.txt'

            __models[category][genname] = __ModelWrapper(data_path, model_path)
            request_more_data(category, genname, num, callback)

    # for category, gendict in __models.items():
    #     for genname in gendict:
    #         request_more_data(category, genname, num, callback)

    while True:
        sleep(SLEEP_TIME)
        for category, gendict in __models.items():
            for genname, modelwrap in gendict.items():
                # Before we re-train the model (if necessary), make sure
                # the frontend has a buffer of generated names.
                if modelwrap.has_new_data:
                    callback(category, genname, modelwrap.generate(num))
                    modelwrap.train_loop()
