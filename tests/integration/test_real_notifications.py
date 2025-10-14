import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.models import NotificationData
from notif.notify import NotificationKit


class TestRealNotifications:
	"""真实的集成测试 - 只 Mock 外部依赖，让内部代码真正执行"""

	@pytest.mark.asyncio
	async def test_real_notification_with_env_config(
		self,
		notification_kit: NotificationKit,
		multiple_mixed_data: NotificationData,
	):
		"""
		真实接口测试 - 需要在 .env.test 文件中配置相应平台

		此测试会实际发送通知到配置的平台，用于验证端到端流程。
		使用 ENABLE_REAL_TEST=true 环境变量启用此测试。
		"""
		enable_key = 'ENABLE_REAL_TEST'
		if os.getenv(enable_key) != 'true':
			pytest.skip(f'未启用真实接口测试。请在 `.env.test` 中设置 `{enable_key}=true`')

		# 尝试发送通知（发送到所有已配置的平台）
		await notification_kit.push_message(
			title='集成测试消息',
			content=multiple_mixed_data,
		)

	@pytest.mark.asyncio
	async def test_notification_system_with_real_rendering(self, config_env_setter, single_success_data):
		"""
		测试通知系统的真实模板渲染

		覆盖：
		- NotificationKit 初始化
		- 配置解析（字符串、JSON）
		- 默认模板加载
		- Stencil 模板渲染
		- 所有发送器的 send 方法
		"""
		# 配置多种格式
		config_env_setter('dingtalk', 'https://mock.webhook')  # 字符串格式
		config_env_setter(
			'wecom',
			{  # JSON 格式带自定义模板
				'webhook': 'https://mock.webhook',
				'template': '测试账号：{{ stats.success_count }}/{{ stats.total_count }}',
			},
		)
		config_env_setter('email', {'user': 'test@example.com', 'pass': 'test_pass', 'to': 'recipient@example.com'})

		kit = NotificationKit()

		# Mock HTTP
		with patch('httpx.AsyncClient') as mock_http:
			mock_response = MagicMock()
			mock_response.status_code = 200
			mock_response.json.return_value = {'errcode': 0}

			mock_client = MagicMock()
			mock_client.post = AsyncMock(return_value=mock_response)
			mock_client.__aenter__ = AsyncMock(return_value=mock_client)
			mock_client.__aexit__ = AsyncMock()
			mock_http.return_value = mock_client

			# Mock SMTP
			with patch('smtplib.SMTP_SSL') as mock_smtp:
				mock_server = MagicMock()
				mock_smtp.return_value.__enter__.return_value = mock_server

				# 发送通知（真正执行渲染逻辑）
				await kit.push_message(title='测试', content=single_success_data)

				# 验证发送器被调用
				assert mock_client.post.call_count >= 2  # 至少 2 个平台
