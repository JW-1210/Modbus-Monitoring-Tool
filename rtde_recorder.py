import os
import time
import pandas as pd
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal

try:
    from rtde_control import RTDEControlInterface as RTDEControl
    from rtde_receive import RTDEReceiveInterface as RTDEReceive
    from rtde_io import RTDEIOInterface as RTDEIO

except ImportError:
    # 모듈 미설치 시 로그용 가상 클래스
    class RTDEReceive:
        def __init__(self, ip, variables=None):
            self.ip = ip
            self.variables = variables
            self._connected = False
            
        def isConnected(self):
            return self._connected
            
        def getOutputDoubleRegister(self, i):
            return 0.0

class RTDEIO:
    def __init__(self, ip):
        self.ip = ip

# Define the output registers we want to monitor
output_registers = [
    "output_double_register_0",    # timer
    "output_double_register_1",    # WCR IN
    "output_double_register_2",    # Welding Current
    "output_double_register_3",    # Welding Voltage
    "output_double_register_4",    # X offset
    "output_double_register_5",    # Z offset
    "output_double_register_6",    # PLUS Integral
    "output_double_register_7",    # MINUS Integral
    "output_double_register_8",    # Standard_Arc_Current
    "output_double_register_9",    # ALL Integral
    "output_double_register_10",   # x up
    "output_double_register_11",   # x ui
    "output_double_register_12",   # z up
    "output_double_register_13",   # z ui
    "output_double_register_14",   # x
    "output_double_register_15",   # y
    "output_double_register_16",   # z
    "output_double_register_17",   # welding on/off polyscope
    "output_double_register_18",   # touch on/off polyscope
    "output_double_register_19",   # ratio_t
    "output_double_register_20",   # get_wcr polyscope
    "output_double_register_21",   # get_touch polyscope
    "output_double_register_22",   # write_welder
    "output_double_register_23",   # peak_vlaue
    "output_double_register_24",   # Arc_percent
    "output_double_register_25",   # set_current
    "output_double_register_26",   # set_voltage
    "output_double_register_27",   # set speed (cpm)
    "output_double_register_28",   # set amplitude
    "output_double_register_29",   # set frequency
    "output_double_register_30",   # set x_offset
    "output_double_register_31",   # set z_offset
    "output_double_register_32",   # set rx
    "output_double_register_33",   # set ry
]

# 레지스터 번호와 설명 매핑
register_descriptions = {
    0: "timer",
    1: "WCR IN",
    2: "Welding Current",
    3: "Welding Voltage",
    4: "X offset",
    5: "Z offset",
    6: "PLUS Integral",
    7: "MINUS Integral",
    8: "Standard_Arc_Current",
    9: "ALL Integral",
    10: "x up",
    11: "x ui",
    12: "z up",
    13: "z ui",
    14: "x",
    15: "y",
    16: "z",
    17: "welding on/off polyscope",
    18: "touch on/off polyscope",
    19: "ratio_t",
    20: "get_wcr polyscope",
    21: "get_touch polyscope",
    22: "write_welder",
    23: "peak_vlaue",
    24: "Arc_percent",
    25: "set_current",
    26: "set_voltage",
    27: "set speed (cpm)",
    28: "set amplitude",
    29: "set frequency",
    30: "set x_offset",
    31: "set z_offset",
    32: "set rx",
    33: "set ry",
}

class RTDERecorderThread(QThread):
    """RTDE 레지스터 녹화 쓰레드"""
    log_signal = pyqtSignal(str)
    sample_count_signal = pyqtSignal(int)
    
    def __init__(self, robot_ip="192.168.1.7", sample_interval=0.1):
        super().__init__()
        self.robot_ip = robot_ip
        self.sample_interval = sample_interval
        self._running = True
        self._recording = False
        self.df = pd.DataFrame()
        self.sample_count = 0
        self.previous_timer = None
        
    def run(self):
        """쓰레드 시작 메서드"""
        try:
            # RTDE 연결
            self.rtde_r = RTDEReceive(self.robot_ip, variables=output_registers)
            self.rtde_io = RTDEIO(self.robot_ip)
            
            if not self.rtde_r.isConnected():
                self.log_signal.emit(f"RTDE Connecting Failed : {self.robot_ip}")
                return
                
            self.log_signal.emit(f"RTDE Connected: {self.robot_ip}")
            self.previous_timer = self.rtde_r.getOutputDoubleRegister(0)
            
            # 메인 루프
            while self._running:
                # 녹화 중인 경우
                if self._recording:
                    self.record_sample()
                    
                # 대기
                time.sleep(self.sample_interval)
                
        except Exception as e:
            self.log_signal.emit(f"RTDE Thread ERR! : {str(e)}")
        finally:
            # 정리
            self.log_signal.emit("RTDE Close")

    def record_sample(self):
        """데이터 샘플 기록"""
        try:
            # 현재 timer 값 확인
            current_timer = self.rtde_r.getOutputDoubleRegister(0)
            
            # 데이터 샘플링
            timestamp = time.time()
            data = {}
            
            # 모든 레지스터를 읽고 딕셔너리에 저장
            for i in range(34):
                reg_name = register_descriptions.get(i, f"register_{i}")
                val = self.rtde_r.getOutputDoubleRegister(i)
                data[reg_name] = val
            
            # 이 시점의 데이터를 DataFrame에 추가
            df_row = pd.DataFrame(data, index=[timestamp])
            self.df = pd.concat([self.df, df_row])
            
            # 타이머 값 업데이트
            self.previous_timer = current_timer
            self.sample_count += 1
            
        except Exception as e:
            self.log_signal.emit(f"Recording ERR! : {str(e)}")

    def toggle_recording(self):
        """녹화 시작/중지 토글"""
        if not self._recording:
            # 녹화 시작
            self.df = pd.DataFrame()  # 데이터 초기화
            self.sample_count = 0
            self._recording = True
            self.log_signal.emit("RTDE Recording...")
            self.sample_count_signal.emit(0)
            return True
        else:
            # 녹화 중지
            self._recording = False
            self.log_signal.emit(f"RTDE Recording Done (Samples: {self.sample_count})")
            
            # 데이터 저장
            if not self.df.empty:
                self.save_data()
            
            return False
        
    def save_data(self):
        """데이터 저장"""
        try:
            if self.df.empty:
                self.log_signal.emit("Data is Empty!")
                return
            
            # 기본 파일명 생성 (현재 날짜/시간)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"./RTDE sample/rtde_registers_{timestamp}.csv"
            
            # CSV로 저장
            self.df.to_csv(filename)
            self.log_signal.emit(f"Data {filename}Saved: (Total {self.sample_count})")
            
        except Exception as e:
            self.log_signal.emit(f"CSV Save Err: {str(e)}")

    def stop(self):
        """쓰레드 중지"""
        self._running = False
        if self._recording:
            # 녹화 중이었다면 저장
            self.toggle_recording()