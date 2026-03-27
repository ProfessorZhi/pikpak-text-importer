# PikPak Text Importer

把包含 `https://mypikpak.com/s/...` 的文本批量解析出来，并转存到你的 PikPak 网盘。

这是一个本地桌面客户端项目，适合自己运行，也适合整理后上传到 GitHub。

## 功能

- 桌面客户端界面
- 本地保存账号配置与会话缓存
- 账号校验成功后，按层浏览 PikPak 网盘目录
- 从文本里提取分享链接和标题
- 每个链接按一个独立目标项处理
- 显示导入进度和处理结果

## 启动

推荐直接双击：

- `StartPikPakImporter.bat`

如果想用命令行启动：

```powershell
python -m pip install -r .\requirements.txt
python .\scripts\run_gui.py
```

## 使用流程

1. 打开客户端
2. 填写 PikPak 账号和密码
3. 选择会话文件保存位置
4. 点击“保存配置”
5. 点击“校验账号”
6. 校验成功后，按层进入你想放置内容的父目录
7. 粘贴包含 PikPak 分享链接的文本
8. 点击“预览将创建的文件夹”或“开始转存”

## 目录说明

- `app/pikpak_importer/gui.py`
  桌面客户端界面
- `app/pikpak_importer/importer.py`
  文本解析、账号校验、目录读取、转存逻辑
- `scripts/run_gui.py`
  GUI 启动入口
- `scripts/run_cli.py`
  CLI 启动入口
- `tests/test_pikpak_text_importer.py`
  基础单测
- `assets/pikpak_importer_icon.svg`
  客户端图标

## 本地配置

这些文件只在你本机使用，不应该上传到 GitHub：

- `config/account.json`
- `.pikpak_session.json`
- `.codex/pikpak/session.json`

仓库里提供了一个示例文件：

- `config/account.example.json`

你可以参考它了解配置结构，但不要把自己的真实账号配置提交到仓库。

打包后的 EXE 版本会把真实配置写到用户目录，而不是安装目录。

默认位置：

- `%LOCALAPPDATA%\PikPakTextImporter\config\account.json`
- `%LOCALAPPDATA%\PikPakTextImporter\session\session.json`

## 项目结构

```text
pikpakdownloader/
  app/
    pikpak_importer/
      __init__.py
      __main__.py
      gui.py
      importer.py
  assets/
    pikpak_importer_icon.svg
  config/
    account.example.json
  scripts/
    run_cli.py
    run_gui.py
  tests/
    test_pikpak_text_importer.py
  .gitignore
  README.md
  requirements.txt
  StartPikPakImporter.bat
  启动PikPak批量转存界面.bat
```

## 依赖

- `pikpakapi`
- `PySide6`

安装：

```powershell
python -m pip install -r .\requirements.txt
```

## 测试

```powershell
python -m unittest discover -s tests -v
```

## 打包

为了让客户端启动更快，项目默认使用 PyInstaller 的 `onedir` 方式，而不是 `onefile`。

直接双击：

- `BuildRelease.bat`

或者命令行执行：

```powershell
python .\packaging\build_release.py
```

输出结果：

- `dist\app\PikPakTextImporter\`
  适合本地直接运行，启动更快
- `dist\installer\PikPakTextImporter-Setup.exe`
  安装版 EXE
