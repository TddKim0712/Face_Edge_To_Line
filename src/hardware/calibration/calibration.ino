// ===============================
// calibration firmware
// ===============================

#define JOY_X A0
#define JOY_Y A1
#define JOY_SW A2

float steps_per_mm = 100.0;

long pos_x = 0;
long pos_y = 0;

long rec_start_x = 0;
long rec_start_y = 0;

bool recording = false;
bool last_sw = HIGH;


// step pins
int Xpins[4] = {2,3,4,5};
int Ypins[4] = {6,7,8,9};

int stepX = 0;
int stepY = 0;

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


void check_record_toggle()
{

  bool sw = digitalRead(JOY_SW);

  if(last_sw == HIGH && sw == LOW)
  {
    recording = !recording;

    if(recording)
    {
      rec_start_x = pos_x;
      rec_start_y = pos_y;

      Serial.println("REC_START");
    }
    else
    {
      long dx = pos_x - rec_start_x;
      long dy = pos_y - rec_start_y;

      float pred_x = dx / steps_per_mm;
      float pred_y = dy / steps_per_mm;

      Serial.print("REC_STOP ");
      Serial.print(dx);
      Serial.print(" ");
      Serial.print(dy);
      Serial.print(" ");
      Serial.print(pred_x);
      Serial.print(" ");
      Serial.println(pred_y);
    }

    delay(200);
  }

  last_sw = sw;
}


void loop()
{

  jog_control();

  check_record_toggle();

}