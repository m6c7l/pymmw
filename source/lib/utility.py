#
# Copyright (c) 2018, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# utility functions
#

def hex2dec(value):
    """ 'ff' -> 255 ; 'af fe' -> (175, 254) ; ('af', 'fe) -> (175, 254) """
    if type(value) == str:
        value = value.strip()
        if ' ' not in value:
            return int(value, 16)
        else:
            return hex2dec(value.split(' '))
    else:
        return tuple(int(item, 16) for item in value)


def dec2hex(value, delim=''):
    """ 12648430 -> 'c0ffee' ; (255, 255) -> 'ffff' ; (256 * 256 - 1, 10) -> 'ffff0a' """
    if type(value) == int:
        s = hex(value)
        return '0' * (len(s) % 2) + s[2:]     
    else:       
        return delim.join(dec2hex(item, delim) for item in value) 


def dec2bit(value, bits=8):
    """ bits=8: 42 -> (False, True, False, True, False, True, False, False) """
    v = value % 2**bits
    seq = tuple(True if c == '1' else False for c in bin(v)[2:].zfill(bits)[::-1])
    if value - v > 0: seq = seq + dec2bit(value // 2**bits)
    return seq
 
 
def intify(value, base=16, size=2):
    if type(value) not in (list, tuple, bytes,):
        value = (value,)
    if (type(value) in (bytes,) and base == 16) or (type(value) in (list, tuple,)):
        return sum([item*((base**size)**i) for i, item in enumerate(value)])
    else:
        return sum([((item // 16)*base+(item % 16))*((base**size)**i) for i, item in enumerate(value)])


def split(value, size=2):
    return tuple(value[0 + i:size + i] for i in range(0, len(value), size))
