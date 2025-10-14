from unittest.mock import patch

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


def test_normalize_msg_type(email_config):
	"""验证消息类型规范化（'text' → 'plain' 转换 + 其他类型保持不变）。"""
	sender = EmailSender(email_config)

	# 'text' 转为 'plain'（带警告）
	with patch('builtins.print') as mock_print:
		result = sender._normalize_msg_type('text')
		assert result == 'plain'
		assert '已弃用' in mock_print.call_args[0][0]

	# 其他类型保持不变
	assert sender._normalize_msg_type('plain') == 'plain'
	assert sender._normalize_msg_type('html') == 'html'


def test_determine_msg_type(email_config):
	"""验证消息类型确定逻辑（配置优先 + 自动检测）。"""
	# 1. 配置优先：配置了 message_type 时，即使内容是纯文本也使用配置的类型
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
