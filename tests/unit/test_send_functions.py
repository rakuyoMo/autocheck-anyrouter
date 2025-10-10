from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestEmailSender:
	"""测试邮件发送器"""

	@pytest.mark.asyncio
	@patch('smtplib.SMTP_SSL')
	async def test_email_sending_with_mock(self, mock_smtp: MagicMock):
		"""测试邮箱发送逻辑（使用 mock）"""
		from src.notif.models import EmailConfig
		from src.notif.senders import EmailSender

		# 创建配置
		config = EmailConfig(
			user='test@example.com',
			password='testpass',
			to='recipient@example.com',
			smtp_server=None,
			platform_settings=None,
			template=None
		)

		mock_server = MagicMock()
		mock_smtp.return_value.__enter__.return_value = mock_server

		# 创建 sender 并发送
		sender = EmailSender(config)
		await sender.send('测试标题', '测试内容')

		assert mock_server.login.called
		assert mock_server.send_message.called


class TestPushPlusSender:
	"""测试 PushPlus 发送器"""

	@pytest.mark.asyncio
	@patch('httpx.AsyncClient')
	async def test_pushplus_sending_with_mock(self, mock_client: MagicMock):
		"""测试 PushPlus 发送逻辑（使用 mock）"""
		from src.notif.models import PushPlusConfig
		from src.notif.senders import PushPlusSender

		# 创建配置
		config = PushPlusConfig(
			token='test_token',
			platform_settings=None,
			template=None
		)

		mock_client_instance = AsyncMock()
		mock_client.return_value.__aenter__.return_value = mock_client_instance

		# 创建 sender 并发送
		sender = PushPlusSender(config)
		await sender.send('测试标题', '测试内容')

		mock_client_instance.post.assert_called_once()


class TestServerPushSender:
	"""测试 Server 酱发送器"""

	@pytest.mark.asyncio
	@patch('httpx.AsyncClient')
	async def test_serverpush_sending_with_mock(self, mock_client: MagicMock):
		"""测试 Server 酱发送逻辑（使用 mock）"""
		from src.notif.models import ServerPushConfig
		from src.notif.senders import ServerPushSender

		# 创建配置
		config = ServerPushConfig(
			send_key='test_key',
			platform_settings=None,
			template=None
		)

		mock_client_instance = AsyncMock()
		mock_client.return_value.__aenter__.return_value = mock_client_instance

		# 创建 sender 并发送
		sender = ServerPushSender(config)
		await sender.send('测试标题', '测试内容')

		mock_client_instance.post.assert_called_once()


class TestDingTalkSender:
	"""测试钉钉发送器"""

	@pytest.mark.asyncio
	@patch('httpx.AsyncClient')
	async def test_dingtalk_sending_with_mock(self, mock_client: MagicMock):
		"""测试钉钉发送逻辑（使用 mock）"""
		from src.notif.models import WebhookConfig
		from src.notif.senders import DingTalkSender

		# 创建配置
		config = WebhookConfig(
			webhook='https://example.com/webhook',
			platform_settings=None,
			template=None
		)

		mock_client_instance = AsyncMock()
		mock_client.return_value.__aenter__.return_value = mock_client_instance

		# 创建 sender 并发送
		sender = DingTalkSender(config)
		await sender.send('测试标题', '测试内容')

		mock_client_instance.post.assert_called_once()


class TestFeishuSender:
	"""测试飞书发送器"""

	@pytest.mark.parametrize(
		'use_card,color_theme',
		[
			(True, 'red'),
			(True, 'blue'),
			(False, None),
		]
	)
	@pytest.mark.asyncio
	@patch('httpx.AsyncClient')
	async def test_feishu_card_modes(
		self,
		mock_client: MagicMock,
		use_card: bool,
		color_theme: str | None
	):
		"""测试飞书的卡片模式和普通模式"""
		from src.notif.models import WebhookConfig
		from src.notif.senders import FeishuSender

		# 构造配置
		platform_settings: dict[str, Any] = {'use_card': use_card}
		if use_card and color_theme:
			platform_settings['color_theme'] = color_theme

		config = WebhookConfig(
			webhook='https://example.com/webhook',
			platform_settings=platform_settings,
			template=None
		)

		mock_client_instance = AsyncMock()
		mock_client.return_value.__aenter__.return_value = mock_client_instance

		# 创建 sender 并发送
		sender = FeishuSender(config)
		await sender.send('测试标题', '测试内容')

		# 验证调用了 post 方法
		assert mock_client_instance.post.called
		call_args = mock_client_instance.post.call_args
		data = call_args[1]['json']

		if use_card:
			# 验证是卡片模式
			assert data['msg_type'] == 'interactive'
			assert 'card' in data
			if color_theme:
				assert data['card']['header']['template'] == color_theme
		else:
			# 验证是文本模式
			assert data['msg_type'] == 'text'
			assert 'text' in data


class TestWeComSender:
	"""测试企业微信发送器"""

	@pytest.mark.parametrize(
		'markdown_style,expected_msgtype',
		[
			('markdown', 'markdown'),
			('markdown_v2', 'markdown_v2'),
			(None, 'text'),
			('invalid', 'text'),
		]
	)
	@pytest.mark.asyncio
	@patch('httpx.AsyncClient')
	async def test_wecom_markdown_style_modes(
		self,
		mock_client: MagicMock,
		markdown_style: str | None,
		expected_msgtype: str
	):
		"""测试企业微信的 markdown_style 配置"""
		from src.notif.models import WebhookConfig
		from src.notif.senders import WeComSender

		# 构造配置
		config = WebhookConfig(
			webhook='https://example.com/webhook',
			platform_settings={'markdown_style': markdown_style},
			template=None
		)

		mock_client_instance = AsyncMock()
		mock_client.return_value.__aenter__.return_value = mock_client_instance

		# 创建 sender 并发送
		sender = WeComSender(config)
		await sender.send('测试标题', '测试内容')

		# 验证调用了 post 方法
		assert mock_client_instance.post.called
		call_args = mock_client_instance.post.call_args
		data = call_args[1]['json']

		# 验证消息格式
		assert data['msgtype'] == expected_msgtype
		if 'markdown' in expected_msgtype:
			assert expected_msgtype in data
			assert '**测试标题**' in data[expected_msgtype]['content']
		else:
			assert 'text' in data
