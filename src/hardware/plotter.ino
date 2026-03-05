// =======================================
// Pen Plotter Firmware
// G-code Receiver
// UNO + 28BYJ-48
// =======================================

#define STEPS_PER_MM 20      // 나중에 calibration으로 수정
#define Z_STEPS_PER_MM 20

#define BUF 80

struct Axis
{
  int pins[4];
  int stepIndex;
  long pos;
};

Axis axisX = {{2,3,4,5},0,0};
Axis axisY = {{6,7,8,9},0,0};
Axis axisZ = {{10,11,12,13},0,0};

int stepTable[8][4] =
{
 {1,0,0,0},
 {1,1,0,0},
 {0,1,0,0},
 {0,1,1,0},
 {0,0,1,0},
 {0,0,1,1},
 {0,0,0,1},
 {1,0,0,1}
};

char line[BUF];
int lineIndex = 0;

// ----------------------
// stepper low level
// ----------------------

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
  a.pos++;
}

void stepBackward(Axis &a)
{
  a.stepIndex--;
  if(a.stepIndex<0) a.stepIndex=7;
  stepMotor(a);
  a.pos--;
}

// ----------------------
// single axis move
// ----------------------

void moveAxis(Axis &a, long target)
{
  while(a.pos != target)
  {
    if(a.pos < target)
      stepForward(a);
    else
      stepBackward(a);

    delayMicroseconds(800); // 속도
  }
}

// ----------------------
// XY linear move
// Bresenham style
// ----------------------

void moveXY(long tx,long ty)
{
  long x0 = axisX.pos;
  long y0 = axisY.pos;

  long dx = abs(tx - x0);
  long dy = abs(ty - y0);

  long sx = (x0 < tx) ? 1 : -1;
  long sy = (y0 < ty) ? 1 : -1;

  long err = dx - dy;

  while(true)
  {
    if(axisX.pos == tx && axisY.pos == ty)
      break;

    long e2 = 2*err;

    if(e2 > -dy)
    {
      err -= dy;
      if(sx==1) stepForward(axisX);
      else stepBackward(axisX);
    }

    if(e2 < dx)
    {
      err += dx;
      if(sy==1) stepForward(axisY);
      else stepBackward(axisY);
    }

    delayMicroseconds(800);
  }
}

// ----------------------
// G-code parsing
// ----------------------

float parseValue(char code)
{
  char *ptr = strchr(line,code);
  if(ptr) return atof(ptr+1);
  return NAN;
}

void processLine()
{
  if(line[0]=='G')
  {
    int g = atoi(&line[1]);

    float x = parseValue('X');
    float y = parseValue('Y');
    float z = parseValue('Z');

    long tx = axisX.pos;
    long ty = axisY.pos;
    long tz = axisZ.pos;

    if(!isnan(x)) tx = x * STEPS_PER_MM;
    if(!isnan(y)) ty = y * STEPS_PER_MM;
    if(!isnan(z)) tz = z * Z_STEPS_PER_MM;

    if(g==0 || g==1)
    {
      moveXY(tx,ty);
      moveAxis(axisZ,tz);
    }
  }

  Serial.println("ok");
}

// ----------------------
// setup
// ----------------------

void setup()
{
  Serial.begin(115200);

  Axis* axes[] = {&axisX,&axisY,&axisZ};

  for(int a=0;a<3;a++)
  {
    for(int i=0;i<4;i++)
      pinMode(axes[a]->pins[i],OUTPUT);
  }

  Serial.println("ready");
}

// ----------------------
// loop
// ----------------------

void loop()
{
  while(Serial.available())
  {
    char c = Serial.read();

    if(c=='\n')
    {
      line[lineIndex]=0;
      processLine();
      lineIndex=0;
    }
    else
    {
      if(lineIndex < BUF-1)
        line[lineIndex++] = c;
    }
  }
}