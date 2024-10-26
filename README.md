# daqopen-apps

This repository is a collection of various apps which uses the daqopen-lib.

- [daq-zmq-server](#daq-zmq-server): ZMQ Pulisher for DAQ Data
- [daq-zmq-viewer](#daq-zmq-viewer): GUI with ZMQ Subscriber for live viewing data

## daq-zmq-server

The daq-zmq-server.py is an application for decoupling the actual acquisition-process from the consuming application. It can be run on e.g. an edge device like Raspberry Pi.

### Features

- Collect data with the DueDaq library from the (USB) interface
- Add timestamp to each data package
- Publish the data together with necessary metadata with DaqPublisher

### Usage

1. Install requirements

   ```bash
   pip install daqopen-lib
   ```

1. Edit the config/daqinfo.toml file regarding your needs
2. Start the daq-zmq-server.py manually or create a systemd service
3. Start client application and subscribe to the data (e.g. daq-zmq-viewer or DEWETRON OXYGEN with daqopen-oxygen-plugin)

## daq-zmq-viewer

Debugging and testing tool for the daq-zmq-server. You can subscribe to the daqopen-device and live view the data. Bases on PyQt6 framework. It uses also ChannelBuffer for demonstration.

![image-20241026143034059](/home/moberhofer/Projekte/DaqOpen/daqopen-apps/resources/daq-zmq-viewer-0.png)

### Features

- Set connection parameters in GUI
- Start acquisition (correct: start transfer)
- View live data
- Select channel to be viewed
- Set time window size

### Usage

1. Install requirements

   ```bash
   pip install daqopen-lib PyQt6 pyqtgraph
   ```
1. Edit the config/daq-zmq-viewer.toml and set default parameters
2. Start the daq-zmq-viewer.py
3. Optionally edit connection parameter
4. Press **Start** to connect and start transfer