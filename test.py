import numpy as np
import matplotlib.pyplot as plt
import pyvisa
import time
import struct
def gaussian_win(t, tau_env, sigma, min_val=0.1,
                               amplitude=1.0, t_start=None):
    t = np.asarray(t, dtype=float)
    if t_start is None:
        t_start = t[0]


    t_mod = (t - t_start) % tau_env
    center = 0.5 * tau_env
    half   = 0.5 * tau_env

    g      = np.exp(-((t_mod - center) ** 2) / (2.0 * sigma ** 2))
    g_edge = np.exp(-half ** 2 / (2.0 * sigma ** 2))

   # if g_edge >= 1.0 - 1e-15:          
   #     return amplitude * np.ones_like(t)

    env = min_val + (1.0 - min_val) * (g - g_edge) / (1.0 - g_edge)
    return amplitude * env


def rigol_len(length):
    rtxt = "#"
    rtxt += str(len(str(length))) + str(length)
    return rtxt

def load_dac(loaded_data, samplerate):
    rm=pyvisa.ResourceManager()
    devices = rm.list_resources()
    print(devices)
    a = int(input("choice device "))
    device = rm.open_resource(devices[a])
    device.write(':OUTP1 OFF')
    device.write('*RST')
    device.write(':OUTP1:LOAD 50')
    time.sleep(1)
    signal = loaded_data
    samplerate = float(samplerate)
    amplitude = float(1)
    channel = int(1)
    device.write(':SOUR{}:BURS OFF'.format(channel))

    signal = signal/np.max(np.abs(signal))
    q = 2**15 - 1
    value = np.round(signal * q).astype(int)
    samplebytes = struct.pack('<' + 'h' * len(value), *value)
    xcount = 32768
    device.write(':OUTP{} OFF'.format(channel))
    device.write('*CLS')
    time.sleep(0.2)
    device.write(':APPL:SEQ')
    device.write(':SOUR{}:FUNC:SEQ:FILT INSE'.format(channel))
    device.write(':SOUR{}:VOLT {}'.format(channel,amplitude))
    device.write(':SOUR{}:FUNC:SEQ:SRAT {}'.format(channel,samplerate))
    while (device.query('*OPC?') != '1\n'):
        time.sleep(0.1)
    while (len(samplebytes) > xcount):
        header = f":SOURce{channel}:DATA:DAC16 VOLATILE,CON,"
        device.write_raw(header.encode('utf-8') + rigol_len(xcount).encode('utf-8') + samplebytes[0:xcount])
        time.sleep(0.2)
        while ( device.query('*OPC?') != '1\n'):
            time.sleep(0.1)
        samplebytes = samplebytes[xcount:]
    header = f":SOURce{channel}:DATA:DAC16 VOLATILE,END,"
    device.write_raw(header.encode('utf-8') + rigol_len(len(samplebytes)).encode('utf-8') + samplebytes)
    time.sleep(0.2)

    delay = 0
    device.write(':SOUR{}:BURS ON'.format(channel))
    while ( device.query('*OPC?') != '1\n'):
        time.sleep(0.1)
    device.write(':SOUR{}:BURS:MODE TRIG'.format(channel))
    device.write(':OUTP{} ON'.format(channel))
    device.write(':SOUR{}:BURS:NCYC 1'.format(channel))
    device.write(':SOUR{}:BURS:TRIG:SOUR MAN'.format(channel))
    device.write(':OUTP{}:SYNC 1'.format(channel))
    device.write(':OUTP{}:SYNC:POL POS'.format(channel))
    device.write(':SOUR{}:BURS:TDEL {}'.format(channel, delay/2))


f = 7e6
tau1 = (1/f)*20
samplerate = 60e6
n1 = round((tau1*samplerate))
N = n1
c1 = round(n1*f/samplerate)
t1 = np.linspace(0, c1*2*np.pi, n1)

tau_win = (1/f)*5
sigma = tau_win*10
min_val = 0.5
t = np.linspace(0, tau1, n1)
window = gaussian_win(t, tau_win, sigma=sigma, min_val=min_val)
q = 2**15 - 1      
sine_value1 = (np.sin(t1) * window * q)
normalized1 = np.round(sine_value1).astype(int)

load_dac(normalized1, samplerate)

plt.plot(t, normalized1)
plt.show()