import os, datetime, serial, csv, time, random, signal
import io
import serial.tools.list_ports
from serial import Serial
import matplotlib.pyplot as plt
import numpy as np
import csv

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

analog_val = 0 # max for test will be 0.45 if even needed
## ----- CHANGE TO BE ANALOG VALUE OF 0-4095 INSTEAD OF VOLTAGE
out_data = []
data_w_current = []
err = False
while port_found or debug_mode:
    val_in = str(input("Enter Current to set: "))
    
    if val_in == 'x':
        if not debug_mode:
            sio.write('0f')   # Stop current
            sio.flush()
        break
    
    val_out = curr_to_val(float(val_in))
    
    if not debug_mode and not err:
        sio.write(str(val_out) + 'f')    # TODO: Make this into a function
        sio.flush()
    
    
    actual_current = float(input("Actual Current: "))

    data = sio.read().split('\n')[-2]
    data = data.split("|")
    sio.flush()

    time.sleep(0.2)

    averages = 10
    analog_val = 0

    for i in range(averages):
        data = sio.read().split('\n')[-2]
        data = data.split("|")
        sio.flush()
        print(data[1])
        analog_val += int(data[1])
        time.sleep(0.1)

    analog_val /= float(averages)    

    current_voltage = ((float(analog_val)/4095)*3.358) 

    print("Shunt Voltage: %.4f" %(current_voltage))
    
    actual_voltage = float(input("Actual Shunt Voltage: "))
   

    out_data.append([actual_current, actual_voltage, current_voltage])


if not debug_mode:
    ser.close()

with open('current_cal.csv', 'w+', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(["Actual Current", "Actual Shunt Voltage", "Read Shunt Voltage"])
    for row in out_data:
        csvwriter.writerow(row)
