<div align="center">
<img src="assets/icon.ico">
    <h1>Easy_Cidaren</h1>
    <h4>Cidaren_Automatic_Answer</h4>
<p>词达人自动刷题|自动过班级任务、自学任务|<a href="https://github.com/github123666/cidaren">github123666/cidaren</a>魔改项目</p>
</div>
<div align="center">
    <img src="https://img.shields.io/badge/condition-Stable-blue">
    <img src="https://img.shields.io/github/v/release/ularch/Easy_Cidaren?color=green">
    <img src="https://img.shields.io/github/downloads/ularch/Easy_Cidaren/total">
</div>

## 从1.5.4版本后开始大量采用vibe coding

- 因为倒卖太多了，导致本脚本的滥用，外加官方封堵此类型脚本，本项目决定从1.5.0版本开始不再开源，但依旧免费发布
- 从1.5.4版本后，本项目开始大量采用vibe coding，并且再次开源
- 请勿宣传本软件，请勿滥用本软件，低调使用，且用且珍惜，切记，此类型脚本官方可以很轻松的封堵！！
- 本脚本仅供个人学习使用，请勿用于商业用途
- 有问题请前往[讨论区](https://github.com/ularch/Easy_Cidaren/discussions)，发现bug请提交[Issue](https://github.com/ularch/Easy_Cidaren/issues)（请使用模板格式提交，上传完整log日志，否则不予处理）

## 功能简介

`词达人自动过学习任务,测试任务`

- 自动过**学习任务**
- 自动过**测试任务**
- 暂不支持词达人官方VIP课程（可能会有问题）
- 随时可能失效,**且用且珍惜**
- 可手动选择指定任务
- 支持已完成的任务重刷
- **得分95+**（异常情况、自建任务可能80+）


## 唯一用户社区
[telegram](https://t.me/+GJXB2dFp0BQ1NjU1)

## 日志

<details> <summary> <b>展开</b> </summary>

**2026-08-12**

+ 添加答题进度显示功能，主界面实时显示已完成/总题数

**2026-07-27**

+ 重构主程序结构并优化base64解码功能

**2026-05-18**

+ 添加内置Token获取功能并完善日志系统

**2026-03-29**

+ 添加获取token子菜单功能

**2025-12-09**

+ 添加关于页面和设备ID显示功能，支持一键复制

**2025-12-08**

+ 新增任务执行状态上报与任务分数上传功能
+ 优化任务执行逻辑与UI控制

**2025-11-24**

+ 改进API错误处理和日志记录，增加文件日志记录器

**2025-11-22**

+ 修正base64解码异常处理逻辑，调整3_1024等异常jv的处理方式

**2025-11-13**

+ 修复base64解码异常处理逻辑并更新混淆索引
+ 优化更新检测逻辑

**2025-11-02**

+ 统一API错误处理并优化日志记录
+ 
**2025-10-27**

+ 修复学习任务运行报错的相关问题

**2025-10-27**

+ 发布v1.3.0版本

**2025-03-12**

+ 添加自动检测更新功能

**2024-12-23**

+ 修复“英译汉”题型报错

**2024-09-06**

+ 修复自建自学任务的已知问题

**2024-05-02**

+ 更新GUI

**2023-04-26**

+ 在原项目的基础上添加了手动选择章节功能
+ 将token等设置从config文件改为了在控制台输入

</details>

## 声明

+ 原项目[github123666/cidaren](https://github.com/github123666/cidaren)
+ 仅供学习参考，**严禁盗卖盈利！** 使用后果由使用者承担
+ 请勿在任何平台公开发布本项目

### **侵权或有疑问请联系**

+ 邮箱：cdr@ularch.top
+ Telegram：[harold_lach_lei](https://t.me/Harold_Lach_Lei)

## 快速上手

### 从源码运行（Windows、macOS、Linux）

使用 Python 3.12 和图形桌面环境，在项目根目录创建虚拟环境并安装依赖。已有的虚拟环境不能在不同操作系统或 CPU 架构之间直接复制，应在目标机器上重新创建。项目目录及 `config`、`log` 和 `get token/fetch_token` 目录需要可写。

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

Linux 需要桌面会话、Qt 所需的系统图形库及音频服务；具体系统包名称取决于发行版。依赖使用的预编译包也取决于 Python 版本、CPU 架构和系统。首次安装后可使用同一条启动命令再次运行。Windows 原有 `.bat` 脚本仍可使用，但上述虚拟环境方式更容易管理依赖。

### 获取 token

可在主界面选择“帮助 → 获取 token → 内置”，或将已获得的 token 手动输入。也可以用虚拟环境中的 Python 直接运行 `get token/fetch_token/main.py`；它会持续运行，按 Ctrl+C 结束。

- Windows 和 macOS：内置工具尝试设置系统 HTTP/HTTPS 代理并在结束时恢复；系统可能要求授权。Windows 还会尝试将 mitmproxy 证书导入当前用户证书库。
- Linux：请在目标客户端手动设置 HTTP 和 HTTPS 代理为 `127.0.0.1:8888`，结束后恢复原设置。客户端必须支持并实际使用该代理。
- macOS 和 Linux：首次启动 mitmproxy 后，根据目标客户端的证书信任方式，手动信任 `~/.mitmproxy/mitmproxy-ca-cert.cer`。证书信任和代理设置是否生效取决于客户端；如无法抓取，请手动输入 token。
- 捕获期间端口 8888 必须可用。程序正常结束后会停止代理进程；系统异常退出时需检查并手动恢复代理设置。第三方 `.exe` 工具仅适用于 Windows，且需要自行提供。

## 支持项目
**[请我喝杯奶茶☕️](https://afdian.com/a/ularch)**

<div align="center">
🌟 请点点右上角的 Star，多多支持本项目开发~
</div>

[![Stargazers over time](https://starchart.cc/ularch/Easy_Cidaren.svg?variant=adaptive)](https://starchart.cc/ularch/Easy_Cidaren)
