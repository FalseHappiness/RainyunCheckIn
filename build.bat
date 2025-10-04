chcp 65001

@echo off
echo 正在使用 Nuitka 打包 RainyunAutoCheckIn...
echo.

set PLAYWRIGHT_BROWSERS_PATH=./playwright

python -m nuitka --standalone ^
                 --follow-imports ^
                 --python-flag="-S" ^
                 --mingw64 ^
                 --main="app.py" ^
                 --onefile-cache-mode="auto" ^
                 --include-data-files=captcha.html=.\ ^
                 --include-data-files=index.html=.\ ^
                 --include-data-files=env.js=.\ ^
                 --playwright-include-browser="webkit-2203" ^
                 --playwright-include-browser="winldd-1007" ^
                 --output-dir="dist" ^
                 --output-filename="RainyunAutoCheckIn.exe" ^
                 --company-name="FalseHappiness" ^
                 --product-name="RainyunAutoCheckIn" ^
                 --file-version="1.2.0" ^
                 --product-version="1.2.0" ^
                 --file-description="雨云自动签到程序 https://github.com/FalseHappiness/RainyunCheckIn" ^
                 --copyright="Copyright © 2025 FalseHappiness" ^
                 --enable-plugin=no-qt ^
                 --windows-console-mode="force"

echo.
echo 打包完成！
pause