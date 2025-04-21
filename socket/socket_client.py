import asyncio
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal

class SocketClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.callback = None
        self.connected = False
        self.running = True
        
    def set_callback(self, callback):
        """콜백 함수 설정"""
        self.callback = callback
        
    async def connect(self):
        """서버에 연결"""
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.connected = True
            
            if self.callback:
                self.callback(f"server Connected: {self.host}:{self.port}")
                
            return True
        except Exception as e:
            if self.callback:
                self.callback(f"Server connection failed: {str(e)}")
            return False
            
    async def receive_messages(self):
        """서버로부터 메시지 수신"""
        try:
            while self.running and self.connected:
                try:
                    data = await asyncio.wait_for(self.reader.read(4096), timeout=0.1)
                    if not data:
                        if self.callback:
                            self.callback("Connection Closed.")
                        self.connected = False
                        break
                    
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    message = data.decode('utf-8', errors='replace')
                    
                    if self.callback:
                        self.callback(f"[{timestamp}] Recieved: {message}")
                except asyncio.TimeoutError:
                    # 타임아웃은 정상적인 상황
                    pass
                except Exception as e:
                    if self.callback:
                        self.callback(f"Recieve ERR: {str(e)}")
                    self.connected = False
                    break
                
                # CPU 사용량 감소를 위한 짧은 대기
                await asyncio.sleep(0.01)
        except Exception as e:
            if self.callback:
                self.callback(f"Recieve thread ERR: {str(e)}")
            self.connected = False
    
    async def disconnect(self):
        """서버와 연결 종료"""
        self.running = False
        if self.connected and self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
                
                if self.callback:
                    self.callback("서버와의 연결을 종료했습니다.")
            except Exception as e:
                if self.callback:
                    self.callback(f"연결 종료 오류: {str(e)}")
        
        self.connected = False

class SocketClientThread(QThread):
    log_signal = pyqtSignal(str)
    connection_status_signal = pyqtSignal(bool)  # 연결 상태 신호
    
    def __init__(self, host='127.0.0.1', port=12345):
        super().__init__()
        self.host = host
        self.port = port
        self.client = SocketClient(host, port)
        self.client.set_callback(self.process_message)
        self._loop = None
        self._running = True
        
    def run(self):
        """쓰레드 시작 메서드"""
        # 새 이벤트 루프 생성
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        # 클라이언트 실행
        self._loop.run_until_complete(self.run_client())
    
    async def run_client(self):
        """클라이언트 실행"""
        # 서버에 연결
        success = await self.client.connect()
        
        # 연결 상태 신호 전송
        self.connection_status_signal.emit(success)
        
        if success:
            # 메시지 수신 태스크 시작
            receive_task = asyncio.create_task(self.client.receive_messages())
            
            # 스레드가 종료될 때까지 대기
            try:
                while self._running and self.client.connected:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                pass
            finally:
                # 태스크 취소
                receive_task.cancel()
                try:
                    await receive_task
                except asyncio.CancelledError:
                    pass
                
                # 연결 종료
                await self.client.disconnect()
        
    def process_message(self, message):
        """클라이언트 메시지 처리"""
        self.log_signal.emit(message)
        
        # 연결 상태 변경 감지
        if "연결되었습니다" in message:
            self.connection_status_signal.emit(True)
        elif "연결이 종료되었습니다" in message or "연결 실패" in message:
            self.connection_status_signal.emit(False)
        
    def stop(self):
        """쓰레드 중지"""
        self._running = False
        if self._loop:
            asyncio.run_coroutine_threadsafe(self.cleanup(), self._loop)
    
    async def cleanup(self):
        """정리 작업"""
        await self.client.disconnect()