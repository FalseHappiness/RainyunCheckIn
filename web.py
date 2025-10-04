import sys
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
import os

import main

if getattr(sys, 'frozen', False):
    # noinspection PyProtectedMember,PyUnresolvedReferences
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

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
    return send_from_directory(Path(base_path), "index.html")


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


@app.route('/auto_check_in', methods=['GET'])
def handle_auto_check_in():
    force = request.args.get("force", "").lower()  # 获取参数并转为小写
    force_bool = force in ("true", "1", "yes", "on")  # 检查是否表示 True
    return jsonify(main.auto_check_in(force_bool))


# 检查签到状态路由
@app.route('/is_check_in', methods=['GET'])
def get_check_in_status():
    data = main.get_check_in_status()
    if 'error' in data:
        return jsonify(data), data.code if 'code' in data else 500
    else:
        return jsonify(data), 200


if __name__ == '__main__':
    app.run(host='localhost', port=31278, debug=True)
