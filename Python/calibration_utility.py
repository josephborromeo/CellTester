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
    print("Arduino not found! Ending Program")
    # os.kill(os.getpid(), signal.SIGTERM)
    exit()

elif not debug_mode:
    ser = Serial(serial_port, 9600, timeout=0)
    sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))

print("------------------SYNTAX------------------")
print("|Type v_.__ to set voltage output of DAC|")
print("|Type i_.__ to set current output of DAC|")
print("------------------------------------------")

analog_val = 0 # max for test will be 0.45 if even needed
## ----- CHANGE TO BE ANALOG VALUE OF 0-4095 INSTEAD OF VOLTAGE
data = []
data_w_current = []
err = False
while port_found or debug_mode:
    if not debug_mode and not err:
        sio.write(str(analog_val) + 'f')    # TODO: Make this into a function
        sio.flush()
    val_in = str(input("%i : " %(analog_val)))

    # data2 = sio.read().split('\n')[-2]
    # data2 = data2.split("|")

    # current = ((float(data2[1])/4095)*3.30)/0.1195 

    if val_in == 'x':
        if not debug_mode:
            sio.write(str(0))   # Stop current
            sio.flush()
        break
    try:
        data.append([analog_val, float(val_in)])
        # data_w_current.append([analog_val, float(val_in), current])
    except ValueError:
        print("Woops, please enter a number")
        err = True
    else:
        if analog_val < 25:
            analog_val += 1
        elif analog_val < 200:
            analog_val += 5     # FIXME: Change to get more precision
        else:
            analog_val += 25
        err = False

if not debug_mode:
    ser.close()

with open('calibration_data.csv', 'w+', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)
    for row in data:
        csvwriter.writerow(row)



x, y = np.transpose(data)
plt.figure("Calibration Data", figsize=(14,8))
plt.title("Current vs. Setpoint")
plt.xlabel("Analog Setpoint")
plt.ylabel("Current [A]")

plt.grid()

plt.plot(x, y, label='Raw Data')
plt.tight_layout()

# Get polyfit
third_order = np.polyfit(x,y,3)
fifth_order = np.polyfit(x,y,5)
seventh_order = np.polyfit(x,y,7)


poly3 = np.poly1d(third_order)
poly5 = np.poly1d(fifth_order)
poly7 = np.poly1d(seventh_order)

print("Third order Fit:\n", poly3)
print("\nFifth order Fit:\n", poly5)
print("\nSeventh order Fit:\n", poly7)

poly_x = np.linspace(x[0], x[-1])

poly3_y = poly3(poly_x)
poly5_y = poly5(poly_x)
poly7_y = poly7(poly_x)


"""     IDEALIZED CURVE     """
# I = V/R
# I = [(analog_val/4095)*3.30] /0.12
# I = analog_val * ((3.30/0.12)/4095)
# This gives us a theoretical precision of 6.716 mA per step

ideal_plot = poly_x * ((3.30/0.12)/4095)

plt.plot(poly_x, ideal_plot, 'D-', label="Ideal Plot")
plt.plot(poly_x, poly3_y, 'o-', label='Third order fit')
plt.plot(poly_x, poly5_y, 'H-', label='Fifth order fit')
plt.plot(poly_x, poly7_y, 's-', label='Seventh order fit')

plt.legend(loc='upper left')

plt.show()