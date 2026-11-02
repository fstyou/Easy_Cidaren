import platform
import re
import subprocess
from pathlib import Path

from easy_cidaren.logging.config import Log

if platform.system( ) == "Windows":
    import winreg

proxy_logger = Log("proxy_manager")


class ProxyManager:
    def __init__(self):
        self.os = platform.system( )
        self.original_settings = {}  # 保存原始代理设置
    
    def _get_network_services(self):
        """获取 macOS 网络服务列表"""
        output = subprocess.check_output(
                ["networksetup", "-listallnetworkservices"],
                text = True
        )
        return [s for s in output.splitlines( )[1:] if not s.startswith("*")]
    
    def _get_proxy_info(self, service):
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
            
            web_enabled = "Enabled: Yes" in web_output
            secure_enabled = "Enabled: Yes" in secure_output
            
            web_host = re.search(r'Server: (.+)', web_output)
            web_port = re.search(r'Port: (\d+)', web_output)
            secure_host = re.search(r'Server: (.+)', secure_output)
            secure_port = re.search(r'Port: (\d+)', secure_output)
            
            return {
                'web_enabled': web_enabled,
                'web_host': web_host.group(1).strip( ) if web_host else '',
                'web_port': web_port.group(1) if web_port else '',
                'secure_enabled': secure_enabled,
                'secure_host': secure_host.group(1).strip( ) if secure_host else '',
                'secure_port': secure_port.group(1) if secure_port else '',
            }
        except (OSError, subprocess.SubprocessError) as exc:
            proxy_logger.logger.error("读取 macOS 代理设置失败：%s", exc)
            return None
    
    def _get_windows_proxy_settings(self):
        """获取 Windows 当前的代理设置"""
        try:
            key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                    0,
                    winreg.KEY_READ
            )
            
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
            
            winreg.CloseKey(key)
            
            return {
                'enabled': bool(proxy_enable),
                'server': proxy_server,
                'override': proxy_override
            }
        except Exception as e:
            proxy_logger.logger.error(f"读取代理设置失败: {e}")
            return None
    
    def _set_windows_proxy_settings(self, enabled, server = "", override = "<local>"):
        """设置 Windows 代理"""
        try:
            key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                    0,
                    winreg.KEY_WRITE
            )
            
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1 if enabled else 0)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, server)
            winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, override)
            
            winreg.CloseKey(key)
            
            # 通知系统代理设置已更改
            import ctypes
            INTERNET_OPTION_SETTINGS_CHANGED = 39
            INTERNET_OPTION_REFRESH = 37
            internet_set_option = ctypes.windll.Wininet.InternetSetOptionW
            internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
            internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0)
            
            return True
        except Exception as e:
            proxy_logger.logger.error(f"设置代理失败: {e}")
            return False
    
    def _windows_store_has_cert(self, store_name):
        """检测指定证书存储是否已有 mitmproxy 证书"""
        try:
            ps_cmd = (
                f"(Get-ChildItem -Path Cert:\\CurrentUser\\{store_name} "
                f"| Where-Object {{$_.Subject -like '*mitmproxy*'}} | Measure).Count"
            )
            result = subprocess.run(
                    ["powershell", "-NoLogo", "-NoProfile", "-Command", ps_cmd],
                    capture_output = True,
                    text = True,
                    check = True,
                    timeout = 10
            )
            return int(result.stdout.strip( ) or "0") > 0
        except Exception:
            return False
    
    def _ensure_windows_mitm_cert(self):
        """自动导入 mitmproxy 证书到 Windows 系统"""
        cert_path = Path.home( ) / ".mitmproxy" / "mitmproxy-ca-cert.cer"
        if not cert_path.exists( ):
            proxy_logger.logger.warning("未找到 mitmproxy 证书，将在首次运行 mitmdump 时自动生成")
            return
        
        for store in ("Root", "CA"):
            if self._windows_store_has_cert(store):
                continue
            try:
                subprocess.run(
                        ["certutil", "-addstore", "-f", "-user", store, str(cert_path)],
                        check = True,
                        stdout = subprocess.DEVNULL,
                        stderr = subprocess.STDOUT,
                        timeout = 10
                )
                proxy_logger.logger.info(f"已将 mitmproxy 证书导入 CurrentUser\\{store}")
            except subprocess.CalledProcessError:
                proxy_logger.logger.warning(
                        f"导入证书到 {store} 失败，可手动执行：certutil -addstore -f -user {store} \"{cert_path}\"")
            except Exception as e:
                proxy_logger.logger.error(f"导入证书时出错: {e}")
    
    def enable_proxy(self, host = "127.0.0.1", port = 8888):
        proxy_logger.logger.info("启用系统代理...")
        
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
            # 先确保证书已导入
            self._ensure_windows_mitm_cert( )
            
            # 保存当前代理设置
            self.original_settings['windows'] = self._get_windows_proxy_settings( )
            if self.original_settings['windows'] is None:
                self.original_settings.clear( )
                raise RuntimeError("无法读取 Windows 代理设置")
            
            # 设置新代理
            proxy_server = f"{host}:{port}"
            if not self._set_windows_proxy_settings(
                    enabled = True,
                    server = proxy_server,
                    override = "<local>"
            ):
                raise RuntimeError("无法设置 Windows 系统代理")
            proxy_logger.logger.info(f"已设置系统代理: {proxy_server}")
        
        elif self.os == "Linux":
            # 进程环境变量不会影响已经运行的微信或其他客户端。
            proxy_logger.logger.info(f"请在目标客户端手动设置代理 {host}:{port}")
    
    def disable_proxy(self):
        proxy_logger.logger.info("恢复原代理设置...")
        
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
                
                proxy_logger.logger.info("已恢复原始代理设置")
        
        proxy_logger.logger.info("代理已恢复")
