"""
App: daq-zmq-viewer.py
Description: app for reading the data from zmq and displaying it in gui

Author: Michael Oberhofer
Created on: 2024-03-13
Last Updated: 2024-10-26

License: MIT

Notes: 

Version: 0.02
Github: https://github.com/DaqOpen/daqopen-apps/
"""

import sys
import numpy as np
from PyQt6.QtCore import QLocale
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QGridLayout, QLabel, QHBoxLayout, QComboBox, QLineEdit
from PyQt6.QtGui import QIntValidator, QDoubleValidator
from pyqtgraph import PlotWidget
import sys
import zmq
import tomli

from daqopen.channelbuffer import AcqBufferPool
from daqopen.daqzmq import DaqSubscriber


class GuiWithZmq(QMainWindow):
    """ GUI Class for Testing the DueDaq with a separate Acquisition Process
    """

    def __init__(self):
        super().__init__()

        with open("config/daq-zmq-viewer.toml", "rb") as f:
            self.config = tomli.load(f)

        self.setWindowTitle("DAQ Test Application")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        # Main application Layout
        self.main_layout = QVBoxLayout(self.central_widget)

        # Connection Input fields
        self.connect_layout = QHBoxLayout()
        self.lbl_hostname = QLabel("Hostname: ")
        self.connect_layout.addWidget(self.lbl_hostname)
        self.le_zmq_hostname = QLineEdit(self.config["zmq_server"]["host"])
        self.le_zmq_hostname.editingFinished.connect(self.set_zmq_hostname)
        self.connect_layout.addWidget(self.le_zmq_hostname)
        self.lbl_zmq_port = QLabel("Port: ")
        self.connect_layout.addWidget(self.lbl_zmq_port)
        self.le_zmq_port = QLineEdit(str(self.config["zmq_server"]["port"]))
        port_num_validator = QIntValidator(1000, 65535, self)
        self.le_zmq_port.setValidator(port_num_validator)
        self.connect_layout.addWidget(self.le_zmq_port)
        self.le_zmq_port.editingFinished.connect(self.set_zmq_port)
       
        self.main_layout.addLayout(self.connect_layout)

        # Graph Widget
        self.graphWidget = PlotWidget()
        self.main_layout.addWidget(self.graphWidget)
        self.graphWidget.setLabel('left', 'Value')
        self.graphWidget.setLabel('bottom', 'Time (s)')
        self.graphWidget.showGrid(x=True, y=True)

        # Control Widgets
        self.lower_layout = QGridLayout()
        self.value_layout = QHBoxLayout()
        self.lower_layout.addLayout(self.value_layout, 0, 0, 1, 2)
        self.cb_channel_selector = QComboBox()
        self.value_layout.addWidget(self.cb_channel_selector, 0)
        self.lbl_value = QLabel("0.0")
        self.value_layout.addWidget(self.lbl_value, 1)
        self.le_time_span = QLineEdit("0.1")
        self.le_time_span.setMaximumWidth(100)
        time_span_validator = QDoubleValidator(0.01, 10, 2, self)
        time_span_validator.setLocale(QLocale("EN_en"))
        self.le_time_span.setValidator(time_span_validator)
        self.le_time_span.editingFinished.connect(self.set_window_time_span)
        self.value_layout.addWidget(self.le_time_span, 2)
        self.window_time_span_sec = 0.1
        self.max_time_span_sec = 0.1

        self.btn_acq_start = QPushButton('Start', self)
        self.lower_layout.addWidget(self.btn_acq_start, 1, 0)
        self.btn_acq_start.clicked.connect(self.start_transfer)

        self.btn_acq_stop = QPushButton('Stop', self)
        self.lower_layout.addWidget(self.btn_acq_stop, 1, 1)
        self.btn_acq_stop.clicked.connect(self.stop_transfer)

        self.main_layout.addLayout(self.lower_layout)

        self.x_data = np.arange(0, 10, 0.1)
        self.y_data = np.sin(self.x_data)
        self.sample_count = 0

        self.data_line = self.graphWidget.plot(self.x_data, self.y_data)

        self.data_update_timer = self.startTimer(100)
        self.daq_sub = None

        
    def start_transfer(self):
        # Create DaqSubscriber Instance
        self.daq_sub = DaqSubscriber(self.config["zmq_server"]["host"], self.config["zmq_server"]["port"])
        print("Daq Connected")
        # Create DAQ Buffer Object
        self.daq_buffer = AcqBufferPool(daq_info=self.daq_sub.daq_info, 
                                        data_columns=self.daq_sub.data_columns,                                        
                                        start_timestamp_us=int(self.daq_sub.timestamp*1e6))
        
        self.cb_channel_selector.clear()
        self.cb_channel_selector.addItems(self.daq_sub.daq_info.channel.keys())
        self.sample_count = 0
        self.graphWidget.enableAutoRange()
        self.max_time_span_sec = self.daq_buffer._buffer_size/self.daq_sub.daq_info.board.samplerate
        print(self.max_time_span_sec)


    def stop_transfer(self):
        if isinstance(self.daq_sub, DaqSubscriber):
            self.daq_sub.terminate()
            self.daq_sub = None

    def set_window_time_span(self):
        self.window_time_span_sec = min(self.max_time_span_sec, float(self.le_time_span.text()))
        self.le_time_span.setText(f"{self.window_time_span_sec:.2f}")
    
    def set_zmq_hostname(self):
        self.config["zmq_server"]["host"] = self.le_zmq_hostname.text()

    def set_zmq_port(self):
        self.config["zmq_server"]["port"] = int(self.le_zmq_port.text())

    def timerEvent(self, event):
        """ Update data in graph
        """
        if not isinstance(self.daq_sub, DaqSubscriber):
            return None
        new_data = False
        # Read all data from queue, only remember last block
        while self.daq_sub.sock.poll(10) == zmq.POLLIN:
            m_data = self.daq_sub.recv_data().copy()
            self.sample_count += m_data.shape[0]
            self.daq_buffer.put_data_with_timestamp(m_data, int(self.daq_sub.timestamp*1e6))
            new_data = True
        
        # Return, if there is no new data
        if not new_data:
            return None

        # Process new data
        start_sample_idx = int(self.sample_count - self.window_time_span_sec*self.daq_sub.daq_info.board.samplerate)
        if start_sample_idx <= 0:
            return None
        start_sample_idx = max(self.daq_buffer.actual_sidx-self.daq_buffer._buffer_size+1, start_sample_idx)
        self.x_data = np.arange(start_sample_idx, self.sample_count-1)/self.daq_sub.daq_info.board.samplerate
        self.y_data = self.daq_buffer.channel[self.cb_channel_selector.currentText()].read_data_by_index(start_sample_idx, self.sample_count - 1)
        if not self.y_data.size > 0:
            print("No data returned - ", start_sample_idx, self.sample_count - 1)
            return None
        self.data_line.setData(self.x_data, self.y_data)
        frequency, trms, frms = (0,0,0)#estimate_frequency(self.y_data, self.daq_info.samplerate)
        self.lbl_value.setText(f"mean: {self.y_data.mean():.3f} min: {self.y_data.min():.3f} max: {self.y_data.max():.3f} rms: {trms:.3f} freq: {frequency:.4f}")


    def closeEvent(self, event):
        self.stop_transfer()
        print("Worker Stopped")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GuiWithZmq()
    window.show()
    app.exec()