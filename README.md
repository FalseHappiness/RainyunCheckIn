# Rainyun Check-In

一个自动签到雨云的 Python 脚本，支持命令行、API 和网页界面操作。

此脚本仅作为学习交流使用。

在 Windows 11 与 Ubuntu 24.04.1 LTS 上经过测试。

优点：无需安装浏览器，不使用机器学习，在低配电脑、服务器上也能较快完成签到。

## 下载与安装

### 方法一：Windows 直接下载可执行文件

1. 前往 [GitHub Releases](https://github.com/FalseHappiness/RainyunCheckIn/releases) 下载最新版本的
   `RainyunCheckIn.zip` ，并把文件解压到一个空目录
2. 下载后，进入到目录，运行类似下面的方法，把开头的 `python app.py` 替换为 `.\RainyunCheckIn.exe` 即可

### 方法二：克隆仓库使用 Python 运行

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

#### 3. 配置凭据登录雨云账号

见[配置凭据](#配置凭据)

#### 4. 运行程序：

```bash
python app.py [命令]
```

```bash
.\RainyunCheckIn.exe [命令]
```

使用 `python app.py -h` `.\RainyunCheckIn.exe -h` 查看帮助

## 配置文件

在程序同目录创建 config.json 文件，或者使用 --config 指定路径

基本格式如下

```json
{
  "auth": {
    "x-api-key": "",
    "dev-code": "",
    "rain-session": ""
  },
  "headers": {
    "Name": "value"
  }
}
```

### 配置凭据

配置凭据登录雨云账号

如果启动命令为 web，可不用配置，但要在调用 API 时传入

#### 方法一：使用 API 密钥（推荐）

按照以下格式填写你的雨云 API 密钥：

```json
{
  "auth": {
    "x-api-key": "API 密钥"
  }
}
```

获取 API 密钥 的方法：

1. 登录雨云网站
2. 打开 [总览 → 用户 → 账户设置 → API 密钥](https://app.rainyun.com/account/settings/api-key)
3. 复制 `API 密钥` 或者 `重新生成` 一个，并保存到 `config.json`

#### 方法二：使用 Cookies （不建议使用）

按照以下格式填写你的雨云 Cookies 信息：

```json
{
  "auth": {
    "dev-code": "",
    "rain-session": ""
  }
}
```

获取 Cookies 的方法：

1. 登录雨云网站
2. 按`(Fn+)F12`打开开发者工具（或者右键，然后点击 `检查` ）
3. 转到`应用程序 (Application)`选项卡
4. 在右侧 `存储` 项目下点开 `Cookie`，找到 `https://app.rainyun.com/` 的 Cookie
5. 复制名称为 `dev-code` 和 `rain-session` 的值并保存到 `config.json`

> ⚠️ **警告**: 不要把 `config.json` 分享给其他人，否则其他人可以直接操作你的雨云账号！

#### 配置多个凭据

类似以下格式即可

```json
{
  "auth": [
    {
      "x-api-key": "API Key",
      "name": "配置1（昵称，仅用于辨别配置）"
    },
    {
      "dev-code": "Dev code",
      "rain-session": "Rain session",
      "name": "配置2"
    }
  ]
}
```

### 配置请求头（可选）

配置请求雨云、验证码所用的请求头，可采用以下格式：

```json
{
  "headers": {
    "Header-Name": "value"
  }
}
```

```json
{
  "headers": [
    {
      "name": "Header-Name",
      "value": "value"
    }
  ]
}
```

```json
{
  "headers": [
    [
      "Header-Name",
      "value"
    ]
  ]
}
```

```json
{
  "headers": [
    "Header-Name: value"
  ]
}
```

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
  -p PORT, --port PORT  网页端口（命令为 web 时生效，默认为 31278）
  -m {template,brute,speed}, --method {template,brute,speed}
                        匹配背景块与需选块的方法（命令为 check_in 且开启 自动签到模式 时生效，默认为 template）
  -c CONFIG, --config CONFIG
                        设置 config 文件路径，默认为程序同目录 config.json

示例: python app.py check_in --auto
```

### 网页模式

运行以下命令启动网页界面和 API 接口

[API 接口文档](https://rainyun-check-in.apifox.cn/)

```bash
python app.py web
```

然后在浏览器中访问 `http://localhost:31278` (默认端口31278，可通过`--port`参数更改)

开启网页并指定端口

```bash
.\RainyunCheckIn.exe web --port 14514
```

### 自动签到

强制签到（跳过签到状态检测）

```bash
python app.py check_in --auto --force
```

自动签到

```bash
.\RainyunCheckIn.exe check_in --auto
```

#### --method

匹配背景块与需选块的方法，具体差异请看[匹配方法比较](#匹配方法比较)

可选 `template` `brute` `speed`

```bash
python app.py check_in -a --method template
```

```bash
.\RainyunCheckIn.exe check_in -a -m speed
```

### 手动签到

强制签到（跳过签到状态检测）

```bash
python app.py check_in --force
```

手动签到

```bash
.\RainyunCheckIn.exe check_in
```

### 签到状态

查看签到状态

```bash
python app.py status
```

```bash
.\RainyunCheckIn.exe status
```

### 指定配置文件

#### 绝对路径

```bash
python app.py check_in -a --config /path/to/config.json
```

```bash
python app.py check_in -a --config C:/path/to/config.json
```

#### 相对路径

可输入相对于工作目录（执行程序的目录）的路径

```bash
.\RainyunCheckIn.exe check_in -a -c ./path/to/config.json
```

## 开发

### 项目结构

- `app.py` - 程序入口和命令行接口
- `detect_accuracy.py` - 验证码识别准确率检测
- `build.py` - 构建可执行文件的脚本
- `src/main.py` - 主要逻辑实现
- `src/web.py` - 网页支持功能
- `src/ICR.py` - 交互式验证码识别（Interactive CAPTCHA Recognition）模块
- `src/utils.py` - 实用工具
- `src/version.py` - 版本信息
- `static/index.html` - 网页主页面
- `static/captcha.html` - 签到页面
- `static/env.js` - 补充 NodeJS 环境

### 构建程序

运行 `build.bat` 可以构建可执行文件。

### PyMiniRacer

自动完成 TCaptcha 时，需要获取请求参数，需要通过 PyMiniRacer 运行 NodeJS 脚本以获取参数。

### 匹配方法比较

匹配时会有 10 次尝试，如果 10 次失败，则完成验证码失败。

这些测试仅为简单测试，并未控制每次使用的验证码图片相同。

有不同的方法可以比较背景中的图形和待选择的图形，下列方法按照识别速度排序：

#### 1.speed

正确率：87% (261/300)

#### 2.template

正确率：100% (300/300)

#### 3.brute

未测试正确率，理论上和 template 方法差不多甚至更准确，但是可能会消耗很长时间。

## 许可证

本项目采用 MIT
许可证。有关详细信息，请参阅 [LICENSE](https://github.com/FalseHappiness/RainyunCheckIn/blob/main/LICENSE) 文件。

## 问题反馈

如果您遇到任何问题或需要请求新功能，请在 [GitHub Issues](https://github.com/FalseHappiness/RainyunCheckIn/issues) 提出。

如果您可以解决问题，请创建一个 [拉取请求](https://github.com/FalseHappiness/RainyunCheckIn/pulls)。