import sys
import os
from PyQt5.QtWidgets import QTabWidget, QApplication, QMainWindow, QWidget, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QPushButton

# 패키지 모듈 가져오기
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
__package__ = 'modbus_monitoring'
from .widgets import RegisterDisplayWidget, LogWidget
from .core import MonitorThread
from .socket import SocketLogWidget
from .rtde_recorder import RTDERecorderThread

class MainWindow(QMainWindow):

    def __init__(self):
        # 로봇 ip 입력
        self.robot_address = "192.168.1.7"  # 기본값으로 설정

        super().__init__()
        self.setWindowTitle("Modbus & Socket Monitoring")
        self.setGeometry(100, 100, 1000, 600)
        
        # 중앙 위젯 생성
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 전체 레이아웃
        self.main_layout = QHBoxLayout()

        # IP 설정 UI 추가
        self.setup_ip_config()

        # 탭 위젯 생성
        self.tab_widget = QTabWidget()

        # 모드버스 모니터링 탭
        self.modbus_tab = QWidget()
        self.modbus_layout = QHBoxLayout()
        
        # 모니터링 스레드 생성
        self.monitor_thread = MonitorThread(host=self.robot_address)

        # RTDE 녹화 스레드 생성
        self.rtde_thread = RTDERecorderThread(robot_ip=self.robot_address)
        
        # LogWidget 생성
        self.log_widget = LogWidget(self.monitor_thread)

        # RTDE 녹화 버튼 설정
        self.log_widget.setup_rtde_recording(self.rtde_thread)
        
        # RegisterDisplayWidget 생성
        self.register_widget = RegisterDisplayWidget()
        
        # 로그 시그널 연결
        self.monitor_thread.log_signal.connect(self.log_widget.append_log)
        
        # 레지스터 업데이트 시그널 연결
        self.monitor_thread.register_update_signal.connect(self.register_widget.update_register_value)
        
        # 레지스터 추가 버튼 클릭 시그널 연결
        self.register_widget.add_button.clicked.connect(
            lambda: self.monitor_thread.add_monitored_register(self.register_widget.register_spinbox.value())
        )

        # 레지스터 값 쓰기 시그널 연결 (새로 추가)
        self.register_widget.register_write_signal.connect(
            self.monitor_thread.write_register_value
        )

        # 레지스터 삭제 후 재추가 콜백
        self.register_widget.on_register_removed = self.monitor_thread.remove_monitored_register

        # 레이아웃에 위젯 추가
        self.modbus_layout.addWidget(self.log_widget, 2)  # 로그 위젯 (비율 2)
        self.modbus_layout.addWidget(self.register_widget, 1)  # 레지스터 위젯 (비율 1)
        self.modbus_tab.setLayout(self.modbus_layout)

        # 소켓 모니터링 탭
        self.socket_log_widget = SocketLogWidget()

        # 탭에 위젯 추가
        self.tab_widget.addTab(self.modbus_tab, "Modbus Monitoring")
        self.tab_widget.addTab(self.socket_log_widget, "Socket Monitoring")
        
        # 메인 레이아웃에 탭 위젯 추가
        self.main_layout.addWidget(self.tab_widget)
        self.central_widget.setLayout(self.main_layout)
        
        # MainWindow 생성자 내부
        # 기본으로 저장해서 출력할 레지스터 
        for reg in [202, 138]:
            self.monitor_thread.add_monitored_register(reg)
            self.register_widget.register_spinbox.setValue(reg)
            self.register_widget.add_register_monitor()
        
        # 모니터 스레드 시작
        self.monitor_thread.start()

        # RTDE 스레드 시작
        self.rtde_thread.start()

        # 하트비트 연결
        self.register_widget.heartbeat_signal.connect(
            self.monitor_thread.set_heartbeat
        )
        
    def closeEvent(self, event):
        # 모드버스 모니터 스레드 종료료
        self.monitor_thread.stop()
        self.monitor_thread.wait()

        # RTDE 스레드 종료
        if hasattr(self, 'rtde_thread') and self.rtde_thread:
            self.rtde_thread.stop()
            self.rtde_thread.wait()

        # 소켓 스레드 종료 - 소켓 로그 위젯 내에서 관리하므로 여기서는 체크만 함
        if hasattr(self.socket_log_widget, 'socket_thread') and self.socket_log_widget.socket_thread:
            self.socket_log_widget.stop_socket_server()
        
        event.accept()

    def setup_ip_config(self):
        # IP 설정 그룹박스
        self.ip_group = QGroupBox("Robot IP Configuration")
        ip_layout = QHBoxLayout()
        
        # IP 주소 입력 필드
        ip_layout.addWidget(QLabel("Robot IP:"))
        self.ip_input = QLineEdit(self.robot_address)  # 기본값으로 기존 IP 설정
        self.ip_input.setFixedWidth(150)
        ip_layout.addWidget(self.ip_input)
        
        # 연결 버튼
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_robot)
        ip_layout.addWidget(self.connect_button)
        
        # 빈 공간 추가
        ip_layout.addStretch()
        
        self.ip_group.setLayout(ip_layout)
        self.main_layout.addWidget(self.ip_group)

    def connect_to_robot(self):
        # 현재 입력된 IP 가져오기
        self.robot_address = self.ip_input.text().strip()
        
        # 기존 스레드 중지
        if hasattr(self, 'monitor_thread') and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.monitor_thread.wait()
        
        # 새 스레드 생성 및 시작
        self.monitor_thread = MonitorThread(host=self.robot_address)  # 업데이트된 속성 사용
        
        # 로그 시그널 연결
        self.monitor_thread.log_signal.connect(self.log_widget.append_log)
        
        # 레지스터 업데이트 시그널 연결
        self.monitor_thread.register_update_signal.connect(self.register_widget.update_register_value)
        
        # 하트비트 연결
        self.register_widget.heartbeat_signal.connect(
            self.monitor_thread.set_heartbeat
        )
        
        # 모니터 스레드 시작
        self.monitor_thread.start()
        
        # 연결 로그 표시
        self.log_widget.append_log(f"새 IP({robot_ip})로 연결 중...")


