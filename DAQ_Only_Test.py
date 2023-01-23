import sys
import os
from os.path import exists
from PIL import ImageTk
import PIL.Image
from matplotlib.figure import Figure
from matplotlib import style
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.lines as lines
matplotlib.use("TkAgg")
import plotly.graph_objects as go
import plotly.tools as tls
import pandas as pd
from pandastable import Table, TableModel
import tkinter.messagebox as mb
import numpy as np
import time
import serial
import datetime
import tooltip as tp # tooltip is a specific Python file in current folder
import Comp_mapping2 as cm # Comp_mapping2 is a specific Python file in current folder
import multiprocessing as mp
import threading
import queue
from scipy import signal
from queue import Empty

if sys.version_info[0] == 2:
    from Tkinter import *
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg #NavigationToolbar2TkAgg not currently used
    from tkFont import Font
    import tkFileDialog
    import ttk as ttk
    py3=False
else:
    from tkinter import *
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from tkinter.font import Font
    from tkinter import filedialog as tkFileDialog
    import tkinter.ttk as ttk
    from ttkthemes import ThemedTk
    py3=True

path = '/home/pi/Desktop/THM-Meter-DAQ/icons/'  #'C:/Users/fih2o/Desktop/DAQ/icons/'
#path2 = '/home/pi/Desktop/THM-Meter DAQ/'  #'C:/Users/fih2o/Desktop/DAQ/'
path2 = '/home/pi/Desktop/THM-Meter-DAQ/data/'
time_array = []
signal_array = []
"""
from control import DuetController

controller = DuetController("/dev/ttyACM0")

print("Initializing...")
controller.connect()
controller.reset() # reset to clear out any old settings

diode_power = controller.create_output(pin="io4.out")

coil_heater_temp = controller.create_thermistor(
    pin="temp1", resistance=200e3, # 200k thermistor
    b=4725, c=7.06e-8, # example calibration constants
)

coil_heater = controller.create_heater(
    pin="out1", temp_sensor=coil_heater_temp,
    # obtained from manually invoked auto-tuning
    rate=0.207, tc=904, dt=2.71,
)

CMS_heater_temp = controller.create_thermocouple(pin="spi.cs1", kind="K")

CMS_heater = controller.create_heater(
    pin="out2", temp_sensor=CMS_heater_temp,
    # obtained from manually invoked auto-tuning
    rate=0.207, tc=904, dt=2.71,
)

cooler_temp = controller.create_thermistor(
    pin="temp0", resistance=15e3, # 15k thermistor
    b=4725, c=7.06e-8, # example calibration constants
)

cooler = controller.create_heater(
    pin="out0", temp_sensor=cooler_temp,
    # obtained from manually invoked auto-tuning
    rate=0.207, tc=904, dt=2.71, invert=True,
)

pump = controller.create_pump(driver=2, peak_current=4000,
                            steps_per_rev=3200, revs_per_ml=1, invert=True)

valve0 = controller.create_output(pin="io0.out") # Controls Reagents
valve1 = controller.create_output(pin="io1.out") # Controls Reagents
#valve2 = controller.create_output(pin="io2.out") # Controls rinse water

valve7 = controller.create_output(pin="out7") # valve 3 - Internal Standard
valve8 = controller.create_output(pin="out8") # valve 2 - Sample
valve9 = controller.create_output(pin="out9") # valve 1 - Rinse CMS with water
"""

valve7 = 7 # Placeholder values to allow program to run without controller board
valve8 = 8
valve9 = 9

#controller.finish_creation()

#water_only = False # When True, sends only water through 4-way valve
running = True # While True, 4-way valve stays on
def valve_fn():
    """valve_interval = 1
    valve_state = False

    next_time = time.monotonic() + valve_interval
    while running:
        if water_only==True:
            valve1.set_value(False)
            valve2.set_value(False)
            valve3.set_value(True)
        else:
            valve1.set_value(valve_state)
            valve_state = not valve_state
            valve2.set_value(valve_state)

        time.sleep(next_time - time.monotonic())
        next_time += valve_interval

    valve1.set_value(False)
    valve2.set_value(False)
    valve3.set_value(False)"""

valve_thread = threading.Thread(target=valve_fn, daemon=True)

CMS_set_temp = 50 # degrees C
coil_set_temp = 80 # degrees C
cooler_set_temp = 5 # degrees C
def start_stop_heater_cooler(start_heater=True):
    """if start_heater==True:
        print("Turning on heater...")
        CMS_heater.enable(CMS_set_temp)
        coil_heater.enable(coil_set_temp)
        cooler.enable(cooler_set_temp)
        curr_temp = 0
        while ((curr_temp < 45) & (start_heater==True)):
            curr_temp = CMS_heater_temp.get_value()
            print(f"CMS Heater Temperature: {curr_temp:0.1f}        ", end="\r")
            time.sleep(1)
        curr_temp = 0
        while ((curr_temp < 50) & (start_heater==True)):
            curr_temp = coil_heater_temp.get_value()
            print(f"Coil Heater Temperature: {curr_temp:0.1f}        ", end="\r")
            time.sleep(1)
        curr_temp = 100
        while ((curr_temp > 20.5) & (start_heater==True)):
            curr_temp = cooler_temp.get_value()
            print(f"Cooler Temperature: {curr_temp:0.1f}        ", end="\r")
            time.sleep(1)
    else:
        CMS_heater.disable()
        coil_heater.disable()
        cooler.disable()
        curr_temp = coil_heater_temp.get_value()
        while (curr_temp > 43.8):
            curr_temp = coil_heater_temp.get_value()
            print(f"Temperature: {curr_temp:0.1f}        ", end="\r")
            time.sleep(1)"""

first_run = True # Notes whether it is the first run since the program was started
pump_already_started = False # Used to prevent pump/valves from being started twice
def start_stop_pump_valves(start_pump=True):
    """global pump_already_started
    global first_run
    global valve_thread
    if (start_pump==True) and (pump_already_started==False):
        print("Turning on pump...")
        #pump.set_rate(8)
        print("Turning on 4-way valve..")
        if not first_run:
            valve_thread = threading.Thread(target=valve_fn, daemon=True)
        valve_thread.start()
        pump_already_started = True
        first_run = False
    elif(start_pump==False):
        print("Shutting off pump...")
        pump.set_rate(0)
        print("Shutting off valve...")
        valve7.set_value(False)
        valve8.set_value(False)
        valve9.set_value(False)
        print("Turning off 4-way valve..")
        valve_thread.join()
        pump_already_started = False"""

