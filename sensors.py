import psutil
import time

from typing import Dict, List, Tuple


class BAT:
    def __init__(self):
        # percent, secs_left, power_plugged
        self.bat: Tuple[float, int, bool] = (0.0, 0, False)

        self.update()

    def update(self) -> None:
        b = psutil.sensors_battery()
        self.bat = (b.percent, b.secsleft, b.power_plugged)

    def __str__(self) -> str:
        return f"{self.bat}\n"


class CPU:
    def __init__(self):
        self.cpu_count = psutil.cpu_count(logical=True)

        self.cpu_usage = 0.0
        self.cpu_usage_core: List[float] = [0.0 for _ in range(self.cpu_count)]
        self.cpu_freq = 0.0
        self.cpu_freq_core: List[float] = [0.0 for _ in range(self.cpu_count)]

        self.update()

    def update(self) -> None:
        self.cpu_usage = psutil.cpu_percent(percpu=False)
        self.cpu_usage_core = psutil.cpu_percent(percpu=True)
        self.cpu_freq = psutil.cpu_freq(percpu=False).current
        self.cpu_freq_core = [ i.current for i in psutil.cpu_freq(percpu=True) ]

    def __str__(self) -> str:
        return (f'CPU Cores: {self.cpu_count}\n'
                f'CPU Usage: {self.cpu_usage}\n'
                f'CPU Usage Core: {self.cpu_usage_core}\n'
                f'CPU Frequency: {self.cpu_freq}\n'
                f'CPU Frequency Core: {self.cpu_freq_core}\n')


class FAN:
    def __init__(self):
        self.fans = {}
        self.update()

    def update(self) -> None:
        self.fans = psutil.sensors_fans()

    def __str__(self) -> str:
        return f"{self.fans}\n"


class NET:
    def __init__(self):
        c = psutil.net_io_counters()

        self.bytes_sent = c.bytes_sent
        self.bytes_recv = c.bytes_recv
        self.bytes_time = time.time()
        self.bytes_sent_old = self.bytes_sent
        self.bytes_recv_old = self.bytes_recv
        self.bytes_time_old = self.bytes_time

        self.rate_sent = 0.0
        self.rate_recv = 0.0

    def update(self) -> None:
        c = psutil.net_io_counters()

        self.bytes_sent_old = self.bytes_sent
        self.bytes_recv_old = self.bytes_recv
        self.bytes_time_old = self.bytes_time

        self.bytes_sent = c.bytes_sent
        self.bytes_recv = c.bytes_recv
        self.bytes_time = time.time()

        self.rate_sent = (c.bytes_sent - self.bytes_sent_old) / (self.bytes_time - self.bytes_time_old)
        self.rate_recv = (c.bytes_recv - self.bytes_recv_old) / (self.bytes_time - self.bytes_time_old)

    def __str__(self) -> str:
        return (f'Network Bytes Sent: {self.bytes_sent}\n'
                f'Network Bytes Received: {self.bytes_recv}\n'
                f'Network Bytes Sent Rate: {self.rate_sent}\n'
                f'Network Bytes Received Rate: {self.rate_recv}\n')


class TEMP:
    def __init__(self, fahrenheit: bool = False):
        # (name, label, current)
        self.psutil_temp: Dict[str, List[Tuple[str, float]]] = {}
        self.fahrenheit = fahrenheit

        self.update()

    def update(self) -> None:
        sensors = {}

        for t in psutil.sensors_temperatures(fahrenheit=self.fahrenheit).items():
            sensors[t[0]] = [ (f"id {k}" if t[1][k].label == "" else t[1][k].label, t[1][k].current) for k in range(len(t[1])) ]

        self.psutil_temp = sensors

    def __str__(self) -> str:
        return f"{self.psutil_temp}\n"


if __name__ == "__main__":
    cpu = CPU()
    net = NET()
    temp = TEMP()
    fan = FAN()
    bat = BAT()
    time.sleep(1)
    net.update()

    print(cpu)
    print(net)
    print(temp)
    print(bat)
    print(fan)
