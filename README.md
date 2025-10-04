# Rainyun Auto Check-In

一个自动签到雨云的 Python 脚本，支持命令行和网页界面操作。

请不要使用此脚本白嫖雨云积分，仅作为学习交流使用。

在 Windows 11 与 Ubuntu 24.04.1 LTS 上经过测试。

## 下载与安装

### 克隆仓库使用 Python 运行

本项目使用 Python 3.11.0

#### 1. 克隆本仓库：

创建一个空目录并执行

```bash
git clone https://github.com/FalseHappiness/RainyunCheckIn.git
```

#### 2. 安装依赖：

安装 Python 包，最好创建虚拟环境运行

```bash
pip install -r requirements.txt
```

#### 3. 安装 Playwright Webkit

可以不执行这步操作，运行 app.py 时会自动处理并安装

如果不需要模拟浏览器完成验证码，也不需要安装

在 Linux 上可能还需要安装一些依赖

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

#### 3. 配置 auth.json 登录雨云账号

##### 方法一：使用 API 密钥（推荐）

1. 在程序目录下创建或编辑 `auth.json` 文件
2. 按照以下格式填写你的雨云 API 密钥：

```json
{
  "x-api-key": ""
}
```

获取 API 密钥 的方法：

1. 登录雨云网站
2. 打开 [总览 → 用户 → 账户设置 → API 密钥](https://app.rainyun.com/account/settings/api-key)
3. 复制 `API 密钥` 或者 `重新生成` 一个，并保存到 `auth.json`

##### 方法二：使用 Cookies

1. 在程序目录下创建或编辑 `auth.json` 文件
2. 按照以下格式填写你的雨云 Cookies 信息：

```json
{
  "dev-code": "",
  "rain-session": ""
}
```

获取 Cookies 的方法：

1. 登录雨云网站
2. 按`(Fn+)F12`打开开发者工具（或者右键，然后点击 `检查` ）
3. 转到`应用程序 (Application)`选项卡
4. 在右侧 `存储` 项目下点开 `Cookie`，找到 `https://app.rainyun.com/` 的 Cookie
5. 复制名称为 `dev-code` 和 `rain-session` 的值并保存到 `auth.json`

> ⚠️ **警告**: 不要把 `auth.json` 分享给其他人，否则其他人可以直接操作你的雨云账号！

#### 4. 运行程序：

```bash
python app.py [命令]
```

使用 `python app.py -h` 查看帮助

## 使用说明

### 帮助

```
位置参数:
  {web,check_in,status}
                        要执行的命令（web: 开启网页, check_in: 签到, status: 获取签到状态）

可选参数:
  -h, --help            显示帮助信息并退出
  -a, --auto            是否开启自动模式（命令为 check_in 时生效，默认关闭）
  -f, --force           是否跳过签到状态检测（命令为 check_in 时生效，默认关闭）
  -b, --browser-captcha
                        是否模拟浏览器行为完成验证码（命令为 check_in 且开启 自动签到模式 时生效，默认关闭）
  -p PORT, --port PORT  网页端口（命令为 web 时生效，默认为 31278）

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
python app.py check_in --auto
```

#### --browser-captcha

使用 Playwright 模拟浏览器行为完成验证码。如果不开启此选项，程序将自动构造验证码请求完成验证码，并使用 PyMiniRacer
来获取部分请求参数。

不开启此选项通常会更快完成验证码。

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
- `ICR.py` - 交互式验证码识别（Interactive CAPTCHA Recognition）模块（经过简单测试“正确率: 94.00% (188/200)”，多次尝试可确保验证成功）
- `utils.py` - 实用工具
- `index.html` - 网页主页面
- `captcha.html` - 签到页面
- `detect_accuracy.py` - 验证码识别准确率检测
- `build.bat` - 构建可执行文件的脚本
- `env.js` - 补充 NodeJS 环境

### 构建程序

运行 `build.bat` 可以构建可执行文件。

### Playwright

开启参数 --browser-captcha 自动完成 TCaptcha 时，需要获取请求参数，需要通过无头 Playwright Webkit 运行 JS 脚本以获取参数。

为了方便使用，此程序会在用到它时，自动安装 Playwright Webkit 在程序所在目录下，哪怕已经在其他地方安装过，这会带来额外的空间占用。

### PyMiniRacer

不开启参数 --browser-captcha 自动完成 TCaptcha 时，需要获取请求参数，需要通过 PyMiniRacer 运行 NodeJS 脚本以获取参数。

## 许可证

本项目采用 MIT
许可证。有关详细信息，请参阅 [LICENSE](https://github.com/FalseHappiness/RainyunCheckIn/blob/main/LICENSE) 文件。

## 问题反馈

如果您遇到任何问题，请在 [GitHub Issues](https://github.com/FalseHappiness/RainyunCheckIn/issues) 提出。

如果您可以解决问题，请创建一个 [拉取请求](https://github.com/FalseHappiness/RainyunCheckIn/pulls)。