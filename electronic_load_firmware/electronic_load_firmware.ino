#include<SPI.h>

// Pin Definititions
#define SS PA4
#define ambient_sensor PA0
#define pos_term_thermistor PA1
#define middle_thermistor PA2
#define neg_term_thermistor PA3

#define cell_voltage_sense PB1
#define current_sense PB0

bool ACTIVE = true; // If test is done or not basically - LVC check will change this

bool state = false;
float sense_resistance = 0.11965;  // Resistance in Ohms -- Tweak for accurate vals

float LVC = 2.2; // Low voltage cutoff
float diff_max = 0.01; // slope

int counter = 0; // For testing

String output_data;

// Thermistors
unsigned int ambient_val = 0;
unsigned int pos_term_val = 0;
unsigned int middle_val = 0;
unsigned int neg_term_val = 0;

// Voltage/ current sense
float cell_voltage = 0;
unsigned int current = 0;

int dac_setpoint = 0;


// Offload processing to PC 


void setup() {
  // Setup pins
  pinMode(SS, OUTPUT);
  pinMode(PC13, OUTPUT);

  pinMode (ambient_sensor, INPUT);
  pinMode (pos_term_thermistor, INPUT);
  pinMode (middle_thermistor, INPUT);
  pinMode (neg_term_thermistor, INPUT);

  pinMode (cell_voltage_sense, INPUT);
  pinMode (current_sense, INPUT_PULLDOWN);
  
  // Setup SPI communication for MCP4921
  SPI.begin(); //Initialize the SPI_1 port.
  SPI.setBitOrder(MSBFIRST); // Set the SPI_1 bit order
  SPI.setDataMode(SPI_MODE0); //Set the  SPI_2 data mode 0
  SPI.setClockDivider(SPI_CLOCK_DIV16);      // Slow speed (72 / 16 = 4.5 MHz SPI_1 speed)
  digitalWrite(SS, HIGH);

  // Start serial comm. for PC
  Serial.begin(9600);
  
  writeDAC(0); // Make sure no current at first

}

int averages = 500;

int lvc_counter = 0;
bool hit_lvc = false;

void loop() {
  // Data Acquisition & Safety Checks (Under voltage, etc.)

  for (int i=0; i<averages; i++){
    /* Check for low voltage condition*/
    float temp_voltage = (float)analogRead(cell_voltage_sense);
    cell_voltage += ((temp_voltage/4095.0)*3.350)*4.300;
    current += analogRead(current_sense);
    
    /* Get Temp values */
    ambient_val += analogRead(ambient_sensor);
    pos_term_val += analogRead(pos_term_thermistor);
    middle_val += analogRead(middle_thermistor);
    neg_term_val += analogRead(neg_term_thermistor);
  }
  /* Check for low voltage condition*/
  cell_voltage /= averages;
  current /= averages;
  /* Get Temp values */
  ambient_val /= averages;
  pos_term_val /= averages;
  middle_val /= averages;
  neg_term_val /= averages;

 
/*RE-ENABLE BEFORE CAPACITY TEST*/
  /*
  if (cell_voltage < LVC){
    hit_lvc = true;
    lvc_counter++;
  }
  else if (hit_lvc && lvc_counter > 0){
    lvc_counter--;
    hit_lvc=false;
  } 
  if (lvc_counter > 3){
    ACTIVE = false;
  }
    
  if(!ACTIVE){  // Ensures it is off after low voltage cutoff
    writeDAC(0);
    dac_setpoint = 0;
  }

  */

  
  if (Serial.available() > 0 & ACTIVE){
    int data = Serial.parseInt();
    Serial.flush();
//    float data = Serial.parseFloat();
//    int val = current_to_val(data);
//    int val = volt_to_val(data);
    writeDAC(data);
    dac_setpoint = data;
    
//    // State is for LED indicator -- Ensure proper operation
//    state = !state;
//    digitalWrite(PC13, state);
  }

  // Send Data
  // FORMAT: VOLTAGE|CURRENT|AMBIENT_TEMP|POS_TEMP|MIDDLE_TEMP|NEG_TEMP

  if (dac_setpoint > 1){
    digitalWrite(PC13, LOW);
  }
  else{
    digitalWrite(PC13, HIGH);
  }

  output_data = String(cell_voltage, 3) + "|" + String(current) + "|" + String(ambient_val) + "|" + String(pos_term_val) + "|" + String(middle_val) + "|" + String(neg_term_val)+"\n";
  Serial.print(output_data);

  
  delay(5);   // 200Hz

}

// Custom function to send data to MCP4921
void writeDAC(unsigned int val){
  if (val > 4095){
    val = 4095;
  }
  
  //Setup data packet
  byte byte1 = B00110000;
  byte byte2 = lowByte(val);
  byte1 |= (B00001111 & highByte(val));
  
  // Set CS LOW and transfer data
  digitalWrite(SS, LOW);
  SPI.transfer(byte1);
  SPI.transfer(byte2);
  // Set CS back high to end transfer
  digitalWrite(SS, HIGH);
}

int volt_to_val(float volt){
  float supply = 3.35;
  float ratio = volt/supply;
  return round(ratio*4095);
}

int current_to_val(float current_setpoint){
  // V = I*R
  // I = V / R
  // R = sense_resistance
  // V = Effective PWM voltage which is VCC*Duty cycle == 5.0*(PWM_value/4095)
  // We must solve for PWM_value and set the output accordingly

  // Therefore if V = I*R then 5.0*(PWM_value/4095) = current_setpoint * sense_resistance

  // Handle over-current and negative current request

  float voltage = 3.30;   // FIXME: measure proper voltage

  // Max possible current will be voltage/sense_resistance, we can artificially cap this though
  
  if (current_setpoint > 30){
    current_setpoint = 30;
  }

  if (current_setpoint < 0){
    current_setpoint = 0;
  }

  float pwm_val = ((current_setpoint*sense_resistance)/voltage)*4095;
  int pwm_setpoint = round(pwm_val); // Have to set it to the closest value since we need an int

  return pwm_setpoint;
}
