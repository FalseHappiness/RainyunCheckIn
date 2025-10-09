import base64
import binascii
import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import warnings

import requests
from fastapi import FastAPI, Request, Depends, HTTPException, UploadFile
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, RedirectResponse
import uvicorn

config_path = 'config.json'

if __name__ == '__main__':
    # 将项目根目录添加到 sys.path
    project_root = Path(__file__).parent.parent
    sys.path.append(str(project_root))
    config_path = str(project_root / "config.json")

from src.ICR import find_part_positions, main as icr_main
from src.utils import get_base_path

from src.main import MainLogic

app = FastAPI(
    title="RainyunCheckIn API",
    description="雨云自动签到 API 接口",
    version="1.5.1",
    terms_of_service="https://github.com/FalseHappiness/RainyunCheckIn",
    license_info={
        "name": "MIT",
        "url": "https://github.com/FalseHappiness/RainyunCheckIn/blob/main/LICENSE",
    },
    docs_url=None,  # 禁用 Swagger UI
    redoc_url=None,  # 禁用 ReDoc
)


# 访问 /docs 时跳转到第三方页面
@app.get("/docs", include_in_schema=False)
async def redirect_to_external_docs():
    return RedirectResponse("https://rainyun-check-in.apifox.cn/1_5_0", status_code=301)


# 忽略警告
warnings.filterwarnings("ignore", message="Duplicate Operation ID")


def make_err(err_msg):
    return {"error": err_msg}


# 捕获所有异常
@app.exception_handler(Exception)
async def universal_exception_handler(_: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={"error": str(exc)}
    )


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )


# 根路由返回HTML文件
@app.get("/", response_class=HTMLResponse)
async def serve_html():
    static_dir = Path(get_base_path()) / 'static'
    return FileResponse(static_dir / "index.html")


def json_parse(json_str, else_none=True):
    data = None if else_none else json_str
    try:
        if isinstance(json_str, str):
            data = json.loads(json_str)
    except json.JSONDecodeError:
        pass
    return data


# 通用参数解析器
async def parse_params(request: Request) -> Dict[str, Any]:
    """
    通用参数解析器，支持表单、JSON和查询参数
    """
    params: Dict[str, Any] = {}

    # 添加查询参数
    query_params = dict(request.query_params)
    params.update(query_params)

    # 尝试解析表单数据
    form_data = await request.form()
    if form_data:
        params.update(form_data)

    # 尝试解析JSON体
    try:
        json_body = await request.json()
        if json_body:
            params.update(json_body)
    except ValueError:
        pass

    return params


# 解析从 API 传入的配置数据
async def parse_api_config(request: Request, params: Optional[dict] = None) -> dict:
    def raise_error(e):
        raise HTTPException(status_code=200, detail=make_err(e))

    params = params or await parse_params(request)

    data = {}
    params_auth = params.get('auth', None)
    if params_auth is not None:
        if not isinstance(params_auth, dict):
            raise_error("参数错误：auth 必须是对象")
        data['auth'] = params_auth

    auth = {}
    x_api_key = params.get('x_api_key', None) or params.get('x-api-key', None)
    if x_api_key is not None:
        if not x_api_key:
            raise_error("参数错误：x_api_key 如果传入，则不能为空")
        auth['x-api-key'] = x_api_key

    rain_session = params.get('rain_session', None) or params.get('rain-session', None)
    dev_code = params.get('dev_code', None) or params.get('dev-code', None)
    if rain_session is not None or dev_code is not None:
        if not rain_session or not dev_code:
            raise_error("参数错误：rain_session、dev_code 如果要提供，必须同时提供且不能为空")
        auth['rain-session'] = rain_session
        auth['dev-code'] = dev_code

    if auth:
        data['auth'] = auth

    params_headers = params.get('headers', None)
    if params_headers is not None:
        if not isinstance(params_headers, dict) and not isinstance(params_headers, list):
            raise_error("参数错误：headers 必须是对象或数组")
        data['headers'] = params_headers

    return data


