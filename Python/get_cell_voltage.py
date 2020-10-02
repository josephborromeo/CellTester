import os, datetime, serial, csv, time, random, signal
import io
import serial.tools.list_ports
from serial import Serial

debug_mode = False

if debug_mode:
    print("STARTING IN DEBUG MODE")

ports = serial.tools.list_ports.comports()
all_ports = []

for port, desc, hwid in sorted(ports):
        print("{}: {}".format(port, desc))
        all_ports.append("{}: {}".format(port, desc))

print(all_ports)
serial_port = ""
port_found = False
for p in all_ports:
    curr = p.lower()
    if 'usb serial' in curr:
        serial_port = p.split(':')[0]
        port_found = True
        print("Found STM32 device on serial port")

if not port_found and not debug_mode:
    print("Device not found! Ending Program")
    # os.kill(os.getpid(), signal.SIGTERM)
    exit()

elif not debug_mode:
    ser = Serial(serial_port, 9600, timeout=0)
    sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))


voltage_offset = 0.016

while port_found or debug_mode:

    input("Press enter to get cell voltage")
    data = sio.read().split('\n')[0]
    data = data.split("|")
    sio.flush()

    if len(data) == 6:
        print(data[0])
        volt = float(data[0])+ voltage_offset
        print("Cell Voltage: %.3fV"%(volt))

if not debug_mode:
    ser.close()