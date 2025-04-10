from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                            QPushButton, QFileDialog, QLabel)

class LogWidget(QWidget):
    def __init__(self, monitor_thread):
        super().__init__()
        self.monitor_thread = monitor_thread
        self.layout = QVBoxLayout()
        
        # 로그를 표시할 텍스트 에디터
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.layout.addWidget(self.log_display)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        # 저장 버튼
        self.save_button = QPushButton("Save Log")
        self.save_button.clicked.connect(self.save_log)
        button_layout.addWidget(self.save_button)
        
        # 초기화 버튼 추가
        self.reset_button = QPushButton("Reset All Register")
        self.reset_button.clicked.connect(self.reset_registers)
        button_layout.addWidget(self.reset_button)

        # 로그 지우기 버튼 추가
        self.clear_button = QPushButton("Clear Log")
        self.clear_button.clicked.connect(self.clear_log)
        button_layout.addWidget(self.clear_button)

        # 일괄 출력 버튼 추가
        self.print_all_button = QPushButton("Print All")
        self.print_all_button.clicked.connect(self.print_all_registers)
        button_layout.addWidget(self.print_all_button)
        
        self.layout.addLayout(button_layout)
        self.setLayout(self.layout)
    
    def append_log(self, text):
        self.log_display.append(text)
        # 자동 스크롤
        cursor = self.log_display.textCursor()
        cursor.movePosition(cursor.End)
        self.log_display.setTextCursor(cursor)
    
    def save_log(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "로그 파일 저장",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_display.toPlainText())
    
    def reset_registers(self):
        # 모니터 스레드에 초기화 신호 보내기
        self.monitor_thread.reset_registers()
        self.append_log("레지스터 초기화 명령을 전송했습니다.")
        
    def clear_log(self):
        self.log_display.clear()

    def print_all_registers(self):
        """모든 레지스터 값을 일괄 출력하는 요청"""
        self.monitor_thread.run_monitor_once_manual()
        self.append_log("전체 레지스터 값 출력 요청 중...")
    
    def setup_rtde_recording(self, rtde_thread):
        """RTDE 녹화 관련 UI 설정"""
        self.rtde_thread = rtde_thread
        
        # RTDE 녹화 관련 레이아웃
        rtde_layout = QHBoxLayout()
        
        # 녹화 상태 라벨
        self.rtde_status_label = QLabel("RTDE: Standby")
        self.rtde_status_label.setStyleSheet("color: gray;")
        rtde_layout.addWidget(self.rtde_status_label)
        
        # 녹화 샘플 수
        self.rtde_sample_label = QLabel("Sample: 0")
        rtde_layout.addWidget(self.rtde_sample_label)
        
        # 빈 공간 추가
        rtde_layout.addStretch(1)
        
        # RTDE 녹화 버튼
        self.rtde_record_button = QPushButton("RTDE Record")
        self.rtde_record_button.setCheckable(True)
        self.rtde_record_button.clicked.connect(self.toggle_rtde_recording)
        self.rtde_record_button.setStyleSheet("background-color: #4CAF50; color: white;")
        rtde_layout.addWidget(self.rtde_record_button)
        
        # 레이아웃에 추가
        self.layout.addLayout(rtde_layout)
        
        # RTDE 신호 연결
        if self.rtde_thread:
            self.rtde_thread.log_signal.connect(self.append_log)
            self.rtde_thread.sample_count_signal.connect(self.update_rtde_sample_count)
    
    def toggle_rtde_recording(self):
        """RTDE 녹화 시작/중지 토글"""
        if not self.rtde_thread:
            self.append_log("RTDE Thread is not working")
            return
        
        is_recording = self.rtde_record_button.isChecked()
        
        if is_recording:
            # 녹화 시작
            self.rtde_thread.toggle_recording()
            self.rtde_record_button.setText("RTDE Recording Stop")
            self.rtde_record_button.setStyleSheet("background-color: #F44336; color: white;")
            self.rtde_status_label.setText("RTDE: Recording")
            self.rtde_status_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            # 녹화 중지 및 저장
            self.rtde_thread.toggle_recording()
            self.rtde_record_button.setText("RTDE Recording")
            self.rtde_record_button.setStyleSheet("background-color: #4CAF50; color: white;")
            self.rtde_status_label.setText("RTDE: Standby")
            self.rtde_status_label.setStyleSheet("color: gray;")

    def update_rtde_sample_count(self, count):
        """RTDE 녹화 샘플 수 업데이트"""
        if self.rtde_sample_label:
            self.rtde_sample_label.setText(f"Sample: {count}")