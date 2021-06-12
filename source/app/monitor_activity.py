#
# Copyright (c) 2019, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# monitor activity (max dB value diff signal to noise per range bin)
#

import os
import sys
import time
import math

try:

    __base__ = os.path.dirname(os.path.abspath(__file__))
    while 'lib' not in [d for d in os.listdir(__base__) if os.path.isdir(os.path.join(__base__, d))]: __base__ = os.path.join(__base__, '..')
    if __base__ not in sys.path: sys.path.append(__base__)
    
    from lib.capture import *

except ImportError as e:
    print(e, file=sys.stderr, flush=True)
    sys.exit(3)

# ------------------------------------------------

RANGE_BIN = 1.0  # meters

# ------------------------------------------------

def update(data):
    
    if 'range_profile' not in data: return
    
    r = data['range_profile']

    if 'noise_profile' in data:
        n = data['noise_profile']
    else:
        n = [0] * len(r)

    if len(r) == len(n):

        bin = range_max / len(r)
        x = [i*bin for i in range(len(r))]
        x = [v - range_bias for v in x]
        
        segm = [[]]
        for i in range(1, len(x)):
            if x[i] < RANGE_BIN * len(segm):
                segm[-1].append(r[i] - n[i])  # mathematically not correct (dB values), but ok for this purpose
            else:
                segm.append([])
        
        segm.pop()
        
        try:
            s = ('{:.3f}' + ' {}' * len(segm)).format(time.time(), *[max(0, int(round(max(seg)))) for seg in segm])
            fh.write(s + '\n')
            fh.flush()
        except:
            pass

        os.fsync(fh.fileno())

# ------------------------------------------------  

if __name__ == "__main__":

    if len(sys.argv[1:]) != 2:
        print('Usage: {} {}'.format(sys.argv[0].split(os.sep)[-1], '<range_maximum> <range_bias>'))
        sys.exit(1)
    
    fh, fp = None, 'log'

    try:

        range_max = float(sys.argv[1])
        range_bias = float(sys.argv[2])
 
        this_name = os.path.basename(sys.argv[0])
        this_name = this_name[len('capture '):-len('.py')]
                 
        if not os.path.exists(fp): os.makedirs(fp)
        utc = time.strftime('%Y%m%d-%H%M%S', time.gmtime())
        fh = open('{}/{}-{}.log'.format(fp, this_name, utc), 'w')        

        start_capture(update)
        
    except Exception as e:
        print(e, file=sys.stderr, flush=True)
        sys.exit(2)
