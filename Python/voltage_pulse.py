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


setpoint = 4095
while port_found or debug_mode:
    # Set output to 0
    if not debug_mode:
        sio.write(str(setpoint + 'f'))
        sio.flush()

    input("Press Enter To Send Pulse")
    
    if setpoint == 'x':
        break

    # Set output high
    if not debug_mode:
        sio.write(str(setpoint + 'f'))
        sio.flush()


    # Change sleep time to change pulse duration
    time.sleep(0.001)


if not debug_mode:
    ser.close()