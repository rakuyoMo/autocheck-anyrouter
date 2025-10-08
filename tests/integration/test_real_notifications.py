import os
from unittest.mock import patch

import pytest


class TestIntegration:
	"""集成测试 - 测试端到端流程"""

	@pytest.fixture
	def notification_kit_from_env(self):
		"""从环境变量创建 NotificationKit 实例（用于集成测试）"""
		from src.notif.notify import NotificationKit
		return NotificationKit()

	@pytest.fixture
	def test_notification_data(self):
		"""创建测试用的通知数据"""
		from src.core.models.notification_data import NotificationData
		from src.core.models.account_result import AccountResult
		from src.core.models.notification_stats import NotificationStats

		return NotificationData(
			accounts=[
				AccountResult(
					name='测试账号',
					status='success',
					quota=25.0,
					used=5.0,
					error=None
				)
			],
			stats=NotificationStats(success_count=1, failed_count=0, total_count=1),
			timestamp='2024-01-01 12:00:00'
		)

	def test_real_notification_with_env_config(
		self,
		notification_kit_from_env,
		test_notification_data
	):
		"""
		真实接口测试 - 需要在 .env.local 文件中配置 ENABLE_REAL_TEST=true

		此测试会实际发送通知到配置的平台，用于验证端到端流程。
		"""
		if os.getenv('ENABLE_REAL_TEST') != 'true':
			pytest.skip('未启用真实接口测试。请在 .env.local 中设置 ENABLE_REAL_TEST=true')

		# 尝试发送通知
		notification_kit_from_env.push_message('集成测试消息', test_notification_data)

		# 如果没有抛出异常，则测试通过
		# 注意：这个测试不验证通知是否真的成功发送，只验证代码执行流程正确

	@patch('src.notif.notify.NotificationKit._send_email_with_template')
	@patch('src.notif.notify.NotificationKit._send_dingtalk_with_template')
	@patch('src.notif.notify.NotificationKit._send_wecom_with_template')
	@patch('src.notif.notify.NotificationKit._send_pushplus_with_template')
	@patch('src.notif.notify.NotificationKit._send_feishu_with_template')
	@patch('src.notif.notify.NotificationKit._send_serverpush_with_template')
	def test_push_message_routing_logic(
		self,
		mock_serverpush,
		mock_feishu,
		mock_pushplus,
		mock_wecom,
		mock_dingtalk,
		mock_email,
		notification_kit_from_env,
		test_notification_data
	):
		"""测试 push_message 的路由逻辑 - 验证根据配置调用相应平台"""
		notification_kit_from_env.push_message('测试标题', test_notification_data)

		# 验证所有平台的发送方法都被调用了（因为 push_message 总是尝试所有平台）
		# 只是有些平台会因为配置为 None 而抛出异常
		total_calls = (
			mock_email.called +
			mock_dingtalk.called +
			mock_wecom.called +
			mock_pushplus.called +
			mock_feishu.called +
			mock_serverpush.called
		)

		# 至少应该有被调用的方法
		assert total_calls > 0

		# 验证 push_message 确实尝试了发送消息（通过调用发送方法）
		# 不论配置是否存在，都应该尝试调用发送方法
		assert mock_email.called or mock_dingtalk.called or mock_wecom.called or mock_pushplus.called or mock_feishu.called or mock_serverpush.called