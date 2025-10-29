from contextlib import ExitStack
from unittest.mock import patch

import httpx
import pytest

from notif.models import BarkConfig, EmailConfig, PushPlusConfig, ServerPushConfig, TelegramConfig, WebhookConfig
from notif.senders import (
	BarkSender,
	DingTalkSender,
	EmailSender,
	FeishuSender,
	PushPlusSender,
	ServerPushSender,
	TelegramSender,
	WeComSender,
)
from tests.fixtures.mock_dependencies import MockHttpClient, MockSMTP


class TestSenders:
	"""测试所有发送器"""

	@pytest.mark.asyncio
	@pytest.mark.parametrize(
		'sender_class,config,expected_json_keys',
		[
			(DingTalkSender, WebhookConfig(webhook='https://test.dingtalk.com', template=None), ['msgtype', 'text']),
			(FeishuSender, WebhookConfig(webhook='https://test.feishu.com', template=None), ['msg_type', 'text']),
			(WeComSender, WebhookConfig(webhook='https://test.wecom.com', template=None), ['msgtype', 'text']),
		],
	)
	async def test_webhook_senders(self, sender_class, config, expected_json_keys: list[str]):
		"""测试 Webhook 类发送器（钉钉/飞书/企微）"""
		sender = sender_class(config)
		test_title = '测试标题'
		test_content = '测试内容 **加粗**'
		test_context = {'all_success': True}

		with ExitStack() as stack:
			sent_data = {}

			async def post_handler(*args, **kwargs):
				# 捕获发送的数据
				if 'json' in kwargs:
					sent_data.update(kwargs['json'])
				return MockHttpClient.build_response(status=200, json_data={'errcode': 0, 'code': 0})

			MockHttpClient.setup(stack, MockHttpClient.get_success_handler, post_handler)

			await sender.send(
				title=test_title,
				content=test_content,
				context_data=test_context,
			)

			# 验证发送的数据结构
			for key in expected_json_keys:
				assert key in sent_data, f'发送数据缺少键: {key}, 实际数据: {sent_data}'

			# 验证内容被包含（可能在嵌套结构中）
			sent_json_str = str(sent_data)
			assert test_title in sent_json_str or test_content in sent_json_str, '发送数据不包含标题或内容'

	@pytest.mark.asyncio
	@pytest.mark.parametrize(
		'sender_class,config_builder',
		[
			(DingTalkSender, lambda: WebhookConfig(webhook='https://test.dingtalk.com', template=None)),
			(PushPlusSender, lambda: PushPlusConfig(token='test_token', template=None)),
			(BarkSender, lambda: BarkConfig(device_key='test_key', server_url='https://api.day.app', template=None)),
			(TelegramSender, lambda: TelegramConfig(bot_token='test_token', chat_id='123456', template=None)),
		],
	)
	async def test_http_network_errors(self, sender_class, config_builder):
		"""测试 HTTP 网络错误处理（超时、连接失败）"""
		sender = sender_class(config_builder())

		# 测试超时异常
		with patch('httpx.AsyncClient.post', side_effect=httpx.TimeoutException('Request timeout')):
			with pytest.raises(httpx.TimeoutException):
				await sender.send(title='测试', content='内容', context_data={})

		# 测试连接错误
		with patch('httpx.AsyncClient.post', side_effect=httpx.ConnectError('Connection failed')):
			with pytest.raises(httpx.ConnectError):
				await sender.send(title='测试', content='内容', context_data={})

	@pytest.mark.asyncio
	@pytest.mark.parametrize(
		'sender_class,config_builder,error_match',
		[
			(
				DingTalkSender,
				lambda: WebhookConfig(webhook='https://test.dingtalk.com', template=None),
				'钉钉推送失败.*500',
			),
			(
				BarkSender,
				lambda: BarkConfig(device_key='test_key', server_url='https://api.day.app', template=None),
				'Bark 推送失败.*400',
			),
			(
				TelegramSender,
				lambda: TelegramConfig(bot_token='test_token', chat_id='123456', template=None),
				'Telegram 推送失败.*400',
			),
		],
	)
	async def test_http_status_code_errors(self, sender_class, config_builder, error_match: str):
		"""测试 HTTP 状态码错误（404/500/502）"""
		sender = sender_class(config_builder())

		with ExitStack() as stack:
			# 钉钉用 500 错误，Bark 和 Telegram 用 400 错误
			status_code = 500 if sender_class == DingTalkSender else 400

			async def post_handler_error(*args, **kwargs):
				return MockHttpClient.build_response(status=status_code, text='Error')

			MockHttpClient.setup(stack, MockHttpClient.get_success_handler, post_handler_error)

			with pytest.raises(Exception, match=error_match):
				await sender.send(title='测试', content='内容', context_data={})

	@pytest.mark.asyncio
	@pytest.mark.parametrize(
		'sender_class,config_builder,error_match,title,should_raise',
		[
			# Email 发送器
			(
				EmailSender,
				lambda: EmailConfig(
					user='test@example.com', password='password', to='recipient@example.com', template=None
				),
				'邮件推送需要提供非空的 title 参数',
				None,
				True,
			),
			(
				EmailSender,
				lambda: EmailConfig(
					user='test@example.com', password='password', to='recipient@example.com', template=None
				),
				'邮件推送需要提供非空的 title 参数',
				'',
				True,
			),
			(
				EmailSender,
				lambda: EmailConfig(
					user='test@example.com', password='password', to='recipient@example.com', template=None
				),
				'',
				'有效标题',
				False,
			),
			# ServerPush 发送器
			(
				ServerPushSender,
				lambda: ServerPushConfig(send_key='test_key', template=None),
				'Server 酱推送需要提供非空的 title 参数',
				None,
				True,
			),
			(
				ServerPushSender,
				lambda: ServerPushConfig(send_key='test_key', template=None),
				'Server 酱推送需要提供非空的 title 参数',
				'',
				True,
			),
			(ServerPushSender, lambda: ServerPushConfig(send_key='test_key', template=None), '', '有效标题', False),
		],
	)
	async def test_title_validation(
		self,
		sender_class,
		config_builder,
		error_match: str,
		title: str | None,
		should_raise: bool,
	):
		"""测试发送器的 title 验证（Email/ServerPush）"""
		config = config_builder()
		sender = sender_class(config)

		if should_raise:
			with pytest.raises(ValueError, match=error_match):
				if sender_class == EmailSender:
					with ExitStack() as stack:
						MockSMTP.setup(stack)
						await sender.send(title=title, content='测试内容', context_data={})
				else:
					await sender.send(title=title, content='测试内容', context_data={})
		else:
			if sender_class == EmailSender:
				with ExitStack() as stack:
					MockSMTP.setup(stack)
					await sender.send(title=title, content='测试内容', context_data={})
			else:
				with ExitStack() as stack:
					MockHttpClient.setup(stack, MockHttpClient.get_success_handler, MockHttpClient.post_success_handler)
					await sender.send(title=title, content='测试内容', context_data={})
