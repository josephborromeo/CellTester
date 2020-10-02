import os, datetime, serial, csv, time, random, signal, math
import io
import serial.tools.list_ports
from serial import Serial

import numpy as np
import matplotlib.pyplot as plt

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
        print("Found STM32 device on serial port\n")

if not port_found and not debug_mode:
    print("Device not found! Ending Program")
    # os.kill(os.getpid(), signal.SIGTERM)
    exit()

elif not debug_mode:
    ser = Serial(serial_port, 9600, timeout=0)
    sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))


# setpoint = lambda x: 0.0926*x**3-1.4644-x**2+13.756*x+1.2818
# setpoint = lambda x: round(-23.1667+0.166667*math.sqrt(30000*x+19321))
# current_val = lambda x: 0.0012*x**2 + 0.0556*x

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


def val_to_temp(a_in):
    v_in = (a_in/4095.0)*3.30
    resistance = (330000.0/((a_in/4095.0)*3.30)) - 100000.0
    temp = -4.107*math.pow(10,-35)*math.pow(resistance, 7) + 5.219*math.pow(10,-29)*math.pow(resistance, 6) - 2.681*math.pow(10,-23)*math.pow(resistance, 5) + 7.149*math.pow(10,-18)*math.pow(resistance, 4) - 1.061*math.pow(10,-12)*math.pow(resistance, 3) + 8.823*math.pow(10,-8)*math.pow(resistance, 2) - 0.004115*resistance + 121.4
    return temp

volt, current, ambient, pos_temp, middle_temp, neg_temp = 0,0,0,0,0,0
data, out_data = [], []
ambient_data, pos_data, middle_data, neg_data = [], [], [], []

time_data, voltage_data, current_data = [], [], []


LVC = 2.5   # Low voltage cutoff

loop_speed = 5     # Loop speed in Hz
loop_time = float(1.0/loop_speed)

filename = input("Enter test name: ") +"_"+ str(datetime.date.today())

current_setpoint = float(input("Enter the discharge current: "))

while current_setpoint <= 0 or current_setpoint > 25:
    print("Discharge current out of range. Please choose a current between 0 and 25A")
    current_setpoint = float(input("Enter the discharge current: "))

# Setup filesystem
data_folder = 'data'

# Create folder if doesn't exist
if 'data' not in os.listdir():
    print("No data folder, making folder now")
    os.mkdir('data')

os.chdir('data')

if filename not in os.listdir():
    print("Creating folder", filename)
    os.mkdir(filename)
else:
    print("Data folder with the same name already exists, QUITTING")
    quit()

os.chdir(filename)


print("\nTEST SUMMARY")
print("NAME:", filename)
print("DISCHARGE CURRENT: %.2fA"%(current_setpoint))
print()

setpoint = curr_to_val(current_setpoint)
current_val = current_setpoint

print("Setting Setpoint to", setpoint)
print("Actual Discharge Current: %.2fA" %(current_val))

input("Press enter to begin the test")

running = True

csvfile = open(filename+'_data.csv', 'w+', newline='')
writer = csv.writer(csvfile)
writer.writerow(['Time', 'Cell Voltage', 'Cell Current', 'Ambient Temp', 'Pos Term Temp', 'Middle Temp', 'Neg Term Temp'])
csvfile.flush()

start_time = time.clock()

voltage_offset = 0.04

# Record 10 data points before starting discharge to see voltage drop

for i in range(loop_speed): # Run for 1s
    data = sio.read().split('\n')[0]
    data = data.split("|")

    volt = float(data[0]) + voltage_offset
    current = ((float(data[1])/4095)*3.358)/0.1187

    elapsed = time.clock() - start_time

    ambient = val_to_temp(int(data[2]))
    pos_temp = val_to_temp(int(data[3]))
    middle_temp = val_to_temp(int(data[4]))
    neg_temp = val_to_temp(int(data[5]))
    if volt > 2 and volt < 4.5:
        time_data.append(elapsed)
        voltage_data.append(volt)
        current_data.append(current)
        ambient_data.append(ambient)
        pos_data.append(pos_temp)
        middle_data.append(middle_temp)
        neg_data.append(neg_temp)


    out_data = [elapsed, volt, current, ambient, pos_temp, middle_temp, neg_temp]
    
    writer.writerow(out_data)
    csvfile.flush() # Write data immediately in case program crashes

    time.sleep(loop_time)

# Offset temps so they have the same initial value
neg_average = np.average(neg_data)
middle_average = np.average(middle_data)
pos_average = np.average(pos_data)

middle_offset = middle_average - neg_average
pos_offset = pos_average - neg_average



# Set current
sio.write(str(setpoint) + 'f')
sio.flush()

hit_lvc = False
lvc_counter = 0

