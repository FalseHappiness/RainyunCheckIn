chcp 65001

@echo off
echo 正在使用 Nuitka 打包 RainyunCheckIn...
echo.

python -m nuitka --standalone ^
                 --nofollow-import-to="matplotlib" ^
                 --nofollow-import-to="pillow" ^
                 --python-flag="-S" ^
                 --mingw64 ^
                 --main="app.py" ^
                 --include-data-files=.\static\captcha.html=.\static\ ^
                 --include-data-files=.\static\index.html=.\static\ ^
                 --include-data-files=.\static\env.js=.\static\ ^
                 --output-dir="dist" ^
                 --output-filename="RainyunCheckIn.exe" ^
                 --company-name="FalseHappiness" ^
                 --product-name="RainyunCheckIn" ^
                 --file-version="1.4.0" ^
                 --product-version="1.4.0" ^
                 --file-description="雨云自动签到程序 https://github.com/FalseHappiness/RainyunCheckIn" ^
                 --copyright="Copyright © 2025 FalseHappiness" ^
                 --enable-plugin=no-qt ^
                 --enable-plugins="upx" ^
                 --upx-binary="./upx-5.0.2-win64" ^
                 --windows-console-mode="force" ^
                 --no-deployment-flag=self-execution

echo.

echo 创建压缩文件...
tar -a -c -f "./dist/RainyunCheckIn.zip" "./dist/app.dist"

echo.
echo 打包完成！
pause