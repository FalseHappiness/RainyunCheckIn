import base64
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
import requests
import json

import cv2
import numpy as np

from playwright.sync_api import sync_playwright, Position
from py_mini_racer import MiniRacer

import ocr
from utils import get_base_path, is_nuitka, is_bundle

base_path = get_base_path()

if not is_nuitka():
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(Path(base_path) / "playwright")

# 公共请求头
COMMON_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Not;A=Brand\";v=\"99\", \"Microsoft Edge\";v=\"139\", \"Chromium\";v=\"139\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "referer": "https://app.rainyun.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0"
}


def load_header_auth(headers, boolean=False):
    headers = headers.copy()
    try:
        with open('auth.json', 'r') as f:
            auth = json.load(f)
            key = auth.get('x-api-key', None)
            dev_token = auth.get('dev-code', None)
            if key:
                headers['x-api-key'] = key
                if dev_token:
                    headers['rain-dev-token'] = dev_token
                return True if boolean else headers

    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return False if boolean else headers


# 加载和保存cookie的函数
def load_cookies_auth():
    try:
        if load_header_auth({}, True):
            return {}
        else:
            with open('auth.json', 'r') as f:
                return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "dev-code": "",
            "rain-session": ""
        }


def save_cookies_auth(cookies):
    # 如果文件不存在，直接写入
    if not os.path.exists('auth.json'):
        with open('auth.json', 'w') as f:
            json.dump(cookies, f, indent=2)
        return

    # 读取现有内容
    with open('auth.json', 'r') as f:
        existing_data = json.load(f)

    # 合并新 cookies（覆盖同名字段）
    existing_data.update(cookies)

    # 写回文件
    with open('auth.json', 'w') as f:
        json.dump(existing_data, f, indent=2)


# 更新cookie的函数
def update_cookies_from_response(response, current_cookies):
    if 'set-cookie' in response.headers:
        new_cookies = current_cookies.copy()
        new_cookies.update(response.cookies.get_dict())
        save_cookies_auth(new_cookies)
        return new_cookies
    return current_cookies


# 获取CSRF token的函数
def get_csrf_token():
    cookies = load_cookies_auth()
    url = "https://api.v2.rainyun.com/user/csrf"

    try:
        response = requests.get(url, headers=load_header_auth(COMMON_HEADERS), cookies=cookies, timeout=10)
        cookies = update_cookies_from_response(response, cookies)

        if response.status_code == 200:
            return response.json().get('data'), cookies
        return None, cookies
    except requests.exceptions.RequestException:
        return None, cookies


def check_in(data):
    if not isinstance(data, dict):
        return {'error': '未提供数据。'}

    if data.get('randstr') and data.get('ticket'):
        data = {
            "task_name": "每日签到",
            "verifyCode": "",
            "vticket": data['ticket'],
            "vrandstr": data['randstr']
        }

    # 获取CSRF token并更新cookies
    csrf_token, cookies = get_csrf_token()
    if csrf_token is None:
        return {'error': '无法获取 CSRF 令牌。可能已经退出登录。'}

    # 准备请求头
    headers = load_header_auth(COMMON_HEADERS)
    headers.update({
        "content-type": "application/json",
        "x-csrf-token": csrf_token
    })

    try:
        # 转发请求到目标API
        response = requests.post(
            "https://api.v2.rainyun.com/user/reward/tasks",
            headers=headers,
            cookies=cookies,
            json=data,
            timeout=10
        )

        # 更新cookie
        update_cookies_from_response(response, cookies)

        # 返回API的响应
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def auto_check_in(force=False, browser_captcha=False):
    if not force:
        if get_check_in_status().get('check_in'):
            return {'error': '今日已经签到。'}
    verify = complete_captcha_browser() if browser_captcha else complete_captcha()
    if verify.get('error', None):
        return {'error': verify['error']}

    return check_in({
        "task_name": "每日签到",
        "verifyCode": "",
        "vticket": verify['ticket'],
        "vrandstr": verify['randstr']
    })


def get_check_in_status():
    # 获取CSRF token并更新cookies
    csrf_token, cookies = get_csrf_token()
    if csrf_token is None:
        return {'error': '无法获取 CSRF 令牌。可能已经退出登录。'}

    # 准备请求头
    headers = load_header_auth(COMMON_HEADERS)
    headers.update({
        "x-csrf-token": csrf_token
    })

    try:
        # 获取任务列表
        response = requests.get(
            "https://api.v2.rainyun.com/user/reward/tasks",
            headers=headers,
            cookies=cookies,
            timeout=10
        )

        # 更新cookie
        update_cookies_from_response(response, cookies)

        if response.status_code == 200:
            data = response.json()
            tasks = data.get('data', [])
            for task in tasks:
                if task.get('Name') == '每日签到' and task.get('Status') == 2:
                    return {'check_in': True}
            return {'check_in': False}
        return {'error': 'Failed to get tasks', 'code': response.status_code}
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


