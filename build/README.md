# 本机打包

使用 Python 3.12 建立虚拟环境。  
先安装项目依赖，再安装打包依赖：

```bash
python -m pip install -r requirements.txt
python -m pip install -r build/requirements.txt
```

从项目根目录执行对应命令：

- Windows：安装 Inno Setup 6.5 或更新版本，并将 `ISCC.exe` 加入 PATH；运行 `python build/build.py windows`。
- macOS：运行 `python build/build.py macos`。
- Linux：安装 Ruby、`fpm`、`dpkg-deb` 和 `rpmbuild`，运行 `python build/build.py linux`。

打包好的安装包位于 `build/output/`。  
打包时产生的临时文件位于 `build/temp/`，打包成功后会自动删除，失败时会保留以便排查。

打包时排除 spaCy 测试、开发源码及重复的 Python 源文件，以及本软件不使用的 mitmproxy 独立网页和终端界面；保留语言模型和
mitmdump 抓包功能。

Linux 安装包目前没有声明系统图形库等运行时依赖，需自行提供兼容的 Qt 图形运行环境。  
构建时使用的系统库版本也会限制可运行的发行版。

用户设置、词库与日志存放在用户可写目录，卸载软件时不会删除这些数据。

## GitHub Actions

`Build packages` 工作流可手动运行，也会在推送 `v*` 标签时运行。
工作流包含 Windows x64、macOS Intel 和 Apple Silicon，以及 Linux x64 和 ARM64 的 DEB/RPM。

## 对于 Windows ARM64

目前上游的相关支持工作尚未完成。

`build/build.py`、`windows.iss` 和工作流已编写打包 ARM64 的相关内容，但工作流中暂未启用，目前不会执行。

启用前需要：

1. 核实 mitmproxy 及其原生依赖提供可用的 Windows ARM64 版本，并更新项目依赖。
2. 核实 Python 3.12、PyInstaller、PyQt6、spaCy 及其依赖均支持 Windows ARM64；若更新 spaCy，应同时更新并验证英语模型。
3. 确认 `windows-11-arm` runner 可用，且安装了 ARM64 Python 和 Inno Setup，然后取消工作流中的 ARM64 任务注释。
4. 在 ARM64 环境完成构建，验证可执行文件架构、安装与卸载，以及图形界面、模型和抓包功能。  
