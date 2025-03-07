import sys
import asyncio
from datetime import datetime
import re
import ast  # 문자열을 리스트로 변환하기 위한 모듈
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QTextEdit, QPushButton, QLabel, QSpinBox, QFileDialog, QGroupBox,
                           QCheckBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt

class PoseParser:
    """UR이 전송하는 A_ 시작 메시지 파싱 클래스"""
    def __init__(self, callback=None):
        self.prepos_data = []  # A_prepos_l 데이터
        self.touch_data = []   # A_touch_p 데이터
        self.callback = callback  # 콜백 함수 저장

    def set_callback(self, callback):
        """콜백 함수 설정"""
        self.callback = callback

    def parse_pose_line(self, line):
        """단일 포즈 라인 파싱"""
        try:
            # 변수명과 데이터 분리
            var_name, data_part = line.split(':', 1)
            var_name = var_name.strip()

            # 여러 줄 문자열을 한 줄로 정리
            data_part = ' '.join(data_part.split())
            
            # p[] 형식을 []로 변환
            data_part = data_part.strip().replace('p[', '[')
            poses = ast.literal_eval(data_part)
            
            return var_name, poses
            
        except Exception as e:
            if self.callback:
                self.callback(f"포즈 라인 파싱 오류: {e}")
            return None, None
        
    def _format_poses(self, name, poses):
        """파싱된 포즈 데이터 포맷팅"""
        result = [f"\n=== {name} ==="]
        for i, pose in enumerate(poses):
            if any(pose):  # 0이 아닌 값이 있는 경우
                meaning = self.get_pose_meaning(i)
                result.append(f"{meaning}: {pose}")
        return "\n".join(result)
                
    def parsing_poses(self, messages):
        """전체 메시지를 파싱하여 각 변수별로 분리"""
        result = []
        
        try:
            # 줄바꿈으로 메시지 분리
            lines = messages.strip().split('\n')
            
            current_line = ""
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith(("A_prepos_l:", "A_touch_p:")):
                    if current_line:  # 이전 줄 처리
                        parsed = self.process_line(current_line)
                        if parsed:
                            result.append(parsed)
                    current_line = line
                else:
                    current_line += " " + line
            
            # 마지막 줄 처리
            if current_line:
                parsed = self.process_line(current_line)
                if parsed:
                    result.append(parsed)
            
            # 결과 반환
            return "\n".join(result)

        except Exception as e:
            if self.callback:
                self.callback(f"파싱 오류: {e}")
            return None
        
    def process_line(self, line):
        """하나의 완성된 라인 처리"""
        if line.startswith("A_prepos_l:") or line.startswith("A_touch_p:"):
            var_name, poses = self.parse_pose_line(line)
            if var_name == "A_prepos_l":
                self.prepos_data = poses
                return self._format_poses("A_prepos_l", poses)
            elif var_name == "A_touch_p":
                self.touch_data = poses
                return self._format_poses("A_touch_p", poses)
        return None
        
    def get_pose_meaning(self, index):
        """포즈 인덱스의 의미 반환"""
        pose_meanings = {
            1: "A_VL1",        # 좌측 수직상향 1패스 준비자세
            2: "A_VL2",        # 좌측 수직상향 2패스 준비자세
            3: "A_VR1",        # 우측 수직상향 1패스 준비자세
            4: "A_VR2",        # 우측 수직상향 2패스 준비자세
            5: "A_HOR_L",      # 좌측 수평 기본 준비자세
            6: "A_HOR_ML",     # 좌측 수평 중앙 준비자세
            7: "A_HOR_R",      # 우측 수평 기본 준비자세
            8: "A_HOR_MR",     # 우측 수평 중앙 준비자세
            9: "A_HOR_M",      # 수평 중앙 준비자세
            10: "A_VL1_END",   # 좌측 수직 1패스 종료점 준비자세
            11: "A_VL2_END",   # 좌측 수직 2패스 종료점 준비자세
            12: "A_VR1_END",   # 우측 수직 1패스 종료점 준비자세
            13: "A_VR2_END"    # 우측 수직 2패스 종료점 준비자세
        }

        return pose_meanings.get(index, f"미사용 포즈 ({index})")

