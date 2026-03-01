# Pen Plotter Machine
성균관대 로봇 동아리 SIOR 2026 홍보부스용 

웹캠으로 사람을 인식하고,
그 윤곽선을 벡터로 변환한 뒤,
펜 플로터로 실제 종이에 그리는 로봇 만들기

---

## What This Project Does

1. 웹캠에서 사람 감지
2. 사람 윤곽선만 추출
3. 윤곽선을 벡터(선 좌표)로 변환
4. 펜이 움직일 경로 정렬
5. G-code로 변환하여 HW 전송

---

## Overall Flow

### 0. Webcam

### 1. Cam Frame 벡터화
  
#### 1-1. 윤곽선 추출 (vision.py)

  
#### 1-2. 좌표를 mm 단위로 변환 (normalize.py)
  
#### 1-3. 기계가 그리기 좋은 형태로 정리 (vision_postprocess.py)

 
### 2. 펜 이동 순서 최적화 (planning.py)
  
### 3. G-code 생성 (gcode.py)

### 4. 하드웨어 연동
  
#### 4-1. Serial - Plotter 

#### 4-2. Arduino + Motor Control

---

## File Structure

camera.py  
- 카메라 프레임을 종이 비율에 맞게 자름

vision.py  
- 사람 마스크 추출 (YOLO)
- 엣지 검출
- contour → 선 벡터 변환

normalize.py  
- 픽셀(px) 좌표를 실제 종이(mm) 좌표로 변환

vision_postprocess.py  
- 너무 짧은 선 제거
- 불필요한 점 제거
- 일정 간격으로 재샘플링

planning.py  
- 펜이 덜 이동하도록 선 순서 정렬
- Pen UP / DOWN 구분

gcode.py  
- 플로터가 이해할 수 있는 G0 / G1 코드 생성

main.py  
- 실행 시작 파일

---

## Hardware Info

- To be written


---

## CAD Files

- To be Written

---

## Coordinates (Not Fixed)

- 종이 크기: 260mm x 190mm
- 좌표 원점: 왼쪽 아래 (BOTTOM_LEFT)
- CNC/GRBL 호환 염두

---

## Supported Commands (G-Code)

현재 생성되는 G-code는 GRBL / CNC 호환 최소 스펙을 기반으로 한다.

- G21 → mm 단위 사용

- G90 → 절대 좌표 모드

- G0 X.. Y.. → Pen UP 이동

- G1 X.. Y.. → Pen DOWN 이동

- M3 → Pen DOWN

- M5 → Pen UP

## Motion Policy

- Pen UP 상태에서 이동 → G0

- Pen DOWN 상태에서 이동 → G1

- 모든 좌표는 mm 단위

- 절대 좌표계 (G90) 사용

- Feedrate는 향후 config 분리 예정

### Example Output

아래는 사각형을 그리는 간단한 예시이다.


<code>G21
G90
M5
G0 X10 Y10
M3
G1 X30 Y10
G1 X30 Y30
G1 X10 Y30
M5</code>



---

## How to Execute?

1. 카메라 연결
2. main.py 실행 
3. 스페이스바로 캡처
4. 경로 확인
5. G-code 생성 후 플로터 전송

---

## Objectives

- 과한 필터링 없이 깔끔한 윤곽선
- 기계가 안정적으로 그릴 수 있는 벡터
- 불필요한 펜 이동 최소화
- 실시간 데모 가능 구조

---

## 앞으로 개선할 것
- 하드웨어 연동
- 가속도 제어 (S-curve)
- 실시간 시리얼 전송
- 다중 레이어 드로잉
- Z축 제어 개선

