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


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Спектрометр")
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

        self.label = ttk.Label(self.utility, text="Генератор")
        self.label.grid(row=2, column=2)

        # выбор генератора
        self.combo = ttk.Combobox(self.utility, state='readonly', width=30)
        self.combo.grid(row=2, column=3)

        # подключение
        self.btn_con_awg = ttk.Button(self.utility, text="Подключиться", command=self.connect)
        self.btn_con_awg.grid(row=2, column=4)

        self.btn_con = ttk.Button(self.utility, text="Обновить", command=self.update_list)
        self.btn_con.grid(row=2, column=5)

        # статус
        self.status = ttk.Label(self.utility, text="Отключено")
        self.status.grid(row=3, column=2)

        # кнопка загрузки файла
        self.load_btn = ttk.Button(self.utility, text="Загрузить отсчёты", command=self.load_file)
        self.load_btn.grid(row=4, column=2)
        # задать f
        self.label4 = ttk.Label(self.utility, text="Частота РЧ:")
        self.label4.grid(row=5, column=2)
        self.frate = Entry(self.utility)
        self.frate.grid(row=5, column=3)
        self.frate.insert(0, "7.0e6")
        # задать tau
        self.label5 = ttk.Label(self.utility, text="Длительность:")
        self.label5.grid(row=6, column=2)
        self.duration = Entry(self.utility)
        self.duration.grid(row=6, column=3)
        self.duration.insert(0, "10.0e-6")
        # задать fd
        self.label1 = ttk.Label(self.utility, text="Частота дискретизации:")
        self.label1.grid(row=4, column=3)
        self.srate = Entry(self.utility)
        self.srate.grid(row=4, column=4)
        self.srate.insert(0, "60e6")
        # задать amplitude
        self.label6 = ttk.Label(self.utility, text="Амплитуда:")
        self.label6.grid(row=7, column=2)
        self.ampl = Entry(self.utility)
        self.ampl.grid(row=7, column=3)
        self.ampl.insert(0, "0.1")
        # выбор канала
        self.label2 = ttk.Label(self.utility, text="Канал:")
        self.label2.grid(row=3, column=5)
        self.chan = Entry(self.utility, width=3)
        self.chan.grid(row=4, column=5)
        self.chan.insert(0, "1")
        # загрузить отсчёты в генератор
        self.btn_load_file_awg = ttk.Button(self.utility, text="Загрузить в генератор", command=self.load_dac)
        self.btn_load_file_awg.grid(row=5, column=4)
        # вкл/выкл 1 канал
        self.chk_var = tk.IntVar()
        self.chk = tk.Checkbutton(self.utility, text="Канал 1", variable=self.chk_var, command=self.checkbox_change)
        self.chk.grid(row=6, column=4)
        # вкл/выкл 2 канал
        self.chk2_var = tk.IntVar()
        self.chk2 = tk.Checkbutton(self.utility, text="Канал 2", variable=self.chk2_var, command=self.checkbox_change)
        self.chk2.grid(row=6, column=5)
        # вкл/выкл режима пачки импульсов
        self.chk3_var = tk.IntVar()
        self.chk3 = tk.Checkbutton(self.utility, text="Burst", variable=self.chk3_var, command=self.burst)
        self.chk3.grid(row=5, column=5)
        # запуск пачки
        self.btn_awg_trig = ttk.Button(self.utility, text="Trig", command=self.trigger)
        self.btn_awg_trig.grid(row=5, column=6)

        self.label3 = ttk.Label(self.utility, text="Осциллограф")
        self.label3.grid(row=10, column=2)
        # выбор осц
        self.combo1 = ttk.Combobox(self.utility, state='readonly', width=30)
        self.combo1.grid(row=10, column=3)
        # подключение к осц
        self.btn_con_osc = ttk.Button(self.utility, text="Подключиться", command=self.connect_osc)
        self.btn_con_osc.grid(row=10, column=4)

        self.status1 = ttk.Label(self.utility, text="Отключено")
        self.status1.grid(row=11, column=2)
        # загрузка отсчётов с памяти осц и построение графика
        self.btn_save_meas = ttk.Button(self.utility, text="Вывести осциллограмму", command=self.save_meas_osc)
        self.btn_save_meas.grid(row=12, column=4)

        self.oscilloscope_frame = ttk.Frame(self.notebook)
        self.oscilloscope_frame.pack(fill=BOTH, expand=True)
        self.notebook.add(self.oscilloscope_frame, text="График")

        self.oscilloscope_per = ttk.Frame(self.notebook)
        self.oscilloscope_per.pack(fill=BOTH, expand=True)
        self.notebook.add(self.oscilloscope_per, text="СПМ")

        self.chk4_var = tk.IntVar()
        self.chk4 = tk.Checkbutton(self.utility, text="Сохранить в файл", variable=self.chk4_var)
        self.chk4.grid(row=13, column=4)

        self.btn_fft_sum = ttk.Button(self.utility, text="Накопить", command=self.sum_fft)
        self.btn_fft_sum.grid(row=14, column=4)

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

    def checkbox_change(self):
        if self.chk_var.get() == 1:
            self.device.write(':OUTP1 ON')
        else:
            self.device.write(':OUTP1 OFF')
        if self.chk2_var.get() == 1:
            self.device.write(':OUTP2 ON')
        else:
            self.device.write(':OUTP2 OFF')

    def update_list(self):
        devices = self.rm.list_resources()
        self.combo['values'] = devices if devices else ["Нет устройств"]
        self.combo1['values'] = devices if devices else ["Нет устройств"]
        # if devices:
        self.combo.current(0)
        self.combo1.current(0)

    def connect(self):
        if self.btn_con_awg['text'] == "Подключиться":
            try:
                self.device = self.rm.open_resource(self.combo.get())
                self.device.write('*IDN?')
                self.status.config(text="Подключено")
                self.device.write(':OUTP1 OFF')
                self.device.write(':OUTP2 OFF')
                self.device.write('*RST')
                self.device.write(':OUTP1:LOAD 50')
                self.device.write(':OUTP2:LOAD 50')
                self.btn_con_awg.config(text="Отключиться")
            except:
                self.status.config(text="Ошибка")
        else:
            if self.device:
                self.device.write(':OUTP1 OFF')
                self.chk_var.set(0)
                self.device.write(':OUTP2 OFF')
                self.chk2_var.set(0)
                self.chk3_var.set(0)
                self.chan.delete(0, tk.END)
                self.device.close()
            self.status.config(text="Отключено")
            self.btn_con_awg.config(text="Подключиться")

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
                self.device_osc.write(":TRIGger:EDGE:SOURce EXT")
                time.sleep(0.1)
                self.device_osc.write(":TRIGger:EDGE:SLOPe NEG")
                time.sleep(0.1)
                self.device_osc.write(":TRIGger:EDGE:LEVel 2")

                self.device_osc.write(":CHANnel1:DISPlay ON")
                self.device_osc.write(":CHANnel1:OFFSet 0")
                self.device_osc.write(":CHANnel1:SCALe 0.1")
                self.device_osc.write(":CHANnel1:COUPling DC")
                self.device_osc.write(":TIMebase:MAIN:SCALe 10e-6")  # время/дел
                self.device_osc.write(":RUN")
                time.sleep(1)
                srat = self.device_osc.query(":ACQuire:SRATe?")
                srat = srat.strip().split(',')
                time.sleep(0.1)
                offset = ((1 / float(srat[0])) * float(dots))
                self.device_osc.write(":TIMebase:MAIN:OFFSet {}".format(offset / 2))  # позиция по времени
                self.device_osc.write(":STOP")
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
        voltage = (data - yreference) * yincrement + yorigin
        time_axis = [xorigin + i * xincrement for i in range(len(voltage))]
        ## построение осциллограммы
        # plt.figure(1,figsize=(12, 6))
        # plt.plot(time_axis, voltage, 'b-', linewidth=1)
        # plt.grid(True, alpha=0.3)
        # plt.xlabel('Время (с)')
        # plt.ylabel('Напряжение (В)')
        # plt.title('Осциллограмма')
        # plt.tight_layout()
        # plt.show()
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
                file_path = 'C:/Users/asus/Desktop/grant/tests/1/{}.txt'.format(self.count_files)
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

    def burst(self):
        channel = int(self.chan.get())
        if self.chk3_var.get() == 1:
            delay = 0
            self.device.write(':SOUR{}:BURS ON'.format(channel))
            while (self.device.query('*OPC?') != '1\n'):
                time.sleep(0.1)
            self.device.write(':SOUR{}:BURS:MODE TRIG'.format(channel))
            self.device.write(':OUTP{} ON'.format(channel))
            if channel == 1:
                self.chk_var.set(1)
            elif channel == 2:
                self.chk2_var.set(1)
            self.device.write(':SOUR{}:BURS:NCYC 1'.format(channel))
            # device.write(':SOUR{}:BURS:INT:PER 0.001'.format(channel))
            # device.write(':SOUR{}:BURS:TRIG:SOUR EXT'.format(channel))
            self.device.write(':SOUR{}:BURS:TRIG:SOUR MAN'.format(channel))
            # self.device.write(':SOUR{}:BURS:TRIG:TRIGO NEG'.format(channel))
            self.device.write(':OUTP{}:SYNC 1'.format(channel))
            self.device.write(':OUTP{}:SYNC:POL POS'.format(channel))
            self.device.write(':SOUR{}:BURS:TDEL {}'.format(channel, delay / 2))
        else:
            self.device.write(':OUTP{} OFF'.format(channel))
            if channel == 1:
                self.chk_var.set(0)
            elif channel == 2:
                self.chk2_var.set(0)
            self.device.write(':SOUR{}:BURS OFF'.format(channel))
            self.device.write(':OUTP{}:SYNC 0'.format(channel))

    def trigger(self):
        if self.chk3_var.get() == 0:
            if self.status1['text'] == "Подключено":
                self.device_osc.write(":RUN")
                time.sleep(0.1)
                self.device_osc.write(":STOP")
            else:
                messagebox.showwarning("Предупреждение", "Сначала включите функцию Burst")
        else:
            if self.status1['text'] == "Подключено":
                self.device_osc.write(":TRIGger:SWEep SING")  # начнёт записывать, когда рч послед закончится
            time.sleep(0.1)
            channel = int(self.chan.get())
            self.device.write(':SOUR{}:BURS:TRIG'.format(channel))

    def load_file(self):
        tau1 = float(self.duration.get())
        tau2 = 0
        delay = 0
        f = float(self.frate.get())
        samplerate = float(self.srate.get())
        n1 = round(tau1 * samplerate)
        n2 = round(tau2 * samplerate)
        ndel = round(delay * samplerate)
        N = n1 + n2 + ndel
        c1 = round(n1 * f / samplerate)
        c2 = round(n2 * f / samplerate)
        t1 = np.linspace(0, c1 * 2 * np.pi, n1)
        t2 = np.linspace(0, c2 * 2 * np.pi, n2)
        window1 = signal.windows.hann(np.size(t1))
        q = 2 ** 15 - 1
        sine_value1 = (np.sin(t1) * 1 * q)
        sine_value2 = (np.sin(t2) * 1 * q)
        normalized1 = np.round(sine_value1).astype(int)
        normalized2 = np.round(sine_value2).astype(int)
        arrdel = np.zeros(ndel).astype(int)
        res = np.concatenate([normalized1, arrdel, normalized2])
        self.loaded_data = res
        self.status.config(text="Загружено")
        self.file_path = "1"

        ## Открываем диалог выбора файла
        # self.file_path = filedialog.askopenfilename(
        #    title="Выберите текстовый файл",
        #    filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        # )
        # if self.file_path:
        #    self.loaded_data = np.loadtxt(self.file_path)
        #    self.status.config(text="Загружено")

        #    self.chan.delete(0, tk.END)
        #    self.srate.delete(0, tk.END)
        #    self.chk3_var.set(0)
        # else:
        #    messagebox.showwarning("Предупреждение","А где файл? :(")

    def rigol_len(self, length):
        rtxt = "#"
        rtxt += str(len(str(length))) + str(length)
        return rtxt

    def load_dac(self):
        if (self.srate.get() == "") or (self.file_path == " ") or (self.chan.get() == ""):
            messagebox.showwarning("Предупреждение",
                                   "Сначала загрузите файл, установите частоту дискретизации и выберете канал")
        else:
            self.status.config(text="Загрузка сигнала в генератор")
            signal = self.loaded_data
            a = self.srate.get()
            samplerate = float(self.srate.get())
            amplitude = float(self.ampl.get())
            channel = int(self.chan.get())
            self.device.write(':SOUR{}:BURS OFF'.format(channel))
            self.chk3_var.set(0)

            signal = signal / np.max(np.abs(signal))
            q = 2 ** 15 - 1
            value = np.round(signal * q).astype(int)
            samplebytes = struct.pack('<' + 'h' * len(value), *value)
            xcount = 32768
            self.device.write(':OUTP{} OFF'.format(channel))
            if channel == 1:
                self.chk_var.set(0)
            elif channel == 2:
                self.chk2_var.set(0)
            self.device.write('*CLS')
            time.sleep(0.2)
            self.device.write(':APPL:SEQ')
            self.device.write(':SOUR{}:FUNC:SEQ:FILT INSE'.format(channel))
            #  self.device.write(':SOUR{}:VOLT:HIGH 5'.format(channel))
            #  self.device.write(':SOUR{}:VOLT:LOW -5'.format(channel))
            self.device.write(':SOUR{}:VOLT {}'.format(channel, amplitude))
            #  self.device.write(':SOUR{}:VOLT:HIGH 5'.format(channel))
            #  self.device.write(':SOUR{}:VOLT:LOW -5'.format(channel))
            self.device.write(':SOUR{}:FUNC:SEQ:SRAT {}'.format(channel, samplerate))
            while (self.device.query('*OPC?') != '1\n'):
                time.sleep(0.1)
            while (len(samplebytes) > xcount):
                header = f":SOURce{channel}:DATA:DAC16 VOLATILE,CON,"
                self.device.write_raw(
                    header.encode('utf-8') + self.rigol_len(xcount).encode('utf-8') + samplebytes[0:xcount])
                time.sleep(0.2)
                while (self.device.query('*OPC?') != '1\n'):
                    time.sleep(0.1)
                samplebytes = samplebytes[xcount:]
            header = f":SOURce{channel}:DATA:DAC16 VOLATILE,END,"
            self.device.write_raw(
                header.encode('utf-8') + self.rigol_len(len(samplebytes)).encode('utf-8') + samplebytes)
            time.sleep(0.2)
            self.status.config(text="Загружен в генератор")
            # self.device.write(':OUTP{} ON'.format(channel))


root = tk.Tk()
app = App(root)
root.mainloop()