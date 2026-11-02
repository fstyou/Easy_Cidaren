# Easy Cidaren

当前版本：1.0.0

词达人任务工具，支持 Windows、macOS 和 Linux。

- 使用 Token 登录，可在界面中获取 Token。
- 选择学习或测试任务，运行时查看进度并可停止任务。
- 导出运行日志，调整答题间隔和提示音。

遇到问题可在[项目问题区](https://github.com/fstyou/Easy_Cidaren/issues)反馈。

## 快速上手

### 从源码运行（Windows、macOS、Linux）

使用 Python 3.12 和图形桌面环境，在项目根目录创建虚拟环境并安装依赖。已有的虚拟环境不能在不同操作系统或 CPU
架构之间直接复制，应在目标机器上重新创建。项目目录及 `data` 目录需要可写；程序运行时会自动创建 `runtime` 目录。

Windows（PowerShell）：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

macOS / Linux（终端）：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Linux 需要桌面会话、Qt 所需的系统图形库及音频服务；具体系统包名称取决于发行版。依赖使用的预编译包也取决于 Python 版本、CPU
架构和系统。首次安装后可使用同一条启动命令再次运行。

### 获取 token

点击主界面的“获取 token”后，按弹窗提示在微信中打开词达人学生端并等待。捕获成功并恢复代理后，弹窗自动关闭，程序会自动填入
token 并尝试登录；也可以手动输入 token。运行任务时主界面显示进度，题目异常等重要信息会弹窗提示，详细调试信息输出到启动程序的终端。

程序会在本机保存最近一次获取的 Token，下次启动时自动填入；点击“登录”即可尝试使用。若 Token 已过期，请重新获取。

控制台日志按时间、级别和模块显示，默认包含 `DEBUG` 信息。可通过环境变量 `EASY_CIDAREN_LOG_LEVEL` 设置最低级别，例如 `INFO`、
`WARNING` 或 `ERROR`：

```bash
EASY_CIDAREN_LOG_LEVEL=INFO .venv/bin/python main.py
```

Windows PowerShell：

```powershell
$env:EASY_CIDAREN_LOG_LEVEL = "INFO"
.\.venv\Scripts\python.exe main.py
```

完整调试记录保存在 `runtime/logs/`，点击主界面的“导出日志”可保存当前运行的日志；较长的接口数据仅写入日志文件。

- Windows 和 macOS：内置工具尝试设置系统 HTTP/HTTPS 代理并在结束时恢复；系统可能要求授权。Windows 还会尝试将 mitmproxy
  证书导入当前用户证书库。
- Linux：请在目标客户端手动设置 HTTP 和 HTTPS 代理为 `127.0.0.1:8888`，结束后恢复原设置。客户端必须支持并实际使用该代理。
- macOS 和 Linux：首次启动 mitmproxy 后，根据目标客户端的证书信任方式，手动信任 `~/.mitmproxy/mitmproxy-ca-cert.cer`
  。证书信任和代理设置是否生效取决于客户端；如无法抓取，请手动输入 token。
- 捕获期间端口 8888 必须可用。程序正常结束后会停止代理进程；系统异常退出时需检查并手动恢复代理设置。

## 项目结构

```text
main.py                         图形程序入口
easy_cidaren/
  app.py                        程序初始化与启动
  api/                          服务端接口与请求
  core/                         状态、任务、答题与词库逻辑
  logging/                      日志配置、格式与导出
  security/                     数据解码和签名
  token_capture/                token 捕获与代理实现
  ui/                           窗口、弹窗和设置
  utils/                        系统与通用辅助工具
  paths.py                      项目和运行数据路径
data/                           答案库、词表池与语言模型
assets/                         图标、图片和提示音
data/models/en_core_web_sm/     随项目提供的语言模型
tests/                          自动化检查
runtime/settings.json           用户设置（首次运行时创建）
runtime/token_capture/          Token 捕获和保存数据（自动创建）
runtime/logs/                   运行日志（自动创建）
```