CAPTCHA_CONFIG = {
    'base_url': "https://turing.captcha.qcloud.com",
    'aid': '2039519451'
}


def get_captcha_data():
    """获取验证码数据"""
    params = {
        "aid": CAPTCHA_CONFIG.get('aid'),
        "protocol": "https",
        "accver": "1",
        "showtype": "popup",
        "ua": base64.b64encode(COMMON_HEADERS['user-agent'].encode()).decode(),
        "noheader": "1",
        "fb": "1",
        "aged": "0",
        "enableAged": "0",
        "enableDarkMode": "0",
        "grayscale": "1",
        "clientype": "2",
        "cap_cd": "",
        "uid": "",
        "lang": "zh-cn",
        "entry_url": "http://localhost/",
        "elder_captcha": "0",
        "js": "/tcaptcha-frame.97a921e6.js",
        "login_appid": "",
        "wb": "1",
        "subsid": "9",
        "callback": "",
        "sess": ""
    }

    try:
        # 获取验证码配置
        response = requests.get(
            f"{CAPTCHA_CONFIG.get('base_url')}/cap_union_prehandle",
            params=params,
            headers=COMMON_HEADERS
        )
        response.raise_for_status()

        # 解析JSON数据
        json_str = response.text.strip()[1:-1]  # 移除括号
        data = json.loads(json_str)

        return data
    except Exception as e:
        print(f"获取验证码失败: {e}")
        return None


def refresh_captcha_data(old_data):
    try:
        # 获取验证码配置
        response = requests.post(
            f"{CAPTCHA_CONFIG.get('base_url')}/cap_union_new_getsig",
            data={
                'sess': old_data.get('sess')
            },
            headers=COMMON_HEADERS
        )
        response.raise_for_status()

        # 解析JSON数据
        data = response.json()

        if int(data.get('ret', -1)) == 0:
            old_data['data']['dyn_show_info'] = data['data']
            old_data['sess'] = data['sess']

        return old_data
    except Exception as e:
        raise Exception(f"获取验证码失败: {e}")


def get_captcha_images(data) -> tuple[bytes | Any, bytes | Any] | tuple[None, None]:
    # 获取图片URL
    bg_url = CAPTCHA_CONFIG.get('base_url') + data["data"]["dyn_show_info"]["bg_elem_cfg"]["img_url"]
    sprite_url = CAPTCHA_CONFIG.get('base_url') + data["data"]["dyn_show_info"]["sprite_url"]
    try:
        # 下载图片
        return (
            requests.get(bg_url, headers=COMMON_HEADERS).content,
            requests.get(sprite_url, headers=COMMON_HEADERS).content
        )
    except Exception as e:
        raise Exception(f"获取验证码图片失败: {e}")


def find_md5_collision(target_md5, prefix):
    start_time = time.time()
    num = 0

    while True:
        current_str = prefix + str(num)
        # 计算MD5
        md5_hash = hashlib.md5(current_str.encode('utf-8')).hexdigest()

        if md5_hash == target_md5:
            end_time = time.time()
            elapsed_ms = int((end_time - start_time) * 1000)  # 转换为毫秒
            return current_str, elapsed_ms

        num += 1

        if num > 114514 * 1000:
            return prefix, int((time.time() - start_time) * 1000)


def get_collect_and_eks(tdc):
    ctx = MiniRacer()

    with open(Path(base_path) / 'env.js', 'r', encoding='utf-8') as f:
        ctx.eval(f.read())

    ctx.eval(tdc)

    ctx.eval('window.TDC && "function" == typeof window.TDC.setData && window.TDC.setData("qf_7Pf__H")')

    tdc_data = ctx.eval(
        '(window.TDC && "function" == typeof window.TDC.getData) ? window.TDC.getData(true) || "---" : "------"'
    )

    tdc_info = ctx.eval(
        '(window.TDC && "function" == typeof window.TDC.getInfo) ? window.TDC.getInfo().info || "---" : "------"'
    )
    return tdc_data, tdc_info


def build_verify_form(data, positions, old_verify=None):
    if old_verify is None:
        comm_captcha_cfg = data['data']['comm_captcha_cfg']
        tdc_content = requests.get(
            CAPTCHA_CONFIG['base_url'] + comm_captcha_cfg['tdc_path'],
            headers=COMMON_HEADERS
        ).text
        collect, eks = get_collect_and_eks(tdc_content)
        pow_answer, pow_calc_time = find_md5_collision(
            comm_captcha_cfg['pow_cfg']['md5'],
            comm_captcha_cfg['pow_cfg']['prefix'],
        )
    else:
        collect = old_verify['collect']
        eks = old_verify['eks']
        pow_answer = old_verify['pow_answer']
        pow_calc_time = old_verify['pow_calc_time']
    ans = []
    for i, coord in enumerate(positions, start=1):
        if len(coord) == 2:  # 确保每个子列表有x和y两个值
            x, y = coord
            ans.append({
                "elem_id": i,
                "type": "DynAnswerType_POS",
                "data": f"{x},{y}"
            })
    return {
        'collect': collect,
        'tlg': str(len(collect)),
        'eks': eks,
        'sess': data.get('sess'),
        'ans': json.dumps(ans),
        'pow_answer': pow_answer,
        'pow_calc_time': str(pow_calc_time)
    }


