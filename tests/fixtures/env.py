import json
import os
from collections.abc import Callable
from typing import Any

import pytest


class EnvManager:
	"""环境变量管理器"""

	@staticmethod
	def set_accounts(accounts: list[dict]):
		"""设置账号环境变量

		Args:
			accounts: 账号列表
		"""
		os.environ['ANYROUTER_ACCOUNTS'] = json.dumps(accounts, ensure_ascii=False)

	@staticmethod
	def set_account_prefix(name: str, account: dict):
		"""
		设置单个账号的环境变量（使用 ANYROUTER_ACCOUNT_* 格式）

		Args:
			name: 环境变量后缀名称
			account: 账号配置
		"""
		os.environ[f'ANYROUTER_ACCOUNT_{name}'] = json.dumps(account, ensure_ascii=False)

	@staticmethod
	def clear_account_prefix_env():
		"""清除所有 ANYROUTER_ACCOUNT_* 环境变量"""
		keys_to_remove = [key for key in os.environ.keys() if key.startswith('ANYROUTER_ACCOUNT_')]
		for key in keys_to_remove:
			os.environ.pop(key, None)

	@staticmethod
	def set_notification(platform: str, config: dict | str):
		"""
		设置通知平台环境变量

		Args:
			platform: 平台名称（dingtalk/feishu/wecom/email/bark/pushplus/serverpush）
			config: 配置（字典或字符串）
		"""
		key_map = {
			'dingtalk': 'DINGTALK_NOTIF_CONFIG',
			'feishu': 'FEISHU_NOTIF_CONFIG',
			'wecom': 'WECOM_NOTIF_CONFIG',
			'email': 'EMAIL_NOTIF_CONFIG',
			'bark': 'BARK_NOTIF_CONFIG',
			'pushplus': 'PUSHPLUS_NOTIF_CONFIG',
			'serverpush': 'SERVERPUSH_NOTIF_CONFIG',
		}

		env_key = key_map.get(platform)
		if not env_key:
			raise ValueError(f'未知的平台: {platform}')

		if isinstance(config, dict):
			os.environ[env_key] = json.dumps(config, ensure_ascii=False)
		else:
			os.environ[env_key] = config

	@staticmethod
	def set_notify_triggers(triggers: str):
		"""
		设置通知触发器

		Args:
			triggers: 触发器字符串（如 "always"、"never"、"success,failed"）
		"""
		os.environ['NOTIFY_TRIGGERS'] = triggers

	@staticmethod
	def set_repo_visibility(visibility: str):
		"""
		设置仓库可见性

		Args:
			visibility: 可见性（public/private）
		"""
		os.environ['REPO_VISIBILITY'] = visibility

	@staticmethod
	def clear_all_notifications():
		"""清除所有通知平台配置"""
		notification_keys = [
			'DINGTALK_NOTIF_CONFIG',
			'FEISHU_NOTIF_CONFIG',
			'WECOM_NOTIF_CONFIG',
			'EMAIL_NOTIF_CONFIG',
			'BARK_NOTIF_CONFIG',
			'PUSHPLUS_NOTIF_CONFIG',
			'SERVERPUSH_NOTIF_CONFIG',
		]

		for key in notification_keys:
			os.environ.pop(key, None)


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
			'BARK_NOTIF_CONFIG',
		]:
			monkeypatch.delenv(key, raising=False)
	yield


@pytest.fixture
def accounts_env(monkeypatch):
	"""设置账号环境变量的工厂函数"""
	# 清理所有 ANYROUTER_ACCOUNT_* 环境变量
	for key in list(os.environ.keys()):
		if key.startswith('ANYROUTER_ACCOUNT_'):
			monkeypatch.delenv(key, raising=False)

	def _set_accounts(accounts_list: list[dict] = []):
		if not accounts_list:
			accounts_list = [{'name': '测试账号', 'cookies': 'test=value', 'api_user': 'user123'}]
		accounts_json = json.dumps(accounts_list)
		monkeypatch.setenv('ANYROUTER_ACCOUNTS', accounts_json)

	return _set_accounts


@pytest.fixture
def account_prefix_env(monkeypatch):
	"""
	设置 ANYROUTER_ACCOUNT_* 前缀环境变量的工厂函数

	用于测试单账号环境变量功能
	"""
	# 清理 ANYROUTER_ACCOUNTS 环境变量
	monkeypatch.delenv('ANYROUTER_ACCOUNTS', raising=False)

	# 清理所有 ANYROUTER_ACCOUNT_* 环境变量
	for key in list(os.environ.keys()):
		if key.startswith('ANYROUTER_ACCOUNT_'):
			monkeypatch.delenv(key, raising=False)

	def _set_account(name: str, account: dict):
		"""
		设置单个账号环境变量

		Args:
			name: 环境变量后缀名称
			account: 账号配置
		"""
		account_json = json.dumps(account, ensure_ascii=False)
		monkeypatch.setenv(f'ANYROUTER_ACCOUNT_{name}', account_json)

	return _set_account


@pytest.fixture
def config_env_setter(monkeypatch: pytest.MonkeyPatch) -> Callable:
	"""设置配置环境变量的工厂函数"""

	def _set_config(platform: str, config: dict[str, Any] | str):
		"""
		设置平台配置环境变量

		Args:
			platform: 平台名称 (email, dingtalk, feishu, wecom, pushplus, serverpush, bark)
			config: 配置内容（字典或字符串）
		"""
		env_key_map = {
			'email': 'EMAIL_NOTIF_CONFIG',
			'dingtalk': 'DINGTALK_NOTIF_CONFIG',
			'feishu': 'FEISHU_NOTIF_CONFIG',
			'wecom': 'WECOM_NOTIF_CONFIG',
			'pushplus': 'PUSHPLUS_NOTIF_CONFIG',
			'serverpush': 'SERVERPUSH_NOTIF_CONFIG',
			'bark': 'BARK_NOTIF_CONFIG',
		}

		env_key = env_key_map.get(platform)
		if not env_key:
			raise ValueError(f'不支持的平台: {platform}')

		config_str = json.dumps(config) if isinstance(config, dict) else config
		monkeypatch.setenv(env_key, config_str)

	return _set_config
