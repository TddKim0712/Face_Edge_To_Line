// ===============================
// Pen Plotter Debug Controller
// UNO + 3 stepper (28BYJ-48)
// joystick control
// ===============================
// ================================
// Pen Plotter Firmware
// ================================

#define JOY_X A0
#define JOY_Y A1
#define JOY_SW A2

float steps_per_mm = 100.0;

long pos_x = 0;
long pos_y = 0;


// step pins
int Xpins[4] = {2,3,4,5};
int Ypins[4] = {6,7,8,9};
int Zpins[4] = {10,11,12,13};


int stepTable[8][4] = {
 {1,0,0,0},
 {1,1,0,0},
 {0,1,0,0},
 {0,1,1,0},
 {0,0,1,0},
 {0,0,1,1},
 {0,0,0,1},
 {1,0,0,1}
};


int stepX = 0;
int stepY = 0;


void stepMotor(int pins[4], int s)
{
  for(int i=0;i<4;i++)
  digitalWrite(pins[i], stepTable[s][i]);
}


void stepForward(int pins[4], int &s)
{
  s++;
  if(s>=8) s=0;
  stepMotor(pins,s);
}


void stepBackward(int pins[4], int &s)
{
  s--;
  if(s<0) s=7;
  stepMotor(pins,s);
}


void setup()
{

  Serial.begin(115200);

  for(int i=0;i<4;i++)
  {
    pinMode(Xpins[i],OUTPUT);
    pinMode(Ypins[i],OUTPUT);
    pinMode(Zpins[i],OUTPUT);
  }

  pinMode(JOY_SW,INPUT_PULLUP);

  Serial.println("ready");
}


void jog_control()
{

  int x = analogRead(JOY_X);
  int y = analogRead(JOY_Y);

  int dead = 80;
  int center = 512;

  if(x > center + dead)
  {
    stepForward(Xpins,stepX);
    pos_x++;
  }

  if(x < center - dead)
  {
    stepBackward(Xpins,stepX);
    pos_x--;
  }

  if(y > center + dead)
  {
    stepForward(Ypins,stepY);
    pos_y++;
  }

  if(y < center - dead)
  {
    stepBackward(Ypins,stepY);
    pos_y--;
  }

}


void report_position()
{

  float x_mm = pos_x / steps_per_mm;
  float y_mm = pos_y / steps_per_mm;

  Serial.print("POS ");
  Serial.print(x_mm);
  Serial.print(" ");
  Serial.println(y_mm);

}


void loop()
{

  jog_control();

  static unsigned long t=0;

  if(millis()-t>500)
  {
    report_position();
    t=millis();
  }

}