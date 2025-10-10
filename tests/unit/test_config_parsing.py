import json
import os

import pytest

from notif.notify import NotificationKit


class TestConfigParsing:
	"""测试配置解析功能"""

	def test_no_config_returns_none(self, monkeypatch: pytest.MonkeyPatch):
		"""测试无配置时所有配置为 None"""
		# 清空所有相关环境变量
		for key in list(os.environ.keys()):
			if 'NOTIF_CONFIG' in key:
				monkeypatch.delenv(key, raising=False)

		kit = NotificationKit()

		assert kit.email_config is None
		assert kit.dingtalk_config is None
		assert kit.feishu_config is None
		assert kit.wecom_config is None
		assert kit.pushplus_config is None
		assert kit.serverpush_config is None

	@pytest.mark.parametrize(
		'config_format,has_template,template_value',
		[
			('json_with_custom_template', True, 'custom template content'),
			('json_with_null_template', False, None),
			('json_without_template_key', False, None),
		],
	)
	def test_wecom_config_formats(
		self,
		monkeypatch: pytest.MonkeyPatch,
		config_format: str,
		has_template: bool,
		template_value: str | None,
	):
		"""测试企业微信配置的各种格式"""
		# 清空环境
		for key in list(os.environ.keys()):
			if 'NOTIF_CONFIG' in key or 'WEBHOOK' in key:
				monkeypatch.delenv(key, raising=False)

		# 构造配置
		if config_format == 'json_with_custom_template':
			config = {'webhook': 'https://example.com/webhook', 'template': template_value}
		elif config_format == 'json_with_null_template':
			config = {'webhook': 'https://example.com/webhook', 'template': None}
		else:  # json_without_template_key
			config = {'webhook': 'https://example.com/webhook'}

		monkeypatch.setenv('WECOM_NOTIF_CONFIG', json.dumps(config))

		kit = NotificationKit()

		assert kit.wecom_config is not None
		assert kit.wecom_config.webhook == 'https://example.com/webhook'

		# 验证模板处理
		if has_template:
			assert kit.wecom_config.template == template_value
		else:
			# template 为 null 或不存在时，应该加载默认模板
			assert kit.wecom_config.template is not None
			assert len(kit.wecom_config.template) > 0

	@pytest.mark.parametrize(
		'config_format,has_template',
		[
			('json_with_custom_template', True),
			('json_with_null_template', False),
		],
	)
	def test_pushplus_config_formats(
		self,
		monkeypatch: pytest.MonkeyPatch,
		config_format: str,
		has_template: bool,
	):
		"""测试 PushPlus 配置的各种格式"""
		# 清空环境
		for key in list(os.environ.keys()):
			if 'NOTIF_CONFIG' in key or 'PUSHPLUS' in key:
				monkeypatch.delenv(key, raising=False)

		# 构造配置
		if config_format == 'json_with_custom_template':
			config = {'token': 'test_token_123', 'template': 'custom pushplus template'}
		else:  # json_with_null_template
			config = {'token': 'test_token_123', 'template': None}

		monkeypatch.setenv('PUSHPLUS_NOTIF_CONFIG', json.dumps(config))

		kit = NotificationKit()

		assert kit.pushplus_config is not None
		assert kit.pushplus_config.token == 'test_token_123'

		if has_template:
			assert kit.pushplus_config.template == 'custom pushplus template'
		else:
			assert kit.pushplus_config.template is not None
			assert len(kit.pushplus_config.template) > 0

	@pytest.mark.parametrize(
		'config_format,has_template',
		[
			('json_with_custom_template', True),
			('json_with_null_template', False),
		],
	)
	def test_serverpush_config_formats(
		self,
		monkeypatch: pytest.MonkeyPatch,
		config_format: str,
		has_template: bool,
	):
		"""测试 Server 酱配置的各种格式"""
		# 清空环境
		for key in list(os.environ.keys()):
			if 'NOTIF_CONFIG' in key or 'SERVERPUSH' in key:
				monkeypatch.delenv(key, raising=False)

		# 构造配置
		if config_format == 'json_with_custom_template':
			config = {'send_key': 'test_send_key', 'template': 'custom serverpush template'}
		else:  # json_with_null_template
			config = {'send_key': 'test_send_key', 'template': None}

		monkeypatch.setenv('SERVERPUSH_NOTIF_CONFIG', json.dumps(config))

		kit = NotificationKit()

		assert kit.serverpush_config is not None
		assert kit.serverpush_config.send_key == 'test_send_key'

		if has_template:
			assert kit.serverpush_config.template == 'custom serverpush template'
		else:
			assert kit.serverpush_config.template is not None
			assert len(kit.serverpush_config.template) > 0

	@pytest.mark.parametrize(
		'config_format,has_template',
		[
			('json_with_custom_template', True),
			('json_with_null_template', False),
		],
	)
	def test_email_config_formats(
		self,
		monkeypatch: pytest.MonkeyPatch,
		config_format: str,
		has_template: bool,
	):
		"""测试邮箱配置的各种格式"""
		# 清空环境
		for key in list(os.environ.keys()):
			if 'NOTIF_CONFIG' in key or 'EMAIL' in key:
				monkeypatch.delenv(key, raising=False)

		# 构造配置
		if config_format == 'json_with_custom_template':
			config = {
				'user': 'test@example.com',
				'pass': 'test_password',
				'to': 'recipient@example.com',
				'template': 'custom email template',
			}
		else:  # json_with_null_template
			config = {
				'user': 'test@example.com',
				'pass': 'test_password',
				'to': 'recipient@example.com',
				'template': None,
			}

		monkeypatch.setenv('EMAIL_NOTIF_CONFIG', json.dumps(config))

		kit = NotificationKit()

		assert kit.email_config is not None
		assert kit.email_config.user == 'test@example.com'
		assert kit.email_config.password == 'test_password'
		assert kit.email_config.to == 'recipient@example.com'

		if has_template:
			assert kit.email_config.template == 'custom email template'
		else:
			assert kit.email_config.template is not None
			assert len(kit.email_config.template) > 0
