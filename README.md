# Modbus-Monitoring-Tool
modbus monitoring tool for robot

## Dependencies
- pyqt5
###

# 사용방법
- 가상환경을 꼭 만들어서 아래 패키지를 설치해주세요!  
$ pip install pyqt5
$ pip install pymodbus
$ pip install pandas

main.py 실행

### 로봇 IP 변경
MainWindow.py 에서 self.robot_address 를 바꿔주세요

### 소켓서버 IP 변경
소켓 서버는 현재 ip주소로 창이 열립니다.

서버 IP 주소를 바꾸려면 main.py를 실행한 후, 실행 상단 Host IP를 바꾸고 start server를 해주세요

! 주의 

로컬 pc 의 IP와 서버 IP가 맞지 않으면 오류가 발생합니다.

### 기능 추가
#### v1.0.1
- v1.0.1 소켓 버그 수정
- 용접기 하트비트 기능 구현
- RTDE 레지스터 읽고 저장하는 기능 추가 (저장경로 : RTDE sample 폴더)