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
    print("Arduino not found! Ending Program")
    # os.kill(os.getpid(), signal.SIGTERM)
    exit()

elif not debug_mode:
    ser = Serial(serial_port, 9600, timeout=0)
    sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))

# print("------------------SYNTAX------------------")
# print("|Type v_.__ to set voltage output of DAC|")
# print("|Type i_.__ to set current output of DAC|")
# print("------------------------------------------")

while port_found or debug_mode:
    setpoint = str(input("Set Setpoint: "))
    # setpoint = int(setpoint * 1e5)
    print(setpoint)
    if setpoint == 'x':
        break
    if not debug_mode:
        sio.write(str(setpoint + 'f'))
        sio.flush()
    time.sleep(0.01)
    print("Data", sio.read())
    sio.flush()
if not debug_mode:
    ser.close()