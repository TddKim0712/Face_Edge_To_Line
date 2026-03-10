
// ==================================
// Pen Plotter Fast Jog Controller
// Modular version
// UNO + 28BYJ-48 + Joystick
// ==================================

#define JOY_X A0
#define JOY_Y A1
#define JOY_SW A2

#define CENTER 512
#define DEAD   60

struct Axis
{
  int pins[4];
  int stepIndex;
  int dir;
  unsigned long lastStep;
  unsigned long dirChange;
};

Axis axisX = {{2,3,4,5},0,0,0,0};
Axis axisY = {{6,7,8,9},0,0,0,0};
Axis axisZ = {{10,11,12,13},0,0,0,0};

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


void stepMotor(Axis &a)
{
  for(int i=0;i<4;i++)
    digitalWrite(a.pins[i], stepTable[a.stepIndex][i]);
}

void stepForward(Axis &a)
{
  a.stepIndex++;
  if(a.stepIndex>=8) a.stepIndex=0;
  stepMotor(a);
}

void stepBackward(Axis &a)
{
  a.stepIndex--;
  if(a.stepIndex<0) a.stepIndex=7;
  stepMotor(a);
}


void jogAxis(Axis &a, int value, unsigned long now)
{
  if(value > CENTER + DEAD)
  {
    int newDir = 1;

    if(newDir != a.dir)
    {
      a.dir = newDir;
      a.dirChange = now;
    }

    int interval = map(value, CENTER+DEAD, 1023, 3000, 400);

    if(now - a.dirChange > 1000)
    {
      if(now - a.lastStep > interval)
      {
        stepForward(a);
        a.lastStep = now;
      }
    }
  }

  else if(value < CENTER - DEAD)
  {
    int newDir = -1;

    if(newDir != a.dir)
    {
      a.dir = newDir;
      a.dirChange = now;
    }

    int interval = map(value, CENTER-DEAD, 0, 3000, 400);

    if(now - a.dirChange > 1000)
    {
      if(now - a.lastStep > interval)
      {
        stepBackward(a);
        a.lastStep = now;
      }
    }
  }
}


void setup()
{
  Serial.begin(115200);

  Axis* axes[] = {&axisX,&axisY,&axisZ};

  for(int a=0;a<3;a++)
  {
    for(int i=0;i<4;i++)
      pinMode(axes[a]->pins[i],OUTPUT);
  }

  pinMode(JOY_SW,INPUT_PULLUP);

  Serial.println("Modular jog controller ready");
}


void loop()
{
  unsigned long now = micros();

  int x = analogRead(JOY_X);
  int y = analogRead(JOY_Y);

  jogAxis(axisX, x, now);
  jogAxis(axisY, y, now);

  // Z axis test
  if(digitalRead(JOY_SW)==LOW)
  {
    if(now - axisZ.lastStep > 2000)
    {
      stepForward(axisZ);
      axisZ.lastStep = now;
    }
  }
}

