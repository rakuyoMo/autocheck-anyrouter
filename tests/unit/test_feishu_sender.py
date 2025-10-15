from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from notif.models import WebhookConfig
from notif.senders import FeishuSender


@pytest.fixture
def feishu_config():
	"""创建基础的 FeishuSender 配置用于测试"""
	return WebhookConfig(
		webhook='https://open.feishu.cn/open-apis/bot/v2/hook/test_token',
		platform_settings={'use_card': True, 'color_theme': 'blue'},
	)


@pytest.mark.asyncio
async def test_feishu_dynamic_color_theme(feishu_config):
	"""验证飞书动态 color_theme 渲染（覆盖全部成功/部分成功/全部失败三种场景）"""
	# 配置动态 color_theme
	feishu_config.platform_settings['color_theme'] = (
		'{% if all_success %}green{% else %}{% if partial_success %}orange{% else %}red{% endif %}{% endif %}'
	)
	sender = FeishuSender(feishu_config)

	with patch('httpx.AsyncClient') as mock_http:
		# Mock HTTP 响应
		mock_response = MagicMock()
		mock_response.is_success = True
		mock_client = MagicMock()
		mock_client.post = AsyncMock(return_value=mock_response)
		mock_client.__aenter__ = AsyncMock(return_value=mock_client)
		mock_client.__aexit__ = AsyncMock()
		mock_http.return_value = mock_client

		# 场景 1: 全部成功 → 绿色
		await sender.send(
			title='测试',
			content='内容',
			context_data={'all_success': True, 'partial_success': False},
		)
		assert mock_client.post.call_args.kwargs['json']['card']['header']['template'] == 'green'

		# 场景 2: 部分成功 → 橙色
		await sender.send(
			title='测试',
			content='内容',
			context_data={'all_success': False, 'partial_success': True},
		)
		assert mock_client.post.call_args.kwargs['json']['card']['header']['template'] == 'orange'

		# 场景 3: 全部失败 → 红色
		await sender.send(
			title='测试',
			content='内容',
			context_data={'all_success': False, 'partial_success': False},
		)
		assert mock_client.post.call_args.kwargs['json']['card']['header']['template'] == 'red'


@pytest.mark.asyncio
async def test_feishu_static_color_and_text_mode(feishu_config):
	"""验证飞书静态 color_theme（向后兼容）和文本模式"""
	sender = FeishuSender(feishu_config)

	with patch('httpx.AsyncClient') as mock_http:
		# Mock HTTP 响应
		mock_response = MagicMock()
		mock_response.is_success = True
		mock_client = MagicMock()
		mock_client.post = AsyncMock(return_value=mock_response)
		mock_client.__aenter__ = AsyncMock(return_value=mock_client)
		mock_client.__aexit__ = AsyncMock()
		mock_http.return_value = mock_client

		# 测试静态颜色（向后兼容）
		await sender.send(
			title='测试',
			content='内容',
			context_data=None,
		)
		json_data = mock_client.post.call_args.kwargs['json']
		assert json_data['card']['header']['template'] == 'blue'

		# 测试文本模式
		feishu_config.platform_settings['use_card'] = False
		sender = FeishuSender(feishu_config)
		await sender.send(
			title='测试标题',
			content='测试内容',
			context_data=None,
		)
		json_data = mock_client.post.call_args.kwargs['json']
		assert json_data['msg_type'] == 'text'
		assert json_data['text']['content'] == '测试标题\n测试内容'


@pytest.mark.asyncio
async def test_feishu_template_fallback():
	"""验证模板渲染失败时的降级行为（返回原始值）"""
	config = WebhookConfig(
		webhook='https://test.com',
		platform_settings={'use_card': True, 'color_theme': '{% if invalid %}'},
	)
	sender = FeishuSender(config)

	with patch('httpx.AsyncClient') as mock_http:
		# Mock HTTP 响应
		mock_response = MagicMock()
		mock_response.is_success = True
		mock_client = MagicMock()
		mock_client.post = AsyncMock(return_value=mock_response)
		mock_client.__aenter__ = AsyncMock(return_value=mock_client)
		mock_client.__aexit__ = AsyncMock()
		mock_http.return_value = mock_client

		# 错误的模板应该降级为原始值
		await sender.send(
			title='测试',
			content='内容',
			context_data={'all_success': True},
		)
		json_data = mock_client.post.call_args.kwargs['json']
		assert json_data['card']['header']['template'] == '{% if invalid %}'

		# 无 context_data 时，即使是有效模板也返回原始值
		config2 = WebhookConfig(
			webhook='https://test.com',
			platform_settings={'use_card': True, 'color_theme': '{% if all_success %}green{% endif %}'},
		)
		sender2 = FeishuSender(config2)
		await sender2.send(
			title='测试',
			content='内容',
			context_data=None,
		)
		json_data = mock_client.post.call_args.kwargs['json']
		assert json_data['card']['header']['template'] == '{% if all_success %}green{% endif %}'

