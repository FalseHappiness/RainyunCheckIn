import json
import sys
from pathlib import Path


def is_bundle():
    return is_nuitka() or is_pyinstaller()


def is_nuitka():
    return "__compiled__" in globals()


def is_pyinstaller():
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_base_path():
    # noinspection PyProtectedMember,PyUnresolvedReferences
    return str(sys._MEIPASS if is_pyinstaller() else Path(__file__).absolute().parent.parent)


def get_program_base_path():
    return Path(sys.argv[0]).absolute().parent


def json_parse(json_str, else_none=True):
    data = None if else_none else json_str
    try:
        if isinstance(json_str, (str, bytes, bytearray)):
            data = json.loads(json_str)
    except json.JSONDecodeError:
        pass
    return data


def json_stringify(var, **args):
    return json.dumps(var, ensure_ascii=False, **args)
