import argparse
import base64
import binascii
import signal
import sys
import time
from pathlib import Path

import src.utils as utils
from src.auth_process import AuthProcess
from src.utils import json_parse
from src.version import PROGRAM_VERSION


def handle_exit(_, __):
    print("\n退出程序")
    sys.exit(0)


# 注册信号处理函数
signal.signal(signal.SIGINT, handle_exit)  # Ctrl+C
signal.signal(signal.SIGTERM, handle_exit)  # kill 命令默认发送的信号

is_bundle = utils.is_bundle()

base_path = utils.get_base_path()


# print(
#     utils.is_bundle(), utils.is_nuitka(), utils.is_pyinstaller(),
#     utils.get_base_path(), utils.get_program_base_path()
# )


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
    print(utils.json_stringify(binary, indent=2))


def print_program_info():
    print(f"""{'=' * 18}
雨云自动签到程序 v{PROGRAM_VERSION}
https://github.com/FalseHappiness/RainyunCheckIn
{'=' * 18}""")


parser = ChineseArgumentParser(
    formatter_class=ChineseHelpFormatter,
    description=f"雨云自动签到程序 v{PROGRAM_VERSION} https://github.com/FalseHappiness/RainyunCheckIn",
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
parser.add_argument(
    "-m", "--method",
    type=str,
    default='template',
    choices=['template', 'brute', 'speed'],
    help="匹配背景块与需选块的方法（命令为 check_in 且开启 自动签到模式 时生效，默认为 template）"
)
parser.add_argument(
    "-c", "--config",
    type=str,
    default='',
    help="设置 config 文件路径，默认为程序同目录 config.json"
)

args = parser.parse_args()

print_program_info()

command = args.command

config_path = (Path(utils.get_program_base_path()) / 'config.json').resolve()

if args.config:
    config_path = Path(args.config).resolve()

if command == 'check_in':
    from src.main import MainLogic, check_in, get_check_in_status

    main = MainLogic(config_path)

    auto = args.auto
    print(f"执行{'自动' if auto else '手动'}签到")

    auth_process = AuthProcess(main.config, main.common_headers)

    for auth_info in auth_process.enumerate():
        name = auth_info.name
        if auth_process.multi:
            print(f"=== 执行 {name} ===")

        if auth_info.error:
            print("错误")
            json_print(auth_info.error)
        else:
            if args.force:
                print('跳过签到状态检测')
            else:
                print('进行签到状态检测...')
                status = get_check_in_status(auth_info)
                if 'check_in' in status:
                    if status.get('check_in'):
                        print('已签到')
                        if auth_process.multi:
                            print()
                        continue
                    else:
                        print('未签到')
                else:
                    print('签到状态检测失败')
                    json_print(status)
            if auto:
                print('请等待执行自动签到')
                start_time = time.time()
                result = main.auto_check_in(auth_info, True, args.method)
                end_time = time.time()
                execution_time = end_time - start_time
                print(f"自动签到执行耗时: {execution_time:.4f} 秒")
            else:
                captcha = None
                while True:
                    try:
                        text = f"请打开 {Path(base_path) / 'static' / 'captcha.html'} 完成验证码，并输入显示的 Base64 验证码: " if captcha is None else "验证码错误，请重新输入: "
                        captcha = json_parse(base64.b64decode(input(text)), else_none=True) or {}
                        if captcha.get('randstr') or captcha.get('ticket'):
                            break
                    except binascii.Error:
                        pass
                    captcha = ''
                result = check_in(captcha, auth_info)
            print('签到结果: ' + ('签到成功' if result.get('code') == 200 else ''))
            json_print(result)

        if auth_process.multi:
            print()
elif command == 'web':
    import src.web as web

    web.config_path = config_path

    web.run_main(host='localhost', port=args.port)
elif command == 'status':
    from src.main import MainLogic, get_check_in_status

    main = MainLogic(config_path)

    auth_process = AuthProcess(main.config, main.common_headers)

    print('检测签到状态...')
    for auth_info in auth_process.enumerate():
        name = f"{auth_info.name}: " if auth_process.multi else ''
        status = get_check_in_status(auth_info)
        if 'check_in' in status:
            if status.get('check_in'):
                print(f"{name}已签到")
            else:
                print(f"{name}未签到")
        else:
            print(f"{name}签到状态检测失败")
            json_print(status)