class DAQ_GUI:
        def __init__(self, master):
            start_stop_heater_cooler()
            self.master = master
            master.title("THM-Meter")
            master.configure(bg="white")
            ws = master.winfo_screenwidth()
            hs = master.winfo_screenheight()
            master.geometry('%dx%d' % (ws, hs))
            master.attributes("-fullscreen", False)
            self.tool_frame = Frame(master, borderwidth=1, relief="raised", bg='#f9f5d2')
            self.tool_frame.pack(side=LEFT, fill=Y)
            self.oper_img = ImageTk.PhotoImage(PIL.Image.open(path+'operation.png'))  #pyimage1
            self.operation_frame_button = Button(self.tool_frame,image=self.oper_img,width='34',height='34', relief="raised",
                                            bg='#9b9b9b',activebackground='#c2d6d6',bd=2,justify=RIGHT,command = lambda: self.page_lift(self.operation_mainframe))
            self.operation_frame_button.pack(side=TOP,padx=2,pady=2)
            self.operation_frame_button_ttp = tp.CreateToolTip(self.operation_frame_button, \
            'Current Run')
            self.setup_img = ImageTk.PhotoImage(PIL.Image.open(path+'setup.png')) ###pyimage2
            self.setup_frame_button = Button(self.tool_frame,image=self.setup_img,width='34',height='34', relief="raised",
                                            bg='#9b9b9b',activebackground='#c2d6d6',bd=2,justify=RIGHT,command = lambda: self.page_lift(self.setup_mainframe))
            self.setup_frame_button.pack(side=TOP,padx=2,pady=2)
            self.setup_frame_button_ttp = tp.CreateToolTip(self.setup_frame_button, \
            'Settings')
            self.data_img = ImageTk.PhotoImage(PIL.Image.open(path+'data.png')) ###pyimage3
            self.data_frame_button = Button(self.tool_frame,image=self.data_img,width='34',height='34', relief="raised",
                                            bg='#9b9b9b',activebackground='#c2d6d6',bd=2,justify=RIGHT,command = lambda: self.page_lift(self.data_mainframe))
            self.data_frame_button.pack(side=TOP, padx=2, pady=2)
            self.data_frame_button_ttp = tp.CreateToolTip(self.data_frame_button, \
            'Data-log')
            self.container = Frame(master, bg='white')
            self.container.pack(side=TOP, fill="both", expand=True)
            self.iter_var = IntVar()
            self.incrementVar = IntVar()
            self.IOvar = StringVar()
            self.compvar = StringVar()
            self.on_off = StringVar()
            self.typevar = StringVar()
            self.posvar = StringVar()
            self.itervar = IntVar()
            self.evtvar = StringVar()
            self.current_data_frame()
            self.setup_frame()
            self.operation_frame()
            self.cnt = 0
            self.dataframe = pd.DataFrame(columns=['State','Event','Time'])
            """new_data = {'Event':'Valve 2', 'Time':18, 'State':'ON'}
            self.dataframe = self.dataframe.append(new_data, ignore_index=True)
            new_data = {'Event':'Valve 2', 'Time':23, 'State':'OFF'}
            self.dataframe = self.dataframe.append(new_data, ignore_index=True)
            new_data = {'Event':'Valve 3', 'Time':0.0, 'State':'ON'} #Internal Standard
            self.dataframe = self.dataframe.append(new_data, ignore_index=True)
            new_data = {'Event':'Valve 3', 'Time':5, 'State':'OFF'}
            self.dataframe = self.dataframe.append(new_data, ignore_index=True)
            new_data = {'Event':'Valve 1', 'Time':23, 'State':'ON'}
            self.dataframe = self.dataframe.append(new_data, ignore_index=True)
            new_data = {'Event':'Valve 1', 'Time':45, 'State':'OFF'}
            self.dataframe = self.dataframe.append(new_data, ignore_index=True)"""
            for value in range(self.dataframe.shape[0]):
                self.tree.insert('', 'end', text=self.dataframe.iat[value, 1],
                    values=(self.dataframe.iat[value, 2], self.dataframe.iat[value, 0]))
            #self.comp_dataframe = pd.DataFrame(columns=['Components','Start-Time','End-Time'])
            self.autocal_method = pd.DataFrame(columns=['Type','Level','Position','Runtime','Iters','Events','Filename'])
            #self.valves = {'Valve 3':valve7, 'Valve 2':valve8, 'Valve 1':valve9}
            self.valves = {'Valve 3':valve7, 'Valve 2':valve8, 'Valve 1':valve9}
            self.index= None
            self.index_2= None
            self.iterations = None
            self.delay=None
            self.current_time=None
            self.x = 0
            self.run_time = 0
            self.file_name = None
            self.display_file_name = None
            self.date = None
            self.xid = None
            self.lines = []
            self.lined = dict()
            self.meta_data = dict()
            self.peak_dict = dict()
            self.show_integration = False
            self.eventfile_list = []
            for file in os.listdir(path2):
                if file.endswith('.evt'):
                    self.eventfile_list.append(file)

        def operation_frame(self): # Current run page (main page)
            self.operation_mainframe = Frame(self.container, bg="white")
            self.operation_mainframe.place(in_=self.container, x=0, y=0, relwidth=1, relheight=1)
            self.setframe = Frame(self.operation_mainframe, bg="white")
            self.setframe.pack(side=LEFT,fill=Y,expand=True, anchor='w')
            self.play_img = ImageTk.PhotoImage(PIL.Image.open(path+'play.png'))   ###pyimage4
            self.stop_img = ImageTk.PhotoImage(PIL.Image.open(path+'stop.png'))
            self.add_img = ImageTk.PhotoImage(PIL.Image.open(path+'add.png'))
            self.remove_img = ImageTk.PhotoImage(PIL.Image.open(path+'remove.png'))
            self.save_img = ImageTk.PhotoImage(PIL.Image.open(path+'save.png'))
            self.run_button= Button(self.setframe,image=self.play_img, width='60', height='60',
                    bg='white',activebackground='white', bd=0,justify=CENTER, command=lambda:self.start_stop(sequence=False))
            self.run_button.grid(row=0,column=0,rowspan=2, sticky='w')
            self.run_button_ttp = tp.CreateToolTip(self.run_button, \
            'Start/Stop Run')
            self.iter_button = ttk.Checkbutton(self.setframe,text="Iterations", variable=self.iter_var)
            self.iter_button.grid(row=0,column=1,sticky='w')
            self.iter_button_ttp = tp.CreateToolTip(self.iter_button, \
            'Check to run multiple analyses.')
            self.iter_entry = ttk.Entry(self.setframe,width=10,validate='key', validatecommand= (self.master.register(self.onValidation), '%P'))
            self.iter_entry.grid(row=0, column=2,sticky='w')
            self.iter_entry_ttp = tp.CreateToolTip(self.iter_entry, \
            'Number of analyses to run.')
            self.delay_label = Label(self.setframe,bg="white", text ='Delay (hrs)')
            self.delay_label_ttp = tp.CreateToolTip(self.delay_label, \
            'Determines how long of a delay is between runs.')
            self.delay_label.grid(row=1,column=1,pady=2,sticky='w')
            self.delay_entry = ttk.Entry(self.setframe,width=10,validate='key', validatecommand= (self.master.register(self.onValidation), '%P'))
            self.delay_entry.grid(row=1,column=2,pady=2,sticky='w')
            self.delay_entry_ttp = tp.CreateToolTip(self.delay_entry, \
            'Determines how long of a delay is between runs.')
            self.run_progress = ttk.Progressbar(self.setframe,orient="horizontal",length=150,maximum=100,mode="determinate") #style="run.Horizontal.TProgressbar",
            self.run_progress.grid(row=2,column=0,columnspan=2,pady=5, sticky='w')
            self.runvalue_label = Label(self.setframe,bg="white",text ='0 %')
            self.runvalue_label.grid(row=2,column=2,sticky="w")
            self.next_run_label = Label(self.setframe,bg="white",text ='Next Run at:')
            self.next_run_label.grid(row=3,column=0,sticky="w")
            self.next_run_timeupdate_label = Label(self.setframe,bg="white",text=' - - : - - : - - : - - ')
            self.next_run_timeupdate_label.grid(row=3,column=1, columnspan=2, sticky="w")

            self.file = Label(self.setframe, text= 'File name',bg='WHITE')
            self.file.grid(row=4, column=0, sticky='w', pady=5)
            self.file_ttp = tp.CreateToolTip(self.file, \
            'Name to save your file as.')
            self.file_entry = ttk.Entry(self.setframe,width=10)
            self.file_entry.grid(row=4, column=1)
            self.file_entry_ttp = tp.CreateToolTip(self.file_entry, \
            'Name to save your file as.')
            self.auto_increments_button = ttk.Checkbutton(self.setframe,text = 'Auto-Increment', variable=self.incrementVar)
            self.incrementVar.set(1)
            self.auto_increments_button_ttp = tp.CreateToolTip(self.auto_increments_button, \
            'Check to auto-save the files with the increment of 1.')
            self.auto_increments_button.grid(row=4, column=2, sticky='w', pady=15)
            self.ts = Label(self.setframe, text= 'Runtime', bg='WHITE')
            self.ts.grid(row=5,column=0, sticky='w', padx=10)
            self.ts_ttp = tp.CreateToolTip(self.ts, \
            'Enter the minutes for a single run.')
            self.bs = ttk.Entry(self.setframe,width=10,validate='key', validatecommand= (self.master.register(self.onValidation), '%P'))
            self.bs_ttp = tp.CreateToolTip(self.bs, \
            'Enter the minutes for a single run.')
            self.bs.grid(row=5, column=1, sticky='e')
            self.timelabel = Label(self.setframe, text= 'mins', bg='WHITE')
            self.timelabel.grid(row=5, column=2, sticky='w')
            self.led_power = Label(self.setframe,bg="white",text ='LED Power:')
            self.led_power.grid(row=8,column=0,sticky="w")
            #self.diode_signal = (ads.get_last_result())*LSB
            self.diode_signal = 100
            self.led_power_update_label = Label(self.setframe,bg="white",text='{:d} mV'.format(int(self.diode_signal)))
            self.led_power_update_label.grid(row=8,column=1, columnspan=2, sticky="w")

            self.file_frame = LabelFrame(self.setframe, bg='white', text='File', width='140', height='65')
            self.file_frame.grid(row=6,columnspan=3, sticky='w')
            self.file_frame.grid_propagate(False)
            self.add_file_bt = Button(self.file_frame, image=self.add_img,width='30',height='30',
                                                bg='white', activebackground='white',relief='raised',justify=RIGHT,
                                                command=lambda:self.add_file(by='file',data=None,file=None))
            self.add_file_bt.grid(row=0,column=0,padx=(10,1))
            tp.CreateToolTip(self.add_file_bt, 'Open a file.')
            self.remove_file_bt = Button(self.file_frame, image=self.remove_img,width='30',height='30',
                                                bg='white',activebackground='white',relief='raised', justify=RIGHT,  command=self.remove_event_connect)
            self.remove_file_bt.grid(row=0,column=1,padx=1)
            tp.CreateToolTip(self.remove_file_bt, 'Remove selected file from graph')
            self.save_file_bt = Button(self.file_frame, image=self.save_img, width='30',height='30',relief='raised',
                                                bg='white',activebackground='white',justify=RIGHT)
            self.save_file_bt.grid(row=0,column=2,padx=1)
            tp.CreateToolTip(self.save_file_bt, 'Save file as...')
            self.graph_lims = LabelFrame(self.setframe, bg='white', text='Axes-limits', width='280', height='110')
            self.graph_lims.grid(row=7, columnspan=3, sticky='w')
            self.graph_lims.grid_propagate(False)
            Ax_from = Label(self.graph_lims, text='From', bg='white')
            Ax_from.grid(row=0, column=1)
            y_lab = Label(self.graph_lims, text='Y-Axes', bg='white')
            y_lab.grid(row=1, column=0)
            self.y_lim_start = ttk.Entry(self.graph_lims, width=7, validate='key', validatecommand= (self.master.register(self.onValidation), '%P'))
            self.y_lim_start.grid(row=1, column=1)
            x_lab = Label(self.graph_lims, text='X-Axes', bg='white', pady = 5)
            x_lab.grid(row=2, column=0)
            self.x_lim_start = ttk.Entry(self.graph_lims, width=7, validate='key', validatecommand= (self.master.register(self.onValidation), '%P'))
            self.x_lim_start.grid(row=2, column=1)
            Ax_to = Label(self.graph_lims, text='To', bg='white')
            Ax_to.grid(row=0, column=2)
            tp.CreateToolTip(self.y_lim_start, 'Lower limit of Y-axes')
            tp.CreateToolTip(self.x_lim_start, 'Lower limit of X-axes')
            self.y_lim_end = ttk.Entry(self.graph_lims, width=7, validate='key', validatecommand= (self.master.register(self.onValidation), '%P'))
            self.y_lim_end.grid(row=1, column=2, padx = 4)
            self.x_lim_end = ttk.Entry(self.graph_lims, width=7, validate='key', validatecommand= (self.master.register(self.onValidation), '%P'))
            self.x_lim_end.grid(row=2, column=2)
            tp.CreateToolTip(self.y_lim_end, 'Upper limit of Y-axes')
            tp.CreateToolTip(self.x_lim_end, 'Upper limit of X-axes')
            axes_lim_set = ttk.Button(self.graph_lims, text='SET', width=4,command = self.ylims_set)
            axes_lim_set.grid(row=1, column=3, rowspan=2, padx=(5,0))
            self.graph_frame = Frame(self.operation_mainframe)
            self.graph_frame.pack(side=TOP, anchor='n')
            plt.ion()
            #self.f = Figure(figsize=(6.5, 3))
            self.f = Figure(figsize=(7.5, 2.5))
            self.ax1 = self.f.add_subplot(111)
            self.ax1.set_ylabel('mV')
            self.ax1.set_xlabel('Time (min)')   #, labelpad =-140) # negative padding to move the label to top
            self.f.subplots_adjust(right=0.99,left=0.11,top=0.985, bottom = .19)
            self.data_line, = self.ax1.plot([], [])
            self.canvas = FigureCanvasTkAgg(self.f, self.graph_frame)
            if py3:
                self.canvas.draw()
            else:
                self.canvas.show()
            self.canvas.get_tk_widget().pack(side=BOTTOM, fill=BOTH, expand=False)
            self.update_meter_image()
            self.toolbar = NavigationToolbar2Tk(self.canvas,self.graph_frame)
            self.toolbar.update()
            #self.operation_mainframe.lift()
            #self.style = ttk.Style()

        def setup_frame(self): # Settings page (second page)
            self.up_img = ImageTk.PhotoImage(PIL.Image.open(path+'up_arrow.png'))
            self.down_img = ImageTk.PhotoImage(PIL.Image.open(path+'down_arrow.png'))
            self.setup_mainframe = Frame(self.container,bg='WHITE')
            self.setup_mainframe.place(in_=self.container, x=0, y=0, relwidth=1, relheight=1)

            #Create password lock
            self.adminframe = Frame(self.setup_mainframe,bg='WHITE')
            self.adminframe.place(x=300, y=200)
            self.admin_label = Label(self.adminframe,
                                     text="Enter Administrative Password",
                                     font=("Comic Sans",25),
                                     bg='WHITE'
                                     )
            self.admin_label.grid(row=0,column=0)
            self.password_entry = ttk.Entry(self.adminframe,
                                            width=10,
                                            #validate='key',
                                            #validatecommand= (self.master.register(self.onValidation), '%P'),
                                            font=("Comic Sans",15)
                                            )
            self.password_entry.grid(row=1, column=0,)
            self.password_entry_ttp = tp.CreateToolTip(self.password_entry, \
            'Enter Password')
            self.password=Button(self.adminframe, text='Enter', width=7, font=("Comic Sans",15), command=self.admin_password)
            self.password.grid(row=2, column=0, padx=20)

            #self.backframe = Frame(self.setup_mainframe,bg='WHITE')
            #self.backframe.place(x=1300, y=325)

            self.eventframe = Frame(self.setup_mainframe,bg='WHITE')
            #self.eventframe.place(x=1300, y=325)

            self.tree=ttk.Treeview(self.eventframe,selectmode='browse')
            self.tree["columns"]=("one","two")
            self.tree.column("#0", width=150,stretch=False)
            self.tree.column("one", width=100,stretch=False)
            self.tree.column("two", width=100,stretch=False)
            self.tree.heading("#0",text="Events")
            self.tree.heading("one", text="Time")
            self.tree.heading("two", text="On/Off")
            self.tree.pack(side=LEFT)
            vsb = ttk.Scrollbar(self.eventframe, orient="vertical", command=self.tree.yview)
            vsb.pack(side=LEFT, anchor='n',fill='y')
            self.tree.configure(yscrollcommand=vsb.set)

            self.buttonframe = Frame(self.setup_mainframe,bg='WHITE')

            #self.buttonframe.place(x=1300, y=600)

            self.add=ttk.Button(self.buttonframe, text='  Add ', width=7, command=self.add_event)
            self.add.grid(row=1, column=0)
            self.add_ttp = tp.CreateToolTip(self.add, \
            'Adds a data entry.')
            self.change=ttk.Button(self.buttonframe, text='Change', width=7, command=self.change_event)
            self.change.grid(row=1, column=1, padx=20)
            self.change_ttp = tp.CreateToolTip(self.change, \
            'Edits the values of a data entry.')
            self.load=ttk.Button(self.buttonframe, text=' Load ', width=7, command=self.load_event)
            self.load.grid(row=1, column=2)
            self.load_ttp = tp.CreateToolTip(self.load, \
            'Loads the data from a file.')
            self.save=ttk.Button(self.buttonframe, text=' Save ', width=7, command=self.save_event)
            self.save.grid(row=2, column=0, padx=20)
            self.save_ttp = tp.CreateToolTip(self.save, \
            'Save events to file')
            self.remove_evt=ttk.Button(self.buttonframe, text='Remove', width=7, command=self.remove_event)
            self.remove_evt.grid(row=2, column=1,padx=10, pady=10)
            self.remove_evt_ttp = tp.CreateToolTip(self.remove_evt, \
            'Remove selected event')
            self.clear_evt=ttk.Button(self.buttonframe, text='Clear', width=7, command=lambda:self.clear_all(table='event'))
            self.clear_evt.grid(row=2, column=2, padx=20)
            self.clear_evt_ttp = tp.CreateToolTip(self.clear_evt, \
            'Clear all events')

            #control frame
            self.control_frame = Frame(self.setup_mainframe,bg='WHITE')

            #self.control_frame.place(x=0, y=0)

             #Heater Input
            self.heater_entry = ttk.Entry(self.control_frame,
                                          width=10,
                                          validate='key',
                                          validatecommand= (self.master.register(self.onValidation), '%P'),
                                          font=("Comic Sans",15)
                                          )
            self.heater_entry.grid(row=4, column=1,)
            self.heater_entry_ttp = tp.CreateToolTip(self.heater_entry, \
            'Set coil heater temperature in C')

            #CMS Heater Input
            self.cmsheater_entry = ttk.Entry(self.control_frame,
                                          width=10,
                                          validate='key',
                                          validatecommand= (self.master.register(self.onValidation), '%P'),
                                          font=("Comic Sans",15)
                                          )
            #Heater Input
            self.heater_entry = ttk.Entry(self.control_frame,
                                          width=10,
                                          validate='key',
                                          validatecommand= (self.master.register(self.onValidation), '%P'),
                                          font=("Comic Sans",15)
                                          )
            self.heater_entry.grid(row=4, column=1,)
            self.heater_entry_ttp = tp.CreateToolTip(self.heater_entry, \
            'Set coil heater temperature in C')

            #CMS Heater Input
            self.cmsheater_entry = ttk.Entry(self.control_frame,
                                          width=10,
                                          validate='key',
                                          validatecommand= (self.master.register(self.onValidation), '%P'),
                                          font=("Comic Sans",15)
                                          )
            self.cmsheater_entry.grid(row=7, column=1,)
            self.cmsheater_entry_ttp = tp.CreateToolTip(self.cmsheater_entry, \
            'Set CMS heater temperature in C')

            #Pump Slider and Input
            self.pump_entry = ttk.Entry(self.control_frame,
                                          width=10,
                                          validate='key',
                                          validatecommand= (self.master.register(self.onValidation), '%P'),
                                          font=("Comic Sans",15)
                                          )
            self.pump_entry.grid(row=10, column=1,)
            self.pump_entry_ttp = tp.CreateToolTip(self.pump_entry, \
            'Set peristaltic pump rpm')

            #Peltier Cooler Input
            self.cooler_entry = ttk.Entry(self.control_frame,
                                          width=10,
                                          validate='key',
                                          validatecommand= (self.master.register(self.onValidation), '%P'),
                                          font=("Comic Sans",15)
                                          )
            self.cooler_entry.grid(row=1, column=1,)
            self.cooler_entry_ttp = tp.CreateToolTip(self.cooler_entry, \
            'Set cooler temperature in C')

            #Input Set Buttons
            self.button_heater_input = Button(self.control_frame, text="Set", command=self.click_set_heater, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_heater_input.grid(row=4, column=0,)
            self.button_cmsheater_input = Button(self.control_frame, text="Set", command=self.click_set_cmsheater, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_cmsheater_input.grid(row=7, column=0,)
            self.button_pump_input = Button(self.control_frame, text="Set", command=self.click_set_pump, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_pump_input.grid(row=10, column=0,)
            self.button_cooler_input = Button(self.control_frame, text="Set", command=self.click_set_cooler, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_cooler_input.grid(row=1, column=0,)

            #3way Valve Buttons
            self.button_on_7 = Button(self.control_frame, text="On", command=self.click_on_7, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_on_7.grid(row=1,column=2,sticky='w')
            self.button_off_7 = Button(self.control_frame, text="Off", command=self.click_off_7, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_off_7.grid(row=2,column=2,sticky='w')
            self.button_on_8 = Button(self.control_frame, text="On", command=self.click_on_8, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_on_8.grid(row=4,column=2,sticky='w')
            self.button_off_8 = Button(self.control_frame, text="Off", command=self.click_off_8, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_off_8.grid(row=5,column=2,sticky='w')
            self.button_on_9 = Button(self.control_frame, text="On", command=self.click_on_9, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_on_9.grid(row=7,column=2,sticky='w')
            self.button_off_9 = Button(self.control_frame, text="Off", command=self.click_off_9, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_off_9.grid(row=8,column=2,sticky='w')

            #4way Valve Buttons
            self.button_valve_1_on = Button(self.control_frame, text="Position 1 on", command=self.click_valve_1_on, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_valve_1_on.grid(row=12,column=0,sticky='w')
            self.button_valve_2_on = Button(self.control_frame, text="Position 2 on", command=self.click_valve_2_on, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_valve_2_on.grid(row=13,column=0,sticky='w')
            self.button_valve_3_on = Button(self.control_frame, text="Position 3 on", command=self.click_valve_3_on, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_valve_3_on.grid(row=14,column=0,sticky='w')
            self.button_valve_4_on = Button(self.control_frame, text="Position 4 on", command=self.click_valve_4_on, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_valve_4_on.grid(row=15,column=0,sticky='w')
            self.button_valve_1_off = Button(self.control_frame, text="Position 1 off", command=self.click_valve_1_off, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_valve_1_off.grid(row=12,column=1,sticky='w')
            self.button_valve_2_off = Button(self.control_frame, text="Position 2 off", command=self.click_valve_2_off, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_valve_2_off.grid(row=13,column=1,sticky='w')
            self.button_valve_3_off = Button(self.control_frame, text="Position 3 off", command=self.click_valve_3_off, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_valve_3_off.grid(row=14,column=1,sticky='w')
            self.button_valve_4_off = Button(self.control_frame, text="Position 4 off", command=self.click_valve_4_off, font=("Comic Sans",15), fg="#004f7c", activeforeground="#004f7c")
            self.button_valve_4_off.grid(row=15,column=1,sticky='w')

            #Control Labels
            self.cooler_label = Label(self.control_frame, text="Cooler Temperature", font=("Comic Sans",15), bg='WHITE')
            self.cooler_label.grid(row=0,column=1)
            self.cooler_set_label = Label(self.control_frame, text="", font=("Comic Sans",15), bg='WHITE')
            self.cooler_set_label.grid(row=2,column=1)
            self.heater_label = Label(self.control_frame, text="Coil Heater Temperature", font=("Comic Sans",15), bg='WHITE')
            self.heater_label.grid(row=3,column=1)
            self.heater_set_label = Label(self.control_frame, text="", font=("Comic Sans",15), bg='WHITE')
            self.heater_set_label.grid(row=5,column=1)
            self.cmsheater_label = Label(self.control_frame, text="CMS Heater Temperature", font=("Comic Sans",15), bg='WHITE')
            self.cmsheater_label.grid(row=6,column=1)
            self.cmsheater_set_label = Label(self.control_frame, text="", font=("Comic Sans",15), bg='WHITE')
            self.cmsheater_set_label.grid(row=8,column=1)
            self.pump_label = Label(self.control_frame, text="Peristaltic Pump Speed", font=("Comic Sans",15), bg='WHITE')
            self.pump_label.grid(row=9,column=1)
            self.pump_set_label = Label(self.control_frame, text="", font=("Comic Sans",15), bg='WHITE')
            self.pump_set_label.grid(row=11,column=1)
            self.valve_7_label = Label(self.control_frame, text="Valve 7", font=("Comic Sans",15), bg='WHITE')
            self.valve_7_label.grid(row=0,column=2)
            self.valve_8_label = Label(self.control_frame, text="Valve 8", font=("Comic Sans",15), bg='WHITE')
            self.valve_8_label.grid(row=3,column=2)
            self.valve_9_label = Label(self.control_frame, text="Valve 9", font=("Comic Sans",15), bg='WHITE')
            self.valve_9_label.grid(row=6,column=2)
            self.valve_4_way_label = Label(self.control_frame, text="4 Way Valve", font=("Comic Sans",15), bg='WHITE')
            self.valve_4_way_label.grid(row=11,column=0)

            self.report_subframe = Frame(self.setup_mainframe)

            #self.report_subframe.place(x=1300, y=0)

            empty_data = ({'Components':['Baseline','Sample'],'Start (min)':[17, 31],'Stop (min)':[20,34],
                            'Average':['-', '-']})
            df = pd.DataFrame(empty_data)
            self.avg_table = pK = Table(self.report_subframe, dataframe=df, ascending=False,
                                showtoolbar=False, showstatusbar=False)
            self.avg_table.expandColumns()
            self.avg_table.show()
            del df
            self.style = ttk.Style()

        def clear_frame(self): # Removes text box when correct password entered
            for widget in self.adminframe.winfo_children():
                widget.destroy()

        def inc_pw(self): # Message when incorrect password is entered
            inc_top= Toplevel(self.setup_mainframe)
            inc_top.geometry("400x200")
            inc_top.title("Admin Frame")
            inc_label= Label(inc_top, text="Incorrect Password", font=("Comic Sans",25) )
            inc_label.pack()

        def admin_password(self): # Password entry processing
            pw = self.password_entry.get()

            #if pw == "dolphin":
            if pw == "":
                self.clear_frame()
                self.eventframe.place(x=600, y=200)
                self.report_subframe.place(x=530, y=0, relheight=.3)
                self.buttonframe.place(x=600, y=480)
                self.control_frame.place(x=0, y=0)
            else:
                self.inc_pw()

        def click_set_heater(self):
            global coil_set_temp
            coil_set_temp = float(self.heater_entry.get())
            coil_heater.enable(coil_set_temp)
            print("Coil Heater Temperature set to", coil_set_temp)

        def click_set_cmsheater(self):
            global CMS_set_temp
            CMS_set_temp = float(self.cmsheater_entry.get())
            CMS_heater.enable(CMS_set_temp)
            print("CMS Heater Temperature set to", CMS_set_temp)

        def click_set_pump(self):
            global pump_speed
            pump_speed = float(self.pump_entry.get())
            print("Pump rpm to", pump_speed)

        def click_set_cooler(self):
            global cooler_set_temp
            cooler_set_temp = float(self.cooler_entry.get())
            cooler.enable(cooler_set_temp)
            print("Cooler Temperature set to", cooler_set_temp)

        def click_valve_1_on(self):
            valve1.set_value(True)
            print("Valve 1 On")

        def click_valve_1_off(self):
            valve1.set_value(False)
            print("Valve 1 Off")

        def click_valve_2_on(self):
            valve2.set_value(True)
            print("Valve 2 On")

        def click_valve_2_off(self):
            valve2.set_value(False)
            print("Valve 2 Off")

        def click_valve_3_on(self):
            valve3.set_value(True)
            print("Valve 3 On")

        def click_valve_3_off(self):
            valve3.set_value(False)
            print("Valve 3 Off")

        def click_valve_4_on(self):
            valve4.set_value(True)
            print("Valve 4 On")

        def click_valve_4_off(self):
            valve4.set_value(False)
            print("Valve 4 Off")

        def click_on_7(self):
            valve7.set_value(True)
            print("Valve 7 On")

        def click_off_7(self):
            valve7.set_value(False)
            print("Valve 7 Off")

        def click_on_8(self):
            valve8.set_value(True)
            print("Valve 8 On")

        def click_off_8(self):
            valve8.set_value(False)
            print("Valve 8 Off")

        def click_on_9(self):
            valve9.set_value(True)
            print("Valve 9 On")

        def click_off_9(self):
            valve9.set_value(False)
            print("Valve 9 Off")

        def update_meter_image(self, THM_conc=0, end_run=False): # Updates/Creates new image of meter with THM Conc
            THM_conc = THM_conc/10
            fig = go.Figure(go.Indicator(
                domain = {'x': [0, 1], 'y': [0, 1]},
                value = THM_conc,
                mode = "gauge+number",
                title = {'text': "THM Concentration (ppb)"},
                gauge = {'axis': {'range': [None, 100]},
                        'bar': {'color': "black"},
                         'steps' : [
                             {'range': [0, 60], 'color': "green"},
                             {'range': [60, 80], 'color': "yellow"},
                             {'range': [80, 100], 'color': "red"}]}))
            fig.update_traces(gauge_axis_dtick=10)
            fig.write_image(path+"fig1.png")
            img_1 = PIL.Image.open(path+'fig1.png')
            #img_area = (50, 80, 650, 410)
            img_area = (40, 70, 670, 415)
            self.meter_img = img_1.crop(img_area)
            #self.meter_img = self.meter_img.resize((400,217))
            self.meter_img = self.meter_img.resize((600,370))
            self.meter_img = ImageTk.PhotoImage(self.meter_img)
            self.meter_subframe = Frame(self.operation_mainframe)
            self.meter_subframe.pack(side=TOP,fill=Y, expand=True, anchor='n')
            if (end_run):
                self.meter_button.config(image=self.meter_img)
            else:
                self.meter_button= Button(self.meter_subframe,image=self.meter_img, width='600', height='370',
                    bg='white',activebackground='white', bd=0,justify=CENTER)
                self.meter_button.grid(row=0,column=0, sticky='w')

        def ylims_set(self): # "Axes-limits" on Current Run page
            try:
                up_lim = float(self.y_lim_end.get())
                lo_lim = float(self.y_lim_start.get())
                left_lim = float(self.x_lim_start.get())
                right_lim = float(self.x_lim_end.get())
                if up_lim < lo_lim or left_lim > right_lim:
                    mb.showwarning('warning', 'Upper limit should be greater than lower limit')
                    return
                self.ax1.set_ylim((lo_lim, up_lim))
                self.ax1.set_xlim((left_lim, right_lim))
                self.canvas.draw()
                self.canvas.flush_events()
            except ValueError as e:
                mb.showerror('Error', 'Enter proper values in the boxes')

        def add_file(self,by=None,data=None,file=None): # "Open a file" on Current run page under "File"
            try:
                if by == 'file':
                    load_chrname = tkFileDialog.askopenfilename(initialdir = path2, title = "Load file",filetypes = (("Data","*.gra"),("all files","*.*")))
                    data = pd.read_parquet(load_chrname)
                    line = os.path.basename(load_chrname)
                    meta_data = data[['Components', 'Start (min)', 'Stop (min)', 'Average']].copy().dropna()
                elif by == 'current':
                    data = data
                    self.data_line.set_data([], [])
                    self.canvas.draw_idle()
                    line = os.path.basename(file)
                    meta_data = data[['Components', 'Start (min)', 'Stop (min)', 'Average']].copy().dropna()
                    self.show_current_data(meta_data)
                    if self.file_name == path2:
                        file_name_csv = path2 + "unnamed.csv"
                        data.to_csv(file_name_csv,index=False)
                    elif self.file_name != None:
                        file_name_csv = self.file_name + ".csv"
                        data.to_csv(file_name_csv,index=False)
                if len(self.lines)>0:
                    if line in self.ax1.get_legend_handles_labels()[1]:
                        return
                line = self.ax1.plot(data['Time'], data['Signal'], label=line)
                """mi.data(data['Time'],data['Signal'])
                size = data['Start'].count()
                cm.find_match(meta_data, line[0])
                cm.find_match.comp_table_2 = self.comp_dataframe
                self.show_current_data(line[0])"""
                text_list = []
                iline_list = []
                self.peak_dict.clear()  ### helps to allow users edit the last added file
                peak_prop = {}
                self.peak_dict[line[0]] = peak_prop
                self.meta_data[line[0]] = [iline_list, text_list]
                self.leg=self.ax1.legend(loc='upper left')
                self.lines.extend(line)
                self.lined.clear()
                for legline, origline in zip(self.leg.get_lines(), self.lines):
                    legline.set_picker(5)
                    #self.lined[legline] = [origline, [self.meta_data[origline][0],self.meta_data[origline][1]]]
                    self.lined[legline] = origline
                self.canvas.draw_idle()
            except IOError:
                mb.showerror('Error', 'Select a file to open')

        def remove_event_connect(self): # "Remove selected file from graph" on Current run page under "File"
            try:
                if self.remove_file_bt['relief'] == 'raised':
                    self.remove_file_bt.config(relief='sunken')
                    self.ppid = self.canvas.mpl_connect('pick_event', self.plot_remove)
                else:
                    self.remove_file_bt.config(relief='raised')
                    self.canvas.mpl_disconnect(self.ppid)
            except Exception as e:
                mb.showerror('Error', '{} line: {}'.format(e, sys.exc_info()[-1].tb_lineno))

        def compute_average(self, time_start, time_stop): # Compute average signal over a given period of time
            sum = 0.0
            num = 0
            for i in range(len(time_array)):
                if (time_array[i] > time_start) & (time_array[i] < time_stop):
                    sum += signal_array[i]
                    num += 1
            if (num==0):
                return 0
            avg = sum/num
            return(avg)

        def compute_conc(self, samp_sig):
            m = 4.5324 # From calibration curve
            b = -27.656 # From calibration curve
            samp_conc = (samp_sig - b)/m
            return samp_conc

        """def compute_conc_IS(self, samp_sig, std_sig): # Uses internal standard equation to calculate concentration of sample
            std_conc = ____Needs_to_be_assigned____
            response_factor = ____Needs_to_be_assigned____
            sample_conc = samp_sig * (std_conc/std_sig) / response_factor # std_sig = signal from the standard
            print(sample_conc)"""

        def plot_remove(self, event):
            try:
                legline = event.artist
                if not legline in self.lined.keys():
                    return
                if self.file_name != None:
                    if legline.get_label() == os.path.basename(self.file_name)+'.gra':
                        return
                #origline = self.lined[legline][0]
                origline = self.lined[legline]
                self.ax1.lines.remove(origline)
                """for text in self.lined[legline][1][1]:
                    text.remove()"""
                """for iline in self.lined[legline][1][0]:
                    self.ax1.lines.remove(iline)"""
                self.lines.remove(origline)
                self.meta_data.pop(origline)
                """cm.find_match.instances.pop(origline)
                if len(cm.find_match.instances)>0:
                    self.show_current_data(list(cm.find_match.instances.keys())[-1])"""
                self.lined.clear()
                self.leg=self.ax1.legend(loc='upper left')
                for legline, origline in zip(self.leg.get_lines(), self.lines):
                        legline.set_picker(5)
                        self.lined[legline] = origline
                        #self.lined[legline] = [origline, [self.meta_data[origline][0],self.meta_data[origline][1]]]
                self.canvas.draw_idle()
            except Exception as e:
                mb.showerror('Error', '{} line: {}'.format(e, sys.exc_info()[-1].tb_lineno))

        def previous_plot_remove(self, file=None):
            try:
                index = self.ax1.get_legend_handles_labels()[1].index(file+'.gra')
                origline = self.ax1.get_legend_handles_labels()[0][index]
                #legline = list(self.lined.keys())[list(self.lined.values())[0].index(origline)]
                self.ax1.lines.remove(origline)
                """for text in self.lined[legline][1][1]:
                    text.remove()"""
                """for iline in self.lined[legline][1][0]:
                    self.ax1.lines.remove(iline)"""
                self.lines.remove(origline)
                self.meta_data.pop(origline)
                """cm.find_match.instances.pop(origline)
                if len(cm.find_match.instances)>0:
                    self.show_current_data(list(cm.find_match.instances.keys())[-1])"""
                self.lined.clear()
                self.leg=self.ax1.legend(loc='upper left')
                """for legline, origline in zip(self.leg.get_lines(), self.lines):
                        legline.set_picker(5)
                        self.lined[legline] = [origline, [self.meta_data[origline][0],self.meta_data[origline][1]]]"""
                self.canvas.draw_idle()
            except Exception as e:
                mb.showerror('Error', '{} line: {}'.format(e, sys.exc_info()[-1].tb_lineno))

        def show_current_data(self, current_data):
            try:
                df = current_data.sort_values(by='Start (min)', ascending=True)
                self.avg_table.model.df = df
                self.avg_table.redraw()
                del df
                return
            except Exception as e:
                mb.showerror('Error', '{} line: {}'.format(e, sys.exc_info()[-1].tb_lineno))

        def add_event(self, condition=None): # "Add" on Settings page under event list
            try:
                self.event_window=Toplevel(bg='WHITE')
                self.event_window.title('ADD EVENTS')
                self.event_window.geometry("%dx%d+%d+%d" % (350,100, 50, 400))
                self.event_window.transient(master=self.master)
                self.event_window.grab_set()
                self.IO_select = ttk.Combobox(self.event_window, textvariable=self.IOvar, values=sorted(self.valves.keys()), state="readonly",
                                              width=15, height=5)
                myfont = Font(family ='Times New Roman', size=12)
                self.IO_select.config(font = myfont)
                self.style.map('TCombobox', fieldbackground=[('readonly','white')])
                self.style.map('TCombobox', selectbackground=[('readonly', 'white')])
                self.style.map('TCombobox', selectforeground=[('readonly', 'blue')])
                self.IOvar.set('Valve 1')
                self.IO_select.grid(row=0, column=0)
                self.event_time = Entry(self.event_window, bg='white', width=8,validate='key', validatecommand= (self.master.register(self.onValidation), '%P'))
                self.event_time.grid(row=0, column=1, padx=5)
                if condition == None:
                    self.event_time.insert(0,'0.0')
                self.timelabel = Label(self.event_window, text='mins', bg='WHITE')
                self.timelabel.grid(row=0, column=2, sticky='w')
                self.on_off_button = Checkbutton(self.event_window, bg='WHITE', text='ON/OFF', variable = self.on_off,
                     onvalue = 'ON', offvalue = 'OFF')
                self.on_off.set('OFF')
                self.on_off_button.grid(row=0, column=3, sticky='e')
                self.insert = ttk.Button(self.event_window, text = 'Insert', command=lambda:self.insert_event(condition))
                self.insert.grid(row=1, column=0, columnspan=3, pady=5)
                return
            except Exception as e:
                mb.showerror('Error', '{} line: {}'.format(e, sys.exc_info()[-1].tb_lineno))

        def insert_event(self, condition=None): # "Insert" on Settings page under the event list after clicking "Add"
            try:
                if condition == None:
                    new_data = {'Event':self.IOvar.get(), 'Time':float(self.event_time.get()), 'State':self.on_off.get()}
                    self.dataframe = self.dataframe.append(new_data, ignore_index=True)
                    self.dataframe.sort_values(by=['Time'], ascending=True, inplace=True)
                    self.dataframe.reset_index(drop=True, inplace =True)
                    self.tree.delete(*self.tree.get_children())
                elif condition == 'change':
                    item_idex = self.index
                    self.dataframe.at[item_idex, 'Event']=self.IOvar.get()
                    self.dataframe.at[item_idex, 'Time']=float(self.event_time.get())
                    self.dataframe.at[item_idex, 'State']=self.on_off.get()
                    self.dataframe.sort_values(by=['Time'], ascending=True, inplace=True)
                    self.dataframe.reset_index(drop=True, inplace =True)
                    self.tree.delete(*self.tree.get_children())
                    self.event_window.destroy()
                for value in range(self.dataframe.shape[0]):
                        self.tree.insert('', 'end', text=self.dataframe.iat[value, 1],
                             values=(self.dataframe.iat[value, 2], self.dataframe.iat[value, 0]))
            except Exception as e:
                mb.showerror('Error', '{} line: {}'.format(e, sys.exc_info()[-1].tb_lineno))

        def change_event(self): # "Change" on Settings page under event list
            try:
                item_idex = self.tree.focus()
                if item_idex != '':
                    self.add_event('change')
                    current_item=self.tree.item(item_idex)
                    self.index = self.tree.index(item_idex)
                    self.IOvar.set(current_item['text'])
                    self.event_time.insert(0, current_item['values'][0])
                    self.on_off.set(current_item['values'][1])
                else:
                    mb.showerror('Error', 'Select a row to edit')
            except Exception as e:
                mb.showerror('Error', '{} line: {}'.format(e, sys.exc_info()[-1].tb_lineno))

        def save_event(self): # "Save" on Settings page under event list
            try:
                save_filename = tkFileDialog.asksaveasfilename(initialdir = path2,title = "Save file",filetypes = (("Event","*.evt"),("all files","*.*")))
                self.dataframe.to_csv(os.path.join(os.path.splitext(save_filename)[0]+'.evt'), sep=',',index=False, encoding='ascii')
                del self.eventfile_list[:]
                for file in os.listdir(path2):
                    if file.endswith('.evt'):
                        self.eventfile_list.append(file)
            except IOError:
                mb.showerror('Error', 'Select a file to open')

        def load_event(self): # "Load" on Settings page under event list
            try:
                load_filename = tkFileDialog.askopenfilename(initialdir = path2,title = "Load file",filetypes = (("Event","*.evt"),("all files","*.*")))
                file_display_event=os.path.basename(load_filename)
                self.eventfile_display.configure(text='File name: ' + file_display_event)
                self.dataframe = pd.read_csv(load_filename, sep=',')
                self.dataframe.sort_values(by=['Time'], ascending=True, inplace=True)
                self.tree.delete(*self.tree.get_children())
                for value in range(self.dataframe.shape[0]):
                    self.tree.insert('', 'end', text=self.dataframe.iat[value, 1],
                         values=(self.dataframe.iat[value,2], self.dataframe.iat[value,0]))
            except IOError:
                mb.showerror('Error', 'Select a file to open')

        def remove_event(self): # "Remove" on Settings page under event list
            try:
                item_idex = self.tree.focus()
                if item_idex != '':
                    index = self.tree.index(item_idex)
                    self.dataframe.drop(self.dataframe.index[index], inplace = True)
                    self.dataframe.sort_values(by=['Time'], ascending=True, inplace=True)
                    self.dataframe.reset_index(drop=True, inplace =True)
                    self.tree.delete(*self.tree.get_children())
                    for value in range(self.dataframe.shape[0]):
                        self.tree.insert('', 'end', text=self.dataframe.iat[value, 1],
                             values=(self.dataframe.iat[value, 2], self.dataframe.iat[value, 0]))
                else:
                    mb.showwarning('warning', 'Select an event to remove')
            except Exception as e:
                mb.showerror('Error', '{} line: {}'.format(e, sys.exc_info()[-1].tb_lineno))

        def clear_all(self, table=None): # "Clear" on Settings page for event list table
            try:
                if table == 'event':
                    self.tree.delete(*self.tree.get_children())
                    self.dataframe.drop(self.dataframe.index[:], inplace=True)
                    self.eventfile_display.configure(text='Event file name: ' )
            except Exception as e:
                mb.showerror('Error', '{} line: {}'.format(e, sys.exc_info()[-1].tb_lineno))

        def current_data_frame(self, date="None given", sample_conc=0): # Data-log page
            self.data_mainframe = Frame(self.container)
            self.data_mainframe.place(in_=self.container, x=0, y=0, relwidth=1, relheight=1)
            self.timeseries_frame = Frame(self.data_mainframe)
            self.timeseries_frame.pack(fill=BOTH,expand =1)
            data_file = path2 + "data_log.csv"
            new_data_row = {'Date': date, 'THM (ppb)': sample_conc}
            if exists (data_file):
                df1 = pd.read_csv(data_file)
                if df1.loc[0].at['Date'] == "None": # To check if 1st run
                    df1 = pd.DataFrame({'Date': [date], 'THM (ppb)': [sample_conc]})
                elif(date != "None given"):
                    df1 = df1.append(new_data_row, ignore_index = True)
            else: # This only executes for 1st run and makes the default data-log
                empty_data = {'Date': "None", 'THM (ppb)': [None],}
                df1 = pd.DataFrame(empty_data)
            df1.sort_values(by=["Date"], inplace=True, ascending=False)
            self.data_log_table = pK1 = Table(self.timeseries_frame, dataframe=df1, ascending=False,
                                showtoolbar=False, showstatusbar=False)
            self.data_log_table.expandColumns()
            self.data_log_table.show()
            df1.to_csv(data_file,index=False)

        def onValidation(self, e):
            if e == "":
                return True
            try:
                float(e)
            except:
                return False
            return True

        def page_lift(self, frame):
            try:
                frame.lift()
            except Exception as e:
                mb.showerror('Error', '{} line: {}'.format(e, sys.exc_info()[-1].tb_lineno))

        def start_stop(self,sequence=False): # From green play button on Current run page
            global running
            try:
                if self.run_button.cget('image') == str(self.play_img):
                    self.run_button.config(image=self.stop_img)
                    self.run= True
                    if sequence == False:
                        self.iterations= self.iter_entry.get()
                        self.delay= self.delay_entry.get()
                        if not self.bs.get():
                            self.run_time = 0.0
                        else:
                            self.run_time = float(self.bs.get())
                    if self.run_time == 0.0:
                        self.stop_run()
                        mb.showwarning('Warning', "Run time should be more than 0.0")
                        return
                    """coil_heater_diff = abs(coil_set_temp - coil_heater_temp.get_value())
                    if coil_heater_diff >= 5.0:
                        print(coil_heater_temp.get_value())
                        self.stop_run()
                        mb.showwarning('Warning', "Coil Heater temp not ready")
                        return
                    CMS_heater_diff = abs(CMS_set_temp - CMS_heater_temp.get_value())
                    if CMS_heater_diff >= 5.0:
                        print(CMS_heater_temp.get_value())
                        self.stop_run()
                        mb.showwarning('Warning', "CMS Heater temp not ready")
                        return
                    cooler_diff = abs(cooler_set_temp - cooler_temp.get_value())
                    if cooler_diff >= 5.0:
                        print(cooler_temp.get_value())
                        self.stop_run()
                        mb.showwarning('Warning', "Cooler temp not ready")
                        return"""
                    if self.dataframe.shape[0]>0:
                        if self.dataframe['Time'].iat[-1] > self.run_time:
                            self.stop_run()
                            mb.showwarning('Warning', "Event time exceeds run time")
                            return
                    if self.iterations == " " or self.iterations == 0 or self.iter_var.get()==0:
                        if self.file_name != None:
                            self.previous_plot_remove(file = os.path.basename(self.display_file_name))
                        self.ax1.set_ylabel('mV')
                        self.ax1.set_xlabel('Time (min)')
                        self.data_line, = self.ax1.plot([], [])
                        self.ax1.set_xlim([0, self.run_time + 1])
                        self.canvas.draw_idle()
                        self.canvas.flush_events()
                        self.delay = 0
                        self.iterations=1
                        self.incrementVar.set(0)
                        self.next_run_timeupdate_label.config(text=' - - : - - : - - : - - ')
                        while not data_queue.empty(): # Empties data from previous run
                            print(data_queue.get())
                        self.run_process = threading.Thread(target=DAQ, args=(self.dataframe, 5, self.run_time, data_queue, 2/3))
                        self.run_process.deamon= True
                        self.run_process.start()
                        start_stop_pump_valves()
                        self.start_run()
                    else:
                        self.repeat_thread = threading.Thread(target=self.repeat_run)
                        self.repeat_thread.deamon = True
                        self.repeat_thread.start()
                    ## start data collection thread or process here
                else:
                    self.stop_run()
            except Exception as e:
                self.stop_run()
                mb.showerror('Error', '{} line: {}'.format(e, sys.exc_info()[-1].tb_lineno))

        def start_run(self):
            try:
                """self.diode_signal = (ads.get_last_result())*LSB
                print(self.diode_signal)
                self.led_power_update_label.config(text='{:d} mV'.format(int(self.diode_signal)))"""
                self.iterations= self.iter_entry.get()
                Grad_array = [[],[]]
                iid = self.master.after(1000,self.start_run)  ## Recall interval needs to be 2 times the sampling time
                try:
                    if not data_queue.empty():
                        Grad_array = data_queue.get(False).split('|')
                except Empty:
                    pass
                if len(Grad_array[0])> 0 and Grad_array[0] != 'END':
                    for y in Grad_array[0].split(','):
                        signal_array.append(float(y))
                    for x in Grad_array[1].split(','):
                        time_array.append(float(x))
                    self.data_line.set_data(np.array(time_array), np.array(signal_array))
                    self.ax1.relim()
                    self.ax1.autoscale_view(True, True, True)
                    self.canvas.draw_idle()
                    self.canvas.flush_events()
                if self.run == True:
                    self.current_time = datetime.datetime.now()
                    self.date = self.current_time.strftime("%m-%d-%Y %H:%M")
                    if len(time_array) > 0 and Grad_array[0] != 'END':
                        percent_complete = (time_array[-1]/self.run_time)*100
                        self.run_progress['value'] = percent_complete
                        self.runvalue_label.config(text='{:d} %'.format(int(percent_complete)))
                    if Grad_array[0] == 'END':
                        self.run_progress['value'] = 100
                        self.runvalue_label.config(text='{:d} %'.format(100))
                        self.master.after_cancel(iid)
                        if len(time_array) != len(signal_array):
                            len_time = len(time_array)
                            len_signal = len(signal_array)
                            diff = len_time - len_signal
                            if diff > 0:   # time array has more values
                                signal_array.extend([signal_array[-1]]*diff)
                            else: # signal array has more values
                                freq = time_array[-1] - time_array[-2]
                                for i in range(abs(diff)):
                                    time_array.append(time_array[-1]+freq)
                        samp_conc = self.compute_average(18, 21) # Time range in minutes
                        #self.prev_run_results_update.config(text=str(samp_conc) + " ppb")
                        self.update_meter_image(samp_conc, True)
                        """samp_sig = self.compute_average(____Needs_time_range____)
                        samp_conc = self.compute_conc(samp_sig)
                        samp_sig = self.compute_average(21, 24)
                        std_sig = self.compute_average(28, 31)
                        samp_conc = self.compute_conc_IS(samp_sig, std_sig)"""
                        self.current_time = datetime.datetime.now()
                        self.date = self.current_time.strftime(("%m-%d-%Y %H:%M"))
                        samp_sig = self.compute_average(.20, .25)
                        std_sig = self.compute_average(.30, .35)
                        self.save_to_file(samp_sig, std_sig)
                        """if (samp_conc/10) > 80: # The "/10" is temporary until calibration is complete
                            mb.showwarning('Warning', 'THM concentration is too high')"""
                        self.stop_run(full_stop=True)
                        self.current_data_frame(self.date, samp_conc)
                else:
                    self.save_to_file()
                    self.stop_run(full_stop=True)
                    self.master.after_cancel(iid)
                return
            except Exception as e:
                mb.showerror('Error', '{} line: {}'.format(e, sys.exc_info()[-1].tb_lineno))

        def stop_run(self, full_stop=False):
            self.run_button.config(image=self.play_img)
            self.run = False
            if full_stop:
                global running
                running = False
                del time_array[:]
                del signal_array[:]
                self.run_process.join()
                start_stop_pump_valves(False)
                running = True

        def save_to_file(self, samp_sig = None, std_sig = None):
            try:
                self.file_name = self.file_entry.get()
                if self.incrementVar.get() == 1:
                    self.file_name = path2 + self.file_name.split('_')[0] + "_" + str(self.x)
                    self.x = int(self.file_name.split('_')[-1])+1
                    avg_df= pd.DataFrame({'Components':['Baseline','Sample'],'Start (min)':[20, 30],'Stop (min)':[25,35],
                                            'Average':[samp_sig, std_sig]})
                    sig_df = pd.DataFrame({'Time':time_array, 'Signal':signal_array}, dtype='float32')
                    data = pd.concat([sig_df, avg_df], axis=1, sort =False)
                    data.to_parquet(self.file_name+'.gra')
                    self.display_file_name = self.file_name   ## differentiate saved file name and displayed file
                    self.add_file(data=data, by='current', file=self.display_file_name+'.gra')
                    self.file_name = (self.file_name.split('/')[-1]).split('_')[0] + "_" + str(self.x)
                else:
                    self.file_name = path2 + self.file_name
                    self.display_file_name = self.file_name
                    idf= pd.DataFrame({'Components':['Baseline','Sample'],'Start (min)':[20, 30],'Stop (min)':[25,35],
                                            'Average':[samp_sig, std_sig]})
                    df = pd.DataFrame({'Time':time_array, 'Signal':signal_array}, dtype='float32')
                    data = pd.concat([df, idf], axis=1, sort =False)
                    data.to_parquet(self.file_name+'.gra')
                    self.add_file(data=data, by='current', file=self.file_name+'.gra')
                return
            except Exception as e:
                mb.showerror('Error', '{} line: {}'.format(e, sys.exc_info()[-1].tb_lineno))

        def repeat_run(self):
            try:
                for iters in range(int(self.iterations)):
                    if self.iter_var.get():
                        self.current_time = datetime.datetime.now()
                        if self.delay == "" or self.delay == 0:
                            self.delay= 0.16
                        else:
                            self.delay = float(self.delay)
                            self.current_time = self.current_time + datetime.timedelta(hours= self.delay + self.run_time/60)
                            self.next_run_timeupdate_label.config(text=self.current_time.strftime("%d-%B-%Y %I:%M"))
                        self.run_button.config(image=self.stop_img)
                        if self.file_name != None:
                            self.previous_plot_remove(file = os.path.basename(self.display_file_name))
                        self.ax1.set_ylabel('mV')
                        self.ax1.set_xlabel('Time (min)')
                        self.data_line, = self.ax1.plot([], [])
                        self.ax1.set_xlim([0, self.run_time + 1])
                        self.canvas.draw_idle(),
                        self.canvas.flush_events()
                        self.run_process = threading.Thread(target=DAQ, args=(self.dataframe, 5, self.run_time, data_queue, 2/3))
                        self.run_process.deamon = True
                        self.run_process.start()
                        start_stop_pump_valves()
                        self.start_run()
                        if iters <=0:
                            self.file_name = self.file_entry.get()
                        self.file_entry.delete(0, END)
                        self.file_entry.insert(0, self.file_name.split('/')[-1])
                        self.iterations =(int(self.iterations))-1
                        delay = self.delay*3600
                        delay_time = 0
                        while self.run == True:      ## Waits until run finishes here
                            time.sleep(2)
                        current_time = time.time()
                        if iters <= self.iterations and self.iter_var.get():
                            while delay_time <= delay:   ## Delay timer starts after run finsishes
                                time.sleep(2)
                                delay_time = time.time() - current_time
                        if self.incrementVar.get() == 0:
                            self.master.after_cancel(self.xid)
                            self.run = False
                            self.x=0
                            self.run_button.config(image=self.play_img)
                            self.incrementVar.set(1)
                        else:
                            self.run = True
                    else:
                        self.next_run_timeupdate_label.config(text=' - - : - - : - - : - - ')
                        mb.showinfo('Interrupt', 'Iterations stopped')
                        break
                self.next_run_timeupdate_label.config(text=' - - : - - : - - : - - ')
                mb.showinfo('Completed', 'Iterations completed')
            except Exception as e:
                mb.showerror('Error', '{} line: {}'.format(e, sys.exc_info()[-1].tb_lineno))

        def switch(self,pos):
            try:
                command = "GO"+str(pos)+"\r\n"
                self.port.write(command.encode('ascii'))
                time.sleep(0.05)
                self.port.write(b"cp\r\n")
                time.sleep(0.05)
                out = self.port.readline().decode('ascii').strip()
                if out !="":
                    out = out.split()[-1]
                    if out == '13':
                        self.pos_update.config(text="Blank")
                    elif out == "14":
                        self.pos_update.config(text="Online")
                    else:
                        self.pos_update.config(text=out)
                else:
                    self.run = False
                    mb.showerror('Error', 'Auto-cal communication error')
            except Exception as e:
                self.run = False
                mb.showerror('Error', '{} line: {}'.format(e, sys.exc_info()[-1].tb_lineno))

import RPi.GPIO as GPIO
"""import Adafruit_ADS1x15
from detector import Detector

ads = Adafruit_ADS1x15.ADS1115()"""
Gain = {2/3:0.1875,1:0.125,2:0.0625,4:0.03125,8:0.015625,16:0.0078125}
LSB = Gain[2/3]
"""ads.start_adc_difference(0, gain=2/3)

detector = Detector("/dev/ttyUSB0")
detector.connect()
print("Starting detector...")
#detector.set_detector_control_voltage(1.0)
detector.set_led_current(0.7)"""

class DAQ:
    def __init__(self,eventlist, samp_freq, runtime, queue, gain):
        self.Gain = {2/3:0.1875,1:0.125,2:0.0625,4:0.03125,8:0.015625,16:0.0078125}
        self.Channel = 0
        self.out_pin_list = {'Valve 3':valve7, 'Valve 2':valve8, 'Valve 1':valve9}
        self.runtime = runtime
        self.LSB = self.Gain[gain]
        self.Eventlist = eventlist
        self.queue = queue
        self.freq = samp_freq
        self.Start_Gradient()

    def Events(self, pin=None, state=None):
        if pin != None and state !=None:
            pin = self.out_pin_list[pin]
            if state == 'ON':
                pin.set_value(True)
            else:
                pin.set_value(False)

    def Start_Gradient(self):
        global running
        start_time = time.monotonic_ns()
        elapsed_time = 0
        x_value = -1/(self.freq*60)
        time_array = []
        signal = []
        x=0
        while True:
            if running == True and elapsed_time <= self.runtime:
                """mVs = detector.get_latest_samples()[0][4]
                signal.append(str(mVs))"""
                elapsed_time = (time.monotonic_ns() - start_time)/(60*1e9)
                x_value += 1/(self.freq*60)
                time_array.append(str(x_value))
                if len(time_array) > 1 and self.queue.empty():
                    self.queue.put(','.join(signal) + '|' + ','.join(time_array))
                    del time_array[:]
                    del signal[:]
                if self.Eventlist.shape[0] > 0:
                    if x < len(self.Eventlist):
                        if elapsed_time >= self.Eventlist.iat[x,2]:
                            self.Events(self.Eventlist.iat[x,1], self.Eventlist.iat[x,0])
                            x += 1
            else:
                time_array = []
                signal = []
                self.queue.put('END' + '|' + 'END')
                break
            time.sleep(1/self.freq)    # 5Hz sampling (sleep in secs)

try:
    if __name__ == '__main__':
            root = ThemedTk(theme='arc')  #radiance, clearlooks, arc -- works and looks better"""
            ui = DAQ_GUI(root)
            data_queue = mp.Queue()
            root.mainloop()
finally:
    """valve1.set_value(False)
    valve2.set_value(False)
    valve3.set_value(False)
    controller.reset()
    detector.set_led_current(0)"""