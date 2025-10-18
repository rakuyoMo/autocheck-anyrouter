from unittest.mock import MagicMock, patch

import pytest

from notif.models import EmailConfig
from notif.senders import EmailSender


@pytest.fixture
def email_config():
	"""创建基础的 EmailConfig 用于测试。"""
	return EmailConfig(
		user='test@example.com',
		password='test_pass',
		to='recipient@example.com',
	)


@pytest.mark.asyncio
async def test_email_sender_comprehensive(email_config):
	"""综合测试邮件发送器的各种功能（消息类型确定、title 必填验证）。"""
	# 1. 测试消息类型确定逻辑：配置优先 + 自动检测
	email_config.platform_settings = {'message_type': 'html'}
	sender = EmailSender(email_config)
	assert sender._determine_msg_type('This is plain text') == 'html'

	# 2. 自动检测：没有配置时，根据内容自动检测
	email_config.platform_settings = None
	sender = EmailSender(email_config)

	# 纯文本应该被检测为 plain
	assert sender._determine_msg_type('This is plain text') == 'plain'

	# HTML 内容应该被检测为 html
	assert sender._determine_msg_type('<html><body>Test</body></html>') == 'html'

	# 包含常见标签的内容应该被检测为 html
	assert sender._determine_msg_type('<div>Content</div>') == 'html'

	# 3. 测试无效的 message_type 配置（会降级为 plain 并发出警告）
	email_config.platform_settings = {'message_type': 'invalid_type'}
	sender = EmailSender(email_config)
	result = sender._determine_msg_type('content')
	assert result == 'plain'

	# 4. 测试 title 必填验证（邮件必须提供 title）
	email_config.platform_settings = None
	sender = EmailSender(email_config)

	# title 为 None 时应该抛出 ValueError
	with pytest.raises(ValueError, match='邮件推送需要提供非空的 title 参数'):
		await sender.send(title=None, content='测试内容')

	# title 为空字符串时也应该抛出 ValueError
	with pytest.raises(ValueError, match='邮件推送需要提供非空的 title 参数'):
		await sender.send(title='', content='测试内容')

	# 5. 测试正常发送（有 title）
	with patch('smtplib.SMTP_SSL') as mock_smtp:
		mock_server = MagicMock()
		mock_smtp.return_value.__enter__.return_value = mock_server

		await sender.send(title='测试标题', content='测试内容')

		# 验证 SMTP 操作被调用
		mock_server.login.assert_called_once_with('test@example.com', 'test_pass')
		mock_server.send_message.assert_called_once()
