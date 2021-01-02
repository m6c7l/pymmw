#
# Copyright (c) 2018, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# helper functions
#

import math
import numpy as np

from lib.utility import *

# ------------------------------------------------

# log2_10 = 20 * np.log10(2)
# 
# def log_to_lin(a):
#     return 2**(a)  # * log_lin) # * comp_lin
# 
# 
# def lin_to_log(a):
#     return a * log2_10  # * log_lin + comp_log

# ------------------------------------------------

def twos(value, bits):
    m = 2**(bits - 1)
    if value > m:
        value = value - 2*m
    return value


def pow2_ceil(x):
    if (x < 0): return 0
    x -= 1
    x |= x >> 1
    x |= x >> 2
    x |= x >> 4
    x |= x >> 8
    x |= x >> 16
    return x + 1


def q_to_dec(value, n):
    return value / (1 << n)


def dec_to_q(value, n):
    return int(value * (1 << n))


def q_to_db(value):
    return q_to_dec(value, 9) * 6

# ------------------------------------------------

def fft_range_scale_compensation(fft_min_size, fft_size):
    smin = (2.0**(math.ceil(math.log2(fft_min_size) / math.log2(4)-1))) / fft_min_size
    slin = (2.0**(math.ceil(math.log2(fft_size) / math.log2(4)-1))) / fft_size
    slin = slin / smin
    return slin


def fft_doppler_scale_compensation(fft_min_size, fft_size):
    slin = 1.0 * fft_min_size / fft_size
    return slin

# ------------------------------------------------

def num_tx_antenna(cfg, mask=(True, True, True)):
    b = dec2bit(cfg['channelCfg']['txMask'], 3)
    m = (True,) * (len(b) - len(mask)) + mask
    res = [digit if valid else 0 for digit, valid in zip(b, m)]
    return sum(res)


def num_tx_azim_antenna(cfg, mask=(True, False, True)):
    return num_tx_antenna(cfg, mask)


def num_tx_elev_antenna(cfg, mask=(False, True, False)):
    return num_tx_antenna(cfg, mask)


def num_rx_antenna(cfg):
    return sum(dec2bit(cfg['channelCfg']['rxMask'], 3))


def num_virtual_antenna(cfg):
    return num_tx_antenna(cfg) * num_rx_antenna(cfg)


def num_range_bin(cfg):
    return int(pow2_ceil(cfg['profileCfg']['adcSamples']))


def num_doppler_bin(cfg):
    return int(chirps_per_frame(cfg) / num_tx_antenna(cfg))


def num_angular_bin(cfg):
    return 64


def chirps_per_loop(cfg):
    if cfg['dfeDataOutputMode']['type'] == 1:
        return (cfg['frameCfg']['endIndex'] - cfg['frameCfg']['startIndex'] + 1)
    raise NotImplementedError('dfeDataOutputMode != 1')


def chirps_per_frame(cfg):
    return chirps_per_loop(cfg) * cfg['frameCfg']['loops']


def bandwidth(cfg):
    return 1.0 * cfg['profileCfg']['freqSlope'] * cfg['profileCfg']['adcSamples'] / cfg['profileCfg']['sampleRate']


def range_resolution(cfg):
    return range_maximum(cfg) / cfg['profileCfg']['adcSamples']


def range_bin(cfg):
    return range_maximum(cfg, 1.0) / num_range_bin(cfg)


def doppler_resolution(cfg):
    return 3e8 / (2 * cfg['profileCfg']['startFreq'] * 1e9 * (cfg['profileCfg']['idleTime'] + cfg['profileCfg']['rampEndTime']) * 1e-6 * chirps_per_frame(cfg))


def angular_resolution(cfg):
    n = num_rx_antenna(cfg) * num_tx_azim_antenna(cfg)
    if n == 1: return float('nan')
    return math.degrees(math.asin(2 / (num_rx_antenna(cfg) * num_tx_azim_antenna(cfg))))


def range_unambiguous(cfg):
    return range_maximum(cfg, 0.8)


def range_maximum(cfg, correction=1.0):
    return correction * 300 * cfg['profileCfg']['sampleRate'] / (2 * cfg['profileCfg']['freqSlope'] * 1e3)


def doppler_maximum(cfg):
    return doppler_resolution(cfg) * num_doppler_bin(cfg) / 2


def adc_sample_swap(cfg):
    return cfg['adcbufCfg']['sampleSwap']


def samples_per_chirp(cfg):
    return cfg['profileCfg']['adcSamples']


def samples_per_frame(cfg):
    return samples_per_chirp(cfg) * chirps_per_frame(cfg)

