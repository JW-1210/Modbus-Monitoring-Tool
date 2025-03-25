import asyncio
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
from .utils import PoseParser

class SocketServer:
    def __init__(self, host='0.0.0.0', port=12345):
        self.host = host
        self.port = port
        self.callback = None
        self.server = None
        self.running = True
        self.buffer = ""  # 메시지 버퍼 추가
        self.pose_parser = PoseParser()  # 포즈 파서 추가
        
    def set_callback(self, callback):
        """콜백 함수 설정"""
        self.callback = callback
        self.pose_parser.set_callback(callback)

    async def start(self):
        """소켓 서버 시작"""
        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        
        addr = self.server.sockets[0].getsockname()
        if self.callback:
            self.callback(f"Socket Server Started {addr[0]}:{addr[1]}")
        
        async with self.server:
            await self.server.serve_forever()
            
    async def handle_client(self, reader, writer):
        """클라이언트 연결 처리"""
        addr = self.server.sockets[0].getsockname()
        if self.callback:
            self.callback(f"클라이언트 연결 수락: {addr[0]}:{addr[1]}")
            
        # 버퍼 초기화
        self.buffer = ""

        try:
            while self.running:
                data = await reader.read(4096)
                if not data:
                    break
                    
                timestamp = datetime.now().strftime('%H:%M:%S')
                message = data.decode('utf-8', errors='replace')

                # 버퍼에 추가
                self.buffer += message

                # 완전한 메시지 처리 (줄바꿈으로 구분)
                messages = self.process_buffer()
                
                # 각 메시지 별로 콜백 호출
                for message in messages:
                    if self.callback:
                        # A_로 시작하는 메시지는 별도 처리
                        if message.startswith("A_"):
                            parsed = self.pose_parser.parsing_poses(message)
                            if parsed:
                                # self.callback(f"[{timestamp}] {addr[0]}:{addr[1]} \n {message}")
                                self.callback(parsed)
                        else:
                            self.callback(f"\n [{timestamp}] {addr[0]}:{addr[1]} \n {message}\n")
                        
                # 잠시 대기 (CPU 사용량 감소)
                await asyncio.sleep(0.01)    

        except (ConnectionResetError, asyncio.CancelledError):
            if self.callback:
                self.callback(f"연결 종료: {type(e).__name__} - {str(e)}")

        except Exception as e:
            if self.callback:
                self.callback(f"소켓 오류: {type(e).__name__} - {str(e)}")
                
        finally:
            writer.close()
            await writer.wait_closed()
            if self.callback:
                self.callback(f"클라이언트 연결 종료: {addr[0]}:{addr[1]}")

    def process_buffer(self):
        """버퍼에서 완전한 메시지 추출"""
        messages = []
        
        # A_로 시작하는 특별한 메시지 처리
        if "A_" in self.buffer:
            # 완전한 메시지인지 확인 (대괄호 쌍 개수 체크)
            if all(x in self.buffer for x in ["A_", "["]) and self.buffer.count("[") == self.buffer.count("]"):
                # 메시지가 완전하다고 판단
                messages.append(self.buffer)
                self.buffer = ""  # 버퍼 비우기
                return messages
        
        # 일반 메시지는 줄바꿈으로 구분
        lines = self.buffer.split('\n')
        
        # 마지막 줄은 불완전할 수 있으므로 버퍼에 유지
        if len(lines) > 1:
            messages = lines[:-1]
            self.buffer = lines[-1]
        
        return messages
    
    def stop(self):
        """서버 중지"""
        self.running = False
        if self.server:
            self.server.close()

        # 현재 실행 중인 모든 태스크를 강제 취소
        for task in asyncio.all_tasks(asyncio.get_event_loop()):
            if task is not asyncio.current_task():
                task.cancel()

class SocketMonitorThread(QThread):
    log_signal = pyqtSignal(str)
    
    def __init__(self, host='0.0.0.0', port=12345):
        super().__init__()
        self.host = host
        self.port = port
        self.socket_server = SocketServer(host, port)
        self.socket_server.set_callback(self.process_message)
        self._loop = None
        self._running = True
        self.server_started = True
        
    def run(self):
        """쓰레드 시작 메서드"""
        # 새 이벤트 루프 생성
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        # 서버 시작
        try:
            self._loop.run_until_complete(self.socket_server.start())
            
        except OSError as e:
            # 바인딩 오류 발생 시 로그에 메시지 전송
            error_msg = f"소켓 서버 시작 실패: {str(e)}. IP 주소({self.host})가 유효하지 않거나 이미 사용 중일 수 있습니다."
            self.log_signal.emit(error_msg)
            self.server_started = False

        except asyncio.CancelledError:
            pass
        
    def process_message(self, message):
        """소켓 메시지 처리"""
        self.log_signal.emit(message)
        
    def stop(self):
        """쓰레드 중지"""
        self._running = False

        if self._loop:
            try:
                if self._loop and self.socket_server:
                    asyncio.run_coroutine_threadsafe(self.cleanup(), self._loop)
                else:
                    # 서버가 시작되지 않았다면 loop 종료
                    self._loop.call_soon_threadsafe(self._loop.stop)
            
            except Exception as e:
                pass
            
    async def cleanup(self):
        """정리 작업"""
        self.socket_server.stop()