# 解析主逻辑类
async def parse_main_logic(request: Request) -> MainLogic:
    """
    解析由 API 传入的 Config 配置，默认使用服务器配置文件中的配置
    """
    return MainLogic(config_path, await parse_api_config(request))


# 解析无需认证的主逻辑类
async def parse_na_main(request: Request):
    params = await parse_params(request)
    main = MainLogic(config_path, params, no_need_auth=True)
    aid = params.get('aid', None)
    if aid is not None:
        aid = str(aid)

        if not aid.isdigit():
            raise HTTPException(status_code=200, detail=make_err("参数错误：aid 所有字符必须为数字"))

        main.captcha_config['aid'] = aid
    return main


# 签到路由

@app.api_route('/check_in', methods=['GET', 'POST'])
async def handle_check_in(params=Depends(parse_params), main=Depends(parse_main_logic)):
    """
    签到接口
    """
    return main.check_in(params)


def bool_value(value):
    return str(value).lower() in ('true', '1', 'yes', 'on')


# 自动签到路由
@app.api_route('/auto_check_in', methods=['GET', 'POST'])
async def handle_auto_check_in(params=Depends(parse_params), main=Depends(parse_main_logic)):
    """
    自动签到接口
    """
    return main.auto_check_in(bool_value(params.get("force", "")), params.get('method', 'template'))


# 检查签到状态路由
@app.api_route('/is_check_in', methods=['GET', 'POST'])
async def get_check_in_status(main=Depends(parse_main_logic)):
    """
    检测签到状态
    """
    return main.get_check_in_status()


# 获取验证码数据
@app.api_route('/get_captcha_data', methods=['GET', 'POST'])
async def handle_get_captcha_data(main=Depends(parse_na_main)):
    """
    获取验证码数据
    """
    return main.get_captcha_data()


def get_b64_img(bytes_data, data_url=True):
    return f"{'data:image/jpeg;base64,' if data_url else ''}{base64.b64encode(bytes_data).decode('utf-8')}"


# 获取验证码图片
@app.api_route('/get_captcha_images', methods=['GET', 'POST'])
async def handle_get_captcha_images(params=Depends(parse_params), main=Depends(parse_na_main)):
    """
    获取验证码图片
    """
    data = params.get('data', None)
    if data is not None:
        if isinstance(data, str):
            data = json_parse(data)
        if not isinstance(data, dict):
            return {'error': "参数错误：data 必须为对象或 JSON 字符串"}

    return_type = str(params.get('return_type', 'data_url')).lower()
    if return_type not in ['data_url', 'base64', 'url', 'data_uri']:
        return {'error': "参数错误：return_type 必须为以下值之一：data_url, base64, url"}

    bg_url, sprite_url = main.get_captcha_urls(data or main.get_captcha_data())

    if return_type == 'url':
        return {
            'bg': bg_url,
            'sprite': sprite_url
        }

    bg_img, sprite_img = main.get_captcha_images(bg_url=bg_url, sprite_url=sprite_url)
    return {
        'bg': get_b64_img(bg_img, return_type != 'base64'),
        'sprite': get_b64_img(sprite_img, return_type != 'base64')
    }


async def parse_image_data(image_data: Any) -> bytes:
    """
    将各种格式的图片数据转换为 bytes
    支持: 表单文件、base64字符串、data URL、http URL
    """
    # 如果是上传的文件
    if isinstance(image_data, UploadFile):
        return await image_data.read()

    # 如果是字符串
    if isinstance(image_data, str):
        # 检查是否是 data URL (data:image/...;base64,...)
        if image_data.startswith('data:'):
            match = re.match(r'data:image/\w+;base64,(.*)', image_data)
            if not match:
                raise HTTPException(status_code=200, detail=make_err("无效的data URL格式"))
            base64_str = match.group(1)
            try:
                return base64.b64decode(base64_str)
            except Exception:
                raise HTTPException(status_code=200, detail=make_err("无效的base64数据"))

        # 检查是否是普通base64字符串
        try:
            # 尝试解码base64
            return base64.b64decode(image_data)
        except (binascii.Error, ValueError):
            pass

        # 检查是否是http/https URL
        parsed = urlparse(image_data)
        if parsed.scheme in ('http', 'https'):
            try:
                response = requests.get(image_data)
                response.raise_for_status()
                return response.content
            except Exception as e:
                raise HTTPException(status_code=200, detail=make_err(f"无法从URL获取图片: {str(e)}"))

    # 如果以上都不是，尝试直接作为bytes返回
    if isinstance(image_data, bytes):
        return image_data

    raise HTTPException(status_code=200, detail=make_err("不支持的图片格式"))


