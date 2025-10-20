import os
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

import pytest

from core import CheckinService
from tests.conftest import assert_file_content_contains
from tests.fixtures.data import STANDARD_ACCOUNTS
from tests.fixtures.mock_dependencies import (
	CHANGED_QUOTA,
	DEFAULT_USED_QUOTA,
	HttpRequestTracker,
	MockHttpClient,
	MockPlaywright,
	MockSMTP,
)


class TestCheckinFlow:
	"""测试完整签到流程"""

	@pytest.mark.asyncio
	async def test_complete_flow_with_multiple_notifications(self, accounts_env, config_env_setter, tmp_path):
		"""测试完整签到流程（多账号 + 多平台通知 + GitHub 报告）"""
		# 设置账号和通知配置
		accounts_env(STANDARD_ACCOUNTS)
		config_env_setter('dingtalk', 'https://mock.dingtalk.com/hook')

		service = CheckinService()
		service.balance_manager.balance_hash_file = tmp_path / 'balance_hash.txt'
		summary_file = tmp_path / 'summary.md'

		with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(summary_file)}):
			with ExitStack() as stack:
				MockPlaywright.setup_success(stack)

				tracker = HttpRequestTracker()
				MockHttpClient.setup(stack, tracker.get_handler, tracker.post_handler)
				MockSMTP.setup(stack)

				with pytest.raises(SystemExit) as exc_info:
					await service.run()

		# 验证签到成功
		assert exc_info.value.code == 0

		# 验证余额文件已保存并包含正确数据
		assert service.balance_manager.balance_hash_file.exists()
		balance_data = service.balance_manager.load_balance_hash()
		assert balance_data is not None
		assert len(balance_data) == 2  # 2 个账号

		# 验证 GitHub 报告已生成并包含关键信息
		assert summary_file.exists()
		assert_file_content_contains(summary_file, '签到任务完成')
		assert_file_content_contains(summary_file, '成功')

	@pytest.mark.asyncio
	async def test_balance_change_detection_and_notify_triggers(self, accounts_env, config_env_setter, tmp_path, monkeypatch):
		"""测试余额变化检测流程和通知触发器逻辑"""
		accounts_env(STANDARD_ACCOUNTS)
		config_env_setter('dingtalk', 'https://mock.dingtalk.com/hook')

		# 第一次运行（首次运行，会发送通知）
		service_first = CheckinService()
		service_first.balance_manager.balance_hash_file = tmp_path / 'balance_hash.txt'

		with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
			with ExitStack() as stack:
				MockPlaywright.setup_success(stack)
				tracker_first = HttpRequestTracker()
				MockHttpClient.setup(stack, tracker_first.get_handler, tracker_first.post_handler)

				with patch('notif.notification_kit.NotificationKit.push_message', new=AsyncMock()) as mock_push_first:
					with pytest.raises(SystemExit):
						await service_first.run()

		assert mock_push_first.await_count == 1, "首次运行应该发送通知"

		# 第二次运行（余额未变化，不发送通知）
		service_second = CheckinService()
		service_second.balance_manager.balance_hash_file = tmp_path / 'balance_hash.txt'

		with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
			with ExitStack() as stack:
				MockPlaywright.setup_success(stack)
				tracker_second = HttpRequestTracker()
				MockHttpClient.setup(stack, tracker_second.get_handler, tracker_second.post_handler)

				with patch('notif.notification_kit.NotificationKit.push_message', new=AsyncMock()) as mock_push_second:
					with pytest.raises(SystemExit):
						await service_second.run()

		assert mock_push_second.await_count == 0, "余额未变化不应该发送通知"

		# 第三次运行（余额变化，发送通知）
		service_third = CheckinService()
		service_third.balance_manager.balance_hash_file = tmp_path / 'balance_hash.txt'

		with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
			with ExitStack() as stack:
				MockPlaywright.setup_success(stack)

				async def get_handler_changed(*args, **kwargs):
					return MockHttpClient.build_response(
						status=200,
						json_data={
							'success': True,
							'data': {
								'quota': CHANGED_QUOTA,  # 余额变化
								'used_quota': DEFAULT_USED_QUOTA,
							},
						},
					)

				MockHttpClient.setup(stack, get_handler_changed, MockHttpClient.post_success_handler)

				with patch('notif.notification_kit.NotificationKit.push_message', new=AsyncMock()) as mock_push_third:
					with pytest.raises(SystemExit):
						await service_third.run()

		assert mock_push_third.await_count == 1, "余额变化应该发送通知"

		# 测试不同的触发器场景
		trigger_scenarios = [
			('never', False, '不应该发送通知'),
			('always', True, '应该总是发送通知'),
			('success', True, '有成功账号应该发送通知'),
		]

		for triggers, should_notify, reason in trigger_scenarios:
			monkeypatch.setenv('NOTIFY_TRIGGERS', triggers)
			service = CheckinService()
			service.balance_manager.balance_hash_file = tmp_path / f'hash_{triggers}.txt'

			with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
				with ExitStack() as stack:
					MockPlaywright.setup_success(stack)
					MockHttpClient.setup(stack, MockHttpClient.get_success_handler, MockHttpClient.post_success_handler)

					with patch('notif.notification_kit.NotificationKit.push_message', new=AsyncMock()) as mock_push:
						with pytest.raises(SystemExit):
							await service.run()

			expected_count = 1 if should_notify else 0
			assert mock_push.await_count == expected_count, f"触发器 {triggers}: {reason}"

	@pytest.mark.asyncio
	async def test_partial_and_full_failure_scenarios(self, accounts_env, tmp_path):
		"""测试部分失败和全部失败场景"""
		accounts_env(STANDARD_ACCOUNTS)

		# 测试部分失败
		service_partial = CheckinService()
		service_partial.balance_manager.balance_hash_file = tmp_path / 'hash_partial.txt'

		with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
			with ExitStack() as stack:
				MockPlaywright.setup_success(stack)

				call_count = {'post': 0}

				async def post_handler_partial(*args, **kwargs):
					call_count['post'] += 1
					if call_count['post'] == 1:
						return MockHttpClient.build_response(status=200, json_data={'ret': 1})
					return MockHttpClient.build_response(status=500)  # 第二个账号失败

				MockHttpClient.setup(stack, MockHttpClient.get_success_handler, post_handler_partial)

				with patch('notif.notification_kit.NotificationKit.push_message', new=AsyncMock()) as mock_push:
					with pytest.raises(SystemExit):
						await service_partial.run()

		assert mock_push.await_count == 1, "有失败账号应该发送通知"
		assert call_count['post'] == 2, "应该尝试签到 2 个账号"

		# 测试全部失败
		service_all_fail = CheckinService()
		service_all_fail.balance_manager.balance_hash_file = tmp_path / 'hash_all_fail.txt'

		with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
			with ExitStack() as stack:
				MockPlaywright.setup_success(stack)

				async def post_handler_fail(*args, **kwargs):
					return MockHttpClient.build_response(status=500)

				MockHttpClient.setup(stack, MockHttpClient.get_success_handler, post_handler_fail)

				with patch('notif.notification_kit.NotificationKit.push_message', new=AsyncMock()) as mock_push:
					with pytest.raises(SystemExit) as exc_info:
						await service_all_fail.run()

		assert exc_info.value.code == 1, "全部失败退出码应该是 1"
		assert mock_push.await_count == 1, "有失败账号应该发送通知"
