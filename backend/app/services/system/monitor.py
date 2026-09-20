# -*- coding: utf-8 -*-
'''
@文件    :oa.py
@说明    :获取系统详细信息
@时间    :2025/09/08 23:47:01
@作者    :睿
@版本    :1.0
'''
import time
import psutil
import platform
import socket
from  pathlib import Path
from app.utils.commonFunc import bytes2human


class Service:

    async def detail(self):
        cpu = self._get_cpu_info()
        memory = self._get_memory_info()
        sys = self._get_system_info()
        python = self._get_python_info()
        disk = self._get_disk_info()
        return {
            "cpu": cpu,
            "memory": memory,
            "sys": sys,
            "python": python,
            "disk": disk
        }

    def _get_cpu_info(self):
        cpu_times = psutil.cpu_times_percent()
        cpu_count = psutil.cpu_count(logical=True)
        used = cpu_times.user,
        sys = cpu_times.system,
        free = cpu_times.idle
        return {
            "used": used[0],
            "sys": sys[0],
            "free": free,
            "count": cpu_count
        }
    
    def _get_memory_info(self):
        memory = psutil.virtual_memory()
        return dict(
            total=bytes2human(memory.total),
            used=bytes2human(memory.used),
            free=bytes2human(memory.free),
            usage=memory.percent
        )
    
    def _get_system_info(self):
        hostname = socket.gethostname()
        return dict(
            computer_ip=socket.gethostbyname(hostname),
            computer_name=platform.node(),
            os_arch=platform.machine(),
            os_name=platform.platform(),
            user_dir=str(Path.cwd())
        )

    def _get_python_info(self):
        current_process = psutil.Process()
        memory = psutil.virtual_memory()
        process_memory = current_process.memory_info()
        start_time = current_process.create_time()
        run_time = self._calculate_run_time(start_time)
        return {
            "name" : current_process.name(),
            "version": platform.python_version(),
            "start_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time)),
            "run_time": run_time,
            "home": str(Path(current_process.exe())),
            "total": bytes2human(memory.available),
            "used": bytes2human(process_memory.rss),
            "free": bytes2human(memory.available - process_memory.rss),
            "usage": round((process_memory.rss / memory.available) * 100, 2)
        }

    def _get_disk_info(self):
        result = []
        for disk in psutil.disk_partitions():
            usage = psutil.disk_usage(disk.mountpoint)
            mount_point = str(Path(disk.mountpoint))
            result.append({
                "path": mount_point,
                "fstype": disk.fstype,
                "total": bytes2human(usage.total),
                "used": bytes2human(usage.used),
                "free": bytes2human(usage.free),
                "percent": usage.percent
            })
        return result
    
    def _calculate_run_time(self, start_time: float) -> str:
        """计算运行时间"""
        difference = time.time() - start_time
        days = int(difference // (24 * 60 * 60))
        hours = int((difference % (24 * 60 * 60)) // (60 * 60))
        minutes = int((difference % (60 * 60)) // 60)
        return f'{days}天{hours}小时{minutes}分钟'

service = Service()