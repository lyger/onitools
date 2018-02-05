#!/usr/bin/env python3

import _dynet as dy
import numpy as np
from collections import OrderedDict

# End of word token.
EOW = "<EOW>"


def sample_softmax(x):
    return min((x.cumsum() < np.random.rand()).sum(), len(x) - 1)


def isDynetParam(p):
    return isinstance(p, dy.Parameters) or \
        isinstance(p, dy.LookupParameters) or \
        isinstance(p, dy._RNNBuilder)


class WordGenerator:

    def __init__(self,
                 vocabulary,
                 embedding_dim,
                 hidden_dim,
                 layers,
                 model):

        vocabulary = np.unique(list(vocabulary) + [EOW])

        V = len(vocabulary)

        self._model = model
        self._parameters = OrderedDict()

        self.c2i = {c: i for i, c in enumerate(vocabulary)}
        self.i2c = {i: c for i, c in enumerate(vocabulary)}
        self.lookup = model.add_lookup_parameters((V, embedding_dim))
        self.lstm = dy.VanillaLSTMBuilder(layers,
                                          embedding_dim,
                                          hidden_dim,
                                          model)
        self.W = model.add_parameters((V, hidden_dim))
        self.b = model.add_parameters((V))

    def word_to_indices(self, word):
        word = [EOW] + list(word) + [EOW]
        return [self.c2i[c] for c in word]

    def train_batch(self, words):
        losses = []

        W = dy.parameter(self.W)
        b = dy.parameter(self.b)

        for word in words:
            wlosses = []

            word = self.word_to_indices(word)

            s = self.lstm.initial_state()

            for c, next_c in zip(word, word[1:]):
                s = s.add_input(self.lookup[c])
                unnormalized = dy.affine_transform([b, W, s.output()])
                wlosses.append(dy.pickneglogsoftmax(unnormalized, next_c))

            losses.append(dy.esum(wlosses) / len(word))

        return dy.esum(losses) / len(words)

    def generate(self, num, limit=40, beam=3):
        dy.renew_cg()

        generated = []

        W = dy.parameter(self.W)
        b = dy.parameter(self.b)

        for wordi in range(num):

            # Initialize the LSTM state with EOW token.
            start_state = self.lstm.initial_state()
            start_state = start_state.add_input(self.lookup[self.c2i[EOW]])
            best_states = [('', start_state, 0)]

            final_hypotheses = []

            # Perform beam search.
            while len(final_hypotheses) < beam and len(best_states) > 0:
                new_states = []

                for hyp, s, p in best_states:

                    # Cutoff when we exceed the character limit.
                    if len(hyp) >= limit:
                        final_hypotheses.append((hyp, p))
                        continue

                    # Get the prediction from the current LSTM state.
                    unnormalized = dy.affine_transform([b, W, s.output()])
                    softmax = dy.softmax(unnormalized).npvalue()

                    # Sample beam number of times.
                    for beami in range(beam):
                        ci = sample_softmax(softmax)
                        c = self.i2c[ci]
                        next_p = softmax[ci]
                        logp = p - np.log(next_p)

                        if c == EOW:
                            # Add final hypothesis if we reach end of word.
                            final_hypotheses.append((hyp, logp))
                        else:
                            # Else add to states to search next time step.
                            new_states.append((hyp + c,
                                               s.add_input(self.lookup[ci]),
                                               logp))

                # Sort and prune the states to within the beam.
                new_states.sort(key=lambda t: t[-1])
                best_states = new_states[:beam]

            final_hypotheses.sort(key=lambda t: t[-1])

            generated.append(final_hypotheses[0][0])

        return generated

    def save(self, fname):
        dy.save(fname, [v for k, v in self._parameters.items()])

    def load(self, fname):
        params = dy.load(fname, self._model)
        for name, param in zip(self._parameters, params):
            self.__setattr__(name, param)

    def __setattr__(self, name, value):
        '''When we add an attribute, add it to the internal parameter list if
        the attribute is of type dy.Parameters.
        '''
        if isDynetParam(value):
            self._parameters[name] = value
        super().__setattr__(name, value)


def train(network,
          trainer,
          words,
          epochs,
          batch_size=100,
          max_batch_num=5,
          callback=lambda *args: None):
    last_loss = None

    batch_num = min(len(words) // batch_size + 1, max_batch_num)

    for enum in range(epochs):
        eloss = 0
        bnum = 0

        for bi in range(batch_num):
            bwords = np.random.choice(words, size=batch_size, replace=True)
            if len(bwords) < 1:
                continue
            dy.renew_cg()
            loss = network.train_batch(bwords)
            eloss += loss.value()
            loss.backward()
            trainer.update()
            bnum += 1

        eloss = eloss / bnum

        if last_loss:
            last_loss = 0.95 * last_loss + 0.05 * eloss
        else:
            last_loss = eloss

        # print('Epoch {} loss: {:.6f}  Running avg.: {:.6f}'.format(
        #     enum + 1, eloss, last_loss))
        callback(enum, eloss, last_loss)

    return last_loss
