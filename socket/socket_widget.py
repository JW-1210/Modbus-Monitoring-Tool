import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                         QTextEdit, QPushButton, QLabel, QSpinBox, QFileDialog, QGroupBox,
                         QCheckBox, QLineEdit, QGridLayout)  # QGridLayout 추가
from .socket_server import SocketMonitorThread
import socket

class SocketLogWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # 메인 레이아웃
        self.layout = QVBoxLayout()
        
        # 설정 그룹
        self.setup_config_group()
        
        # 로그 디스플레이
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.layout.addWidget(self.log_display)
        
        # 버튼 레이아웃
        self.button_layout = QHBoxLayout()
        
        # 저장 버튼
        self.save_button = QPushButton("Save Log")
        self.save_button.clicked.connect(self.save_log)
        self.button_layout.addWidget(self.save_button)
        
        # 지우기 버튼
        self.clear_button = QPushButton("Clear Log")
        self.clear_button.clicked.connect(self.clear_log)
        self.button_layout.addWidget(self.clear_button)
        
        # 레이아웃에 버튼 영역 추가
        self.layout.addLayout(self.button_layout)
        
        # 위젯에 레이아웃 설정
        self.setLayout(self.layout)
        
        # 소켓 모니터링 스레드
        self.socket_thread = None
    
    def setup_config_group(self):
        """설정 그룹 생성"""
        self.config_group = QGroupBox("Socket Server Configuration")
        config_layout = QGridLayout()

        # 현재 컴퓨터의 IP 주소 가져오기
        try:
            hostname = socket.gethostname()
            current_ip = socket.gethostbyname(hostname)
        except:
            current_ip = "127.0.0.1"  # 실패 시 기본값
        
        # 호스트 설정
        config_layout.addWidget(QLabel("Host:"), 0, 0)  # 행 0, 열 0
        self.host_input = QLineEdit(current_ip)  
        self.host_input.setFixedWidth(120)
        self.host_input.setPlaceholderText("서버 IP")
        self.host_input.setToolTip("0.0.0.0은 모든 네트워크 인터페이스에서 연결 수락")
        config_layout.addWidget(self.host_input, 0, 1)  # 행 0, 열 1
        
        # 포트 설정
        config_layout.addWidget(QLabel("Port:"), 0, 2)  # 행 0, 열 2
        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(12345)
        self.port_input.setFixedWidth(80)  # 포트 입력 필드 너비도 제한
        config_layout.addWidget(self.port_input, 0, 3)  # 행 0, 열 3
        
        # 시작 버튼
        self.start_button = QPushButton("Start Server")
        self.start_button.setFixedWidth(100)
        self.start_button.clicked.connect(self.start_socket_server)
        config_layout.addWidget(self.start_button, 0, 5)  # 행 0, 열 5
        
        # 중지 버튼
        self.stop_button = QPushButton("Stop Server")
        self.stop_button.setFixedWidth(100)    
        self.stop_button.clicked.connect(self.stop_socket_server)
        self.stop_button.setEnabled(False)
        config_layout.addWidget(self.stop_button, 0, 6)  # 행 0, 열 6
        
        # 빈 공간 추가하여 레이아웃 균형 조정
        spacer_label = QLabel("")
        config_layout.addWidget(spacer_label, 0, 7)
        config_layout.setColumnStretch(7, 1)  # 마지막 열에 신축성 부여
        
        self.config_group.setLayout(config_layout)
        self.layout.addWidget(self.config_group)
    
    def start_socket_server(self):
        """소켓 서버 시작"""
        host = self.host_input.text()
        port = self.port_input.value()
        
        # 이전 스레드가 있으면 종료
        if self.socket_thread and self.socket_thread.isRunning():
            self.socket_thread.stop()
            self.socket_thread.wait()
        
        # 새 스레드 생성 및 시작
        self.socket_thread = SocketMonitorThread(host=host, port=port)
        self.socket_thread.log_signal.connect(self.append_log)
        self.socket_thread.start()
        
        # UI 상태 변경
        self.port_input.setEnabled(False)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        self.append_log(f"Socket Server Started {host}:{port} ...")
    
    def stop_socket_server(self):
        """소켓 서버 중지"""
        if self.socket_thread:
            try:
                if self.socket_thread.isRunning():
                    self.socket_thread.stop()
                    self.socket_thread.wait(2000)

                if self.socket_thread.isRunning():
                    self.socket_thread.terminate()
                    self.socket_thread.wait()

            except Exception as e:
                self.append_log(f"서버 종료 중 오류 발생: {str(e)}")

            ## UI 상태 변경
            self.host_input.setEnabled(True)  # IP 입력 활성화
            self.port_input.setEnabled(True)
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
            self.append_log("소켓 서버가 중지되었습니다.")
    
    def append_log(self, text):
        """로그 추가"""
        self.log_display.append(text)
        # 자동 스크롤
        cursor = self.log_display.textCursor()
        cursor.movePosition(cursor.End)
        self.log_display.setTextCursor(cursor)
    
    def save_log(self):
        """로그 저장"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "로그 파일 저장",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_display.toPlainText())
    
    def clear_log(self):
        """로그 지우기"""
        self.log_display.clear()

class SocketMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Socket Communication Monitor")
        self.setGeometry(100, 100, 800, 600)
        
        # 중앙 위젯
        self.central_widget = SocketLogWidget()
        self.setCentralWidget(self.central_widget)
    
    def closeEvent(self, event):
        """프로그램 종료 시 처리"""
        # 소켓 스레드 종료
        if self.central_widget.socket_thread and self.central_widget.socket_thread.isRunning():
            self.central_widget.socket_thread.stop()
            self.central_widget.socket_thread.wait()
        
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = SocketMonitorApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()