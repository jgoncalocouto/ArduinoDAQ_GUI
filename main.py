from kivy.app import App
from kivy.uix.gridlayout import GridLayout
import kivy.core.window as window
from kivy.base import EventLoop
from kivy.lang import Builder
from os import listdir
from kivy.uix.scrollview import ScrollView
from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget
from kivy.clock import Clock
import kivy.properties as kp
import random
import sys
import glob
import serial
from kivy.config import Config
from kivy.core.window import Window
from math import sin
from kivy_garden.graph import Graph, MeshLinePlot
import matplotlib
import time
import datetime
import numpy as np
from os import path

kv_path = './kv/'
for kv in listdir(kv_path):
    Builder.load_file(kv_path+kv)
    
Window.size = (1500, 900)

# Function to ensure that you can re-run kivy app, otherwise there is an error
def reset():
    if not EventLoop.event_listeners:
        from kivy.cache import Cache
        window.Window = window.core_select_lib('window', window.window_impl, True)
        Cache.print_usage()
        for cat in Cache._categories:
            Cache._objects[cat] = {}




class Container(GridLayout):
    graph= ObjectProperty(None)
    port_selector_id=ObjectProperty(None)
    filepath=ObjectProperty(None)
    filelabel=ObjectProperty(None)
    list_of_graphs=[]
    f_daq=20
    sliding_window=5*60
    N_channels=20
    default_filepath='C:\\Test_data\\'
    
    variable_names_dict={'01':"",'02':"",'03':"",'04':"",'05':"",'06':"",'07':"",'08':"",'09':"",
                         '10':"",'11':"",'12':"",'13':"",'14':"",'15':"",'16':"",'17':"",'18':"",
                         '19':"",'20':""}
    variable_status_dict={'01':False,'02':False,'03':False,'04':False,'05':False,'06':False,
                          '07':False,'08':False,'09':False,'10':False,'11':False,'12':False,
                          '13':False,'14':False,'15':False,'16':False,'17':False,'18':False,
                         '19':False,'20':False}
    list_of_variables=[]
    colors_already_picked=[]
    for i in range(N_channels):
        f=i+1
        exec("variable_%.2d_name = ObjectProperty(None)" % (f))
        exec("variable_%.2d_status = ObjectProperty(None)" % (f))

    def f_serial_ports(self):
        """ Lists serial port names
    
            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')
    
        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        
        if not result:
            result=['<No Port Available>']
            self.serial_ports=result
        return result
    
    def get_port(self):
        self.port_selected=self.port_selector_id.text
        print(self.port_selected)

    def create_graph(self,*args):
        for i,name in enumerate(self.list_of_variables):
            color_chosen=self.random_color()
            self.list_of_graphs.append(MeshLinePlot(color=color_chosen))
            self.graph.add_plot(self.list_of_graphs[i])
            self.list_of_graphs[i].points=[]

    def random_color(self):
        list_of_colors=['firebrick','tomato','darkorange','goldenrod','darkseagreen',
                        'limegreen','mediumseagreen','turquoise','teal','deepskyblue',
                        'slategrey','cornflowerblue','slateblue','mediumaquamarine','orchid',
                        'palevioletred','crimson','lightcyan','rosybrown','palegreen']
        for element in self.colors_already_picked:
            list_of_colors.remove(element)
        
        color_picked=random.choice(list_of_colors)
        self.colors_already_picked.append(color_picked)
        rgba=matplotlib.colors.to_rgba(color_picked, alpha=None)
        return rgba
    
    def calc_unique_excel_filename(self,data_filename_identifier):
        excel_filename = str(datetime.datetime.now().year) + '.' + str(datetime.datetime.now().month) \
        +'.' + str(datetime.datetime.now().day) + '_' + str(datetime.datetime.now().hour) + '.'\
        +str(datetime.datetime.now().minute) + '.' + str(datetime.datetime.now().second) + '__' \
        +data_filename_identifier + '.xls'
        return excel_filename
    
    def decode_line(self,ser_bytes):
        
        timeout=5
        start=time.time()
        decoded_bytes=''
        while (time.time()<start+timeout) and decoded_bytes=='':
            decoded_bytes = ser_bytes.decode("utf-8")
        
        if decoded_bytes=='':
            print('Error in decoding serial message! Some data may be missing!')
            return self.data
            
        txt = decoded_bytes.split(" ,")  # data from arduino comes in the folowing format: "1:25.26,"
        self.data[0].append(time.time() - self.t_0)
        self.data[1].append(datetime.datetime.now().strftime('%x %X'))
        message='TimeStamp: ' + str(self.data[1][-1]) + '; '
        msg_part=''
        for i in range(len(self.data)-2):
            self.data[i + 2].append(float(txt[i][3:]))
            msg_part=self.list_of_variables[i]+': '+str(self.data[i+2][-1])+'; '+msg_part
        message=message+msg_part
        print(message)
        return self.data
    
    def check_list_of_variables(self):
        ser_bytes=self.ser.readline()
        N=0
        while N<10:
            try:
                decoded_bytes = ser_bytes.decode("utf-8")
                txt = decoded_bytes.split(" ,")  # data from arduino comes in the folowing format: "1:25.26,"
                if txt[-1]=='\r\n':
                    number_of_variables=len(txt)-1
                    N=10
                else:
                    N+=1
            except:
                N+=1
    
        try:
            if number_of_variables==len(self.data)-2:
                print('Variable number in GUI matches variable number in serial COM -> Great Success')
            elif number_of_variables>len(self.data)-2:
                number_of_unused_channels=number_of_variables-(len(self.data)-2)
                print('There are '+str(number_of_unused_channels)+' not being used by the GUI')
            elif number_of_variables<len(self.data)-2:
                self.data=self.data[:2+number_of_variables]
                self.list_of_variables=self.list_of_variables[:number_of_variables]
                print('The number of variables selected in the GUI is higher than the number of\
                      variables being passed in the serial port, there will be unused channels in the graph!')
        except:
            print('Error! List of variables could not be verified! Check serial port connection!')
        pass
        
    def start_daq(self,*args):
        ser = serial.Serial(self.port_selected)
        ser.flushInput()
        self.t_0 = time.time()
        self.t_autosave = self.t_0
        self.ser=ser
        print(ser)
            
    def stop_daq(self,*args):
        Clock.unschedule(self.clock_data)
        Clock.unschedule(self.clock_graph)
        Clock.unschedule(self.clock_axis)
        self.ser.close()
        self.remove_all_graphs()
        
        

    def update_data(self,*args):
        ser_bytes=self.ser.readline()  
        try:
            self.data=self.decode_line(ser_bytes)
        except:
            print('Some data may be missing...')
        pass
    
    def initialize_data(self):
        for j in range(len(self.list_of_variables) + 2):
            try:
                b=self.data[0]
            except AttributeError:
                self.data=[]
            self.data.append([])
        
    def update_graph(self,*args):
        for i,name in enumerate(self.list_of_variables):
            try:
                points=np.column_stack((self.data[0],self.data[i+2]))
            except:
                size=min(len(self.data[-1]),len(self.data[0]))
                print(size)
                self.data[0]=self.data[0][:size]
                self.data[i+2]=self.data[i+2][:size]
                points=np.column_stack((self.data[0][-(self.f_daq*self.sliding_window):-1],self.data[i+2][-(self.f_daq*self.sliding_window):-1]))
            self.list_of_graphs[i].points=points
    def update_axis(self,*args):
        self.graph.xmin=max(0,self.data[0][-1]-self.sliding_window)
        self.graph.xmax=max(self.data[0])
        try:
            ymax=max(max(self.data[2:]))*1.2
            ymin=min(min(self.data[2:]))*0.8
            yrange=ymax-ymin
            
            if ymax==ymin:
                self.graph.ymax=1000
                self.graph.ymin=-1000
            else:
                self.graph.ymax=ymax+yrange*0.1
                self.graph.ymin=ymin-yrange*0.1
        except:
            self.graph.ymax=1000
            self.graph.ymin=-1000
            
    
    def get_variable_name(self):
        self.list_of_variables=[]
        for i in range(self.N_channels):
            f=i+1
            exec("self.variable_names_dict['%.2d'] = self.variable_%.2d_name.text" % (f,f))
            exec("self.variable_status_dict['%.2d'] = self.variable_%.2d_status.active" % (f,f))
        for key in self.variable_names_dict.keys():
            if self.variable_status_dict[key]==False:
                self.variable_names_dict[key]==''
            elif (self.variable_status_dict[key]==True):
                if self.variable_names_dict[key]=='':
                    self.variable_names_dict[key]='Channel '+key
                self.list_of_variables.append(self.variable_names_dict[key])
    def update_channel_name_holder(self):
        for key in self.variable_names_dict:
            if self.variable_names_dict[key] not in self.list_of_variables:
                self.variable_status_dict[key]=False
        for i,key in enumerate(self.variable_status_dict):
            f=i+1
            exec("self.variable_%.2d_status.active=self.variable_status_dict[key]" % (f))
            

    def style_channel_name_holder(self):
        i=0
        for key in self.variable_names_dict.keys():
            if (self.variable_status_dict[key]==True):
                color_picked=self.colors_already_picked[i]
                color=matplotlib.colors.to_rgba(color_picked, alpha=None)
                name=self.variable_names_dict[key]
                exec("self.variable_%s_name.background_color = color" % (key))
                exec("self.variable_%s_name.text = name" % (key))
                i+=1
            else:
                color=(0.2,0.07,0.07,1)
                name=""
                exec("self.variable_%s_name.background_color = color" % (key))
                exec("self.variable_%s_name.text = name" % (key))
    
    def remove_all_graphs(self):
        for i,plot in enumerate(self.graph.plots):
            self.graph.remove_plot(plot)
            self.graph._clear_buffer()
        for i,value in enumerate(self.list_of_graphs):
            self.list_of_graphs[i].points=[]
        delattr(self,'data')
        
    def get_filepath_and_label(self) :
        
        filepath_input=self.filepath.text
        if filepath_input=="Add costum filepath":
            self.filepath.text=self.default_filepath
            self.filepath.background_color=(0.203,0.255,0.147,1)
        elif path.exists(filepath_input)==True:
            self.filepath.background_color=(0.133,0.191,0.063,1)
        else:
            self.filepath.text=self.default_filepath
            self.filepath.background_color=(0.203,0.255,0.147,1)
        
        filelabel_input=self.filelabel.text
        if filelabel_input=="Add costum filename label":
            self.filelabel.text="test"
            self.filelabel.background_color=(0.203,0.255,0.147,1)
        filename=self.calc_unique_excel_filename(self.filelabel.text)
        self.filename=filename
        self.filelabel.text=self.filename
            
            
            
            
            
    
    def get_your_shit_together(self):
        self.get_filepath_and_label()
        #self.remove_all_graphs()
        self.colors_already_picked=[]
        self.list_of_graphs=[]
        self.get_port()
        self.get_variable_name()
        self.initialize_data()
        try:
            self.start_daq()
        except:
            self.stop_daq()
            self.start_daq()
        self.check_list_of_variables()
        self.update_channel_name_holder()
        self.clock_data=Clock.schedule_interval(self.update_data, 1/self.f_daq)
        self.create_graph()
        self.style_channel_name_holder()
        self.clock_graph=Clock.schedule_interval(self.update_graph, 1/self.f_daq)
        self.clock_axis=Clock.schedule_interval(self.update_axis,1/self.f_daq)
        

    

            
            


class MainApp(App):

    def build(self):
        self.title = 'Arduino DAQ'
        grid=Container()
        return grid
    
if __name__ == "__main__":
    #reset()
    app = MainApp()
    app.run()
    #grid=Container()
    #grid.port_selected='COM6';
    #grid.start_daq()
    #grid.list_of_variables=['A','B','C','D']
    #grid.initialize_data()
    #grid.check_list_of_variables()
    
    
    pass
    
    
