#
# Copyright (c) 2019, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# super-simple CFAR clustering
#

import os, sys

try:
       
    import numpy as np
    
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    
    __base__ = os.path.dirname(os.path.abspath(__file__))
    while 'lib' not in [d for d in os.listdir(__base__) if os.path.isdir(os.path.join(__base__, d))]: __base__ = os.path.join(__base__, '..')
    if __base__ not in sys.path: sys.path.append(__base__)

    from lib.plot import *

except ImportError as e:
    print(e, file=sys.stderr, flush=True)
    sys.exit(3)

# ------------------------------------------------

def update(data, threshold=0.1):

    if 'detected_points' not in data: return
        
    X, Y, Z = [], [], []

    for _, p in data['detected_points'].items():
        x, y, z, d = p['x'], p['y'], p['z'], p['v']
        X.append(x)
        Y.append(y)
        Z.append(z)

    mx, my, mz, err = np.mean(X), np.mean(Y), np.mean(Z), np.sqrt(np.std(X)**2 + np.std(Y)**2 + np.std(Z)**2)
    
    while err > threshold:
        
        dmin, dmax, d = float('inf'), 0, [] 
 
        for x, y, z in zip(X, Y, Z):
            d.append(np.sqrt(x**2 + y**2 + z**2) - np.sqrt(mx**2 + my**2 + mz**2))
            if d[-1] > dmax: dmax = d[-1]
            if d[-1] < dmin: dmin = d[-1]
     
        dhor = dmin + (dmax - dmin) / 2
 
        k = 0
        for i, r in enumerate(d):
            if r > dhor:
                d[i] = None
                X.pop(i-k)
                Y.pop(i-k)
                Z.pop(i-k)
                k += 1

        if len(X) == 0: return

        mx, my, mz, err = np.mean(X), np.mean(Y), np.mean(Z), np.sqrt(np.std(X)**2 + np.std(Y)**2 + np.std(Z)**2)

        if k == 0 and err > threshold: return
 
    for x, y, z in zip(X, Y, Z):     
        pt = Point((x, y, z), color=(0.5, 0.5, 0.5), size=3, marker='.')
        ax.add_artist(pt)
    
    pt = Point((mx, my, mz), color=(1.0, 0.0, 0.0), size=20, marker='+')
    ax.add_artist(pt)

    xm, ym, zm = ax.get_xlim3d(), ax.get_ylim3d(), ax.get_zlim3d()

    az, el = ax.azim, ax.elev
    
    if abs(az) > 90: x_ = max(xm)
    else: x_ = min(xm)
    
    if az < 0: y_ = max(ym)
    else: y_ = min(ym)
    
    if el < 0: z_ = max(zm)
    else: z_ = min(zm)
    
    xz = Point((mx, y_, mz), color=(1.0, 0.0, 0.0), size=3, marker='.')
    ax.add_artist(xz)

    yz = Point((x_, my, mz), color=(1.0, 0.0, 0.0), size=3, marker='.')
    ax.add_artist(yz)

    xy = Point((mx, my, z_), color=(1.0, 0.0, 0.0), size=3, marker='.')
    ax.add_artist(xy)                    


if __name__ == "__main__":

    if len (sys.argv[1:]) != 1:
        print('Usage: {} {}'.format(sys.argv[0].split(os.sep)[-1], '<range_maximum>'))
        sys.exit(1)
        
    try:

        range_max = float(sys.argv[1])        
        d = range_max  # int(math.ceil(range_max))

        # ---

        fig = plt.figure(figsize=(6, 6))
        ax = plt.subplot(1, 1, 1, projection='3d')  # rows, cols, idx
        ax.view_init(azim=-45, elev=15)
        
        move_figure(fig, (0 + 45*2, 0 + 45*2))
        
        fig.canvas.set_window_title('...')
                           
        ax.set_title('CFAR Detection: Simple Clustering'.format(), fontsize=10)
        
        ax.set_xlabel('x [m]')
        ax.set_ylabel('y [m]')
        ax.set_zlabel('z [m]')
        
        ax.set_xlim3d((-d / 2, +d / 2))
        ax.set_ylim3d((0, d))
        ax.set_zlim3d((-d / 2, +d / 2))
        
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False

        ax.xaxis._axinfo['grid']['linestyle'] = ':'
        ax.yaxis._axinfo['grid']['linestyle'] = ':'
        ax.zaxis._axinfo['grid']['linestyle'] = ':'

        plt.tight_layout(pad=1)
        
        ax.scatter(xs=[], ys=[], zs=[], marker='.', cmap='jet')

        for child in ax.get_children():
            if isinstance(child, art3d.Path3DCollection):
                child.remove()

        from itertools import product, combinations  # a small cube (origin)        
        r = [-0.075, +0.075]
        for s, e in combinations(np.array(list(product(r,r,r))), 2):
            if np.sum(np.abs(s-e)) == r[1]-r[0]:
                ax.plot3D(*zip(s,e), color="black", linewidth=0.5)

        set_aspect_equal_3d(ax)

        mpl.colors._colors_full_map.cache.clear()  # avoid memory leak by clearing the cache
                    
        start_plot(fig, ax, update, 4)
    
    except Exception as e:
        print(e, file=sys.stderr, flush=True)
        sys.exit(2)
