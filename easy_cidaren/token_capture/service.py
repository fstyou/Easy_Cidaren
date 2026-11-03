"""Token 捕获后端服务。"""
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from easy_cidaren.app_logging.config import Log
from easy_cidaren.token_capture.proxy_manager import ProxyManager
from easy_cidaren.token_capture.token_store import SAVED_TOKEN_FILE
from easy_cidaren.utils.executables import find_mitmdump

service_logger = Log("token_capture_service").logger


class TokenCaptureService:
    """Token 捕获服务"""
    
    def __init__(self, capture_directory):
        """
        初始化 Token 捕获服务
        
        Args:
            capture_directory: Token 捕获数据目录
        """
        self.capture_directory = capture_directory
        self.mitm_process = None
        self.proxy_manager = None
        self._is_running = False
        self._stop_requested = threading.Event( )
        self._cleanup_lock = threading.Lock( )
        self._cleaned_up = False
    
    def start_capture(self, status_callback = None, token_callback = None, error_callback = None):
        """
        开始捕获 token（同步方法，会阻塞直到捕获成功或出错）
        
        Args:
            status_callback: 状态更新回调函数 callback(message)
            token_callback: token 捕获成功回调函数 callback(token)
            error_callback: 错误回调函数 callback(error_message)
            
        Returns:
            str: 捕获到的 token，失败返回 None
        """
        if self._stop_requested.is_set( ):
            return None
        self._is_running = True
        service_logger.info("开始 token 捕获流程")
        
        try:
            self.proxy_manager = ProxyManager( )
            
            # 检查 mitmdump 是否可用
            mitmdump = find_mitmdump( )
            if not mitmdump:
                raise RuntimeError("mitmdump 未找到，请先安装 mitmproxy: pip install mitmproxy")
            
            # 检查 8888 端口是否被占用
            if self._is_port_in_use(8888):
                raise RuntimeError("端口 8888 已被占用，请关闭占用该端口的程序（如其他代理软件）后重试")
            if self._stop_requested.is_set( ):
                return None
            
            Path(self.capture_directory).mkdir(parents = True, exist_ok = True)
            token_file = Path(self.capture_directory) / SAVED_TOKEN_FILE
            try:
                stat = token_file.stat( )
                previous_version = (stat.st_ino, stat.st_mtime_ns, stat.st_size)
            except FileNotFoundError:
                previous_version = None
            
            # 启用代理
            service_logger.info("正在启用系统代理 127.0.0.1:8888")
            self.proxy_manager.enable_proxy( )
            if self._stop_requested.is_set( ):
                return None
            if status_callback:
                if sys.platform.startswith("linux"):
                    status_callback("请在目标客户端手动设置 HTTP/HTTPS 代理为 127.0.0.1:8888，结束后恢复原设置。")
            
            # 启动 mitmdump
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO( )
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            addon_path = str(Path(__file__).with_name("addon.py"))
            env = os.environ.copy( )
            env['EASY_CIDAREN_TOKEN_FILE'] = str(token_file.resolve( ))
            self.mitm_process = subprocess.Popen(
                    [
                        mitmdump,
                        "-s", addon_path,
                        "--listen-host", "127.0.0.1",
                        "--listen-port", "8888",
                        "--quiet",
                        "--set", "console_eventlog_verbosity=error"
                    ],
                    stdout = subprocess.DEVNULL,
                    stderr = subprocess.DEVNULL,
                    startupinfo = startupinfo,
                    env = env,
            )
            service_logger.info(f"mitmdump 已启动, PID={self.mitm_process.pid}")
            
            # 等待 mitmproxy 证书生成并自动导入（首次运行必需）
            self._ensure_mitm_cert_ready(status_callback)
            
            if status_callback:
                status_callback("请在微信中打开词达人学生端，等待获取 token。")
            
            # 只处理本次捕获更新的文件。
            while True:
                # 检查是否被用户停止
                if self._stop_requested.is_set( ):
                    service_logger.info("捕获已被用户停止")
                    return None
                
                # 检查进程是否还在运行
                if self.mitm_process.poll( ) is not None:
                    if self._is_running:
                        service_logger.error(f"mitmproxy 进程意外退出, exit code={self.mitm_process.returncode}")
                        if error_callback:
                            error_callback("mitmproxy 进程意外退出")
                    return None
                
                # 检查 token 文件是否有更新
                if token_file.exists( ):
                    stat = token_file.stat( )
                    current_version = (stat.st_ino, stat.st_mtime_ns, stat.st_size)
                    if current_version != previous_version:
                        previous_version = current_version
                        try:
                            with open(token_file, encoding = 'utf-8') as f:
                                token = f.read( ).strip( )
                                if token:
                                    service_logger.info("成功捕获到 UserToken")
                                    if token_callback:
                                        token_callback(token)
                                    return token
                        except Exception as e:
                            service_logger.error(f"读取 token 文件失败: {e}")
                            if error_callback:
                                error_callback(f"读取 token 文件失败: {e}")
                            return None
                
                time.sleep(0.5)
        
        except Exception as e:
            service_logger.error(f"捕获流程发生错误: {e}")
            if error_callback:
                error_callback(f"发生错误: {str(e)}")
            return None
        finally:
            self.cleanup(status_callback)
    
    @staticmethod
    def _is_port_in_use(port):
        """检测端口是否被占用"""
        try:
            with socket.create_connection(("127.0.0.1", port), timeout = 1):
                service_logger.warning(f"端口 {port} 已被占用")
                return True
        except OSError:
            return False
    
    def _ensure_mitm_cert_ready(self, status_callback = None):
        """等待 mitmproxy 首次运行生成证书并自动导入系统证书库"""
        cert_path = Path.home( ) / ".mitmproxy" / "mitmproxy-ca-cert.cer"
        deadline = time.time( ) + 15
        while time.time( ) < deadline:
            if self._stop_requested.is_set( ):
                return
            if cert_path.exists( ):
                break
            if self.mitm_process.poll( ) is not None:
                service_logger.error("mitmproxy 在生成证书前已退出")
                return
            time.sleep(0.5)
        
        if not cert_path.exists( ):
            service_logger.warning(f"等待证书生成超时: {cert_path}")
            return
        
        service_logger.info(f"mitmproxy 证书已生成: {cert_path}")
        
        # 导入证书到系统证书库（仅 Windows 支持免管理员导入）
        if sys.platform == "win32" and self.proxy_manager:
            try:
                self.proxy_manager.ensure_windows_mitm_cert( )
                service_logger.info("mitmproxy 证书导入完成")
            except Exception as e:
                service_logger.error(f"导入 mitmproxy 证书失败: {e}")
        elif sys.platform != "win32":
            service_logger.info("非 Windows 系统，请手动信任 mitmproxy 证书")
            if status_callback:
                status_callback(f"请在客户端信任 mitmproxy 证书：{cert_path}")
    
    def cleanup(self, status_callback = None):
        """清理资源（线程安全，可重复调用，只执行一次）"""
        with self._cleanup_lock:
            if self._cleaned_up:
                return
            self._cleaned_up = True
            self._is_running = False
        
        service_logger.info("开始清理捕获资源")
        
        try:
            if self.mitm_process and self.mitm_process.poll( ) is None:
                service_logger.info("正在停止 mitmproxy 进程")
                self.mitm_process.terminate( )
                try:
                    self.mitm_process.wait(timeout = 3)
                except subprocess.TimeoutExpired:
                    service_logger.warning("mitmproxy 未在 3 秒内退出，强制结束")
                    self.mitm_process.kill( )
                    self.mitm_process.wait( )
                service_logger.info(f"mitmproxy 已停止, exit code={self.mitm_process.returncode}")
        except Exception as e:
            service_logger.error(f"停止 mitmproxy 失败: {e}")
            if status_callback:
                status_callback("⛔ 无法停止 token 代理进程，请检查并手动关闭。")
        
        try:
            if self.proxy_manager:
                service_logger.info("正在恢复系统代理")
                self.proxy_manager.disable_proxy( )
                service_logger.info("系统代理已恢复")
                if status_callback:
                    if sys.platform.startswith('linux'):
                        status_callback("请恢复目标客户端中手动设置的代理。")
        except Exception as e:
            service_logger.error(f"恢复系统代理失败: {e}")
            if status_callback:
                status_callback("⛔ 代理设置恢复失败，请检查系统代理设置。")
    
    def stop(self):
        """停止捕获"""
        service_logger.info("收到停止请求")
        self._stop_requested.set( )
        self._is_running = False
