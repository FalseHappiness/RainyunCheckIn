import os
import json
import sys
from typing import Dict, Any, Optional, Union


class Config:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._load_config()

        # 确保auth配置存在并验证
        if "auth" not in self.config:
            self.config["auth"] = {
                "dev-code": "",
                "rain-session": "",
                "x-api-key": ""
            }
            self._save_config()

        self._validate_auth()
        self._validate_headers()

    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            # 创建默认配置文件
            self.config = {
                "auth": {
                    "dev-code": "",
                    "rain-session": "",
                    "x-api-key": ""
                },
                "headers": {}
            }
            self._save_config()
            print(f"{self.config_path} 文件已创建，请按照文档说明填写 x-api-key 或填写 dev-code 和 rain-session")
            sys.exit(0)

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except json.JSONDecodeError:
            print(f"错误: {self.config_path} 文件不是有效的 JSON 格式")
            sys.exit(1)
        except Exception as e:
            print(f"错误: 读取 {self.config_path} 时发生意外错误 - {str(e)}")
            sys.exit(1)

    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"错误: 无法保存 {self.config_path} 文件 - {str(e)}")
            sys.exit(1)

    def _validate_auth(self):
        """验证auth配置是否有效"""
        auth = self.config.get("auth", {})

        has_api_key = 'x-api-key' in auth and auth['x-api-key']
        has_dev_and_rain = all(
            field in auth and auth[field] for field in ['dev-code', 'rain-session']
        )

        if not has_api_key and not has_dev_and_rain:
            # 如果都没有，则打印详细的错误信息
            if 'x-api-key' not in auth or not auth['x-api-key']:
                print(f"{self.config_path} 错误: 'x-api-key' 字段缺失或为空")
            if 'dev-code' not in auth or not auth['dev-code']:
                print(f"{self.config_path} 错误: 'dev-code' 字段缺失或为空")
            if 'rain-session' not in auth or not auth['rain-session']:
                print(f"{self.config_path} 错误: 'rain-session' 字段缺失或为空")
            print("提示: 必须提供有效的 'x-api-key' 或 ('dev-code' 和 'rain-session')")
            sys.exit(1)

    def load_header_auth(self, headers: Dict[str, str], boolean: bool = False) -> Union[Dict[str, str], bool]:
        """加载认证信息到请求头"""
        headers = headers.copy()
        auth = self.config.get("auth", {})
        key = auth.get('x-api-key', None)
        dev_token = auth.get('dev-code', None)

        if key:
            headers['x-api-key'] = str(key)
            if dev_token:
                headers['rain-dev-token'] = str(dev_token)
            return True if boolean else headers

        return False if boolean else headers

    def load_cookies_auth(self) -> Dict[str, str]:
        """加载cookie认证信息"""
        if self.load_header_auth({}, True):
            return {}
        return self.config.get("auth", {}).copy()

    def save_cookies_auth(self, cookies: Dict[str, str]):
        """保存cookie认证信息"""
        auth = self.config.get("auth", {})
        auth.update(cookies)
        self.config["auth"] = auth
        self._save_config()

    def update_cookies_from_response(self, response, current_cookies: Dict[str, str]) -> Dict[str, str]:
        """从响应中更新cookie"""
        if 'set-cookie' in response.headers:
            new_cookies = current_cookies.copy()
            new_cookies.update(response.cookies.get_dict())
            self.save_cookies_auth(new_cookies)
            return new_cookies
        return current_cookies

    def _validate_headers(self):
        """验证headers配置是否有效"""
        headers = self.config.get("headers", {})

        # 如果headers是列表，尝试转换为字典
        if isinstance(headers, list):
            try:
                headers_dict = {}
                for item in headers:
                    # 处理字符串格式 "Header: value"
                    if isinstance(item, str):
                        if ":" in item:
                            key, value = item.split(":", 1)
                            headers_dict[key.strip()] = value.strip()
                        else:
                            print(f"警告: 忽略无效的header字符串格式 '{item}'，应有 'Header: value' 格式")
                            continue
                    # 处理字典格式 {"name": "Header", "value": "value"}
                    elif isinstance(item, dict) and 'name' in item and 'value' in item:
                        headers_dict[item['name']] = item['value']
                    # 处理元组/列表格式 ["Header", "value"]
                    elif isinstance(item, (tuple, list)) and len(item) == 2:
                        headers_dict[item[0]] = item[1]
                    else:
                        print(f"警告: 忽略无法识别的header格式 {item}")
                        continue

                self.config["headers"] = headers_dict
                headers = headers_dict
                if headers_dict:  # 只在确实转换了内容时显示提示
                    print("提示: headers 已从列表格式自动转换为字典格式")
            except Exception as e:
                print(f"错误: 无法将headers列表转换为字典 - {str(e)}")
                sys.exit(1)

        # 验证headers是否为字典
        if not isinstance(headers, dict):
            print("错误: config中的headers配置必须是一个字典或可转换为字典的列表")
            print("提示: 可接受的headers格式:")
            print('1. 字典格式: {"Header-Name": "value"}')
            print('2. 字典列表: [{"name": "Header-Name", "value": "value"}, ...]')
            print('3. 键值对列表: [["Header-Name", "value"], ...]')
            print('4. 字符串列表: ["Header-Name: value", ...]')
            sys.exit(1)

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """获取配置值"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """设置配置值"""
        self.config[key] = value
        self._save_config()
