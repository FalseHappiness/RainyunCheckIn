import json
from typing import Dict, Union

import requests

from src.utils import json_stringify


def load_header_auth(auth, headers: Dict[str, str] = None, boolean: bool = False, csrf_token=None) \
        -> Union[Dict[str, str], bool]:
    """加载认证信息到请求头"""
    if headers is None:
        headers = {}
    headers = headers.copy()
    headers["Content-Type"] = "application/json"
    key = auth.get('x-api-key', None)
    dev_token = auth.get('dev-code', None)

    if key:
        headers['x-api-key'] = str(key)
        if dev_token:
            headers['rain-dev-token'] = str(dev_token)
        if csrf_token:
            headers["x-csrf-token"] = csrf_token
        return True if boolean else headers

    return False if boolean else headers


def load_cookies_auth(auth) -> Dict[str, str]:
    """加载cookie认证信息"""
    if load_header_auth(auth, {}, True):
        return {}
    return auth


class AuthInfo:
    def __init__(self, name=None, headers=None, cookies=None, update_cookies=None, error=None):
        self.name = name
        self.headers = headers
        self.cookies = cookies
        self.update_cookies = update_cookies

        self.error = error

    def get(self):
        return self.name, self.headers, self.cookies, self.update_cookies


class AuthProcess:
    def __init__(self, config, headers):
        auth = config.get('auth', {}).copy()
        self.multi = isinstance(auth, list)
        self.common_headers = headers
        self.config = config
        self.auth_list = auth if self.multi else [auth]

    def update_cookies_from_response(self, auth, response, current_cookies: Dict[str, str]) -> Dict[str, str]:
        """从响应中更新cookie"""
        if 'set-cookie' in response.headers:
            new_cookies = current_cookies.copy()
            new_cookies.update(response.cookies.get_dict())
            auth.update(new_cookies)
            self.config.save_auth(self.auth_list if self.multi else self.auth_list[0])
            return new_cookies
        return current_cookies

    # 获取CSRF token的函数
    def get_csrf_token(self, auth):
        cookies = load_cookies_auth(auth)

        try:
            response = requests.get(
                "https://api.v2.rainyun.com/user/csrf",
                headers=load_header_auth(auth, self.common_headers),
                cookies=cookies,
                timeout=10
            )
            cookies = self.update_cookies_from_response(auth, response, cookies)

            if response.status_code != 200:
                try:
                    return {
                        "error": f"获取 CSRF 令牌 {response.status_code} 错误：{json_stringify(response.json())}"
                    }, cookies
                except json.decoder.JSONDecodeError:
                    response.raise_for_status()

            result = response.json()

            if result.get('code', 0) != 200:
                return {
                    "error": f"获取 CSRF 令牌错误：{json_stringify(result)}"
                }, cookies

            if 'data' in result and isinstance(result['data'], str):
                return result.get('data'), cookies

            return {
                "error": "获取 CSRF 令牌错误：返回内容未包含 CSRF：" + json_stringify(result)
            }, cookies
        except (requests.exceptions.HTTPError, requests.exceptions.RequestException, json.decoder.JSONDecodeError) as e:
            return {"error": f"获取 CSRF 令牌错误：{str(e)}"}, cookies

    def enumerate(self):
        enum = []
        for i, auth in enumerate(self.auth_list):
            auth_name = str(auth.get('name', ''))
            auth_display_name = f"{auth_name if auth_name else f'认证配置'}({i + 1})"

            use_api_key = load_header_auth(auth, boolean=True)
            cookies = {}
            csrf_token = None

            if not use_api_key:
                csrf_token, cookies = self.get_csrf_token(auth)

                if not isinstance(csrf_token, str):
                    enum.append(AuthInfo(name=auth_display_name, error=csrf_token))
                    continue

            headers = load_header_auth(auth, self.common_headers, csrf_token=csrf_token)

            def update_cookies(res):
                self.update_cookies_from_response(auth, res, cookies)

            enum.append(AuthInfo(auth_display_name, headers, cookies, update_cookies))

        return enum
