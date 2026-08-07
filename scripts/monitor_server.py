"""
服务器监控脚本
启动服务并监控日志，自动捕获错误
"""
import subprocess
import time
import re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 启动服务
log_file = LOG_DIR / f"server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
python = r"D:\Anaconda\envs\zxf\python.exe"

print(f"启动服务...")
print(f"日志文件: {log_file}")
print(f"UI: http://127.0.0.1:5000")
print(f"API: http://127.0.0.1:8000/docs")
print("=" * 50)

# 启动服务进程
process = subprocess.Popen(
    [python, "-u", "-m", "api.main"],
    cwd=str(ROOT),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# 错误模式
error_patterns = [
    r"Traceback",
    r"Error:",
    r"Exception:",
    r"FAILED",
    r"404",
    r"500",
    r"ERR_",
]

# 监控日志
with open(log_file, "w", encoding="utf-8") as f:
    try:
        for line in process.stdout:
            timestamp = datetime.now().strftime("%H:%M:%S")
            line = line.strip()
            
            # 写入日志文件
            f.write(f"[{timestamp}] {line}\n")
            f.flush()
            
            # 检查是否是错误
            is_error = any(re.search(pattern, line, re.IGNORECASE) for pattern in error_patterns)
            
            if is_error:
                print(f"\n{'='*50}")
                print(f"[ERROR DETECTED] {timestamp}")
                print(f"{line}")
                print(f"{'='*50}\n")
            else:
                # 只打印重要信息
                if any(key in line for key in ["INFO", "WARNING", "Running", "startup", "Error"]):
                    print(f"[{timestamp}] {line}")
                    
    except KeyboardInterrupt:
        print("\n停止监控...")
        process.terminate()
