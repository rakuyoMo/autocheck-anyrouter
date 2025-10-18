from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from notif.models import BarkConfig
from notif.senders import BarkSender


@pytest.fixture
def bark_config():
	"""创建基础的 BarkConfig 用于测试"""
	return BarkConfig(
		server_url='https://api.day.app',
		device_key='test_device_key',
	)


@pytest.mark.asyncio
async def test_bark_sender_comprehensive(bark_config):
	"""综合测试 Bark 发送器的各种功能（基础发送、platform_settings 参数传递）"""
	# 1. 测试基础发送（只有 title 和 content）
	sender = BarkSender(bark_config)

	with patch('notif.senders.bark_sender.httpx.AsyncClient') as mock_http:
		# Mock HTTP 响应
		mock_response = MagicMock()
		mock_response.is_success = True
		mock_client = MagicMock()
		mock_client.post = AsyncMock(return_value=mock_response)
		mock_client.__aenter__ = AsyncMock(return_value=mock_client)
		mock_client.__aexit__ = AsyncMock()
		mock_http.return_value = mock_client

		await sender.send(title='测试标题', content='测试内容')

		# 验证 POST 请求被正确调用
		mock_client.post.assert_called_once()
		call_args = mock_client.post.call_args
		assert call_args.args[0] == 'https://api.day.app/push'
		json_data = call_args.kwargs['json']
		assert json_data['device_key'] == 'test_device_key'
		assert json_data['title'] == '测试标题'
		assert json_data['body'] == '测试内容'

	# 2. 测试 platform_settings 的 display 参数
	bark_config.platform_settings = {
		'display': {
			'subtitle': '副标题',
			'badge': 5,
			'icon': 'https://example.com/icon.png',
			'group': 'TestGroup',
		},
	}
	sender = BarkSender(bark_config)

	with patch('notif.senders.bark_sender.httpx.AsyncClient') as mock_http:
		mock_response = MagicMock()
		mock_response.is_success = True
		mock_client = MagicMock()
		mock_client.post = AsyncMock(return_value=mock_response)
		mock_client.__aenter__ = AsyncMock(return_value=mock_client)
		mock_client.__aexit__ = AsyncMock()
		mock_http.return_value = mock_client

		await sender.send(title='标题', content='内容')

		json_data = mock_client.post.call_args.kwargs['json']
		assert json_data['subtitle'] == '副标题'
		assert json_data['badge'] == 5
		assert json_data['icon'] == 'https://example.com/icon.png'
		assert json_data['group'] == 'TestGroup'

	# 3. 测试 platform_settings 的 alert 参数
	bark_config.platform_settings = {
		'alert': {
			'sound': 'birdsong',
			'call': '1',
			'level': 'timeSensitive',
			'volume': '0.8',
		},
	}
	sender = BarkSender(bark_config)

	with patch('notif.senders.bark_sender.httpx.AsyncClient') as mock_http:
		mock_response = MagicMock()
		mock_response.is_success = True
		mock_client = MagicMock()
		mock_client.post = AsyncMock(return_value=mock_response)
		mock_client.__aenter__ = AsyncMock(return_value=mock_client)
		mock_client.__aexit__ = AsyncMock()
		mock_http.return_value = mock_client

		await sender.send(title='标题', content='内容')

		json_data = mock_client.post.call_args.kwargs['json']
		assert json_data['sound'] == 'birdsong'
		assert json_data['call'] == '1'
		assert json_data['level'] == 'timeSensitive'
		assert json_data['volume'] == '0.8'

	# 4. 测试 platform_settings 的 interaction 和 options 参数
	bark_config.platform_settings = {
		'interaction': {
			'url': 'https://example.com',
			'action': 'none',
			'autoCopy': '1',
			'copy': '复制内容',
		},
		'options': {
			'isArchive': '1',
		},
	}
	sender = BarkSender(bark_config)

	with patch('notif.senders.bark_sender.httpx.AsyncClient') as mock_http:
		mock_response = MagicMock()
		mock_response.is_success = True
		mock_client = MagicMock()
		mock_client.post = AsyncMock(return_value=mock_response)
		mock_client.__aenter__ = AsyncMock(return_value=mock_client)
		mock_client.__aexit__ = AsyncMock()
		mock_http.return_value = mock_client

		await sender.send(title='标题', content='内容')

		json_data = mock_client.post.call_args.kwargs['json']
		assert json_data['url'] == 'https://example.com'
		assert json_data['action'] == 'none'
		assert json_data['autoCopy'] == '1'
		assert json_data['copy'] == '复制内容'
		assert json_data['isArchive'] == '1'

	# 5. 测试空值和 None 值的处理（不应该添加到请求中）
	bark_config.platform_settings = {
		'display': {
			'subtitle': '',  # 空字符串不应该添加
			'badge': None,  # None 不应该添加
			'group': 'TestGroup',  # 正常值应该添加
		},
	}
	sender = BarkSender(bark_config)

	with patch('notif.senders.bark_sender.httpx.AsyncClient') as mock_http:
		mock_response = MagicMock()
		mock_response.is_success = True
		mock_client = MagicMock()
		mock_client.post = AsyncMock(return_value=mock_response)
		mock_client.__aenter__ = AsyncMock(return_value=mock_client)
		mock_client.__aexit__ = AsyncMock()
		mock_http.return_value = mock_client

		await sender.send(title='标题', content='内容')

		json_data = mock_client.post.call_args.kwargs['json']
		assert 'subtitle' not in json_data  # 空字符串不应该被添加
		assert 'badge' not in json_data  # None 不应该被添加
		assert json_data['group'] == 'TestGroup'  # 正常值应该存在
