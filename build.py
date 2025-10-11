import subprocess
import sys

from src.version import PROGRAM_VERSION

# 定义 Nuitka 打包命令
nuitka_cmd = [
    sys.executable, "-m", "nuitka",
    "--standalone",
    "--nofollow-import-to=matplotlib",
    "--nofollow-import-to=pillow",
    "--python-flag=-S",
    "--mingw64",
    "--main=app.py",
    "--include-data-files=./static/captcha.html=./static/",
    "--include-data-files=./static/index.html=./static/",
    "--include-data-files=./static/env.js=./static/",
    "--output-dir=dist",
    "--output-filename=RainyunCheckIn.exe",
    "--company-name=FalseHappiness",
    "--product-name=RainyunCheckIn",
    f"--file-version={PROGRAM_VERSION}",
    f"--product-version={PROGRAM_VERSION}",
    "--file-description=雨云自动签到程序 https://github.com/FalseHappiness/RainyunCheckIn",
    "--copyright=Copyright © 2025 FalseHappiness",
    "--enable-plugin=no-qt",
    "--enable-plugins=upx",
    "--upx-binary=./upx-5.0.2-win64",
    "--windows-console-mode=force",
    "--no-deployment-flag=self-execution"
]

# 执行 Nuitka 打包
print("正在使用 Nuitka 打包 RainyunCheckIn...")
subprocess.run(nuitka_cmd, check=True)

# 执行压缩
print("创建压缩文件...")
subprocess.run([
    "powershell", "Compress-Archive",
    "-Path", "./dist/app.dist/*",
    "-DestinationPath", "./dist/RainyunCheckIn.zip",
    "-Force"
], check=True)

print("打包完成！")