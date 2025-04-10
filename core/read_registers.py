import asyncio
from pymodbus.client import AsyncModbusTcpClient
from datetime import datetime
from typing import Callable

class RobotMonitor:
    def __init__(self, host='192.168.225.178', port=502, callback: Callable[[str], None] = None):
        self.client = AsyncModbusTcpClient(
            host=host,
            port=port,
        )
        self.previous_values = {}
        self.callback = callback or print  # 콜백이 없으면 print 사용
        self.running = True
        
    async def connect(self):
        await self.client.connect()
        self.callback("Modbus Server Conneted")
    
    async def read_registers(self, address, count):
        try:
            result = await self.client.read_holding_registers(
                address=address,
                count=count
            )
            if not result.isError():
                return result.registers
            return None
        except Exception as e:
            self.callback(f"Register Read ERR: {e}")
            return None

    def check_changes(self, start_addr, current_values):
        changes = {}
        for i, value in enumerate(current_values):
            addr = start_addr + i
            if addr == 128 or addr ==161 or addr ==211:
                continue
            if addr not in self.previous_values or self.previous_values[addr] != value:
                changes[addr] = value
                self.previous_values[addr] = value
        return changes

    async def monitor_loop(self):
        ranges = [
            (128, 125),  # 첫 번째 범위: 128-252
            (253, 3)     # 두 번째 범위: 253-255
        ]
        
        try:
            while self.running:
                all_changes = {}
                
                for start_addr, count in ranges:
                    values = await self.read_registers(start_addr, count)
                    if values:
                        changes = self.check_changes(start_addr, values)
                        all_changes.update(changes)
                
                if all_changes:
                    # self.callback(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    self.callback("\n")
                    for addr, value in sorted(all_changes.items()):
                        self.callback(f"Register {addr}: {value}")
                
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.callback(f"Monitoring ERR!: {e}")
            
        finally:
            await self.client.close()
    
    def stop(self):
        self.running = False

async def main():
    monitor = RobotMonitor(host="192.168.1.7")
    try:
        await monitor.connect()
        await monitor.monitor_loop()
    except KeyboardInterrupt:
        print("\nClose Monitoring.")
    finally:
        await monitor.client.close()

if __name__ == "__main__":
    asyncio.run(main())