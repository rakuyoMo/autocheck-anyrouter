from typing import Any

import pytest

from notif import NotificationKit
from notif.models import NotificationTemplate
from tests.tools.data_builders import build_account_result, build_notification_data


class TestNotificationKit:
	"""测试 NotificationKit 类"""

	@pytest.mark.parametrize(
		'env_key,env_value,expected_config_attr,expected_value_or_key',
		[
			# Email 平台（字典格式）
			(
				'EMAIL_NOTIF_CONFIG',
				'{"user": "test@example.com", "pass": "password", "to": "recipient@example.com"}',
				'email_config',
				('user', 'test@example.com'),
			),
			# Bark 平台（字典格式）
			(
				'BARK_NOTIF_CONFIG',
				'{"server_url": "https://api.day.app", "device_key": "test_key"}',
				'bark_config',
				('device_key', 'test_key'),
			),
			# PushPlus 平台（字符串格式）
			('PUSHPLUS_NOTIF_CONFIG', 'test_token_123', 'pushplus_config', ('token', 'test_token_123')),
			# ServerPush 平台（字符串格式）
			('SERVERPUSH_NOTIF_CONFIG', 'test_send_key_456', 'serverpush_config', ('send_key', 'test_send_key_456')),
			# DingTalk 平台（字符串格式）
			(
				'DINGTALK_NOTIF_CONFIG',
				'https://oapi.dingtalk.com/robot/send?access_token=test',
				'dingtalk_config',
				('webhook', 'https://oapi.dingtalk.com/robot/send?access_token=test'),
			),
			# Feishu 平台（字典格式，包含模板）
			(
				'FEISHU_NOTIF_CONFIG',
				'{"webhook": "https://open.feishu.cn/hook", "template": {"title": "自定义标题", "content": "自定义内容"}}',
				'feishu_config',
				('template.title', '自定义标题'),
			),
			# WeCom 平台（字典格式）
			(
				'WECOM_NOTIF_CONFIG',
				'{"webhook": "https://qyapi.weixin.qq.com/hook"}',
				'wecom_config',
				('webhook', 'https://qyapi.weixin.qq.com/hook'),
			),
		],
	)
	def test_config_parsing_all_platforms(
		self,
		monkeypatch: pytest.MonkeyPatch,
		clean_notification_env: None,
		env_key: str,
		env_value: str,
		expected_config_attr: str,
		expected_value_or_key: tuple[str, str],
	) -> None:
		"""测试所有平台的配置解析（字典和字符串格式）"""
		monkeypatch.setenv(env_key, env_value)
		kit = NotificationKit()

		config = getattr(kit, expected_config_attr)
		assert config is not None, f'{expected_config_attr} 应该不为 None'

		# 验证配置值
		attr_path, expected_value = expected_value_or_key
		if '.' in attr_path:
			# 嵌套属性（如 template.title）
			parts = attr_path.split('.')
			obj = config
			for part in parts:
				obj = getattr(obj, part)
			assert obj == expected_value, f'{attr_path} 的值不匹配'
		else:
			# 普通属性
			actual_value = getattr(config, attr_path)
			assert actual_value == expected_value, f'{attr_path} 的值不匹配'

	def test_template_merging_and_rendering(
		self,
		monkeypatch: pytest.MonkeyPatch,
		clean_notification_env: None,
	) -> None:
		"""测试默认模板与用户模板的合并和渲染"""
		# 测试完全自定义模板
		monkeypatch.setenv(
			'PUSHPLUS_NOTIF_CONFIG',
			'{"token": "test", "template": {"title": "自定义标题", "content": "自定义内容"}}',
		)
		kit = NotificationKit()
		assert kit.pushplus_config is not None
		assert kit.pushplus_config.template is not None
		assert kit.pushplus_config.template.title == '自定义标题'
		assert kit.pushplus_config.template.content == '自定义内容'

		# 测试只自定义 content（title 使用默认值）
		monkeypatch.setenv(
			'PUSHPLUS_NOTIF_CONFIG',
			'{"token": "test", "template": {"content": "只有内容"}}',
		)
		kit = NotificationKit()
		assert kit.pushplus_config is not None
		assert kit.pushplus_config.template is not None
		assert kit.pushplus_config.template.content == '只有内容'

		# 测试 NotificationTemplate.from_value() 的各种格式
		# 1. 字典格式
		template_dict = NotificationTemplate.from_value({'title': '标题', 'content': '内容'})
		assert template_dict is not None
		assert template_dict.title == '标题'
		assert template_dict.content == '内容'

		# 2. 字符串格式（向后兼容）
		template_str = NotificationTemplate.from_value('旧格式内容')
		assert template_str is not None
		assert template_str.title == 'AnyRouter 签到提醒'
		assert template_str.content == '旧格式内容'

		# 3. None 值
		template_none = NotificationTemplate.from_value(None)
		assert template_none is None

		# 4. 空 title
		template_no_title = NotificationTemplate.from_value({'content': '只有内容'})
		assert template_no_title is not None
		assert template_no_title.title is None
		assert template_no_title.content == '只有内容'

		# 测试模板渲染（通过 NotificationKit）
		kit_for_render = NotificationKit()
		template_with_vars = NotificationTemplate(
			title='{% if all_success %}全部成功{% else %}部分成功{% endif %}',
			content='共 {{ stats.total_count }} 个账号, 成功 {{ stats.success_count }} 个',
		)

		# 构造上下文数据（使用对象而不是字典，因为 stencil 不支持字典的点访问）
		Stats = type('Stats', (), {'total_count': 10, 'success_count': 8})
		context_data = {
			'all_success': True,
			'stats': Stats(),
		}

		# 通过 _render_template 测试渲染
		rendered_title, rendered_content = kit_for_render._render_template(template_with_vars, context_data)
		assert rendered_title == '全部成功'
		assert rendered_content == '共 10 个账号, 成功 8 个'

	@pytest.mark.parametrize(
		'accounts,expected_flags',
		[
			# 全部成功
			(
				[
					build_account_result(name='账号 1', quota=25.0, used=5.0, balance_changed=False),
					build_account_result(name='账号 2', quota=30.0, used=10.0, balance_changed=False),
				],
				{
					'has_success': True,
					'has_failed': False,
					'all_success': True,
					'all_failed': False,
					'partial_success': False,
				},
			),
			# 全部失败
			(
				[
					build_account_result(name='账号 1', status='failed', error='错误 1'),
					build_account_result(name='账号 2', status='failed', error='错误 2'),
				],
				{
					'has_success': False,
					'has_failed': True,
					'all_success': False,
					'all_failed': True,
					'partial_success': False,
				},
			),
			# 部分成功
			(
				[
					build_account_result(name='账号 1', quota=25.0, used=5.0),
					build_account_result(name='账号 2', status='failed', error='错误'),
				],
				{
					'has_success': True,
					'has_failed': True,
					'all_success': False,
					'all_failed': False,
					'partial_success': True,
				},
			),
			# 余额变化测试
			(
				[
					build_account_result(name='账号 1', balance_changed=True),
					build_account_result(name='账号 2', balance_changed=False),
				],
				{
					'has_balance_changed': True,
					'has_balance_unchanged': True,
					'all_balance_changed': False,
					'all_balance_unchanged': False,
				},
			),
		],
	)
	def test_context_data_building(
		self,
		clean_notification_env: None,
		accounts: list[Any],
		expected_flags: dict[str, bool],
	) -> None:
		"""测试上下文数据构建（用于模板渲染）"""
		kit = NotificationKit()
		data = build_notification_data(accounts)
		context = kit._build_context_data(data)

		# 验证所有预期的标志
		for flag_name, expected_value in expected_flags.items():
			actual_value = context.get(flag_name)
			assert actual_value == expected_value, f'{flag_name} 应该是 {expected_value}, 实际是 {actual_value}'
