from tkinter import *
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pyvisa
import numpy as np
import time
import struct
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from scipy import signal
from pathlib import Path


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Осциллограф")
        self.root.geometry('720x300')

        self.rm = pyvisa.ResourceManager()
        self.device = None
        self.device_osc = None
        self.loaded_data = None
        self.file_path = " "
        self.count_sum_fft = 0
        self.count_files = 1
        self.fft_sum = None

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True, padx=5, pady=5)
        # self.notebook.grid(row=1, column=1)
        self.utility = ttk.Frame(self.notebook)
        self.utility.pack(fill=BOTH, expand=True)
        self.notebook.add(self.utility, text="Настройки")

        self.btn_con = ttk.Button(self.utility, text="Обновить", command=self.update_list)
        self.btn_con.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        self.label3 = ttk.Label(self.utility, text="Осциллограф")
        self.label3.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        # выбор осц
        self.combo1 = ttk.Combobox(self.utility, state='readonly', width=30)
        self.combo1.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        # подключение к осц
        self.btn_con_osc = ttk.Button(self.utility, text="Подключиться", command=self.connect_osc)
        self.btn_con_osc.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        self.status1 = ttk.Label(self.utility, text="Отключено")
        self.status1.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        # загрузка отсчётов с памяти осц и построение графика
        self.btn_save_meas = ttk.Button(self.utility, text="Вывести осциллограмму", command=self.save_meas_osc)
        self.btn_save_meas.grid(row=1, column=1, padx=25, pady=5, sticky="w")

        self.oscilloscope_frame = ttk.Frame(self.notebook)
        self.oscilloscope_frame.pack(fill=BOTH, expand=True)
        self.notebook.add(self.oscilloscope_frame, text="График")

        self.oscilloscope_per = ttk.Frame(self.notebook)
        self.oscilloscope_per.pack(fill=BOTH, expand=True)
        self.notebook.add(self.oscilloscope_per, text="СПМ")

        self.chk4_var = tk.IntVar()
        self.chk4 = tk.Checkbutton(self.utility, text="Сохранить в файл", variable=self.chk4_var)
        self.chk4.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        self.btn_fft_sum = ttk.Button(self.utility, text="Накопить", command=self.sum_fft)
        self.btn_fft_sum.grid(row=3, column=1, padx=25, pady=5, sticky="w")

        self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_changed)

        self.update_list()

    def on_tab_changed(self, event):
        current_tab = self.notebook.select()
        tab_text = self.notebook.tab(current_tab, "text")
        if tab_text == "График" or tab_text == "СПМ":
            self.root.geometry('1100x600')
            self.root.attributes('-fullscreen', True)
        else:
            self.root.geometry('620x300')
            self.root.attributes('-fullscreen', False)


    def update_list(self):
        devices = self.rm.list_resources()
        self.combo1['values'] = devices if devices else ["Нет устройств"]
        # if devices:
        self.combo1.current(0)


    def connect_osc(self):
        if self.btn_con_osc['text'] == "Подключиться":
            try:
                self.device_osc = self.rm.open_resource(self.combo1.get())
                self.device_osc.write('*RST')
                time.sleep(1)
                self.device_osc.write(":STOP")
                dots = 1000000  # 1k 10k 100k(opt) 1M 10M 25M
                self.device_osc.write(":ACQuire:MDEPth {}".format(dots))  # количество точек
                self.device_osc.write(":TRIGger:MODE EDGE")
                time.sleep(0.1)
                self.device_osc.write(":TRIGger:SWEep AUTO")
                time.sleep(0.1)
                self.device_osc.write(":TRIGger:EDGE:SOURce CH1")
                time.sleep(0.1)
                self.device_osc.write(":TRIGger:EDGE:SLOPe NEG")
                time.sleep(0.1)
                self.device_osc.write(":TRIGger:EDGE:LEVel 0")

                self.device_osc.write(":CHANnel1:DISPlay ON")
                self.device_osc.write(":CHANnel1:OFFSet 0")
                self.device_osc.write(":CHANnel1:SCALe 0.1")
                self.device_osc.write(":CHANnel1:COUPling DC")
                self.device_osc.write(":TIMebase:MAIN:SCALe 10e-6")  # время/дел
                self.device_osc.write(":RUN")
                time.sleep(1)
                # srat = self.device_osc.query(":ACQuire:SRATe?")
                # srat = srat.strip().split(',')
                # time.sleep(0.1)
                # offset = ((1 / float(srat[0])) * float(dots))
                # self.device_osc.write(":TIMebase:MAIN:OFFSet {}".format(offset / 2))  # позиция по времени
                # self.device_osc.write(":STOP")
                self.device_osc.write(":CLEAr")
                self.status1.config(text="Подключено")
                self.btn_con_osc.config(text="Отключиться")
            except:
                self.status1.config(text="Ошибка")
        else:
            if self.device_osc:
                self.device_osc.write('*RST')
                self.device_osc.close()
            self.status1.config(text="Отключено")
            self.btn_con_osc.config(text="Подключиться")

    def save_meas_osc(self):
        self.trigger()
        self.device_osc.write(":WAV:SOUR CHAN1")  # выбор канала
        self.device_osc.write(
            ":WAV:MODE RAW")  # считывает данные о форме сигнала из внутренней памяти (обязательно STOP)
        self.device_osc.write(":WAV:FORM WORD")  # 16 битный формат, можно ещё в ascii
        self.device_osc.write(":WAV:STAR 1")
        # self.device_osc.write(":WAV:STOP 1000000") # диапазон от 1 до значения в :ACQuire:MDEPth

        # получение параметров (<format>,<type>,<points>,<count>,<xincrement>,<xorigin>,<xreference>,<yincrement>,<yorigin>,<yreference>)
        preamble = self.device_osc.query(":WAVeform:PREamble?")
        parts = preamble.strip().split(',')
        yincrement = float(parts[7])
        yorigin = float(parts[8])
        yreference = float(parts[9])
        xincrement = float(parts[4])
        xorigin = float(parts[5])
        data = self.device_osc.query_binary_values(
            ":WAVeform:DATA?",
            datatype='H',
            is_big_endian=False,
            container=np.array
        )
        voltage = (data + np.abs(yorigin) - yreference) * yincrement 
        time_axis = [xorigin + i * xincrement for i in range(len(voltage))]
 
        for widget in self.oscilloscope_frame.winfo_children():
            widget.destroy()
        self.figure = Figure(figsize=(12, 6), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel('Время (мкс)')
        self.ax.set_ylabel('Напряжение (В)')
        self.ax.set_title('Осциллограмма')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_facecolor('#f0f0f0')

        # встраивание графика в tkinter
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.oscilloscope_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.line, = self.ax.plot([], [], 'b-', linewidth=1.5)
        self.line.set_data(np.array(time_axis).astype(float) * 1e6, voltage)
        self.ax.relim()
        self.ax.autoscale_view()
        self.figure.tight_layout()

        toolbar = NavigationToolbar2Tk(self.canvas, self.oscilloscope_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        self.canvas.draw()
        toolbar.update()
        self.notebook.select(1)

        # периодограмма Уэлча
        for widget in self.oscilloscope_per.winfo_children():
            widget.destroy()
        f_max_analyze = 30e6
        nperseg = 25600
        noverlap = nperseg // 2
        nfft = nperseg * 2
        frequencies, psd = signal.welch(
            voltage, fs=1 / xincrement,
            nperseg=nperseg, window="hann", noverlap=noverlap, nfft=nfft,
            scaling='density', detrend='constant', average='mean'
        )
        mask = frequencies <= f_max_analyze
        freq_filtered = frequencies[mask]
        psd_filtered = psd[mask]

        self.figure2 = Figure(figsize=(12, 4), dpi=100)
        self.ax2 = self.figure2.add_subplot(111)
        self.ax2.semilogy(freq_filtered / 1e6, psd_filtered, 'r-', linewidth=1.5)
        #   self.ax2.semilogy(frequencies/1e6, np.sqrt(psd)*1e9, 'r-', linewidth=1.5)
        self.ax2.set_xlabel('f (МГц)')
        self.ax2.set_ylabel('СПМ (В²/Гц)')
        #  self.ax2.set_ylabel('СПМ (нВ/sqrt(Гц))')
        self.ax2.set_title('Периодограмма Уэлча')
        self.ax2.grid(True, alpha=0.3)

        self.canvas2 = FigureCanvasTkAgg(self.figure2, master=self.oscilloscope_per)
        self.canvas2.draw()
        self.canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.ax2.relim()
        self.ax2.autoscale_view()
        self.figure2.tight_layout()

        toolbar2 = NavigationToolbar2Tk(self.canvas2, self.oscilloscope_per)
        toolbar2.pack(side=tk.TOP, fill=tk.X)

        if self.chk4_var.get() == 1:
            file_path1 = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[
                    ("Текстовые файлы", "*.txt"),
                    ("CSV файлы", "*.csv"),
                    ("Все файлы", "*.*")
                ],
                initialfile="oscillogram_data.txt",
                title="Сохранить отсчёты"
            )
            if file_path1:
                with open(file_path1, 'w', encoding='utf-8') as f:
                    f.write("t (s)\tu (v)\n")

                    for t, v in zip(time_axis, voltage):
                        f.write(f"{t:.10f}\t{v:.10f}\n")
            else:
                pass
        else:
            pass

    def sum_fft(self):
        L = 20
        while self.count_sum_fft < L:
            self.trigger()
            time.sleep(0.3)
            self.device_osc.write(":WAV:SOUR CHAN1")
            self.device_osc.write(":WAV:MODE RAW")
            self.device_osc.write(":WAV:FORM WORD")
            self.device_osc.write(":WAV:STAR 1")
            # self.device_osc.write(":WAV:STOP 10000")

            preamble = self.device_osc.query(":WAVeform:PREamble?")
            parts = preamble.strip().split(',')
            yincrement = float(parts[7])
            yorigin = float(parts[8])
            yreference = float(parts[9])
            xincrement = float(parts[4])
            xorigin = float(parts[5])
            data = self.device_osc.query_binary_values(
                ":WAVeform:DATA?",
                datatype='H',
                is_big_endian=False,
                container=np.array
            )
            voltage = (data - yreference) * yincrement + yorigin
            time_axis = [xorigin + i * xincrement for i in range(len(voltage))]
            if self.chk4_var.get() == 1:
                out_dir = Path(__file__).resolve().parent / "tests" / "1"
                out_dir.mkdir(parents=True, exist_ok=True)
                file_path = out_dir / f"{self.count_files}.txt"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("t (s)\tu (v)\n")
                    for t, v in zip(time_axis, voltage):
                        f.write(f"{t:.10f}\t{v:.10f}\n")
            self.count_files += 1
            window = signal.windows.hann(len(voltage))
            # window = np.ones(len(voltage))
            voltage = voltage * window
            fft = np.fft.rfft(voltage)
            fft = np.abs(fft) ** 2
            if self.count_sum_fft == 0:
                self.fft_sum = None
                self.fft_sum = fft
            else:
                self.fft_sum = fft + self.fft_sum
            self.count_sum_fft += 1
        E = np.sum(window ** 2)
        self.count_sum_fft = 0
        self.fft_sum = (self.fft_sum * xincrement) / (L * E)
        freq = np.fft.rfftfreq(len(voltage), xincrement)

        # периодограмма 
        for widget in self.oscilloscope_per.winfo_children():
            widget.destroy()
        f_max_analyze = 30e6
        mask = freq <= f_max_analyze
        freq_filtered = freq[mask]
        psd_filtered = self.fft_sum[mask]

        self.figure2 = Figure(figsize=(12, 4), dpi=100)
        self.ax2 = self.figure2.add_subplot(111)
        self.ax2.semilogy(freq_filtered / 1e6, psd_filtered, 'r-', linewidth=1.5)
        #  self.ax2.semilogy(freq/1e6, np.sqrt(self.fft_sum)*1e9, 'r-', linewidth=1.5)
        self.ax2.set_xlabel('f (МГц)')
        self.ax2.set_ylabel('СПМ (В²/Гц)')
        #   self.ax2.set_ylabel('СПМ (нВ/sqrt(Гц))')
        self.ax2.set_title('Периодограмма')
        self.ax2.grid(True, alpha=0.3)

        self.canvas2 = FigureCanvasTkAgg(self.figure2, master=self.oscilloscope_per)
        self.canvas2.draw()
        self.canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.ax2.relim()
        self.ax2.autoscale_view()
        self.figure2.tight_layout()

        toolbar2 = NavigationToolbar2Tk(self.canvas2, self.oscilloscope_per)
        toolbar2.pack(side=tk.TOP, fill=tk.X)


    def trigger(self):
        if self.status1['text'] == "Подключено":
            self.device_osc.write(":RUN")
            time.sleep(0.1)
            self.device_osc.write(":STOP")
        else:
                messagebox.showwarning("Предупреждение", "Сначала включите функцию Burst")




root = tk.Tk()
app = App(root)
root.mainloop()