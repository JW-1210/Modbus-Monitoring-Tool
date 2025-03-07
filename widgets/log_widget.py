from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                           QPushButton, QFileDialog)

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