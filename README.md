# Rainyun Check-In

一个自动签到雨云的 Python 脚本，支持命令行和网页界面操作。

## 下载与安装

### 克隆仓库使用 Python 运行

本项目使用 Python 3.11.0

#### 1. 克隆本仓库：

创建一个空目录并执行

```bash
git clone https://github.com/FalseHappiness/RainyunCheckIn.git
```

#### 2. 安装依赖：

安装 Python 包

```bash
pip install -r requirements.txt
```

设置临时环境变量

```bash
export PLAYWRIGHT_BROWSERS_PATH=./playwright  # Mac/Linux
set PLAYWRIGHT_BROWSERS_PATH=./playwright     # Windows (CMD)
$env:PLAYWRIGHT_BROWSERS_PATH="./playwright"  # Windows (PowerShell)
```

安装 Playwright Webkit

```bash
python -m playwright install webkit
```

#### 3. 配置 cookies.json

1. 在程序目录下创建或编辑 `cookies.json` 文件
2. 按照以下格式填写你的雨云cookie信息：

```json
{
  "dev-code": "",
  "rain-session": ""
}
```

获取cookie的方法：

1. 登录雨云网站
2. 按`(Fn+)F12`打开开发者工具（或者右键，然后点击 `检查` ）
3. 转到`应用程序 (Application)`选项卡
4. 在右侧 `存储` 项目下点开 `Cookie`，找到 `https://app.rainyun.com/` 的 Cookie
5. 复制名称为 `dev-code` 和 `rain-session` 的值并保存到 `cookies.json`

#### 4. 运行程序：

```bash
python app.py [命令]
```

使用 `python app.py -h` 查看帮助

## 使用说明

### 帮助

```
用法：app.py [-h] [-a] [-f] [-p PORT] {web,check_in,status}

位置参数:
{web,check_in,status}
要执行的命令（web: 开启网页, check_in: 签到, status: 获取签到状态）

可选参数:
-h, --help显示帮助信息并退出
-a, --auto是否开启自动模式（命令为 check_in 时生效，默认关闭）
-f, --force是否跳过签到状态检测（命令为 check_in 时生效，默认关闭）
-p PORT, --port PORT网页端口（命令为 web 时生效，默认为 31278）

示例: python app.py check_in --auto
```

### 网页模式

运行以下命令启动网页界面

```bash
python app.py web
```

开启网页并指定端口

```bash
python app.py web --port 14514
```

然后在浏览器中访问 `http://localhost:31278` (默认端口31278，可通过`--port`参数更改)

### 自动签到

强制签到（跳过签到状态检测）

```bash
python app.py check_in --auto --force
```

自动签到

```bash
python app.py web check_in --auto
```

### 手动签到

强制签到（跳过签到状态检测）

```bash
python app.py check_in --force
```

手动签到

```bash
python app.py check_in
```

### 签到状态

查看签到状态

```bash
python app.py status
```

## 开发

### 项目结构

- `main.py` - 主要逻辑实现
- `app.py` - 程序入口和命令行接口
- `web.py` - 网页支持功能
- `ocr.py` - 验证码识别模块
- `index.html` - 网页主页面
- `captcha.html` - 签到页面
- `detect_accuracy.py` - 验证码识别准确率检测
- `build.bat` - 构建可执行文件的脚本

### 构建程序

运行 `build.bat` 可以构建可执行文件。

### Playwright

自动完成 TCaptcha 时，需要获取请求参数，需要通过无头 Playwright Webkit 运行 js 以获取参数

## 许可证

本项目采用 MIT
许可证。有关详细信息，请参阅 [LICENSE](https://github.com/FalseHappiness/RainyunCheckIn/blob/main/LICENSE) 文件。

## 问题反馈

如果您遇到任何问题，请在 [GitHub Issues](https://github.com/FalseHappiness/RainyunCheckIn/issues) 提出。