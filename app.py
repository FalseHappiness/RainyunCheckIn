import argparse
import base64
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def handle_exit(_, __):
    print("\n退出程序")
    sys.exit(0)


# 注册信号处理函数
signal.signal(signal.SIGINT, handle_exit)  # Ctrl+C
signal.signal(signal.SIGTERM, handle_exit)  # kill 命令默认发送的信号

is_bundle = getattr(sys, 'frozen', False)

if is_bundle:
    # 运行在打包后的环境中
    # noinspection PyProtectedMember,PyUnresolvedReferences
    base_path = sys._MEIPASS
else:
    # 运行在本地环境中
    base_path = os.path.dirname(os.path.abspath(__file__))

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(Path(base_path) / "playwright")


class ChineseHelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog, indent_increment=2, max_help_position=24, width=None):
        super().__init__(prog, indent_increment, max_help_position, width)

    def _format_usage(self, usage, actions, groups, prefix):
        """重写usage提示"""
        if prefix is None:
            prefix = '用法：'  # 替换 usage:
        return super()._format_usage(usage, actions, groups, prefix)

    def start_section(self, heading):
        """重写section标题"""
        if heading == "positional arguments":
            heading = "位置参数"
        elif heading == "options":
            heading = "可选参数"
        super().start_section(heading)

    def add_usage(self, usage, actions, groups, prefix=None):
        """完全重写usage生成逻辑"""
        if prefix is None:
            prefix = '用法：'
        super().add_usage(usage, actions, groups, prefix)

    def _format_action(self, action):
        """重写帮助文本中的帮助提示"""
        help_text = action.help
        if "%(default)" in (help_text or ""):
            help_text = help_text.replace("(default: %(default)s)", "默认值：%(default)s")
        if help_text and "show this help message and exit" in help_text:
            help_text = "显示帮助信息并退出"
        action.help = help_text
        return super()._format_action(action)


def translate(message):
    translate_map = {
        "the following arguments are required": "以下参数是必需的",
        "argument command": "参数命令",
        "invalid choice": "无效选择",
        "choose from": "仅可选择"
    }
    for original, chinese in translate_map.items():
        message = message.replace(original, chinese)
    return message


class ChineseArgumentParser(argparse.ArgumentParser):
    def __init__(self, prog=None, usage=None, description=None, epilog=None, parents=None,
                 formatter_class=ChineseHelpFormatter, prefix_chars='-', fromfile_prefix_chars=None,
                 argument_default=None, conflict_handler='error', add_help=True, allow_abbrev=True, exit_on_error=True):
        if parents is None:
            parents = []
        super().__init__(prog, usage, description, epilog, parents, formatter_class, prefix_chars,
                         fromfile_prefix_chars, argument_default, conflict_handler, add_help, allow_abbrev,
                         exit_on_error)

    def error(self, message):
        self.print_help()
        self.exit(2, f"{self.prog}: 错误: {translate(message)}\n")


def json_print(binary):
    print(json.dumps(binary, indent=2, ensure_ascii=False))


def check_cookies_file():
    # 定义文件名
    filename = "cookies.json"

    # 检查文件是否存在
    if os.path.exists(filename):
        try:
            # 尝试读取并解析 JSON 文件
            with open(filename, 'r', encoding='utf-8') as f:
                cookies_data = json.load(f)

            # 检查必需的字段是否存在且不为空
            required_fields = ['dev-code', 'rain-session']
            for field in required_fields:
                if field not in cookies_data or not cookies_data[field]:
                    print(f"cookies.json 错误: '{field}' 字段缺失或为空")
                    sys.exit(1)

            # print("cookies.json 文件有效")
            return True

        except json.JSONDecodeError:
            print("错误: cookies.json 文件不是有效的 JSON 格式")
            sys.exit(1)
        except Exception as e:
            print(f"错误: 读取 cookies.json 时发生意外错误 - {str(e)}")
            sys.exit(1)
    else:
        # 文件不存在，创建新文件
        default_data = {
            "dev-code": "",
            "rain-session": ""
        }

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=4)
            print("cookies.json 文件已创建，请按照文档说明填写 dev-code 和 rain-session")
            sys.exit(0)
        except Exception as e:
            print(f"错误: 无法创建 cookies.json 文件 - {str(e)}")
            sys.exit(1)


def print_program_info():
    print(f"""{'=' * 18}
雨云自动签到程序 v1.0.0
https://github.com/FalseHappiness/RainyunCheckIn
{'=' * 18}""")


parser = ChineseArgumentParser(
    formatter_class=ChineseHelpFormatter,
    description="雨云自动签到程序 https://github.com/FalseHappiness/RainyunCheckIn",
    epilog="示例: python app.py check_in --auto"
)

parser.add_argument(
    "command",
    choices=["web", "check_in", 'status'],
    help="要执行的命令（web: 开启网页, check_in: 签到, status: 获取签到状态）"
)
parser.add_argument(
    "-a", "--auto",
    action="store_true",
    help="是否开启自动模式（命令为 check_in 时生效，默认关闭）"
)
parser.add_argument(
    "-f", "--force",
    action="store_true",
    help="是否跳过签到状态检测（命令为 check_in 时生效，默认关闭）"
)
parser.add_argument(
    "-p", "--port",
    type=str,
    default=31278,
    help="网页端口（命令为 web 时生效，默认为 31278）"
)

args = parser.parse_args()

print_program_info()

check_cookies_file()

with sync_playwright() as p:
    if not Path(p.webkit.executable_path).exists():
        if is_bundle:
            print('打包时缺少打包 Playwright Webkit')
            sys.exit(0)
        print("Playwright Webkit 未安装，正在安装...")
        subprocess.run(["playwright", "install", "webkit"], check=True)
        print("Playwright WebKit 安装完成！")

command = args.command

if command == 'check_in':
    auto = args.auto
    print(f"执行{'自动' if auto else '手动'}签到")
    import main

    if args.force:
        print('跳过签到状态检测')
    else:
        print('进行签到状态检测')
        status = main.get_check_in_status()
        if 'check_in' in status:
            if status.get('check_in'):
                print('已签到')
                sys.exit(0)
            else:
                print('未签到')
        else:
            print('签到状态检测失败')
            json_print(status)
    if auto:
        print('请等待')
        start_time = time.time()
        result = main.auto_check_in(True)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"自动签到执行耗时: {execution_time:.4f} 秒")
    else:
        captcha = None
        while True:
            try:
                text = f"请打开 {Path(base_path) / 'captcha.html'} 完成验证码，并输入显示的base64验证码: " if captcha is None else "验证码错误，请重新输入: "
                captcha = json.loads(base64.b64decode(input(text)))
                if captcha.get('randstr') or captcha.get('ticket'):
                    break
            except json.JSONDecodeError:
                pass
            captcha = ''
        result = main.check_in(captcha)
    print('签到结果: ' + ('签到成功' if result.get('code') == 200 else ''))
    json_print(result)
elif command == 'web':
    from web import app

    app.run(host='localhost', port=args.port, debug=False)
elif command == 'status':
    import main

    print('检测签到状态...')
    status = main.get_check_in_status()
    if 'check_in' in status:
        if status.get('check_in'):
            print('已签到')
        else:
            print('未签到')
    else:
        print('签到状态检测失败')
        json_print(status)
