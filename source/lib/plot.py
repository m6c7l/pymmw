#
# Copyright (c) 2018, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# plot support
#

import sys, time, threading, json, queue

import numpy as np

import matplotlib as mpl
import matplotlib.pyplot as plt

from mpl_toolkits.mplot3d import art3d

# ------------------------------------------------

class Line(art3d.Line3D):  # a line in 3D space

    def __init__(self, from_xyz=(0, 0, 0), to_xyz=(1, 1, 1), *args, **kwargs):
        xs, ys, zs = tuple(zip(from_xyz, to_xyz))
        art3d.Line3D.__init__(self, xs, ys, zs, *args, **kwargs)

    def location(self, from_, to_, *args):
        xs, ys, zs = tuple(zip(from_, to_))
        self.set_xdata(xs)
        self.set_ydata(ys)
        self.set_3d_properties(zs)


class Point(Line):  # a point (a very short line) in 3D space

    def __init__(self, xyz=(0, 0, 0), color='black', marker='.', size=1, vanish=1.0, alpha=1.0):
        
        Line.__init__(self, xyz, xyz,
                      color=color, marker=marker, markersize=size,
                      markeredgewidth=1, linestyle='', fillstyle='none', alpha=alpha)
        
        if vanish is not None:
            tt = threading.Thread(target=self.__fadeout, args=(0.1 * vanish, 0.1))
            tt.daemon = True
            tt.start()
     
    def __fadeout(self, period, delta):
        
        def delay():
            t = time.time()
            c = 0
            while True:
                c += 1
                yield max(t + c * period - time.time(), 0)
                
        tick = delay()

        while True:
            time.sleep(next(tick))
            na = self.get_alpha() - delta
            if na <= 0:
                self.remove()
                break
            self.set_alpha(na)

    def location(self, at_, *args):
        Line.location(self, at_, at_)

# ------------------------------------------------

def set_aspect_equal_3d(ax):  # axis have to be equal 

    xlim = ax.get_xlim3d()
    ylim = ax.get_ylim3d()
    zlim = ax.get_zlim3d()

    xmean = np.mean(xlim)
    ymean = np.mean(ylim)
    zmean = np.mean(zlim)

    plot_radius = max([abs(lim - mean_) for lims, mean_ in ((xlim, xmean), (ylim, ymean), (zlim, zmean)) for lim in lims])

    ax.set_xlim3d([xmean - plot_radius, xmean + plot_radius])
    ax.set_ylim3d([ymean - plot_radius, ymean + plot_radius])
    ax.set_zlim3d([zmean - plot_radius, zmean + plot_radius])


def move_figure(fig, xy):
    backend = mpl.get_backend()
    if backend == 'TkAgg':
        fig.canvas.manager.window.wm_geometry("+%d+%d" % xy)
    elif backend == 'WXAgg':
        fig.canvas.manager.window.SetPosition(xy)
    else:  # QT and GTK
        fig.canvas.manager.window.move(*xy)
    
# ------------------------------------------------

def update_data(fig, q):
    while q.alive:
        line = sys.stdin.readline()
        try:
            temp = json.loads(line)
            q.put(temp)
        except Exception as e:
            print(e, file=sys.stderr, flush=True)


def update_plot(fig, q, func, fps):
    
    clk, cnt = 0, 0

    dt = 1 / fps
    
    while q.alive:

        try:
            item = q.get()
            with q.mutex: q.queue.clear()
            clk, cnt = item['header']['time'], item['header']['number']
            func(item)
        except Exception as e:
            print(e, file=sys.stderr, flush=True)
                 
        try:
            fig.canvas.draw_idle()
            fig.canvas.set_window_title(
                'time: {} | count: {} | wait: {} | cycles: {:010} '.format(
                    '{:.3f}'.format(time.time())[-7:],
                    cnt,
                    q.qsize(),
                    clk))
            time.sleep(dt)
        except:
            q.alive = False


def start_plot(fig, ax, func, fps=1):
    
    fig.canvas.draw()
    
    plt.show(block=False)

    q = queue.Queue()
    q.alive = True
    
    threading.Thread(target=update_plot, args=(fig, q, func, fps)).start()
     
    tu = threading.Thread(target=update_data, args=(fig, q, ))
    tu.daemon = True
    tu.start()
    
    plt.show(block=True)
    q.alive = False
