from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from notif.models import NotificationHandler
from notif.notify import NotificationKit
from tests.tools.data_builders import create_account_result_data, create_notification_data


@pytest.mark.asyncio
async def test_notificationkit_without_handlers(clean_notification_env):
	"""验证没有配置时不会推送。"""
	kit = NotificationKit()
	kit._handlers = []

	with patch('notif.notify.logger.warning') as mock_warning:
		await kit.push_message('标题', '内容')

	mock_warning.assert_called_once()


@pytest.mark.asyncio
async def test_notificationkit_handler_skip_and_error(clean_notification_env):
	"""验证处理器跳过与异常分支。"""
	kit = NotificationKit()

	data = create_notification_data(
		[
			create_account_result_data(name='账号 A', quota=25.0, used=5.0),
			create_account_result_data(name='账号 B', status='failed', error='超时'),
		]
	)

	skip_handler = NotificationHandler(name='跳过平台', config=None, send_func=AsyncMock())
	error_config = MagicMock()
	error_config.template = '{{ stats.success_count }}'
	error_handler = NotificationHandler(
		name='异常平台',
		config=error_config,
		send_func=AsyncMock(side_effect=Exception('发送失败')),
	)

	kit._handlers = [skip_handler, error_handler]

	with (
		patch('notif.notify.logger.info') as mock_info,
		patch('notif.notify.logger.error') as mock_error,
		patch('notif.notify.stencil.Template') as mock_template,
	):
		mock_template.side_effect = ValueError('模板错误')
		await kit.push_message('标题', data)

	assert mock_info.call_count >= 1
	assert mock_error.call_count >= 1


def test_notification_config_parsing(clean_notification_env, monkeypatch):
	"""验证各平台的配置解析（字典、字符串格式、向后兼容）。"""
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
		'{"user": "test@example.com", "pass": "test_pass", "to": "recipient@example.com", "platform_settings": {"default_msg_type": "html"}}',
	)
	email_config = kit._load_email_config()
	assert email_config is not None
	assert email_config.user == 'test@example.com'
	assert email_config.platform_settings is not None
	assert email_config.platform_settings['default_msg_type'] == 'html'

	# Email：向后兼容（根目录下的 default_msg_type）
	monkeypatch.setenv(
		'EMAIL_NOTIF_CONFIG',
		'{"user": "test@example.com", "pass": "test_pass", "to": "recipient@example.com", "default_msg_type": "text"}',
	)
	with patch('notif.notify.logger.warning') as mock_warning:
		email_config_compat = kit._load_email_config()

		# 验证警告被触发
		assert mock_warning.call_count >= 1
		assert '建议将 default_msg_type 配置移至 platform_settings 字段下' in str(mock_warning.call_args_list)

		# 验证 default_msg_type 被移到 platform_settings 中
		assert email_config_compat is not None
		assert email_config_compat.platform_settings is not None
		assert email_config_compat.platform_settings['default_msg_type'] == 'text'
