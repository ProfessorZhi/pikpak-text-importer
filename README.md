# PikPak Text Importer

一个本地桌面工具，用来从普通文本中提取 `https://mypikpak.com/s/...` 分享链接，并批量转存到你的 PikPak 网盘。

这个仓库只包含工具代码、界面、打包脚本和中性示例，不包含任何个人测试数据或私密配置。

## 功能

- 桌面客户端界面
- 账号配置与会话缓存
- 账号校验成功后按层浏览 PikPak 目录
- 从文本里提取分享链接和标题
- 批量执行转存并显示进度
- 打包为快速启动的 `onedir` EXE
- 生成安装版 `Setup.exe`

## 启动

推荐直接双击：

- `StartPikPakImporter.bat`

命令行启动：

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
6. 校验成功后，按层进入目标父目录
7. 粘贴包含 PikPak 分享链接的文本
8. 点击“预览将创建的文件夹”或“开始转存”

## 项目结构

```text
pikpakdownloader/
  app/
    pikpak_importer/
      __init__.py
      __main__.py
      gui.py
      importer.py
      paths.py
  assets/
    pikpak_importer_icon.svg
  config/
    account.example.json
  packaging/
    build_release.py
    PikPakTextImporter.iss
  scripts/
    run_cli.py
    run_gui.py
  tests/
    test_pikpak_text_importer.py
  .gitignore
  BuildRelease.bat
  LICENSE
  README.md
  requirements.txt
  StartPikPakImporter.bat
  启动PikPak批量转存界面.bat
```

## 本地配置

这些文件只在本机使用，不会上传到 GitHub：

- `config/account.json`
- `.pikpak_session.json`
- `.codex/pikpak/session.json`

仓库里只保留示例配置：

- `config/account.example.json`

打包后的 EXE 默认把真实配置写到用户目录：

- `%LOCALAPPDATA%\PikPakTextImporter\config\account.json`
- `%LOCALAPPDATA%\PikPakTextImporter\session\session.json`

## 依赖

- `pikpakapi`
- `PySide6`

安装依赖：

```powershell
python -m pip install -r .\requirements.txt
```

## 测试

```powershell
python -m unittest discover -s tests -v
```

## 打包

为了让客户端启动更快，项目默认使用 PyInstaller 的 `onedir` 模式，而不是 `onefile`。

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
