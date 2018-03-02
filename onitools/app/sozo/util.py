#!/usr/bin/env python3

# Decimal codes:
#  48 to 57 for numbers
#  65 to 90 for capital letters
#  97 to 122 for lower case letters
__chrlookup = [chr(i) for i in range(48, 58)] + \
    [chr(i) for i in range(65, 91)] + \
    [chr(i) for i in range(97, 123)]
__ordlookup = {c: i for i, c in enumerate(__chrlookup)}
__k = 15485863
__p = 104395301
__n = len(__chrlookup)


def int_to_shortstring(i):
    j = ((i + 1) * __k) % __p
    s = ''
    while j > 0:
        j, r = divmod(j, __n)
        s += __chrlookup[r]
    return s


def shortstring_to_int(s):
    j = 0
    for c in reversed(s):
        j *= __n
        j += __ordlookup[c]
    while True:
        i, r = divmod(j, __k)
        if r == 0:
            return i - 1
        j += __p
