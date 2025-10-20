from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

# 测试用的默认余额常量
DEFAULT_QUOTA = 25000000  # 25 GB
DEFAULT_USED_QUOTA = 5000000  # 5 GB
CHANGED_QUOTA = 30000000  # 30 GB


class MockPlaywright:
	"""Mock Playwright 依赖"""

	@staticmethod
	def setup_success(stack: ExitStack, cookies: list[dict] = []):
		"""
		设置成功的 Playwright Mock

		Args:
			stack: ExitStack 上下文管理器
			cookies: 自定义 cookies 列表
		"""
		if not cookies:
			cookies = [
				{'name': 'acw_tc', 'value': 'mock_acw_tc'},
				{'name': 'acw_sc__v2', 'value': 'mock_acw_sc'},
				{'name': 'cdn_sec_tc', 'value': 'mock_cdn_sec'},
			]

		mock_page = MagicMock()
		mock_page.goto = AsyncMock()
		mock_page.wait_for_function = AsyncMock()
		mock_page.wait_for_timeout = AsyncMock()

		mock_context = MagicMock()
		mock_context.cookies = AsyncMock(return_value=cookies)
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

	@staticmethod
	def setup_failure(stack: ExitStack, error: Exception = Exception('Playwright 启动失败')):
		"""
		设置失败的 Playwright Mock

		Args:
			stack: ExitStack 上下文管理器
			error: 自定义异常
		"""

		mock_pw = MagicMock()
		mock_pw.return_value.__aenter__.side_effect = error
		mock_pw.return_value.__aexit__ = AsyncMock()

		stack.enter_context(patch('core.checkin_service.async_playwright', mock_pw))


class MockHttpClient:
	"""Mock HTTP 客户端"""

	@staticmethod
	def setup(stack: ExitStack, get_handler, post_handler):
		"""
		设置 HTTP 客户端 Mock

		Args:
			stack: ExitStack 上下文管理器
			get_handler: GET 请求处理函数
			post_handler: POST 请求处理函数

		Returns:
			Mock 客户端对象
		"""
		mock_client = MagicMock()
		mock_client.get = get_handler
		mock_client.post = post_handler
		mock_client.cookies = MagicMock()
		mock_client.__aenter__ = AsyncMock(return_value=mock_client)
		mock_client.__aexit__ = AsyncMock(return_value=None)  # 返回 None 以避免抑制异常

		stack.enter_context(patch('httpx.AsyncClient', return_value=mock_client))
		return mock_client

	@staticmethod
	def build_response(
		status: int = 200,
		json_data: dict | None = None,
		text: str = '',
		json_error: Exception | None = None,
	):
		"""
		构建 HTTP 响应对象

		Args:
			status: HTTP 状态码
			json_data: JSON 响应数据
			text: 文本响应内容
			json_error: JSON 解析异常

		Returns:
			Mock 响应对象
		"""
		response = MagicMock()
		response.status_code = status
		response.text = text
		response.is_success = 200 <= status < 300

		if json_error is not None:
			response.json.side_effect = json_error
		elif json_data is not None:
			response.json.return_value = json_data
		else:
			response.json.return_value = {}

		return response

	@staticmethod
	async def get_success_handler(*args, **kwargs):
		"""成功的 GET 请求处理器"""
		return MockHttpClient.build_response(
			status=200,
			json_data={
				'success': True,
				'data': {
					'quota': DEFAULT_QUOTA,
					'used_quota': DEFAULT_USED_QUOTA,
				},
			},
		)

	@staticmethod
	async def post_success_handler(*args, **kwargs):
		"""成功的 POST 请求处理器"""
		return MockHttpClient.build_response(
			status=200,
			json_data={'ret': 1, 'msg': '签到成功'},
		)


class MockSMTP:
	"""Mock SMTP 依赖"""

	@staticmethod
	def setup(stack: ExitStack):
		"""
		设置 SMTP Mock

		Args:
			stack: ExitStack 上下文管理器

		Returns:
			Mock SMTP 对象
		"""
		smtp_mock = MagicMock()
		smtp_mock.return_value.__enter__.return_value = MagicMock()
		smtp_mock.return_value.__exit__ = MagicMock()

		stack.enter_context(patch('smtplib.SMTP_SSL', smtp_mock))
		return smtp_mock


class HttpRequestTracker:
	"""HTTP 请求追踪器"""

	def __init__(self):
		self.get_count = 0
		self.post_count = 0
		self.checkin_count = 0

	async def get_handler(self, *args, **kwargs):
		"""GET 请求处理器"""
		self.get_count += 1
		return MockHttpClient.build_response(
			status=200,
			json_data={
				'success': True,
				'data': {
					'quota': DEFAULT_QUOTA,
					'used_quota': DEFAULT_USED_QUOTA,
				},
			},
		)

	async def post_handler(self, *args, **kwargs):
		"""POST 请求处理器"""
		self.post_count += 1
		self.checkin_count += 1
		return MockHttpClient.build_response(
			status=200,
			json_data={'ret': 1, 'msg': '签到成功'},
		)
