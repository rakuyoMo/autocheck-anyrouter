import json
import os
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from core import CheckinService
from tests.fixtures.data import SINGLE_ACCOUNT
from tests.fixtures.mock_dependencies import MockHttpClient, MockPlaywright


class TestErrorHandling:
	"""测试错误处理"""

	@pytest.mark.asyncio
	async def test_http_errors_and_network_issues(self, accounts_env, tmp_path):
		"""测试 HTTP 错误和网络问题（401/500/超时/JSON 错误）"""
		# 测试 401/500 错误
		accounts_env([
			{'name': '401 账号', 'cookies': 'session=401', 'api_user': 'user_401'},
			{'name': '500 账号', 'cookies': 'session=500', 'api_user': 'user_500'},
		])
		service_http = CheckinService()
		service_http.balance_manager.balance_hash_file = tmp_path / 'hash_http.txt'

		with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
			with ExitStack() as stack:
				MockPlaywright.setup_success(stack)

				call_count = {'get': 0}

				async def get_handler(*args, **kwargs):
					call_count['get'] += 1
					if call_count['get'] == 1:
						return MockHttpClient.build_response(status=401)
					return MockHttpClient.build_response(status=500)

				MockHttpClient.setup(stack, get_handler, MockHttpClient.post_success_handler)

				with pytest.raises(SystemExit):
					await service_http.run()

		assert call_count['get'] == 2, "应该尝试获取 2 个账号的余额"

		# 测试超时异常
		accounts_env(SINGLE_ACCOUNT)
		service_timeout = CheckinService()
		service_timeout.balance_manager.balance_hash_file = tmp_path / 'hash_timeout.txt'

		with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
			with ExitStack() as stack:
				MockPlaywright.setup_success(stack)

				async def get_handler_timeout(*args, **kwargs):
					raise httpx.TimeoutException('Request timeout')

				MockHttpClient.setup(stack, get_handler_timeout, MockHttpClient.post_success_handler)

				with pytest.raises(SystemExit):
					await service_timeout.run()

		# 测试 JSON 解析错误
		accounts_env(SINGLE_ACCOUNT)
		service_json = CheckinService()
		service_json.balance_manager.balance_hash_file = tmp_path / 'hash_json.txt'

		with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
			with ExitStack() as stack:
				MockPlaywright.setup_success(stack)

				async def get_handler_json(*args, **kwargs):
					resp = MockHttpClient.build_response(status=200)
					resp.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)
					return resp

				async def post_handler_json(*args, **kwargs):
					resp = MockHttpClient.build_response(status=200, text='success')
					resp.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)
					return resp

				MockHttpClient.setup(stack, get_handler_json, post_handler_json)

				with pytest.raises(SystemExit):
					await service_json.run()

	@pytest.mark.asyncio
	async def test_waf_and_playwright_errors(self, accounts_env, tmp_path):
		"""测试 WAF cookies 获取异常和 Playwright 错误"""
		accounts_env(SINGLE_ACCOUNT)
		service = CheckinService()
		service.balance_manager.balance_hash_file = tmp_path / 'hash_waf.txt'

		with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
			with ExitStack() as stack:
				# Playwright 启动失败
				MockPlaywright.setup_failure(stack, Exception('Playwright 启动失败'))

				with pytest.raises(SystemExit) as exc_info:
					await service.run()

		assert exc_info.value.code == 1

		# 测试 cookies 缺失
		service2 = CheckinService()
		service2.balance_manager.balance_hash_file = tmp_path / 'hash_waf2.txt'

		with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
			with ExitStack() as stack:
				# 返回不完整的 cookies
				MockPlaywright.setup_success(stack, cookies=[
					{'name': 'acw_tc', 'value': 'value1'},
					# 缺少其他必需的 cookies
				])

				with pytest.raises(SystemExit):
					await service2.run()

	@pytest.mark.asyncio
	@pytest.mark.parametrize(
		'payload,description',
		[
			(None, '无配置'),
			('not a json', 'JSON 格式错误'),
			('{"name": "test"}', '非数组格式'),
			('[{"name": "test"}]', '缺少必需字段'),
			('[{"name": "", "cookies": "c", "api_user": "u"}]', '空名称字段'),
		],
	)
	async def test_account_config_validation(self, monkeypatch: pytest.MonkeyPatch, tmp_path, payload: str | None, description: str):
		"""测试账号配置验证（参数化测试）"""
		if payload is None:
			monkeypatch.delenv('ANYROUTER_ACCOUNTS', raising=False)
		else:
			monkeypatch.setenv('ANYROUTER_ACCOUNTS', payload)

		service = CheckinService()
		service.balance_manager.balance_hash_file = tmp_path / f'hash_{description}.txt'

		with pytest.raises(SystemExit) as exc_info:
			await service.run()

		assert exc_info.value.code == 0, f"{description}: 配置错误时应该正常退出"


	@pytest.mark.asyncio
	async def test_account_execution_exception(self, accounts_env, tmp_path):
		"""测试账号执行过程中的意外异常"""
		accounts_env(SINGLE_ACCOUNT)
		service = CheckinService()
		service.balance_manager.balance_hash_file = tmp_path / 'hash_exception.txt'

		# Mock _check_in_account 方法抛出异常
		failing_checkin = AsyncMock(side_effect=Exception('Unexpected error'))

		with patch.object(service, '_check_in_account', failing_checkin):
			with patch('notif.notification_kit.NotificationKit.push_message', new=AsyncMock()) as mock_push:
				with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
					with pytest.raises(SystemExit) as exc_info:
						await service.run()

		assert exc_info.value.code == 1, "异常应该导致失败退出"
		assert mock_push.await_count == 1, "异常也应该发送通知"
