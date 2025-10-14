import json
import os
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from core import CheckinService
from notif.notify import NotificationKit


class TestSuperIntegration:
	"""超级集成测试，精简用例但覆盖核心路径。"""

	def test_main_entry_point(self):
		"""验证 main 入口的退出码处理。"""
		from main import run_main

		def _raise_exit(code: int):
			def _handler(coro):
				if hasattr(coro, 'close'):
					coro.close()
				raise SystemExit(code)

			return _handler

		with patch('main.CheckinService') as mock_service_class:
			mock_service = MagicMock()
			mock_service.run = AsyncMock()
			mock_service_class.return_value = mock_service

			with patch('main.asyncio.run') as mock_asyncio_run:
				mock_asyncio_run.side_effect = _raise_exit(0)

				with pytest.raises(SystemExit) as exc_info:
					run_main()

				assert exc_info.value.code == 0
				mock_service_class.assert_called_once()

		with patch('main.CheckinService') as mock_service_class:
			mock_service = MagicMock()
			mock_service_class.return_value = mock_service

			with patch('main.asyncio.run') as mock_asyncio_run:

				def _raise_keyboard(coro):
					if hasattr(coro, 'close'):
						coro.close()
					raise KeyboardInterrupt()

				mock_asyncio_run.side_effect = _raise_keyboard

				with pytest.raises(SystemExit) as exc_info:
					run_main()

				assert exc_info.value.code == 1

		with patch('main.CheckinService') as mock_service_class:
			mock_service = MagicMock()
			mock_service_class.return_value = mock_service

			with patch('main.asyncio.run') as mock_asyncio_run:

				def _raise_error(coro):
					if hasattr(coro, 'close'):
						coro.close()
					raise Exception('测试错误')

				mock_asyncio_run.side_effect = _raise_error

				with pytest.raises(SystemExit) as exc_info:
					run_main()

				assert exc_info.value.code == 1

	@pytest.mark.asyncio
	async def test_checkin_success_flow_with_summary(self, accounts_env, config_env_setter, tmp_path):
		"""验证首次运行的成功流程会生成总结并发送通知。"""
		accounts_env(
			[
				{'name': '测试账号 A', 'cookies': 'session=a', 'api_user': 'user_a'},
				{'name': '测试账号 B', 'cookies': 'session=b', 'api_user': 'user_b'},
			]
		)

		config_env_setter('dingtalk', 'https://mock.dingtalk')
		config_env_setter(
			'feishu',
			{
				'webhook': 'https://mock.feishu',
				'template': '成功：{{ stats.success_count }}',
			},
		)
		config_env_setter('wecom', 'https://mock.wecom')
		config_env_setter('pushplus', 'mock_pushplus_token')
		config_env_setter('serverpush', 'mock_serverpush_key')
		config_env_setter(
			'email',
			{
				'user': 'sender@example.com',
				'pass': 'mock_password',
				'to': 'receiver@example.com',
				'smtp_server': 'smtp.example.com',
			},
		)

		service = CheckinService()
		service.balance_hash_file = tmp_path / 'success_hash.txt'
		summary_file = tmp_path / 'summary_success.md'

		with patch.dict(
			os.environ,
			{
				'REPO_VISIBILITY': 'public',
				'GITHUB_STEP_SUMMARY': str(summary_file),
			},
		):
			with ExitStack() as stack:
				_patch_playwright_success(stack)

				post_calls = {'count': 0, 'checkin': 0}

				async def get_handler(*args, **kwargs):
					return _build_response(
						status=200,
						json_data={
							'success': True,
							'data': {'quota': 25000000, 'used_quota': 5000000},
						},
					)

				async def post_handler(*args, **kwargs):
					post_calls['count'] += 1
					if post_calls['checkin'] < 2:
						post_calls['checkin'] += 1
						return _build_response(status=200, json_data={'ret': 1, 'msg': '签到成功'})
					return _build_response(status=200, json_data={'errcode': 0, 'code': 0, 'message': 'ok'}, text='ok')

				_patch_http_client(stack, get_handler, post_handler)
				_patch_smtp(stack)

				with pytest.raises(SystemExit) as exc_info:
					await service.run()

		assert exc_info.value.code == 0
		assert summary_file.exists()
		assert service.balance_hash_file.exists()
		assert post_calls['count'] >= 2
		assert post_calls['checkin'] == 2

		service_second = CheckinService()
		service_second.balance_hash_file = service.balance_hash_file
		summary_second = tmp_path / 'summary_second.md'

		with patch.dict(
			os.environ,
			{
				'REPO_VISIBILITY': 'public',
				'GITHUB_STEP_SUMMARY': str(summary_second),
			},
		):
			with ExitStack() as stack:
				_patch_playwright_success(stack)

				post_calls_second = {'count': 0, 'checkin': 0}

				async def get_handler_second(*args, **kwargs):
					return _build_response(
						status=200,
						json_data={
							'success': True,
							'data': {'quota': 25000000, 'used_quota': 5000000},
						},
					)

				async def post_handler_second(*args, **kwargs):
					post_calls_second['count'] += 1
					if post_calls_second['checkin'] < 2:
						post_calls_second['checkin'] += 1
						return _build_response(status=200, json_data={'ret': 1, 'msg': '签到成功'})
					return _build_response(status=200, json_data={'errcode': 0})

				_patch_http_client(stack, get_handler_second, post_handler_second)
				_patch_smtp(stack)

				with patch('notif.notify.NotificationKit.push_message', new=AsyncMock()) as mock_push:
					with pytest.raises(SystemExit) as exc_info:
						await service_second.run()

		assert exc_info.value.code == 0
		assert post_calls_second['checkin'] == 2
		assert mock_push.await_count == 0
		assert summary_second.exists()

	@pytest.mark.asyncio
	async def test_checkin_with_http_errors(self, accounts_env, config_env_setter, tmp_path):
		"""验证部分失败及 HTTP 异常路径。"""
		accounts_env(
			[
				{'name': '成功账号', 'cookies': 'session=ok', 'api_user': 'user_ok'},
				{'name': '401 账号', 'cookies': 'session=401', 'api_user': 'user_401'},
				{'name': '500 账号', 'cookies': 'session=500', 'api_user': 'user_500'},
			]
		)
		config_env_setter('wecom', 'https://mock.wecom')
		service = CheckinService()
		service.balance_hash_file = tmp_path / 'partial_hash.txt'

		with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
			with ExitStack() as stack:
				_patch_playwright_success(stack)

				call_state = {'get': 0, 'post': 0}

				async def get_handler(*args, **kwargs):
					call_state['get'] += 1
					if call_state['get'] == 2:
						return _build_response(status=401, json_error=Exception('Unauthorized'))
					if call_state['get'] == 3:
						resp = _build_response(status=500, text='Internal Server Error')
						resp.json.side_effect = Exception('Invalid')
						return resp
					return _build_response(
						status=200,
						json_data={'success': True, 'data': {'quota': 25000000, 'used_quota': 5000000}},
					)

				async def post_handler(*args, **kwargs):
					call_state['post'] += 1
					if call_state['post'] == 1:
						return _build_response(status=200, json_data={'ret': 1})
					return _build_response(status=200, json_data={'errcode': 0})

				_patch_http_client(stack, get_handler, post_handler)

				with pytest.raises(SystemExit) as exc_info:
					await service.run()

		assert exc_info.value.code == 0
		assert call_state['get'] >= 3

		accounts_env(
			[
				{'name': '超时账号', 'cookies': 'session=timeout', 'api_user': 'user_timeout'},
				{'name': 'JSON 错误账号', 'cookies': 'session=json', 'api_user': 'user_json'},
			]
		)
		service_timeout = CheckinService()
		service_timeout.balance_hash_file = tmp_path / 'timeout_hash.txt'

		with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
			with ExitStack() as stack:
				_patch_playwright_success(stack)

				call_state = {'get': 0, 'post': 0}

				async def get_handler_timeout(*args, **kwargs):
					call_state['get'] += 1
					if call_state['get'] == 1:
						raise httpx.TimeoutException('Request timeout')
					resp = _build_response(status=200)
					resp.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)
					return resp

				async def post_handler_timeout(*args, **kwargs):
					call_state['post'] += 1
					resp = _build_response(status=200, text='bad')
					resp.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)
					return resp

				_patch_http_client(stack, get_handler_timeout, post_handler_timeout)

				with pytest.raises(SystemExit) as exc_info:
					await service_timeout.run()

		assert exc_info.value.code == 1

		accounts_env(
			[
				{'name': '非 200', 'cookies': 'session=non200', 'api_user': 'user1'},
				{'name': '纯文本成功', 'cookies': 'session=text', 'api_user': 'user2'},
				{'name': '异常账号', 'cookies': 'session=exception', 'api_user': 'user3'},
			]
		)
		service_checkin = CheckinService()
		service_checkin.balance_hash_file = tmp_path / 'checkin_hash.txt'

		with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
			with ExitStack() as stack:
				_patch_playwright_success(stack)

				call_state = {'post': 0}

				async def get_handler_simple(*args, **kwargs):
					return _build_response(
						status=200,
						json_data={'success': True, 'data': {'quota': 25000000, 'used_quota': 5000000}},
					)

				async def post_handler_simple(*args, **kwargs):
					call_state['post'] += 1
					if call_state['post'] == 1:
						return _build_response(status=500)
					if call_state['post'] == 2:
						resp = _build_response(status=200, text='operation success')
						resp.json.side_effect = json.JSONDecodeError('Invalid', '', 0)
						return resp
					raise Exception('Network error')

				_patch_http_client(stack, get_handler_simple, post_handler_simple)

				with pytest.raises(SystemExit) as exc_info:
					await service_checkin.run()

		assert exc_info.value.code == 0
		assert call_state['post'] == 3

	@pytest.mark.asyncio
	async def test_invalid_account_configs(self, monkeypatch, tmp_path):
		"""验证账号配置的异常输入。"""
		scenarios = [
			None,
			'not a json',
			'{"name": "test"}',
			'[{"name": "test"}]',
			'[{"name": "", "cookies": "cookie", "api_user": "user"}]',
		]

		for index, payload in enumerate(scenarios):
			if payload is None:
				monkeypatch.delenv('ANYROUTER_ACCOUNTS', raising=False)
			else:
				monkeypatch.setenv('ANYROUTER_ACCOUNTS', payload)

			service = CheckinService()
			service.balance_hash_file = tmp_path / f'config_hash_{index}.txt'

			with pytest.raises(SystemExit) as exc_info:
				await service.run()

			assert exc_info.value.code == 0

	@pytest.mark.asyncio
	async def test_privacy_mode_and_account_naming(self, accounts_env, tmp_path):
		"""验证 WAF 异常与隐私模式。"""
		accounts_env(
			[
				{'name': 'WAF 账号', 'cookies': 'session=waf', 'api_user': 'user_waf'},
			]
		)
		service = CheckinService()
		service.balance_hash_file = tmp_path / 'waf_hash.txt'

		with patch('core.checkin_service.async_playwright') as mock_pw:
			mock_pw.return_value.__aenter__.side_effect = Exception('Playwright error')
			mock_pw.return_value.__aexit__ = AsyncMock()

			with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
				with pytest.raises(SystemExit) as exc_info:
					await service.run()

		assert exc_info.value.code == 1

		accounts_env(
			[
				{'name': '自定义名称', 'cookies': 'session=ok', 'api_user': 'user_ok'},
				{'cookies': 'session=fail', 'api_user': 'user_fail'},
			]
		)
		summary_public = tmp_path / 'summary_public.md'
		service_public = CheckinService()
		service_public.balance_hash_file = tmp_path / 'hash_public.txt'

		with patch.dict(
			os.environ,
			{
				'REPO_VISIBILITY': 'public',
				'GITHUB_STEP_SUMMARY': str(summary_public),
			},
		):
			with ExitStack() as stack:
				_patch_playwright_success(stack)

				call_state = {'get': 0, 'post': 0}

				async def get_handler_public(*args, **kwargs):
					call_state['get'] += 1
					if call_state['get'] == 1:
						return _build_response(
							status=200,
							json_data={'success': True, 'data': {'quota': 25000000, 'used_quota': 5000000}},
						)
					resp = _build_response(status=401, text='Unauthorized')
					resp.json.side_effect = Exception('Unauthorized')
					return resp

				async def post_handler_public(*args, **kwargs):
					call_state['post'] += 1
					if call_state['post'] == 1:
						return _build_response(status=200, json_data={'ret': 1})
					return _build_response(status=200, json_data={'errcode': 0})

				_patch_http_client(stack, get_handler_public, post_handler_public)
				_patch_smtp(stack)

				with pytest.raises(SystemExit) as exc_info:
					await service_public.run()

		assert exc_info.value.code == 0
		content_public = summary_public.read_text(encoding='utf-8')
		assert '账号 2' in content_public
		assert '自定义名称' in content_public

		summary_private = tmp_path / 'summary_private.md'
		service_private = CheckinService()
		service_private.balance_hash_file = tmp_path / 'hash_private.txt'

		with patch.dict(
			os.environ,
			{
				'REPO_VISIBILITY': 'private',
				'GITHUB_STEP_SUMMARY': str(summary_private),
			},
		):
			with ExitStack() as stack:
				_patch_playwright_success(stack)

				async def get_handler_private(*args, **kwargs):
					return _build_response(
						status=200,
						json_data={'success': True, 'data': {'quota': 25000000, 'used_quota': 5000000}},
					)

				async def post_handler_private(*args, **kwargs):
					return _build_response(status=200, json_data={'ret': 1})

				_patch_http_client(stack, get_handler_private, post_handler_private)
				_patch_smtp(stack)

				with pytest.raises(SystemExit) as exc_info:
					await service_private.run()

		assert exc_info.value.code == 0
		content_private = summary_private.read_text(encoding='utf-8')
		assert '自定义名称' in content_private

	@pytest.mark.asyncio
	async def test_notification_renders_all_platforms(
		self, config_env_setter, create_notification_data, create_account_result
	):
		"""验证 NotificationKit 渲染多种模板。"""
		config_env_setter('dingtalk', 'https://mock.dingtalk')
		config_env_setter('feishu', {'webhook': 'https://mock.feishu', 'template': '成功：{{ stats.success_count }}'})
		config_env_setter(
			'wecom', {'webhook': 'https://mock.wecom', 'template': '{% if partial_success %}部分成功{% endif %}'}
		)
		config_env_setter('pushplus', 'mock_pushplus_token')
		config_env_setter('serverpush', 'mock_serverpush_key')
		config_env_setter(
			'email',
			{
				'user': 'sender@example.com',
				'pass': 'mock_password',
				'to': 'receiver@example.com',
				'smtp_server': 'smtp.example.com',
			},
		)

		notif_data = create_notification_data(
			[
				create_account_result(name='成功账号', quota=25.0, used=5.0),
				create_account_result(name='失败账号', status='failed', error='连接超时'),
			]
		)

		kit = NotificationKit()

		with ExitStack() as stack:
			post_counter = {'count': 0}

			async def get_handler(*args, **kwargs):
				return _build_response(status=200, json_data={})

			async def post_handler(*args, **kwargs):
				post_counter['count'] += 1
				return _build_response(status=200, json_data={'errcode': 0})

			_patch_http_client(stack, get_handler, post_handler)
			_patch_smtp(stack)

			await kit.push_message(title='测试', content=notif_data)

		assert post_counter['count'] == 5

	@pytest.mark.asyncio
	async def test_checkin_exception_sends_notification(self, accounts_env, tmp_path):
		"""验证账号执行异常时的通知路径。"""
		accounts_env(
			[
				{'name': '异常账号', 'cookies': 'session=error', 'api_user': 'user_error'},
			]
		)
		service = CheckinService()
		service.balance_hash_file = tmp_path / 'exception_hash.txt'

		failing_checkin = AsyncMock(side_effect=Exception('Unexpected error'))
		with patch.object(service, '_check_in_account', failing_checkin):
			with patch('notif.notify.NotificationKit.push_message', new=AsyncMock()) as mock_push:
				with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': '/dev/null'}):
					with pytest.raises(SystemExit) as exc_info:
						await service.run()

		assert exc_info.value.code == 1
		mock_push.assert_awaited()

	def test_notification_data_computed_properties(self, create_account_result, create_notification_data):
		"""验证 NotificationData 的便利属性。"""
		all_success = create_notification_data(
			[
				create_account_result(name='账号 1', quota=25.0, used=5.0),
				create_account_result(name='账号 2', quota=30.0, used=10.0),
			]
		)
		assert all_success.all_success is True
		assert all_success.all_failed is False
		assert all_success.partial_success is False

		all_failed = create_notification_data(
			[
				create_account_result(name='账号 1', status='failed', error='错误 1'),
				create_account_result(name='账号 2', status='failed', error='错误 2'),
			]
		)
		assert all_failed.all_success is False
		assert all_failed.all_failed is True
		assert all_failed.partial_success is False

		mixed = create_notification_data(
			[
				create_account_result(name='账号 1', quota=25.0, used=5.0),
				create_account_result(name='账号 2', status='failed', error='错误'),
			]
		)
		assert mixed.all_success is False
		assert mixed.all_failed is False
		assert mixed.partial_success is True


