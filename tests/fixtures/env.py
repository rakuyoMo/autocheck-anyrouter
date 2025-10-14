import json
import os
from collections.abc import Callable
from typing import Any

import pytest


@pytest.fixture
def clean_notification_env(monkeypatch: pytest.MonkeyPatch):
	"""清理所有通知相关的环境变量"""
	for key in list(os.environ.keys()):
		if 'NOTIF_CONFIG' in key or key in [
			'EMAIL_NOTIF_CONFIG',
			'DINGTALK_NOTIF_CONFIG',
			'FEISHU_NOTIF_CONFIG',
			'WECOM_NOTIF_CONFIG',
			'PUSHPLUS_NOTIF_CONFIG',
			'SERVERPUSH_NOTIF_CONFIG',
		]:
			monkeypatch.delenv(key, raising=False)
	yield


@pytest.fixture
def accounts_env(monkeypatch):
	"""设置账号环境变量的工厂函数"""

	def _set_accounts(accounts_list: list[dict] | None = None):
		if accounts_list is None:
			accounts_list = [{'name': '测试账号', 'cookies': 'test=value', 'api_user': 'user123'}]
		accounts_json = json.dumps(accounts_list)
		monkeypatch.setenv('ANYROUTER_ACCOUNTS', accounts_json)

	return _set_accounts


@pytest.fixture
def config_env_setter(monkeypatch: pytest.MonkeyPatch) -> Callable:
	"""设置配置环境变量的工厂函数"""

	def _set_config(platform: str, config: dict[str, Any] | str):
		"""
		设置平台配置环境变量

		Args:
			platform: 平台名称 (email, dingtalk, feishu, wecom, pushplus, serverpush)
			config: 配置内容（字典或字符串）
		"""
		env_key_map = {
			'email': 'EMAIL_NOTIF_CONFIG',
			'dingtalk': 'DINGTALK_NOTIF_CONFIG',
			'feishu': 'FEISHU_NOTIF_CONFIG',
			'wecom': 'WECOM_NOTIF_CONFIG',
			'pushplus': 'PUSHPLUS_NOTIF_CONFIG',
			'serverpush': 'SERVERPUSH_NOTIF_CONFIG',
		}

		env_key = env_key_map.get(platform)
		if not env_key:
			raise ValueError(f'不支持的平台: {platform}')

		config_str = json.dumps(config) if isinstance(config, dict) else config
		monkeypatch.setenv(env_key, config_str)

	return _set_config