@app.api_route('/find_captcha_positions', methods=['GET', 'POST'])
async def handle_find_captcha_positions(params=Depends(parse_params), main=Depends(parse_na_main)):
    """
    计算验证码位置
    """
    bg = params.get('bg', None)
    sprite = params.get('sprite', None)
    data = params.get('data', None)
    match_method = params.get('method', 'template')
    detailed = bool_value(params.get('detailed', False))

    if isinstance(data, str):
        data = json_parse(data)
    if isinstance(data, dict):
        # noinspection PyBroadException
        try:
            bg, sprite = main.get_captcha_images(data)
        except:
            pass

    if not bg or not sprite:
        if data is None:
            bg, sprite = main.get_captcha_images(main.get_captcha_data())
        else:
            return {'error': "无法通过验证码数据解析 bg 和 sprite"} if data else {
                'error': "参数错误：bg 或 sprite 不能为空"}

    if match_method not in ['template', 'brute', 'speed']:
        return {'error': "参数错误：method 必须为以下值：template, brute, speed"}

    bg = await parse_image_data(bg)
    sprite = await parse_image_data(sprite)
    if detailed:
        data = []
        matches = icr_main(bg, sprite, match_method)
        for match in matches:
            x, y, w, h = match['bg_rect']
            data.append({
                'sprite_idx': match['sprite_idx'],
                'angle': match['angle'],
                'sprite_rect': match['sprite_rect'],
                'bg_rect': match['bg_rect'],
                'position': (x + w / 2, y + h / 2)
            })
        return {"data": data}
    else:
        return {"positions": find_part_positions(bg, sprite, match_method)}


@app.api_route('/complete_captcha', methods=['GET', 'POST'])
async def handle_complete_captcha(params=Depends(parse_params), main=Depends(parse_na_main)):
    """
    完成验证码
    """
    match_method = params.get('method', 'template')
    data = params.get('data', None)

    if match_method not in ['template', 'brute', 'speed']:
        return {'error': "参数错误：method 必须为以下值：template, brute, speed"}

    if isinstance(data, str):
        data = json_parse(data)
    if data is not None and not isinstance(data, dict):
        return {'error': "参数错误：data 必须为对象"}

    return main.complete_captcha(data, match_method=match_method)


@app.api_route('/build_verify_form_data', methods=['GET', 'POST'])
async def handle_build_verify_form_data(params=Depends(parse_params), main=Depends(parse_na_main)):
    """
    构造请求 https://turing.captcha.qcloud.com/cap_union_new_verify 的表单数据
    """
    data = params.get('data', None)
    positions = params.get('positions', None)
    match_method = params.get('method', 'template')

    if positions is None and match_method not in ['template', 'brute', 'speed']:
        return {'error': "参数错误：method 必须为以下值：template, brute, speed"}

    if data is None:
        data = main.get_captcha_data()

    if isinstance(data, str):
        data = json_parse(data)
    if not isinstance(data, dict):
        return {'error': "参数错误：data 必须为对象"}

    if isinstance(positions, str):
        positions = json_parse(positions)
    if positions is not None and not isinstance(positions, dict):
        return {'error': "参数错误：positions 必须为数组"}

    if not positions:
        bg_img, sprite_img = main.get_captcha_images(data)
        positions = find_part_positions(bg_img, sprite_img, match_method)

    return main.build_verify_form(data, positions)


# CORS中间件
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def run_main(**params):
    uvicorn.run(app, **params)


if __name__ == '__main__':
    uvicorn.run("web:app", host='localhost', port=31278, reload=True)