def complete_captcha(retry=10):
    data = get_captcha_data()
    bg_img, sprite_img = get_captcha_images(data)

    form_data = build_verify_form(data, [])

    for i in range(retry):
        positions = ocr.find_part_positions(
            ocr.load_and_preprocess(bg_img),
            ocr.extract_blackest_parts(ocr.load_and_preprocess(sprite_img))
        )

        form_data = build_verify_form(data, positions, form_data)

        response = requests.post(
            CAPTCHA_CONFIG['base_url'] + '/cap_union_new_verify',
            data=form_data,
            headers=COMMON_HEADERS
        )
        response.raise_for_status()  # 检查请求是否成功

        result = response.json()

        if int(result['errorCode']) == 0:
            return result
        else:
            if i < retry:
                data['sess'] = result['sess']

                data = refresh_captcha_data(data)

                if data.get('error'):
                    return {'error': '刷新验证码失败。'}

                bg_img, sprite_img = get_captcha_images(data)

    return {'error': '超出重试次数。'}


def get_image_width_opencv(image_bytes):
    """
    使用OpenCV获取图片尺寸
    """
    try:
        # 将字节数据转换为numpy数组
        nparr = np.frombuffer(image_bytes, np.uint8)
        # 解码图像
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is not None:
            height, width = image.shape[:2]
            return width, height
        return None, None
    except Exception as e:
        print(f"OpenCV处理失败: {e}")
        return None, None


def complete_captcha_browser(retry=10):
    verify = None
    try:
        with sync_playwright() as p:
            if not Path(p.webkit.executable_path).exists():
                if is_bundle():
                    print('打包时缺少打包 Playwright Webkit')
                    sys.exit(0)
                print("Playwright Webkit 未安装，正在安装...")
                subprocess.run(["playwright", "install", "webkit"], check=True)
                print("Playwright WebKit 安装完成！")

            # 启动 WebKit 浏览器
            browser = p.webkit.launch(headless=True)

            # 创建新页面
            page = browser.new_page()

            # 读取 HTML 文件内容
            with open(Path(base_path) / "captcha.html", 'r', encoding='utf-8') as file:
                html_content = file.read()

            # 将 HTML 内容设置到页面中
            page.set_content(html_content)

            # 等待页面加载
            page.wait_for_load_state("networkidle")

            # 等待iframe加载
            page.wait_for_selector("iframe")

            # 获取iframe元素
            iframe_element = page.query_selector("iframe")

            # 获取iframe的内容框架
            iframe = iframe_element.content_frame()

            for i in range(retry):
                # 获取 URL
                sprite_url = iframe.eval_on_selector(
                    ".tc-instruction-icon img",
                    "img => img.src"
                )
                bg_url = sprite_url.replace('img_index=0', 'img_index=1')

                bg_display_width = iframe.eval_on_selector(
                    "#slideBg",
                    """el => {
                        return parseInt(el.style.width);
                    }"""
                ) or 340

                bg_img, sprite_img = (
                    requests.get(bg_url).content,
                    requests.get(sprite_url).content
                )

                bg_original_width = get_image_width_opencv(bg_img)[0] or 672

                bg_scalc_rate = bg_display_width / bg_original_width

                positions = ocr.find_part_positions(
                    ocr.load_and_preprocess(bg_img),
                    ocr.extract_blackest_parts(ocr.load_and_preprocess(sprite_img))
                )

                for _, coord in enumerate(positions, start=1):
                    if len(coord) == 2:  # 确保每个子列表有x和y两个值
                        x, y = coord
                        iframe.click("#tcOperation",
                                     position=Position({'x': x * bg_scalc_rate, 'y': y * bg_scalc_rate}))
                        time.sleep(0.1)

                # 等待验证请求完成
                with page.expect_response(
                        lambda res: "https://turing.captcha.qcloud.com/cap_union_new_verify" in res.url
                ) as response_info:
                    iframe.click(".tc-action.verify-btn")
                    response = response_info.value

                if response.ok:
                    result = response.json()
                    if result.get('randstr', None) and result.get('ticket', None):
                        verify = result

                if verify:
                    break
                else:
                    if i < retry:
                        # 刷新验证码
                        with page.expect_response(
                                lambda res: "https://turing.captcha.qcloud.com/cap_union_new_getsig" in res.url):
                            iframe.click("#reload")

                        time.sleep(0.1)

            # 关闭浏览器
            browser.close()
    except Exception as e:
        return {'error': f"Playwright 完成验证码错误：{e}"}

    return verify or {'error': 'Playwright 完成验证码失败，超出重试次数。'}
