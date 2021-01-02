#
# Copyright (c) 2019, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# range and noise profile - capture
#

import os, sys, time

try:

    __base__ = os.path.dirname(os.path.abspath(__file__))
    while 'lib' not in [d for d in os.listdir(__base__) if os.path.isdir(os.path.join(__base__, d))]: __base__ = os.path.join(__base__, '..')
    if __base__ not in sys.path: sys.path.append(__base__)
    
    from lib.capture import *

except ImportError as e:
    print(e, file=sys.stderr, flush=True)
    sys.exit(3)

# ------------------------------------------------

def update(data):

    x, r, n, o = None, None, None, None
    
    if 'range_profile' in data:
        r = data['range_profile']
        bin = range_max / len(r)
        x = [i*bin for i in range(len(r))]
        x = [v - range_bias for v in x]

    if 'noise_profile' in data:
        n = data['noise_profile']
        if x is None:
            bin = range_max / len(n)
            x = [i*bin for i in range(len(n))]
            x = [v - range_bias for v in x]

    if x is not None:

        if 'detected_points' in data:
            o = [0] * len(x)
            for p in data['detected_points']:
                ri, _ = (int(v) for v in p.split(','))
                if ri < len(o):
                    o[ri] += 1
 
        if 'header' in data:
            
            if 'time' not in data['header']: return
            if 'number' not in data['header']: return

            clk, cnt = data['header']['time'], data['header']['number']
 
            if r is None: r = [float('nan')] * len(x)
            if n is None: n = [float('nan')] * len(x)
            if o is None: o = [0] * len(x)
             
            for i in range(len(x)):
                s = '{} {:.4f} {:.4f} {:.4f} {}'.format(i, x[i], r[i], n[i], o[i])
                if i == 0: s += ' {} {} {:.3f}'.format(cnt, clk, time.time())
                fh.write(s + '\n')
                fh.flush()

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
        fh = open('{}/{}_{}.log'.format(fp, this_name, int(time.time())), 'w')        

        start_capture(update)
        
    except Exception as e:
        print(e, file=sys.stderr, flush=True)
        sys.exit(2)
