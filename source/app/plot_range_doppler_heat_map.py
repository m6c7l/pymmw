#
# Copyright (c) 2018, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# Doppler-range FFT heat map - 2D plot
#

import os, sys

try:
    
    import numpy as np

    import matplotlib.pyplot as plt
    import matplotlib.widgets as wgt
    
    __base__ = os.path.dirname(os.path.abspath(__file__))
    while 'lib' not in [d for d in os.listdir(__base__) if os.path.isdir(os.path.join(__base__, d))]: __base__ = os.path.join(__base__, '..')
    if __base__ not in sys.path: sys.path.append(__base__)

    from lib.plot import *

except ImportError as e:
    print(e, file=sys.stderr, flush=True)
    sys.exit(3)

# ------------------------------------------------

def onclick(event):
    
    if event.button == 3:  # toggle scale of data
        global comp_choice
        comp_choice += 1
        comp_choice %= len(comp_mode)
        
    if event.button == 1:  # toggle color range of heatmap
        global heat_choice
        heat_choice += 1
        heat_choice %= len(heat_mode)
        
    return (event.xdata, event.ydata)
    

def update(data):
 
    if not 'range_doppler' in data or len(data['range_doppler']) != range_bins * doppler_bins:
        return

    a = np.array(data['range_doppler'])
    
    if comp_mode[comp_choice] == 'lin':
        a = comp_lin * 2**(a * log_lin)
    
    elif comp_mode[comp_choice] == 'log':
        a = a * log2_10 * log_lin + comp_log
     
    b = np.reshape(a, (range_bins, doppler_bins))
    c = np.fft.fftshift(b, axes=(1,))  # put left to center, put center to right
     
    im.set_array(c[:,1:].T)  # rotate 90 degrees, cut off first doppler bin
    
    if heat_mode[heat_choice] == 'rel':
        im.autoscale()  # reset colormap
    
    elif heat_mode[heat_choice] == 'abs':
        im.set_clim(0, 1024**2)  # reset colormap    
            

if __name__ == "__main__":

    if len(sys.argv[1:]) != 7:
        print('Usage: {} {}'.format(sys.argv[0].split(os.sep)[-1], '<num_doppler_bin> <doppler_resolution> <num_range_bin> <range_bin> <fft_comp> <log_lin> <range_bias>'))
        sys.exit(1)
        
    try:
        
        heat_mode, heat_choice = ('rel', 'abs'), 0
        comp_mode, comp_choice = ('lin', 'log'), 0
        
        log2_10 = 20 * np.log10(2)
        
        doppler_bins = int(float(sys.argv[1]))        
        res_doppler = float(sys.argv[2])

        range_bins = int(float(sys.argv[3]))
        res_range = float(sys.argv[4])

        comp_lin = float(sys.argv[5])
        comp_log = 20 * np.log10(comp_lin)

        log_lin = float(sys.argv[6])
        range_bias = float(sys.argv[7])

        # ---        
        
        fig = plt.figure(figsize=(6, 6))
        ax = plt.subplot(1, 1, 1)  # rows, cols, idx
        
        cursor = wgt.Cursor(ax, useblit=True, color='white', linewidth=1)
        
        fig.canvas.set_window_title('...')
        
        ax.set_title('Doppler-Range FFT Heatmap [{};{}]'.format(range_bins, doppler_bins), fontsize=10)
        ax.set_xlabel('Longitudinal distance [m]')
        ax.set_ylabel('Radial velocity [m/s]')
        
        ax.grid(color='white', linestyle=':', linewidth=0.5)
        
        move_figure(fig, (0 + 45*4, 0 + 45*4))
         
        scale = max(doppler_bins, range_bins)
        ratio = range_bins / doppler_bins
        
        range_offset = res_range / 2
        range_min = 0 - range_offset
        range_max = range_min + scale * res_range
        
        doppler_scale = scale // 2 * res_doppler
        doppler_offset = 0 # (res_doppler * ratio) / 2
        doppler_min = (-doppler_scale + doppler_offset) / ratio
        doppler_max = (+doppler_scale + doppler_offset) / ratio

        fig.tight_layout(pad=2)

        #n = int(scale) // 2
        #z = np.array(([0, 1] * n + [1, 0] * n) * n)
        #z.shape = (n*2, n*2)
        #im = ax.imshow(z, cmap=plt.cm.gray, interpolation='nearest', extent=[range_min, range_max, doppler_min, doppler_max])
                
        im = ax.imshow(np.reshape([0,] * range_bins * (doppler_bins-1), (range_bins, doppler_bins-1)),
                       cmap=plt.cm.jet,
                       interpolation='quadric',  # none, gaussian, mitchell, catrom, quadric, kaiser, hamming
                       aspect=(res_range / res_doppler) * ratio,
                       extent=[range_min - range_bias, range_max - range_bias, doppler_min, doppler_max], alpha=.95)
        
        #ax.plot([unamb_range, unamb_range], [doppler_min, doppler_max], color='white', linestyle='--', linewidth=0.5, zorder=1)
        ax.plot([0 - range_bias, range_max - range_bias], [0, 0], color='white', linestyle=':', linewidth=0.5, zorder=1)

        fig.canvas.mpl_connect('button_press_event', onclick)
        
        start_plot(fig, ax, update, 5)
    
    except Exception as e:
        print(e, file=sys.stderr, flush=True)
        sys.exit(2)
