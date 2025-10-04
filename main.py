import base64
import hashlib
import os
import sys
import time
from pathlib import Path
from typing import Any
from playwright.sync_api import sync_playwright

import requests
import json

import ocr

if getattr(sys, 'frozen', False):
    # noinspection PyProtectedMember,PyUnresolvedReferences
    browser_path = Path(sys._MEIPASS) / "playwright"
else:
    browser_path = Path(__file__).parent / "playwright"

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_path)

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


# 加载和保存cookie的函数
def load_cookies():
    try:
        with open('cookies.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "dev-code": "",
            "rain-session": ""
        }


def save_cookies(cookies):
    with open('cookies.json', 'w') as f:
        json.dump(cookies, f, indent=2)


# 更新cookie的函数
def update_cookies_from_response(response, current_cookies):
    if 'set-cookie' in response.headers:
        new_cookies = current_cookies.copy()
        new_cookies.update(response.cookies.get_dict())
        save_cookies(new_cookies)
        return new_cookies
    return current_cookies


# 获取CSRF token的函数
def get_csrf_token():
    cookies = load_cookies()
    url = "https://api.v2.rainyun.com/user/csrf"

    try:
        response = requests.get(url, headers=COMMON_HEADERS, cookies=cookies, timeout=10)
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
    if not csrf_token:
        return {'error': '无法获取 CSRF 令牌。可能已经退出登录。'}

    # 准备请求头
    headers = COMMON_HEADERS.copy()
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


def auto_check_in(force=False):
    if not force:
        if get_check_in_status().get('check_in'):
            return {'error': '今日已经签到。'}
    verify = complete_captcha()
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
    if not csrf_token:
        return {'error': '无法获取 CSRF 令牌。可能已经退出登录。'}

    # 准备请求头
    headers = COMMON_HEADERS.copy()
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
    """获取数据，每次调用创建新页面"""
    playwright = sync_playwright().start()

    browser = playwright.webkit.launch(headless=True)

    browser_context = browser.new_context()

    page = browser_context.new_page()

    try:
        result = page.evaluate(tdc + """
() => {
  return [
    (window.TDC && "function" == typeof window.TDC.getData) ? window.TDC.getData(true) || "---" : "------",
    (window.TDC && "function" == typeof window.TDC.getInfo) ? window.TDC.getInfo().info || "---" : "------",
  ]
}
        """)
        return result[0], result[1]
    finally:
        # 确保关闭
        page.close()
        browser_context.close()
        browser.close()
        playwright.stop()


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


def complete_captcha():
    data = get_captcha_data()
    bg_img, sprite_img = get_captcha_images(data)

    form_data = build_verify_form(data, [])

    for i in range(10):
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
            data['sess'] = result['sess']

        data = refresh_captcha_data(data)

        if data.get('error'):
            return {'error': '刷新验证码失败。'}

        bg_img, sprite_img = get_captcha_images(data)

    return {'error': '超出重试次数。'}
