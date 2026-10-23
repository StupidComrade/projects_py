import pyvisa
import time 
import matplotlib.pyplot as plt

def plot_line(x, y, title=" ", xlabel="f, MHz", ylabel="Y", 
              color='blue', marker='o', grid=True, label=None):
 
    plt.figure(figsize=(10, 6))
    plt.plot(x, y, color=color, marker=marker, linewidth=2, label=label)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(grid, alpha=0.3)
    if label:
        plt.legend()
    plt.tight_layout()
    plt.show()


def save_afc_space(freq_values, afc_values, filename="C:/Users/asus/Desktop/grant/2026_1sem/afc.txt", precision=6):
    fmt = f"{{:.{precision}f}}"
    with open(filename, "w", encoding="utf-8") as f:
        for freq, afc in zip(freq_values, afc_values):
            f.write(f"{fmt.format(freq)} {fmt.format(afc)}\n")



freq = 0.5e6  #start
ampl = 10e-3
step = 100e3
freq_stop = 10e6 #stop
attenuation = 1

rm = pyvisa.ResourceManager()
devices = rm.list_resources()
print(f"{devices[0]} - 0")
print(f"{devices[1]} - 1")
gen_id = input("Pick a gen ")
osc_id = input("Pick a osc ")
device_gen = rm.open_resource(devices[int(gen_id)])
device_osc = rm.open_resource(devices[int(osc_id)])

device_gen.write('*RST')
device_gen.write(':OUTP1 OFF')
device_gen.write(':OUTP1:LOAD 50')
device_gen.write(':SOUR1:FUNC SIN')

device_osc.write('*RST')
time.sleep(1)

device_osc.write(':CHANnel1:SCALe 1')
device_osc.write(':ACQuire:MDEPth 1M')


device_osc.write(':TIMebase:MODE MAIN')
device_osc.write(':TIMebase:MAIN:SCALe 0.0001')
device_osc.write(':MEASure:ITEM VPP,CHANnel1')
#device_osc.write(':MEASure:ITEM VPP,CHANnel2')
device_osc.write(':MEASure:STATistic:COUNt 25 ')



device_gen.write(":SOUR1:FREQ {}".format(freq))
device_gen.write(":SOUR1:VOLT {}".format(ampl))
device_gen.write(':SOUR1:VOLT:OFFS 0')
device_gen.write(':SOUR1:PHAS 0')
device_gen.write(':OUTP1 ON')
time.sleep(0.1)
device_osc.write(':AUToset:ENAble 1')
time.sleep(2)

i = 0
Vpp_values = []
freq_values = []
AFC_values = []

while freq <= freq_stop:

    device_gen.write(":SOUR1:FREQ {}".format(freq))
    device_osc.write(":TIMebase:MAIN:SCALe {}".format((1/freq)*10))
    time.sleep(0.3)

    a = device_osc.query(':MEASure:ITEM? VPP,CHANnel1')
  #  b = device_osc.query(':MEASure:ITEM? VPP,CHANnel2')
    Vpp = float(a)
   # Vppin = float(b)
    device_osc.write(":CHANnel1:SCALe {}".format((Vpp/2)))
  #  device_osc.write(":CHANnel2:SCALe {}".format((Vppin/2)))
   # Vppin = Vppin/attenuation
    Vpp_values.append(Vpp)
  #  AFC_values.append(Vpp/Vppin)
    AFC_values.append(Vpp/(ampl*2))
    freq_values.append(freq/1e6)
    i += 1
    freq += step
#save_afc_space(freq_values, AFC_values)
plot_line(freq_values, AFC_values)

 
