import base64
import hashlib

import time
from pathlib import Path
from typing import Any
import requests
import json

from py_mini_racer import MiniRacer

from src.ICR import find_part_positions
from src.config import Config
from src.utils import get_base_path

base_path = get_base_path()


def get_collect_and_eks(tdc):
    ctx = MiniRacer()

    with open(Path(base_path) / 'static' / 'env.js', 'r', encoding='utf-8') as f:
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


class MainLogic:
    def __init__(self, config_path='config.json', config_data=None, no_need_auth=False):
        # 公共请求头
        self.common_headers = {
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
        # 验证码配置
        self.captcha_config = {
            'base_url': "https://turing.captcha.qcloud.com",
            'aid': '2039519451'
        }

        if no_need_auth:
            if not isinstance(config_data, dict):
                config_data = {}
            config_data['auth'] = {
                'x-api-key': 'No need auth'
            }

        self.config = Config(config_path, config_data)

        self.common_headers = self.common_headers | self.config.get('headers', {})
        pass

    # 获取CSRF token的函数
    def get_csrf_token(self, ):
        cookies = self.config.load_cookies_auth()
        url = "https://api.v2.rainyun.com/user/csrf"

        try:
            response = requests.get(url, headers=self.config.load_header_auth(self.common_headers), cookies=cookies,
                                    timeout=10)
            cookies = self.config.update_cookies_from_response(response, cookies)

            if response.status_code == 200:
                return response.json().get('data'), cookies
            return None, cookies
        except requests.exceptions.RequestException:
            return None, cookies

    def check_in(self, data):
        if not isinstance(data, dict):
            return {'error': '未提供数据。'}

        data = {
            "task_name": "每日签到",
            "verifyCode": "",
            "vticket": data.get('ticket', None) or data.get('vticket', None),
            "vrandstr": data.get('randstr', None) or data.get('vrandstr', None)
        }

        # 获取CSRF token并更新cookies
        csrf_token, cookies = self.get_csrf_token()
        if csrf_token is None:
            return {'error': '无法获取 CSRF 令牌。可能已经退出登录。'}

        # 准备请求头
        headers = self.config.load_header_auth(self.common_headers)
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
            self.config.update_cookies_from_response(response, cookies)

            # 返回API的响应
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}

    def auto_check_in(self, force=False, match_method='template'):
        if not force:
            if self.get_check_in_status().get('check_in'):
                return {'error': '今日已经签到。'}
        verify = self.complete_captcha(match_method=match_method)
        if verify.get('error', None):
            return {'error': verify['error']}

        return self.check_in({
            "task_name": "每日签到",
            "verifyCode": "",
            "vticket": verify['ticket'],
            "vrandstr": verify['randstr']
        })

    def get_check_in_status(self):
        # 获取CSRF token并更新cookies
        csrf_token, cookies = self.get_csrf_token()
        if csrf_token is None:
            return {'error': '无法获取 CSRF 令牌。可能已经退出登录。'}

        # 准备请求头
        headers = self.config.load_header_auth(self.common_headers)
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
            self.config.update_cookies_from_response(response, cookies)

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

    def get_captcha_data(self):
        """获取验证码数据"""
        params = {
            "aid": self.captcha_config.get('aid'),
            "protocol": "https",
            "accver": "1",
            "showtype": "popup",
            "ua": base64.b64encode(self.common_headers['user-agent'].encode()).decode(),
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
            "entry_url": "https://turing.captcha.gtimg.com/1/template/drag_ele.html",
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
                f"{self.captcha_config.get('base_url')}/cap_union_prehandle",
                params=params,
                headers=self.common_headers
            )
            response.raise_for_status()

            # 解析JSON数据
            json_str = response.text.strip()[1:-1]  # 移除括号
            data = json.loads(json_str)

            return data
        except Exception as e:
            raise Exception(f"获取验证码数据失败: {e}")

    def refresh_captcha_data(self, old_data):
        try:
            # 获取验证码配置
            response = requests.post(
                f"{self.captcha_config.get('base_url')}/cap_union_new_getsig",
                data={
                    'sess': old_data.get('sess')
                },
                headers=self.common_headers
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

    def get_captcha_urls(self, data, bg_url=None, sprite_url=None):
        bg_url = bg_url or (
                self.captcha_config.get('base_url') + data["data"]["dyn_show_info"]["bg_elem_cfg"]["img_url"])
        sprite_url = sprite_url or (self.captcha_config.get('base_url') + data["data"]["dyn_show_info"]["sprite_url"])
        return bg_url, sprite_url

    def get_captcha_images(self, data=None, bg_url=None, sprite_url=None) \
            -> tuple[bytes | Any, bytes | Any] | tuple[None, None]:
        # 获取图片URL
        bg_url, sprite_url = self.get_captcha_urls(data, bg_url, sprite_url)
        try:
            # 下载图片
            return (
                requests.get(bg_url, headers=self.common_headers).content,
                requests.get(sprite_url, headers=self.common_headers).content
            )
        except Exception as e:
            raise Exception(f"获取验证码图片失败: {e}")

    def build_verify_form(self, data, positions, old_verify=None):
        if old_verify is None:
            comm_captcha_cfg = data['data']['comm_captcha_cfg']
            tdc_content = requests.get(
                self.captcha_config['base_url'] + comm_captcha_cfg['tdc_path'],
                headers=self.common_headers
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

    def complete_captcha(self, data=None, retry=10, match_method='template'):
        data = data or self.get_captcha_data()
        bg_img, sprite_img = self.get_captcha_images(data)

        form_data = self.build_verify_form(data, [])

        for i in range(retry):
            positions = find_part_positions(bg_img, sprite_img, match_method)

            form_data = self.build_verify_form(data, positions, form_data)

            response = requests.post(
                self.captcha_config['base_url'] + '/cap_union_new_verify',
                data=form_data,
                headers=self.common_headers
            )
            response.raise_for_status()  # 检查请求是否成功

            result = response.json()

            if int(result['errorCode']) == 0:
                return result
            else:
                if i < retry:
                    data['sess'] = result['sess']

                    data = self.refresh_captcha_data(data)

                    if data.get('error'):
                        return {'error': '刷新验证码失败。'}

                    bg_img, sprite_img = self.get_captcha_images(data)

        return {'error': '超出重试次数。'}
