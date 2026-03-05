
// ===============================
// Pen Plotter Motor Hardware Test
// UNO + 3x 28BYJ-48
// Each motor rotates for 5 seconds
// ===============================

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
int stepZ = 0;

void stepMotor(int pins[4], int s)
{
  for(int i=0;i<4;i++)
  {
    digitalWrite(pins[i], stepTable[s][i]);
  }
}

void stepForward(int pins[4], int &s)
{
  s++;
  if(s>=8) s=0;
  stepMotor(pins,s);
}

void rotateMotor(int pins[4], int &s, int duration_ms)
{
  unsigned long start = millis();

  while(millis() - start < duration_ms)
  {
    stepForward(pins, s);
    delay(3);   // speed control
  }
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

  Serial.println("Motor test start");
}

void loop()
{
  Serial.println("X motor rotating...");
  rotateMotor(Xpins, stepX, 5000);

  delay(2000);

  Serial.println("Y motor rotating...");
  rotateMotor(Ypins, stepY, 5000);

  delay(2000);

  Serial.println("Z motor rotating...");
  rotateMotor(Zpins, stepZ, 5000);

  delay(4000);
}

