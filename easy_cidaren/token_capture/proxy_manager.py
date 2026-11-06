import hashlib
import platform
import re
import ssl
import subprocess
from pathlib import Path

from easy_cidaren.app_logging.config import get_logger

if platform.system( ) == "Windows":
    import winreg

proxy_logger = get_logger("proxy_manager")


class ProxyManager:
    def __init__(self):
        self.os = platform.system( )
        self.original_settings = {}  # 保存原始代理设置
    
    @staticmethod
    def _get_network_services( ):
        """获取 macOS 网络服务列表"""
        output = subprocess.check_output(
                ["networksetup", "-listallnetworkservices"],
                text = True
        )
        return [s for s in output.splitlines( )[1:] if not s.startswith("*")]
    
    @staticmethod
    def _get_proxy_info(service):
        """获取指定服务的当前代理设置"""
        try:
            # 获取 HTTP 代理
            web_output = subprocess.check_output(
                    ["networksetup", "-getwebproxy", service],
                    text = True
            )
            # 获取 HTTPS 代理
            secure_output = subprocess.check_output(
                    ["networksetup", "-getsecurewebproxy", service],
                    text = True
            )
            
            settings = {}
            for kind, output in (('web', web_output), ('secure', secure_output)):
                enabled = re.search(r'^Enabled:[ \t]*(Yes|No)[ \t]*$', output, re.MULTILINE)
                host = re.search(r'^Server:[ \t]*(.*?)[ \t]*$', output, re.MULTILINE)
                port = re.search(r'^Port:[ \t]*(\d+)[ \t]*$', output, re.MULTILINE)
                if not enabled:
                    raise ValueError(f'{kind} 代理状态无法读取')
                is_enabled = enabled.group(1) == 'Yes'
                if is_enabled and (not host or not host.group(1) or not port or int(port.group(1)) == 0):
                    raise ValueError(f'{kind} 代理缺少地址或端口')
                settings.update({f'{kind}_enabled': is_enabled,
                                 f'{kind}_host': host.group(1) if host else '',
                                 f'{kind}_port': port.group(1) if port else ''})
            return settings
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            proxy_logger.error("读取 macOS 代理设置失败：%s", exc)
            return None
    
    @staticmethod
    def _get_windows_proxy_settings( ):
        """获取 Windows 当前的代理设置"""
        try:
            with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                    0,
                    winreg.KEY_READ
            ) as key:
                try:
                    proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                except FileNotFoundError:
                    proxy_enable = 0
                try:
                    proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
                except FileNotFoundError:
                    proxy_server = ""
                try:
                    proxy_override, _ = winreg.QueryValueEx(key, "ProxyOverride")
                except FileNotFoundError:
                    proxy_override = ""
            
            return {
                'enabled': bool(proxy_enable),
                'server': proxy_server,
                'override': proxy_override
            }
        except Exception as e:
            proxy_logger.error(f"读取代理设置失败: {e}")
            return None
    
    @staticmethod
    def _set_windows_proxy_settings(enabled, server = "", override = "<local>"):
        """设置 Windows 代理"""
        try:
            with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                    0,
                    winreg.KEY_WRITE
            ) as key:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1 if enabled else 0)
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, server)
                winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, override)
            
            # 通知系统代理设置已更改
            import ctypes
            INTERNET_OPTION_SETTINGS_CHANGED = 39
            INTERNET_OPTION_REFRESH = 37
            internet_set_option = getattr(ctypes.windll.Wininet, 'InternetSetOptionW')
            internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
            internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0)
            
            return True
        except Exception as e:
            proxy_logger.error(f"设置代理失败: {e}")
            return False
    
    @staticmethod
    def _windows_store_has_cert(store_name, fingerprint):
        """检测指定证书存储是否已有 mitmproxy 证书"""
        try:
            ps_cmd = (
                f"(Get-ChildItem -Path Cert:\\CurrentUser\\{store_name} "
                f"| Where-Object {{$_.Thumbprint -eq '{fingerprint}'}} | Measure).Count"
            )
            result = subprocess.run(
                    ["powershell", "-NoLogo", "-NoProfile", "-Command", ps_cmd],
                    capture_output = True,
                    text = True,
                    check = True,
                    timeout = 10
            )
            return int(result.stdout.strip( ) or "0") > 0
        except (OSError, subprocess.SubprocessError, ValueError):
            return False
    
    def ensure_windows_mitm_cert(self):
        """自动导入 mitmproxy 证书到 Windows 系统"""
        cert_path = Path.home( ) / ".mitmproxy" / "mitmproxy-ca-cert.cer"
        if not cert_path.exists( ):
            raise RuntimeError("未找到 mitmproxy 证书")
        try:
            certificate = cert_path.read_bytes( )
            if certificate.lstrip( ).startswith(b'-----BEGIN CERTIFICATE-----'):
                certificate = ssl.PEM_cert_to_DER_cert(certificate.decode('ascii'))
            fingerprint = hashlib.sha1(certificate).hexdigest( ).upper( )
        except (OSError, UnicodeError, ValueError) as exc:
            raise RuntimeError("读取 mitmproxy 证书失败") from exc
        
        for store in ("Root", "CA"):
            if self._windows_store_has_cert(store, fingerprint):
                continue
            try:
                subprocess.run(
                        ["certutil", "-addstore", "-f", "-user", store, str(cert_path)],
                        check = True,
                        stdout = subprocess.DEVNULL,
                        stderr = subprocess.STDOUT,
                        timeout = 10
                )
                proxy_logger.info(f"已将 mitmproxy 证书导入 CurrentUser\\{store}")
            except (OSError, subprocess.SubprocessError) as exc:
                raise RuntimeError(f'导入 mitmproxy 证书到 {store} 失败，请检查证书和系统权限') from exc
    
    def enable_proxy(self, host = "127.0.0.1", port = 8888):
        proxy_logger.info("启用系统代理...")
        
        if self.os == "Darwin":
            services = self._get_network_services( )
            
            # 保存当前代理设置
            for service in services:
                self.original_settings[service] = self._get_proxy_info(service)
            if not services or any(value is None for value in self.original_settings.values( )):
                self.original_settings.clear( )
                raise RuntimeError("无法读取 macOS 网络代理设置，请检查 networksetup 权限")
            
            # 设置新代理
            for service in services:
                subprocess.run(
                        ["networksetup", "-setwebproxy", service, host, str(port)],
                        stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL, check = True
                )
                subprocess.run(
                        ["networksetup", "-setsecurewebproxy", service, host, str(port)],
                        stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL, check = True
                )
        
        elif self.os == "Windows":
            # 保存当前代理设置
            self.original_settings['windows'] = self._get_windows_proxy_settings( )
            if self.original_settings['windows'] is None:
                self.original_settings.clear( )
                raise RuntimeError("无法读取 Windows 代理设置")
            
            # 设置新代理
            proxy_server = f"{host}:{port}"
            if not self._set_windows_proxy_settings(
                    enabled = True,
                    server = proxy_server
            ):
                raise RuntimeError("无法设置 Windows 系统代理")
            proxy_logger.info(f"已设置系统代理: {proxy_server}")
        
        elif self.os == "Linux":
            # 进程环境变量不会影响已经运行的微信或其他客户端
            proxy_logger.info(f"请在目标客户端手动设置代理 {host}:{port}")
    
    def disable_proxy(self):
        proxy_logger.info("恢复原代理设置...")
        
        if self.os == "Darwin":
            failures = []
            for service, settings in self.original_settings.items( ):
                if settings is None:
                    continue
                for kind, option in (('web', 'web'), ('secure', 'secureweb')):
                    host, port = settings[f'{kind}_host'], settings[f'{kind}_port']
                    commands = []
                    if host and port:
                        commands.append(["networksetup", f"-set{option}proxy", service, host, port])
                    elif settings[f'{kind}_enabled']:
                        failures.append(f'{service}: {kind} 代理缺少地址或端口')
                    if not settings[f'{kind}_enabled']:
                        commands.append(["networksetup", f"-set{option}proxystate", service, "off"])
                    for command in commands:
                        try:
                            subprocess.run(command, stdout = subprocess.DEVNULL,
                                           stderr = subprocess.DEVNULL, check = True)
                        except (OSError, subprocess.SubprocessError) as exc:
                            failures.append(f'{service}: {exc}')
            if failures:
                raise RuntimeError('恢复 macOS 代理失败：' + '; '.join(failures))
        
        elif self.os == "Windows":
            if 'windows' in self.original_settings:
                settings = self.original_settings['windows']
                
                if not self._set_windows_proxy_settings(
                        enabled = settings['enabled'],
                        server = settings['server'],
                        override = settings['override']
                ):
                    raise RuntimeError("恢复 Windows 代理失败")
                
                proxy_logger.info("已恢复原始代理设置")
        
        proxy_logger.info("代理已恢复")
