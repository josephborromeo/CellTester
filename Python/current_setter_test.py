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


def curr_to_val (current):
    if current < 0:
        current = 0
    if current > 25:
        current = 25
    
    # Piece-wise function   --   10V op-amp
    if current < 4.5:
        setpoint = -0.9428*current**6 + 11.717*current**5 - 53.642*current**4 + 120.05*current**3 - 139.35*current**2 + 119.12*current + 1.1749
        setpoint = round(setpoint)
    else:
        setpoint = 282*current - 807.99
        setpoint = round(setpoint)

    return str(setpoint)

voltage_offset = 0.016

while port_found or debug_mode:
    setpoint = float(input("Set Setpoint: "))
    setpoint = curr_to_val(setpoint)
    print(setpoint)

    if setpoint == 'x':
        break
    if not debug_mode:
        sio.write(str(setpoint + 'f'))
        sio.flush()

    time.sleep(0.5)
    data = sio.read().split('\n')[-2]
    data = data.split("|")
    sio.flush()

    if len(data) == 6:
        print(data[0])
        volt = float(data[0])+ voltage_offset
        current_voltage = ((float(data[1])/4095)*3.358)/0.1187 
        print("Cell Voltage: %.3fV"%(volt))
        print("Read Current: %.2fA"%(current_voltage))

    time.sleep(0.01)
if not debug_mode:
    ser.close()