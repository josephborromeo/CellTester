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



#   Previous code was same as capacity tests #
cycle = 1
test_nums = []

loaded_time = 10
rest_time = 30

ocv = []
loaded_voltages = []
currents = []
internal_resistances = []

while port_found and running:
    print("Starting Cycle", cycle)
    test_nums.append(cycle)
    sio.write('0f')
    sio.flush()
    ser.reset_input_buffer()
    #Let cell rest and take OCV Measurements
    for j in range(loop_speed):
        data = sio.read().split('\n')[0]
        data = data.split("|")
        if len(data) == 6:
            if not '' in data:
                volt = float(data[0]) + voltage_offset
                current = ((float(data[1])/4095)*3.358)/0.1187        # FIXME: this only gives voltage
                elapsed = time.clock() - start_time
                if volt > 2 and volt < 4.5:
                    time_data.append(elapsed)
                    voltage_data.append(volt)
                    current_data.append(current)
        time.sleep(loop_time)

    # Record averageOCV before applying load
    ocv.append(np.average(voltage_data[-(loop_speed-1):-2]))
    
    # Load cell
    sio.write(str(setpoint) + 'f')
    sio.flush()
    # Load cell and take measurements
    for k in range(loop_speed*loaded_time):
        data = sio.read().split('\n')[0]
        data = data.split("|")

        if len(data) == 6:
            if not '' in data:
                volt = float(data[0]) + voltage_offset
                current = ((float(data[1])/4095)*3.358)/0.1187      
                elapsed = time.clock() - start_time
                if volt > 2 and volt < 4.5:
                    time_data.append(elapsed)
                    voltage_data.append(volt)
                    current_data.append(current)
        
        time.sleep(loop_time)
    
    # Stop current 
    sio.write('0f')
    sio.flush()

    # Record Average loaded voltage and current
    loaded_voltages.append(np.average(voltage_data[-(loop_speed-1):-2]))
    currents.append(np.average(current_data[-((loop_speed*loaded_time)-1):-2]))

    temp_ir = (ocv[-1] - loaded_voltages[-1])/currents[-1]
    internal_resistances.append(temp_ir)

    # Fix plot issues
    for j in range(loop_speed):
        data = sio.read().split('\n')[0]
        data = data.split("|")
        if len(data) == 6:
            if not '' in data:
                volt = float(data[0]) + voltage_offset
                current = ((float(data[1])/4095)*3.358)/0.1187       
                elapsed = time.clock() - start_time
                if volt > 2 and volt < 4.5:
                    time_data.append(elapsed)
                    voltage_data.append(volt)
                    current_data.append(current)
        time.sleep(loop_time)


    # Sleep for rest time to allow cell to cool
    if  float(volt) > LVC:
        print("Resting\n")
        cycle += 1
        time.sleep(rest_time)

    else:
        print("Hit LVC, exiting\n")
        running = False

csvfile.close()

# Plot data
fig1, ax1 = plt.subplots(figsize=(12.8,7.2), tight_layout=True)
fig2, ax2 = plt.subplots(figsize=(12.8,7.2), tight_layout=True)
fig3, ax3 = plt.subplots(figsize=(12.8,7.2), tight_layout=True)

ax1.margins(x=0)
ax2.margins(x=0)
ax3.margins(x=0)

ax1.set_title("Voltage vs Time")
ax2.set_title("Current vs Time")
ax3.set_title("IR vs Test number")

ax1.set_xlabel('Time [s]')
ax2.set_xlabel('Time [s]')
ax3.set_xlabel('Test Number')

ax1.set_ylabel('Voltage [V]')
ax2.set_ylabel('Current [A]')
ax3.set_ylabel('IR [mOhms]')

ax1.plot(time_data, voltage_data, 'b', label="Voltage")
ax1.set_yticks(np.arange(0, 4.6, 0.2))
ax1.grid(True)


ax2.plot(time_data, current_data, 'r', label="Current")
ax2.grid(True)

ax3.plot(test_nums, np.array(internal_resistances)*1000, 'g')
ax3.grid(True)

current_data = np.array(current_data)*1000.0    # Convert to mA
time_data = np.array(time_data)/3600.0          # Convert to Hours

text_out = open(filename + "_summary.txt", 'w+')
text_out.write("Cycles Run: %i\n" %(cycles))
text_out.write("Discharge Current: %.2fA\n" %(current_setpoint))
text_out.write("Loaded Time: %is\n" %(loaded_time))
text_out.write("Rest Time: %is\n\n" %(rest_time))
for i in range(cycles):
    text_out.write("Run #%i\tIR = %.3fmOhms\tOCV:%.2fV\tLoaded V:%.2fV\tAVG Current:%.2fA\n" %(i+1, internal_resistances[i]*1000, ocv[i], loaded_voltages[i], currents[i]))
text_out.write("\nAverage IR: %.3fmOhms" %(np.average(internal_resistances)*1000))
text_out.write("\nAverage IR: %.3fmOhms (Without First Test)" %(np.average(internal_resistances[1:])*1000))

text_out.close()

fig1.savefig(filename+'_voltage_plot.png')
fig2.savefig(filename+'_current_plot.png')
fig3.savefig(filename+'_IR_plot.png')

plt.show()


if not debug_mode:
    ser.close()