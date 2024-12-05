import tomllib
import time
from pathlib import Path
import zmq

from daqopen.channelbuffer import AcqBufferPool
from daqopen.daqzmq import DaqSubscriber
from daqopen.helper import GracefulKiller
from pqopen.powersystem import PowerSystem

class CsvWriter(object):
    def __init__(self, filename: str, keys: list):
        self.header_keys = keys
        self.file_path = Path(filename)
        self.file_path.write_text("timestamp," + ",".join(keys)[:-2]+"\n")

    def write_line(self, timestamp_us: int, data: dict):
        with open(self.file_path, "a") as f:
            f.write(f"{timestamp_us/1e6:.3f},")
            f.write(",".join([f"{data[key]:.3f}" if isinstance(data[key], float) else "" for key in self.header_keys])+"\n")

with open("config/pqopen-simple.toml", "rb") as f:
    config = tomllib.load(f)

# Initialize App Killer
app_terminator = GracefulKiller()

# Subscribe to DaqOpen Zmq Server
daq_sub = DaqSubscriber(config["zmq_server"]["host"], config["zmq_server"]["port"])
print("Daq Connected")

# Create DAQ Buffer Object
daq_buffer = AcqBufferPool(daq_info=daq_sub.daq_info, 
                                data_columns=daq_sub.data_columns,
                                start_timestamp_us=int(daq_sub.timestamp*1e6))

# Create Powersystem Object
power_system = PowerSystem(zcd_channel = daq_buffer.channel[config["powersystem"]["zcd_channel"]],
                           input_samplerate = daq_sub.daq_info.board.samplerate,
                           zcd_threshold = 1)

# Add Phases
for phase_name, phase in config["powersystem"]["phase"].items():
    power_system.add_phase(u_channel=daq_buffer.channel[phase["u_channel"]],
                           i_channel=daq_buffer.channel[phase["i_channel"]])
power_system.enable_harmonic_calculation()
power_system.enable_nper_abs_time_sync(daq_buffer.time, interval_sec=10)
    
# Initialize Acq variables
print_values_timestamp = time.time()
last_print_values_acq_sidx = 0
output_channel_keys = list(power_system.output_channels.keys())
csv_writer = CsvWriter("power_values.csv", output_channel_keys)

# Initialize ZMQ Publisher
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5555")  # An Port 5555 binden

# Application Loop
while not app_terminator.kill_now:
    m_data = daq_sub.recv_data()
    daq_buffer.put_data_with_timestamp(m_data, int(daq_sub.timestamp*1e6))
    power_system.process()
    if time.time() > print_values_timestamp + 1:
        power_data = power_system.get_aggregated_data(last_print_values_acq_sidx, daq_buffer.actual_sidx)
        socket.send_pyobj(power_data)
        ts = daq_buffer._last_timestamp_us
        csv_writer.write_line(ts, power_data)
        last_print_values_acq_sidx = daq_buffer.actual_sidx
        print_values_timestamp = time.time()