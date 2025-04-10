"""
로봇 모니터링 패키지
modbus_monitoring/
│
├── __init__.py              # 패키지 초기화 파일
├── main.py                  # 메인 애플리케이션 실행 파일
├── MainWindow.py            # UI 메인 윈도우 관련 실행 파일
├── rtde_recorder.py         # 모션 프로그램에서 전송하는 RTDE output register 저장 코드드
├── widgets/
│   ├── __init__.py          # 위젯 서브패키지 초기화
│   ├── register_display.py  # 레지스터 디스플레이 위젯
│   └── log_widget.py        # 로그 위젯
├── socket/
│   ├── __init__.py          # 소켓 서브패키지 초기화
│   ├── socket_server.py     # 소켓 모니터링 스레드
│   └── socket_widget.py     # 소켓 모니터링 위젯
│   └── utils.py             # 소켓으로 전달받은 변수 파싱
└── core/
    ├── __init__.py          # 코어 서브패키지 초기화
    ├── monitor_thread.py    # 모니터링 스레드
    └── read_registers.py # 모드버스 모니터링 모듈
"""
__version__ = '1.0.0'