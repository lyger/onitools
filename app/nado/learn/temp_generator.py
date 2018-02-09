#!/usr/bin/env python3

from character_lstm import dy, np, WordGenerator, train
from sys import argv, stdin, stdout
from time import sleep


def stdout_callback(e, *args):
    stdout.write('{}\n'.format(e))
    stdout.flush()

if __name__ == '__main__':
    dyparams = dy.DynetParams()
    dyparams.set_mem(20)

    dyparams.init()

    words = [w.strip() for w in stdin.readlines()]

    vocab = set()
    for w in words:
        vocab.update(list(w))

    vocab = ''.join(sorted(vocab))

    m = dy.ParameterCollection()
    generator = WordGenerator(vocab, 6, 12, 1, m)
    trainer = dy.AdadeltaTrainer(m)

    n_epochs = int(argv[1])

    n_generate = int(argv[2])

    train(generator, trainer, words, n_epochs, callback=stdout_callback)

    stdout.write('END\n')

    genned = set()

    for _ in range(6):
        genned.update(generator.generate(n_generate // 4 + 1, beam=2))
        if len(genned) >= n_generate:
            break

    for g in list(genned)[:n_generate]:
        stdout.write('{}\n'.format(g))