while port_found and running or debug_mode:
    data = sio.read().split('\n')[0]
    data = data.split("|")

    if len(data) == 6:
        print(data)
        if not '' in data:
            volt = float(data[0]) + voltage_offset
            
            current = ((float(data[1])/4095)*3.358)/0.1187        # FIXME: this only gives voltage

            elapsed = time.clock() - start_time

            ambient = val_to_temp(int(data[2]))
            pos_temp = val_to_temp(int(data[3])) - pos_offset
            middle_temp = val_to_temp(int(data[4])) - middle_offset
            neg_temp = val_to_temp(int(data[5]))

            print("Cell Voltage: %.3f" %(volt))
            print("Current: %.3fA" %(current))
            print("Ambient Temp %.2fC" %(ambient))
            # print("Positive Term Temp %.2fC" %(pos_temp))
            print("Middle Cell Temp %.2fC" %(middle_temp))
            # print("Negative Term Temp %.2fC" %(neg_temp))
            
            # Only add to output if in range
            # print("ABS DIFF", abs(volt-voltage_data[-1]))
            if volt > 2 and volt < 4.5:
                time_data.append(elapsed)
                voltage_data.append(volt)
                current_data.append(current)
                ambient_data.append(ambient)
                pos_data.append(pos_temp)
                middle_data.append(middle_temp)
                neg_data.append(neg_temp)

                if abs(volt-voltage_data[-1]) < 0.1:
                    print("Writing")
                    out_data = [elapsed, volt, current, ambient, pos_temp, middle_temp, neg_temp]
                    writer.writerow(out_data)
                    csvfile.flush() # Write data immediately in case program crashes
    

    if float(volt) < LVC:
        hit_lvc = True
        lvc_counter += 1

    elif hit_lvc and lvc_counter > 0:
        lvc_counter -= 1
        hit_lvc = False

    if lvc_counter > 3:
        running = False
        print("HIT LVC, STOPPING")
        sio.write('0f')
        sio.flush()

    print(lvc_counter)
    
    time.sleep(loop_time)

csvfile.close()

# Calculate IR -- ROUGH CALC
unloaded_v = float(np.mean(voltage_data[:loop_speed]))  # Get unloaded voltage from 1st second
loaded_v = float(np.mean(voltage_data[loop_speed*5:loop_speed*6]))  # Get loaded voltage after 5s to allow it to settle

print("Unloaded Voltage: %.3fV \t Loaded Voltage: %.3fV" %(unloaded_v, loaded_v))
print("Current:", current_val)

internal_r = (unloaded_v - loaded_v)/current_val

print("Cell IR is: %.5f Ohms" %(internal_r))

# Plot data

fig1, ax1 = plt.subplots(figsize=(12.8,7.2), tight_layout=True)
fig2, ax2 = plt.subplots(figsize=(12.8,7.2), tight_layout=True)
fig3, ax3 = plt.subplots(figsize=(12.8,7.2), tight_layout=True)

ax1.margins(x=0)
ax2.margins(x=0)
ax3.margins(x=0)


ax1.set_title("Voltage vs Time")
ax2.set_title("Current vs Time")
ax3.set_title("Temperature vs Time")

ax1.set_xlabel('Time [s]')
ax2.set_xlabel('Time [s]')
ax3.set_xlabel('Time [s]')

ax1.set_ylabel('Voltage [V]')
ax2.set_ylabel('Current [A]')
ax3.set_ylabel('Temperature [C]')

ax1.plot(time_data, voltage_data, 'b', label="Voltage")
ax1.set_yticks(np.arange(0, 4.6, 0.2))
ax1.grid(True)


ax2.plot(time_data, current_data, 'r', label="Current")
ax2.grid(True)


ax3.plot(time_data, ambient_data, 'b', label="Ambient Temp")
ax3.plot(time_data, pos_data, 'r', label="Positive Term Temp")
ax3.plot(time_data, middle_data, 'y', label="Middle Temp")
ax3.plot(time_data, neg_data, 'k', label="Negative Term Temp")
ax3.grid(True)
ax3.legend()

current_data = np.array(current_data)*1000.0    # Convert to mA
time_data = np.array(time_data)/3600.0          # Convert to Hours

cell_capacity = np.trapz(y=current_data, x=time_data)
print("Calculated Capacity: %.2fmAh"%(cell_capacity))

text_out = open(filename + "_summary.txt", 'w+')

text_out.write("Initial Cell Voltage: %.2fV\n" %(unloaded_v))
text_out.write("Loaded Cell Voltage: %.2fV\n" %(loaded_v))
text_out.write("Discharge Current: %.2fA\n" %(current_val))
text_out.write("DAC Setpoint: %i\n" %(int(setpoint)))
text_out.write("Final Cell voltage: %.3fV\n" %(voltage_data[-1]))
text_out.write("Measured Capacity: %.2fmAh\n" %(cell_capacity))
text_out.write("Measured IR: %.5f Ohms\n" %(internal_r))
text_out.write("Maximum cell temp: %.5fC\n" %(max(max(pos_data), max(middle_data), max(neg_data))))
text_out.write("Test Time: %.3f Hours\n" %(time_data[-1]))

text_out.close()

fig1.savefig(filename+'_voltage_plot.png')
fig2.savefig(filename+'_current_plot.png')
fig3.savefig(filename+'_temp_plot.png')

plt.show()


if not debug_mode:
    ser.close()