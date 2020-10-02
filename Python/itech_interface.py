import easy_scpi as scpi
import pyvisa

# Connect to supply

rm = pyvisa.ResourceManager()

print (rm.list_resources())
my_instrument = rm.open_resource('ASRLCOM8::INSTR')


my_instrument.read_termination = '\n'
my_instrument.write_termination = '\n'
# my_instrument.query('*IDN?')

while True:
    print(my_instrument.read_bytes(1))
    time.sleep(0.1)