import asyncio
import re
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
from .read_registers import RobotMonitor

class MonitorThread(QThread):
    log_signal = pyqtSignal(str)
    register_update_signal = pyqtSignal(int, int)  # 레지스터 주소, 값
    request_read_register_signal = pyqtSignal(int)  # 읽을 레지스터 주소
    register_write_result_signal = pyqtSignal(int, bool)  # 쓰기 결과 시그널 (주소, 성공여부)

    def __init__(self, host, port=502):
        super().__init__()
        self.host = host
        self.port = port
        self.monitor = None
        self._reset_requested = False
        self._monitored_registers = set()  # 모니터링할 레지스터 집합
        self._last_values = {}  # 마지막으로 읽은 값을 저장
        self._pending_registers = set()  # 읽기가 요청된 레지스터

        # 자체 이벤트 루프 생성
        self._loop = None
    
    def run(self):
        
        # 새 이벤트 루프 생성
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        # 읽기 요청 시그널 연결
        self.request_read_register_signal.connect(self.handle_read_request)

        # 모니터링 실행
        # asyncio.run(self.run_monitor())
        self._loop.run_until_complete(self.run_monitor())

    def write_register_value(self, register, value):
        """레지스터에 값을 쓰는 메서드"""
        # 백그라운드에서 비동기 작업 실행
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._write_register_value(register, value), 
                self._loop
            )
            
    async def _write_register_value(self, register, value):
        """실제 비동기로 레지스터에 값을 쓰는 내부 메서드"""
        if not self.monitor or not self.monitor.client or not self.monitor.client.connected:
            self.log_signal.emit(f"모드버스 연결이 활성화되지 않았습니다. 레지스터 {register}에 {value} 쓰기 실패.")
            self.register_write_result_signal.emit(register, False)
            return
        
        try:
            # 클라이언트로 레지스터 쓰기
            await self.monitor.client.write_register(
                address=register,
                value=value
            )

            # 성공 로그
            self.log_signal.emit(f"레지스터 {register}에 값 {value} 쓰기 성공")
            
            # 쓰기 후 값 업데이트를 위해 읽기
            result = await self.monitor.read_registers(register, 1)
            if result:
                # 로그에 값 추가
                self.log_signal.emit(f"레지스터 {register} 값 확인: {result[0]}")
                # 값 캐시 및 UI 업데이트
                self._last_values[register] = result[0]
                self.register_update_signal.emit(register, result[0])
            
            # 쓰기 성공 시그널
            self.register_write_result_signal.emit(register, True)

        except Exception as e:
            self.log_signal.emit(f"레지스터 {register}에 값 {value} 쓰기 실패: {str(e)}")
            self.register_write_result_signal.emit(register, False)
            pass
        
    async def run_monitor(self):
        self.monitor = RobotMonitor(
            host=self.host, 
            port=self.port,
            callback=self.process_monitor_message
        )
        await self.monitor.connect()
        
        # 자체 실행 상태 변수 추가
        self._running = True
        
        # 초기화 요청 처리 및 레지스터 모니터링 루프
        while self._running:
            if self._reset_requested:
                await self.do_reset_registers()
                self._reset_requested = False
            
            # 지정된 레지스터 값 읽기
            if  self._pending_registers and self.monitor and self.monitor.client and self.monitor.client.connected:
                for monitor_register in list(self._monitored_registers):
                    try:
                        # 단일 레지스터 읽기 (주소, 개수)
                        result = await self.monitor.read_registers(monitor_register, 1)

                        if result and hasattr(self, '_last_values'):
                            # 값이 변경되었을 때만 신호 보내기
                            if monitor_register not in self._last_values or self._last_values[monitor_register] != result[0]:
                                self._last_values[monitor_register] = result[0]
                                self.register_update_signal.emit(monitor_register, result[0])

                        else:
                            # 최초 읽기 시에는 항상 업데이트
                            if not hasattr(self, '_last_values'):
                                self._last_values = {}
                            self._last_values[monitor_register] = result[0]
                            self.register_update_signal.emit(monitor_register, result[0])

                    except Exception as e:
                        self.log_signal.emit(f"레지스터 {monitor_register} 읽기 오류: {str(e)}")

                for register in list(self._pending_registers):
                    try:
                        # 레지스터 읽기
                        result = await self.monitor.read_registers(register, 1)
                        if result:
                            self.register_update_signal.emit(register, result[0])
                            self._last_values[register] = result[0]
                            # self.log_signal.emit(f"레지스터 {register}의 초기값: {result[0]}")
                            self._pending_registers.remove(register)
                    except Exception as e:
                        self.log_signal.emit(f"레지스터 {register} 읽기 오류: {str(e)}")
                        self._pending_registers.remove(register)  # 오류나도 제거
            
            try:
                # 짧은 시간 동안만 monitor_loop 실행
                monitor_task = asyncio.create_task(self.run_monitor_once())
                await asyncio.wait_for(monitor_task, timeout=0.5)  # 레지스터 업데이트 주기

            except asyncio.TimeoutError:
                pass

            except Exception as e:
                self.log_signal.emit(f"모니터링 오류: {str(e)}")
                await asyncio.sleep(1)  # 오류 발생 시 잠시 대기
            
            # 잠시 대기
            await asyncio.sleep(0.5)
            
    async def run_monitor_once(self):
        """RobotMonitor의 한 주기만 실행"""
        # 범위 (128-255) 값 읽기 및 변경사항 감지
        ranges = [
            (128, 125),  # 첫 번째 범위: 128-252
            (253, 3)     # 두 번째 범위: 253-255
        ]
        
        all_changes = {}
        for start_addr, count in ranges:
            try:
                values = await self.monitor.read_registers(start_addr, count)
                if values:
                    changes = self.check_changes(start_addr, values)
                    all_changes.update(changes)
            except Exception as e:
                self.log_signal.emit(f"범위 읽기 오류 ({start_addr}-{start_addr+count-1}): {str(e)}")
        
        # 변경 사항이 있으면 로그로 출력
        if all_changes:
            # timestamp = datetime.now().strftime('%H:%M:%S')
            # self.log_signal.emit(f"\n[{timestamp}] 값 변경 감지:")
            self.log_signal.emit(f"\n")
            for addr, value in sorted(all_changes.items()):
                self.log_signal.emit(f"주소 {addr}: {value}")
                
                # 모니터링 중인 레지스터는 UI도 갱신
                if addr in self._monitored_registers:
                    self.register_update_signal.emit(addr, value)
    
    def check_changes(self, start_addr, current_values):
        """값 변경 감지 메서드"""
        changes = {}
        for i, value in enumerate(current_values):
            addr = start_addr + i
            # 128, 161, 211은 제외 (RobotMonitor 클래스와 동일하게 처리)
            if addr == 128 or addr == 161 or addr == 211:
                continue
            if addr not in self._last_values or self._last_values[addr] != value:
                changes[addr] = value
                self._last_values[addr] = value
        return changes

    async def do_reset_registers(self):
        try:
            if self.monitor and self.monitor.client and self.monitor.client.connected:
                # 레지스터 범위 128-255까지 초기화
                start_address = 128
                count = 128  # 128부터 255까지 (총 128개)

                # 레지스터 초기화 로그
                self.log_signal.emit(f"레지스터 {start_address}-{start_address+count-1} 초기화 시작...")
                
                 # 한 번에 여러 레지스터 쓰기 시도
                try:
                    # 배열로 한 번에 쓰기 시도
                    registers = [0] * count
                    await self.monitor.client.write_registers(
                        address=start_address,
                        values=registers
                    )
                    self.log_signal.emit(f"레지스터 {start_address}-{start_address+count-1} 일괄 초기화 완료")
                except Exception as bulk_error:
                    # 실패하면 개별적으로 쓰기
                    self.log_signal.emit(f"일괄 초기화 실패, 개별 초기화로 전환: {str(bulk_error)}")
                    
                    for i in range(count):
                        addr = start_address + i
                        try:
                            # 단일 레지스터 쓰기
                            await self.monitor.client.write_register(
                                address=addr,
                                value=0
                            )
                        except Exception as e:
                            self.log_signal.emit(f"레지스터 {addr} 초기화 오류: {str(e)}")
                
                self.log_signal.emit(f"레지스터 초기화 완료")
            else:
                self.log_signal.emit("모드버스 연결이 활성화되지 않았습니다.")
        except Exception as e:
            self.log_signal.emit(f"레지스터 초기화 중 오류 발생: {str(e)}")
    
    def reset_registers(self):
        self._reset_requested = True
    
    def add_monitored_register(self, register):
        """모니터링할 레지스터 추가"""
        if register not in self._monitored_registers:
            self._monitored_registers.add(register)
            # 읽기 요청 신호 발생 - 스레드 안전한 방식
            self.request_read_register_signal.emit(register)
            self.log_signal.emit(f"레지스터 {register} 모니터링 시작")

        # If there's already deleted _last_values entry, then delete
        if register in self._last_values:
            del self._last_values[register]

    def handle_read_request(self, register):
        """레지스터 읽기 요청 처리 - 스레드 안전한 슬롯"""
        self._pending_registers.add(register)
    
    def remove_monitored_register(self, register):
        """모니터링할 레지스터 제거"""
        if register in self._monitored_registers:
            self._monitored_registers.remove(register)
            self.log_signal.emit(f"레지스터 {register} 모니터링 중지")
        # if register in self._last_values:
        #     del self._last_values[register]

    def process_monitor_message(self, msg):
        """모니터링 메시지 처리 - 레지스터 값 변경 감지 및 로그 출력"""
        self.log_signal.emit(msg)
        
        # 레지스터 값 변경 메시지 처리
        if msg.strip() and "주소" in msg and ":" in msg:
            try:
                # "주소 130: 42" 형식의 메시지에서 레지스터 주소와 값 추출
                parts = msg.split(":")
                addr_part = parts[0].strip()
                value_part = parts[1].strip()
                # 숫자만 추출
                register_match = re.search(r'\d+', addr_part)
                if register_match:
                    register = int(register_match.group())
                    value = int(value_part)
                    
                    # 모니터링 중인 레지스터인 경우 UI 업데이트
                    if register in self._monitored_registers:
                        # 값이 변경된 경우에만 업데이트
                        if register not in self._last_values or self._last_values[register] != value:
                            self._last_values[register] = value
                            self.register_update_signal.emit(register, value)

            except (ValueError, IndexError) as e:
                # 숫자 변환 실패 등의 오류는 무시
                pass
    
    def stop(self):
        self._running = False
        if self._loop:
            # 이벤트 루프 중지
            asyncio.run_coroutine_threadsafe(self.cleanup(), self._loop)

    async def cleanup(self):
        # 필요한 정리 작업
        if self.monitor:
            try:
                self.monitor.stop()
                await self.monitor.client.close()
            except:
                pass
    
    def run_monitor_once_manual(self):
        """사용자 요청으로 모니터링 한 번 실행"""
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._run_monitor_once_manual(), self._loop)

    async def _run_monitor_once_manual(self):
        """비동기 모니터링 한 번 실행"""
        try:

            # 직접 레지스터 범위를 읽어 출력
            ranges = [
                (128, 125),  # 첫 번째 범위: 128-252
                (253, 3)     # 두 번째 범위: 253-255
            ]

            for start_addr, count in ranges:
                try:
                    values = await self.monitor.read_registers(start_addr, count)

                    if values:
                        for i, value in enumerate(values):
                            addr = start_addr + i
                            self.log_signal.emit(f"주소 {addr}: {value}")

                            # 모니터링 중인 레지스터는 UI도 갱신
                            if addr in self._monitored_registers:
                                self._last_values[addr] = value
                                self.register_update_signal.emit(addr, value)

                except Exception as e:
                    self.log_signal.emit(f"범위 읽기 오류 ({start_addr}-{start_addr+count-1}): {str(e)}")

        except Exception as e:
            self.log_signal.emit(f"레지스터 출력 중 오류 발생: {str(e)}")
            # pass

