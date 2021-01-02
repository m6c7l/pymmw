#
# Copyright (c) 2019, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# DFT of IF signal plot (per frame, from memory dump of Capture Demo)
#

import os, sys, threading, time

try:
       
    import numpy as np
    
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    
    __base__ = os.path.dirname(os.path.abspath(__file__))
    while 'lib' not in [d for d in os.listdir(__base__) if os.path.isdir(os.path.join(__base__, d))]: __base__ = os.path.join(__base__, '..')
    if __base__ not in sys.path: sys.path.append(__base__)

    from lib.utility import *
    from lib.helper import *

except ImportError as e:
    print(e, file=sys.stderr, flush=True)
    sys.exit(3)
    
# ------------------------------------------------

def plot_buffer(fig, idx, xy, a, k, n, b):

    chirp = [np.zeros(k, dtype=np.complex) for _ in range(a)]  # average iq per antenna
    for i, chirps in enumerate(xy):
        for j, samples in enumerate(chirps):
            chirp[i] += np.asarray(samples, dtype=np.complex)
        chirp[i] /= n
    
    rng = [r*(i/(k-1)) - b for i in range(k)]
    win = np.ones(k)  # no windowing
    ss = [np.abs(np.fft.fft(chirp[i]))*win for i in range(a)]

    if idx == 0:
        fig._dft_max_ = float('-inf')

    max_ss = np.max(ss)
    if max_ss > fig._dft_max_:
        fig._dft_max_ = max_ss

    l = len(fig.axes)  # increasing over time

    if idx == l:  # setup plots

        fig.tight_layout(pad=1.5)
           
        for i in range(l):
            fig.axes[i].change_geometry(1, l+1, i+1)
                                    
        fig.set_size_inches(4*(l+1), 5)
        ax = fig.add_subplot(1, l+1, l+1)
 
        for i in range(len(ss)):
            ax.plot(rng, ss[i], linewidth=1.0, alpha=1.0 / len(ss))
          
        ax.grid(linestyle=':', linewidth=0.5)
        ax.legend(['RX{}'.format(i) for i in range(len(ss))])
        ax.set_title('frame {}'.format(idx+1))
        ax.set_xlabel('range (m)')
        ax.set_ylabel('DFT result x')

        for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] + ax.get_xticklabels() + ax.get_yticklabels()):
            item.set_fontsize('medium')
        
    else:  # update plots

        axs = fig.get_axes()
        ax = axs[idx]
        col = []
        
        while len(ax.lines) > 0:
            col.append(ax.lines.pop(0).get_color())   
                     
        for i in range(len(ss)):
            ax.plot(rng, ss[i], linewidth=1.0, c=col[i], alpha=1.0 / len(ss))
            
        ax.relim()
        ax.autoscale_view()

    for i in range(len(fig.axes)):  # align subplots wrt dft results
        fig.axes[i].set_ylim((-fig._dft_max_*0.025, fig._dft_max_*1.025))

    fig.canvas.draw()
    fig.canvas.flush_events()
    fig.canvas.set_window_title('time: {}'.format(time.time()))
   

def update_data(fig, a, k, n, s, b, timeout=2):
    size = a * k * n * 2
    buf = [[[0] * k for _ in range(n)] for _ in range(a)]
    fi, vi = 0, 0
    while True:
        t = time.time()
        line = sys.stdin.readline()
        if t + timeout < time.time(): fi = 0
        try:
            line = line.strip()
            if line:
                values = line.split(' ')
                values = [twos(hex2dec(value), 16) for value in values]
                for value in values:
                    ai, ci, si = ((vi//2)//n)%a, (vi//2)%n, (vi//2)%k
                    if vi % 2 == 0:
                        buf[ai][ci][si] = 1j*value if s else value
                    else:
                        buf[ai][ci][si] += value if s else 1j*value
                    vi += 1                
                if vi == size:
                    plot_buffer(fig, fi, buf, a, k, n, b)
                    buf = [[[0] * k for _ in range(n)] for _ in range(a)]
                    fi += 1
                    vi = 0
        except Exception as e:
            print(e, file=sys.stderr, flush=True)

# ------------------------------------------------

if __name__ == "__main__":

    if len(sys.argv[1:]) != 6:
        print('Usage: {} {}'.format(sys.argv[0].split(os.sep)[-1], '<num_rx_antenna> <range_maximum> <range_bias> <adc_sample_swap> <samples_per_chirp> <chirps_per_frame>'))
        sys.exit(1)
       
    try:

        a = int(float(sys.argv[1]))
        r = float(sys.argv[2])
        b = float(sys.argv[3])
        s = bool(int(float(sys.argv[4])))
        k = int(float(sys.argv[5]))
        n = int(float(sys.argv[6]))

        fig = plt.figure()
        fig.suptitle('DFT of IF signals: chirps/frame={}, samples/chirp={}'.format(n, k), fontsize='medium')
        fig.canvas.set_window_title('...')
        
        tu = threading.Thread(target=update_data, args=(fig, a, k, n, s, b))
        tu.daemon = True
        tu.start()

        plt.show()

    except Exception as e:
        print(e, file=sys.stderr, flush=True)
        sys.exit(2)
