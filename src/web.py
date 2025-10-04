import os
import sys
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

if __name__ == '__main__':
    # 将项目根目录添加到 sys.path
    project_root = Path(__file__).parent.parent
    sys.path.append(str(project_root))
    os.environ["CONFIG_PATH"] = str(project_root / "config.json")

from src.utils import get_base_path
import src.main as main

app = Flask(__name__)


# 允许跨域请求
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# 根路由返回HTML文件
@app.route('/')
def serve_html():
    static_dir = Path(get_base_path()) / 'static'
    return send_from_directory(static_dir, "index.html")


# 签到路由
@app.route('/check_in', methods=['POST', 'OPTIONS'])
def handle_check_in():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = main.check_in(request.get_json())

    if 'error' in data:
        return jsonify(data), 500
    else:
        return data, 200


def bool_type(value):
    return str(value).lower() in ('true', '1', 'yes', 'on')


@app.route('/auto_check_in', methods=['GET'])
def handle_auto_check_in():
    force = request.args.get("force", type=bool_type)
    return jsonify(main.auto_check_in(force))


# 检查签到状态路由
@app.route('/is_check_in', methods=['GET'])
def get_check_in_status():
    data = main.get_check_in_status()
    if 'error' in data:
        return jsonify(data), data.code if 'code' in data else 500
    else:
        return jsonify(data), 200


def run_main(**params):
    app.run(**params)


if __name__ == '__main__':
    run_main(host='localhost', port=31278, debug=True)