def _patch_playwright_success(stack: ExitStack):
	"""提供成功的 Playwright mock。"""
	mock_page = MagicMock()
	mock_page.goto = AsyncMock()
	mock_page.wait_for_function = AsyncMock()
	mock_page.wait_for_timeout = AsyncMock()

	mock_context = MagicMock()
	mock_context.cookies = AsyncMock(
		return_value=[
			{'name': 'acw_tc', 'value': 'x'},
			{'name': 'acw_sc__v2', 'value': 'y'},
			{'name': 'cdn_sec_tc', 'value': 'z'},
		]
	)
	mock_context.new_page = AsyncMock(return_value=mock_page)
	mock_context.close = AsyncMock()

	mock_browser = MagicMock()
	mock_browser.new_context = AsyncMock(return_value=mock_context)
	mock_browser.close = AsyncMock()

	mock_playwright = MagicMock()
	mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

	manager = MagicMock()
	manager.__aenter__ = AsyncMock(return_value=mock_playwright)
	manager.__aexit__ = AsyncMock()

	stack.enter_context(patch('core.checkin_service.async_playwright', return_value=manager))


def _patch_http_client(stack: ExitStack, get_handler, post_handler):
	"""提供可配置的 httpx.AsyncClient mock。"""
	mock_client = MagicMock()
	mock_client.get = get_handler
	mock_client.post = post_handler
	mock_client.cookies = MagicMock()
	mock_client.__aenter__ = AsyncMock(return_value=mock_client)
	mock_client.__aexit__ = AsyncMock()
	stack.enter_context(patch('httpx.AsyncClient', return_value=mock_client))
	return mock_client


def _patch_smtp(stack: ExitStack):
	"""提供 SMTP mock。"""
	smtp_mock = MagicMock()
	smtp_mock.return_value.__enter__.return_value = MagicMock()
	smtp_mock.return_value.__exit__ = MagicMock()
	stack.enter_context(patch('smtplib.SMTP_SSL', smtp_mock))
	return smtp_mock


def _build_response(*, status: int, json_data: dict | None = None, json_error: Exception | None = None, text: str = ''):
	"""构造通用响应对象。"""
	response = MagicMock()
	response.status_code = status
	response.text = text
	if json_error is not None:
		response.json.side_effect = json_error
	elif json_data is not None:
		response.json.return_value = json_data
	else:
		response.json.return_value = {}
	return response
