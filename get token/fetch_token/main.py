import os
import subprocess
import sys
from pathlib import Path

# 直接运行子目录脚本时，确保能导入项目根目录下的公共模块。
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from proxy_manager import ProxyManager
from log.log import Log
from util.executables import find_mitmdump

# init log
main_logger = Log("fetch_token_main")

proxy = ProxyManager()
main_logger.logger.info("")

try:
    main_logger.logger.info("正在自动配置代理...")
    # 检查 mitmdump 是否可用
    mitmdump = find_mitmdump()
    if not mitmdump:
        raise RuntimeError("mitmdump 未找到，请先安装 mitmproxy: pip install mitmproxy")
    proxy.enable_proxy()
    if sys.platform.startswith("linux"):
        main_logger.logger.info("请在目标客户端手动设置 HTTP/HTTPS 代理为 127.0.0.1:8888，结束后恢复原设置。")
    if sys.platform != "win32":
        main_logger.logger.info("请在目标客户端手动信任 ~/.mitmproxy/mitmproxy-ca-cert.cer。")

    main_logger.logger.info("启动 mitmproxy...")

    # 在 Windows 上隐藏子进程窗口和错误输出
    startupinfo = None
    if sys.platform == 'win32':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    mitm = subprocess.Popen(
        [
            mitmdump,
            "-s", str(SCRIPT_DIR / "addon.py"),
            "--listen-port", "8888",
            "--quiet",
            "--set", "console_eventlog_verbosity=error"
        ],
        stderr=subprocess.DEVNULL,  # 隐藏 asyncio 异常
        startupinfo=startupinfo
    )

    main_logger.logger.info("请打开 PC 微信并访问授权链接...")
    main_logger.logger.info("程序将持续运行以监听 UserToken 更新，按 Ctrl+C 可退出程序\n")

    # 持续运行，直到用户手动中断
    try:
        mitm.wait()
    except KeyboardInterrupt:
        mitm.terminate()
        try:
            mitm.wait(timeout=3)
        except subprocess.TimeoutExpired:
            mitm.kill()
            mitm.wait()

except KeyboardInterrupt:
    main_logger.logger.warning("用户中断")
    if 'mitm' in locals():
        mitm.terminate()
        try:
            mitm.wait(timeout=3)
        except subprocess.TimeoutExpired:
            mitm.kill()
            mitm.wait()

finally:
    proxy.disable_proxy()
    main_logger.logger.info("已完成，可关闭窗口。")
