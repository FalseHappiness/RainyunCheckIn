import os
import json
from typing import Dict, Any, Optional, Union


class ConfigError(Exception):
    """自定义配置错误异常"""
    pass


class Config:
    def __init__(self, config_path: str | None = "config.json", api_config_data: Optional[Dict[str, Any]] = None):
        self.config_path = config_path
        self.api_config_data = api_config_data
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
        # 优先使用api_config_data中的配置
        if self.api_config_data is not None:
            file_config = self._load_file_config() if self.config_path else {}
            self.config = self._deep_merge_configs(file_config, self.api_config_data)
            return

        # 如果没有api_config_data，则只使用文件配置
        self.config = self._load_file_config()

    def _load_file_config(self) -> Dict[str, Any]:
        """从文件加载配置"""
        if not os.path.exists(self.config_path):
            # 创建默认配置文件
            default_config = {
                "auth": {
                    "dev-code": "",
                    "rain-session": "",
                    "x-api-key": ""
                },
                "headers": {}
            }
            try:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
            except Exception as e:
                raise ConfigError(f"无法创建默认配置文件 {self.config_path} - {str(e)}")

            raise ConfigError(
                f"{self.config_path} 文件已创建，请按照文档说明填写 x-api-key 或填写 dev-code 和 rain-session"
            )

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            raise ConfigError(f"{self.config_path} 文件不是有效的 JSON 格式")
        except Exception as e:
            raise ConfigError(f"读取 {self.config_path} 时发生意外错误 - {str(e)}")

    def _deep_merge_configs(self, base: Dict[str, Any], override: Dict[str, Any], primary=True) -> Dict[str, Any]:
        """深度合并两个配置字典"""
        result = base.copy()

        # 特殊处理auth部分
        if "auth" in override and primary:
            result["auth"] = override["auth"].copy()

        # 合并其他部分
        for key, value in override.items():
            if key == "auth" and primary:
                continue
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_configs(base[key], value, False)
            else:
                result[key] = value
        return result

    def _save_auth_only(self):
        """只保存auth部分到配置文件"""
        if self.api_config_data is not None and "auth" in self.api_config_data:
            return  # 如果auth来自api_config_data，则不保存到文件

        try:
            # 读取现有配置
            existing_config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)

            # 只更新auth部分
            existing_config["auth"] = self.config["auth"]

            # 保存
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(existing_config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise ConfigError(f"无法保存 {self.config_path} 文件 - {str(e)}")

    def _save_config(self):
        """保存整个配置文件"""
        if not self.config_path:
            return

        if self.api_config_data is not None:
            self._save_auth_only()
            return  # 如果使用api_config_data，则不保存到文件

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise ConfigError(f"无法保存 {self.config_path} 文件 - {str(e)}")

    def _validate_auth(self):
        """验证auth配置是否有效"""
        auth_list = self.config.get("auth", {})

        multi = True

        if not isinstance(auth_list, list):
            multi = False
            auth_list = [auth_list]

        for i, auth in enumerate(auth_list):
            if not isinstance(auth, dict):
                raise ConfigError(f"配置文件 auth {f'数组第 {i + 1} 项' if multi else '字段值'}需要为对象格式")

            has_api_key = 'x-api-key' in auth and auth['x-api-key']
            has_dev_and_rain = all(
                field in auth and auth[field] for field in ['dev-code', 'rain-session']
            )

            if not has_api_key and not has_dev_and_rain:
                error_msgs = []
                if auth.get('x-api-key', None):
                    error_msgs.append(f"'x-api-key' 字段缺失或为空")
                if auth.get('dev-code', None):
                    error_msgs.append(f"'dev-code' 字段缺失或为空")
                if auth.get('rain-session', None):
                    error_msgs.append(f"'rain-session' 字段缺失或为空")

                auth_name = str(auth.get('name', ''))
                auth_display_name = f"{auth_name}({i + 1})" if auth_name else i + 1

                raise ConfigError(
                    f"认证配置{f' {auth_display_name} ' if multi else ''}无效: {', '.join(error_msgs)}. "
                    "必须提供有效的 'x-api-key' 或提供有效的 'dev-code' 和 'rain-session'"
                )

    def save_auth(self, auth):
        self.set('auth', auth)

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
                            print(f"警告: 忽略无效的 header 字符串格式 '{item}'，应有 'Header-Name: value' 格式")
                            continue
                    # 处理字典格式 {"name": "Header-Name", "value": "value"}
                    elif isinstance(item, dict) and 'name' in item and 'value' in item:
                        headers_dict[item['name']] = item['value']
                    # 处理元组/列表格式 ["Header-Name", "value"]
                    elif isinstance(item, (tuple, list)) and len(item) == 2:
                        headers_dict[item[0]] = item[1]
                    else:
                        print(f"警告: 忽略无法识别的 header 格式 {item}")
                        continue

                headers = headers_dict
                # if headers_dict:  # 只在确实转换了内容时显示提示
                #     print("提示: headers 已从列表格式自动转换为对象格式")
            except Exception as e:
                raise ConfigError(f"无法将 headers 数组转换为对象 - {str(e)}")

        # 验证headers是否为字典
        if not isinstance(headers, dict):
            raise ConfigError(
                "config中的headers配置必须是一个对象或可转换为对象的数组\n"
                "提示: 可接受的headers格式:\n"
                '1. 对象格式: {"Header-Name": "value", ...}\n'
                '2. 对象数组: [{"name": "Header-Name", "value": "value"}, ...]\n'
                '3. 键值对数组: [["Header-Name", "value"], ...]\n'
                '4. 字符串数组: ["Header-Name: value", ...]'
            )

        return headers

    def get_headers(self):
        try:
            return self._validate_headers()
        except ConfigError:
            return {}

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """获取配置值"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """设置配置值"""
        self.config[key] = value
        self._save_config()
