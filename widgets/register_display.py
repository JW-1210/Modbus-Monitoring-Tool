import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QSpinBox, QPushButton, QGridLayout, QGroupBox,
                           QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal

class RegisterDisplayWidget(QWidget):
     # 새로운 시그널 추가 - 레지스터 주소, 값
    register_write_signal = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        
        # 레지스터 모니터링 그룹
        self.group_box = QGroupBox("Register Monitoring")
        self.group_layout = QVBoxLayout()
        
        # 모니터링할 레지스터 선택 영역
        self.select_layout = QHBoxLayout()
        self.select_layout.addWidget(QLabel("Register Address:"))
        
        self.register_spinbox = QSpinBox()
        self.register_spinbox.setRange(0, 65535)
        self.register_spinbox.setValue(128)  # 기본값 128
        self.select_layout.addWidget(self.register_spinbox)
        
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self.add_register_monitor)
        self.select_layout.addWidget(self.add_button)
        
        self.group_layout.addLayout(self.select_layout)
        
        # 레지스터 값 표시 영역
        self.registers_grid = QGridLayout()
        self.registers_grid.setColumnStretch(1, 1)  # 값 열을 늘려서 표시
        
        # 레이블 생성
        self.registers_grid.addWidget(QLabel("Register : "), 0, 0)
        self.registers_grid.addWidget(QLabel("Value"), 0, 1)
        
        self.group_layout.addLayout(self.registers_grid)
        self.group_box.setLayout(self.group_layout)
        
        self.layout.addWidget(self.group_box)
        self.setLayout(self.layout)
        
        # 모니터링 중인 레지스터 목록
        self.monitored_registers = {}
        self.next_row = 1
    
    def add_register_monitor(self):
        register = self.register_spinbox.value()
        
        # 이미 추가된 레지스터인지 확인
        if register in self.monitored_registers:
            return
        
        # 레지스터 주소 라벨
        reg_label = QLabel(f"{register}")
        reg_label.setAlignment(Qt.AlignCenter)
        
        # 레지스터 값 라벨
        value_label = QLabel("--")
        value_label.setAlignment(Qt.AlignCenter)

        # 값 입력 필드 추가
        value_input = QLineEdit()
        value_input.setPlaceholderText("value")
        value_input.setFixedWidth(80)
        
        # 전송 버튼 추가
        send_button = QPushButton("Send")
        send_button.clicked.connect(lambda: self.send_register_value(register, value_input.text()))
        
        # 삭제 버튼
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(lambda: self.remove_register_monitor(register))
        
        # 그리드에 추가
        self.registers_grid.addWidget(reg_label, self.next_row, 0)
        self.registers_grid.addWidget(value_label, self.next_row, 1)
        self.registers_grid.addWidget(value_input, self.next_row, 2)
        self.registers_grid.addWidget(send_button, self.next_row, 3)
        self.registers_grid.addWidget(delete_button, self.next_row, 4)
        
        # 목록에 추가, tuple, (value_label, value_input)
        self.monitored_registers[register] = (value_label, value_input)
        self.next_row += 1

    def send_register_value(self, register, value_text):
        """register sending func"""
        try:
            value = int(value_text)
            self.register_write_signal.emit(register, value)
            
            # 값 전송 후 입력 필드 비우기
            if hasattr(self.monitored_registers[register], "__getitem__"):
                input_field = self.monitored_registers[register][1]
                input_field.clear()  # 입력 필드 내용 지우기
                input_field.setStyleSheet("")  # 스타일 초기화 (에러 표시가 있었을 경우)

        except ValueError:
            # if not int
            if hasattr(self.monitored_registers[register], "__getitem__"):
                self.monitored_registers[register][1].setStyleSheet("background-color: #ffcccc;")  # 에러 표시
            else:
                pass # 호환성

    def remove_register_monitor(self, register):
        if register in self.monitored_registers:
            # 그리드에서 위젯 제거
            row = 0
            for i in range(1, self.registers_grid.rowCount()):
                item = self.registers_grid.itemAtPosition(i, 0)
                if item and item.widget() and item.widget().text() == str(register):
                    row = i
                    break
            
            if row > 0:
                for col in range(5):
                    item = self.registers_grid.itemAtPosition(row, col)
                    if item and item.widget():
                        widget = item.widget()
                        self.registers_grid.removeItem(item)
                        widget.setParent(None)
                        widget.deleteLater()
            
            # 목록에서 제거
            del self.monitored_registers[register]

            # 스레드에 알림(콜백)
            if hasattr(self, "on_register_removed") and self.on_register_removed:
                self.on_register_removed(register)
    
    def update_register_value(self, register, value):
        if register in self.monitored_registers:

            # tuple
            if hasattr(self.monitored_registers[register], "__getitem__"):
                self.monitored_registers[register][0].setText(str(value))
            else:
                self.monitored_registers[register].setText(str(value))
