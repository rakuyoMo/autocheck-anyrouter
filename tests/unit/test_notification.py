from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from notif.models import NotificationHandler, NotificationTemplate
from notif.notify import NotificationKit
from tests.tools.data_builders import create_account_result_data, create_notification_data


@pytest.mark.asyncio
async def test_notificationkit_without_handlers(clean_notification_env):
	"""验证没有配置时不会推送。"""
	kit = NotificationKit()
	kit._handlers = []

	# 创建测试数据
	data = create_notification_data([
		create_account_result_data(name='测试账号', quota=25.0, used=5.0),
	])

	with patch('notif.notify.logger.warning') as mock_warning:
		await kit.push_message(data)

	mock_warning.assert_called_once()


@pytest.mark.asyncio
async def test_notificationkit_handler_skip_and_error(clean_notification_env):
	"""验证处理器跳过与异常分支。"""
	kit = NotificationKit()

	data = create_notification_data([
		create_account_result_data(name='账号 A', quota=25.0, used=5.0),
		create_account_result_data(name='账号 B', status='failed', error='超时'),
	])

	skip_handler = NotificationHandler(name='跳过平台', config=None, send_func=AsyncMock())
	error_config = MagicMock()
	error_config.template = NotificationTemplate(title='测试标题', content='{{ stats.success_count }}')
	error_handler = NotificationHandler(
		name='异常平台',
		config=error_config,
		send_func=AsyncMock(side_effect=Exception('发送失败')),
	)

	kit._handlers = [skip_handler, error_handler]

	with (
		patch('notif.notify.logger.error') as mock_error,
		patch('notif.notify.stencil.Template') as mock_template,
	):
		mock_template.side_effect = ValueError('模板错误')
		await kit.push_message(data)

	# 验证 skip_handler 没有被调用（因为 config 是 None）
	skip_handler.send_func.assert_not_called()

	# 验证 error_handler 的异常被捕获并记录
	assert mock_error.call_count >= 1


def test_notification_config_parsing(clean_notification_env, monkeypatch):
	"""验证各平台的配置解析（字典、字符串格式、向后兼容）+ NotificationTemplate。"""
	kit = NotificationKit()

	# PushPlus：字典格式
	monkeypatch.setenv('PUSHPLUS_NOTIF_CONFIG', '{"token": "dict-token"}')
	config_dict = kit._load_pushplus_config()
	assert config_dict is not None
	assert config_dict.token == 'dict-token'

	# PushPlus：字符串格式
	monkeypatch.setenv('PUSHPLUS_NOTIF_CONFIG', 'string-token')
	config_str = kit._load_pushplus_config()
	assert config_str is not None
	assert config_str.token == 'string-token'

	# Email：platform_settings 中的配置解析
	monkeypatch.setenv(
		'EMAIL_NOTIF_CONFIG',
		'{"user": "test@example.com", "pass": "test_pass", "to": "recipient@example.com", "platform_settings": {"message_type": "html"}}',
	)
	email_config = kit._load_email_config()
	assert email_config is not None
	assert email_config.user == 'test@example.com'
	assert email_config.platform_settings is not None
	assert email_config.platform_settings['message_type'] == 'html'

	# 测试 NotificationTemplate.from_value() 的各种格式
	# 1. 对象格式
	template_obj = NotificationTemplate.from_value({'title': '自定义标题', 'content': '自定义内容'})
	assert template_obj is not None
	assert template_obj.title == '自定义标题'
	assert template_obj.content == '自定义内容'

	# 2. 字符串格式（向后兼容）
	template_str = NotificationTemplate.from_value('旧格式内容')
	assert template_str is not None
	assert template_str.title == 'AnyRouter 签到提醒'
	assert template_str.content == '旧格式内容'

	# 3. None 值
	template_none = NotificationTemplate.from_value(None)
	assert template_none is None

	# 4. 对象格式但 title 为 None（表示不展示标题）
	template_no_title = NotificationTemplate.from_value({'content': '只有内容'})
	assert template_no_title is not None
	assert template_no_title.title is None
	assert template_no_title.content == '只有内容'

	# 5. 空字符串 title
	template_empty_title = NotificationTemplate.from_value({'title': '', 'content': '内容'})
	assert template_empty_title is not None
	assert template_empty_title.title == ''
	assert template_empty_title.content == '内容'
