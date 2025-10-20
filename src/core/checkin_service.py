import json
import os
from typing import Any

import httpx
from playwright.async_api import async_playwright

from core.privacy_handler import PrivacyHandler
from tools.logger import logger


class CheckinService:
	"""AnyRouter 签到服务"""

	class Config:
		"""服务配置"""

		class URLs:
			"""URL 配置"""

			BASE = 'https://anyrouter.top'
			LOGIN = f'{BASE}/login'
			API_BASE = f'{BASE}/api'
			USER_INFO = f'{API_BASE}/user/self'
			CHECKIN = f'{API_BASE}/user/sign_in'
			CONSOLE = f'{BASE}/console'

		class Env:
			"""环境变量配置"""

			ACCOUNTS_KEY = 'ANYROUTER_ACCOUNTS'
			SHOW_SENSITIVE_INFO = 'SHOW_SENSITIVE_INFO'
			REPO_VISIBILITY = 'REPO_VISIBILITY'
			ACTIONS_RUNNER_DEBUG = 'ACTIONS_RUNNER_DEBUG'
			GITHUB_STEP_SUMMARY = 'GITHUB_STEP_SUMMARY'
			CI = 'CI'
			GITHUB_ACTIONS = 'GITHUB_ACTIONS'

		class File:
			"""文件配置"""

			BALANCE_HASH_NAME = 'balance_hash.txt'

		class Browser:
			"""浏览器配置"""

			USER_AGENT_PARTS = [
				'Mozilla/5.0',
				'(Windows NT 10.0; Win64; x64)',
				'AppleWebKit/537.36',
				'(KHTML, like Gecko)',
				'Chrome/138.0.0.0',
				'Safari/537.36',
			]
			ARGS = [
				'--disable-blink-features=AutomationControlled',
				'--disable-dev-shm-usage',
				'--disable-web-security',
				'--disable-features=VizDisplayCompositor',
				'--no-sandbox',
			]

		class WAF:
			"""WAF 配置"""

			COOKIE_NAMES = ['acw_tc', 'cdn_sec_tc', 'acw_sc__v2']

	async def check_in_account(
		self,
		account_info: dict[str, Any],
		account_index: int,
	) -> tuple[bool, dict[str, Any] | None]:
		"""
		为单个账号执行签到操作

		Args:
		    account_info: 账号配置信息
		    account_index: 账号索引

		Returns:
		    tuple[bool, dict[str, Any] | None]: (是否签到成功, 用户信息)
		"""
		privacy_handler = PrivacyHandler(PrivacyHandler.should_show_sensitive_info())
		account_name = privacy_handler.get_safe_account_name(account_info, account_index)
		logger.processing(f'开始处理 {account_name}')

		# 解析账号配置
		cookies_data = account_info.get('cookies', {})
		api_user = account_info.get('api_user', '')

		# 未找到 API 用户标识符
		if not api_user:
			logger.error('未找到 API 用户标识符', account_name)
			return False, None

		# 解析用户 cookies
		user_cookies = self._parse_cookies(cookies_data)
		if not user_cookies:
			logger.error('配置格式无效', account_name)
			return False, None

		# 步骤1：获取 WAF cookies
		waf_cookies = await self._get_waf_cookies_with_playwright(account_name)
		if not waf_cookies:
			logger.error('无法获取 WAF cookies', account_name)
			return False, None

		# 步骤2：使用 httpx 进行 API 请求
		async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
			try:
				# 合并 WAF cookies 和用户 cookies
				all_cookies = {**waf_cookies, **user_cookies}
				client.cookies.update(all_cookies)

				headers = {
					'User-Agent': ' '.join(self.Config.Browser.USER_AGENT_PARTS),
					'Referer': self.Config.URLs.CONSOLE,
					'Origin': self.Config.URLs.BASE,
					'new-api-user': api_user,
					'Accept': 'application/json, text/plain, */*',
					'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
					'Accept-Encoding': 'gzip, deflate, br, zstd',
					'Connection': 'keep-alive',
					'Sec-Fetch-Dest': 'empty',
					'Sec-Fetch-Mode': 'cors',
					'Sec-Fetch-Site': 'same-origin',
				}

				# 获取用户信息
				user_info = await self._get_user_info(
					client=client,
					headers=headers,
					privacy_handler=privacy_handler,
				)
				if user_info and user_info.get('success'):
					logger.info(user_info['display'], account_name)
				elif user_info:
					logger.warning(user_info.get('error', '未知错误'), account_name)

				logger.debug(
					message='执行签到',
					tag='网络',
					account_name=account_name,
				)

				# 更新签到请求头
				checkin_headers = headers.copy()
				checkin_headers.update({
					'Content-Type': 'application/json',
					'X-Requested-With': 'XMLHttpRequest'
				})  # fmt: skip

				response = await client.post(
					url=self.Config.URLs.CHECKIN,
					headers=checkin_headers,
					timeout=30,
				)

				logger.debug(
					message=f'响应状态码 {response.status_code}',
					tag='响应',
					account_name=account_name,
				)

				# HTTP 请求失败
				if response.status_code != 200:
					logger.error(f'签到失败 - HTTP {response.status_code}', account_name)
					return False, user_info

				# 处理响应结果
				try:
					result = response.json()
					if result.get('ret') == 1 or result.get('code') == 0 or result.get('success'):
						logger.success('签到成功!', account_name)
						return True, user_info

					# 签到失败
					error_msg = result.get('msg', result.get('message', '未知错误'))
					logger.error(f'签到失败 - {error_msg}', account_name)
					return False, user_info

				except json.JSONDecodeError:
					# 如果不是 JSON 响应，检查是否包含成功标识
					if 'success' in response.text.lower():
						logger.success('签到成功!', account_name)
						return True, user_info

					# 签到失败
					logger.error('签到失败 - 无效响应格式', account_name)
					return False, user_info

			except Exception as e:
				logger.error(
					message=f'签到过程中发生错误 - {str(e)[:50]}...',
					account_name=account_name,
					exc_info=True,
				)
				return False, None

	async def _get_waf_cookies_with_playwright(self, account_name: str) -> dict[str, str] | None:
		"""
		使用 Playwright 获取 WAF cookies（无痕模式）

		Args:
		    account_name: 账号名称（用于日志）

		Returns:
		    dict[str, str] | None: WAF cookies 字典，失败返回 None
		"""
		logger.processing('正在启动浏览器获取 WAF cookies...', account_name)

		browser = None
		context = None

		try:
			async with async_playwright() as p:
				# 检测是否在 CI 环境中运行
				is_ci = any(
					os.getenv(env) == 'true'
					for env in (self.Config.Env.CI, self.Config.Env.GITHUB_ACTIONS)
				)  # fmt: skip

				# 使用标准无痕模式，避免临时目录的潜在问题
				# CI 环境使用 headless 模式，本地开发可以看到浏览器界面
				browser = await p.chromium.launch(
					headless=is_ci,
					args=self.Config.Browser.ARGS,
				)

				context = await browser.new_context(
					user_agent=' '.join(self.Config.Browser.USER_AGENT_PARTS),
					viewport={'width': 1920, 'height': 1080},
				)

				page = await context.new_page()

				logger.processing('步骤 1: 访问登录页面获取初始 cookies...', account_name)

				await page.goto(self.Config.URLs.LOGIN, wait_until='networkidle')

				try:
					await page.wait_for_function('document.readyState === "complete"', timeout=5000)
				except Exception:
					await page.wait_for_timeout(3000)

				cookies = await context.cookies()

				waf_cookies = {}
				for cookie in cookies:
					cookie_name = cookie.get('name')
					cookie_value = cookie.get('value')
					if cookie_name in self.Config.WAF.COOKIE_NAMES and cookie_value is not None:
						waf_cookies[cookie_name] = cookie_value

				logger.info(f'步骤 1 后获得 {len(waf_cookies)} 个 WAF cookies', account_name)

				missing_cookies = [c for c in self.Config.WAF.COOKIE_NAMES if c not in waf_cookies]

				if missing_cookies:
					logger.error(f'缺少 WAF cookies: {missing_cookies}', account_name)
					return None

				logger.success('成功获取所有 WAF cookies', account_name)

				return waf_cookies

		except Exception as e:
			logger.error(
				message=f'获取 WAF cookies 时发生错误：{e}',
				account_name=account_name,
				exc_info=True,
			)
			return None

		finally:
			# 确保资源被正确释放
			if context:
				try:
					await context.close()
				except Exception:
					pass
			if browser:
				try:
					await browser.close()
				except Exception:
					pass

	async def _get_user_info(
		self,
		client,
		headers: dict[str, str],
		privacy_handler: PrivacyHandler,
	) -> dict[str, Any]:
		"""
		获取用户信息

		Args:
		    client: httpx 客户端
		    headers: 请求头
		    privacy_handler: 隐私处理器

		Returns:
		    dict[str, Any]: 用户信息字典
		"""
		try:
			response = await client.get(
				url=self.Config.URLs.USER_INFO,
				headers=headers,
				timeout=30,
			)

			# HTTP 请求失败
			if response.status_code != 200:
				return {
					'success': False,
					'error': f'获取用户信息失败：HTTP {response.status_code}',
				}

			# JSON 解析失败
			try:
				data = response.json()
			except json.JSONDecodeError:
				return {
					'success': False,
					'error': '获取用户信息失败：无效的 JSON 响应',
				}

			# API 响应失败
			if not data.get('success'):
				return {
					'success': False,
					'error': data.get('message', '获取用户信息失败：API 错误'),
				}

			# 成功获取用户信息
			user_data = data.get('data', {})
			quota = round(user_data.get('quota', 0) / 500000, 2)
			used_quota = round(user_data.get('used_quota', 0) / 500000, 2)
			return {
				'success': True,
				'quota': quota,
				'used_quota': used_quota,
				'display': privacy_handler.get_safe_balance_display(quota=quota, used=used_quota),
			}

		except httpx.TimeoutException:
			return {
				'success': False,
				'error': '获取用户信息失败：请求超时',
			}

		except httpx.RequestError:
			return {
				'success': False,
				'error': '获取用户信息失败：网络错误',
			}

		except Exception as e:
			return {
				'success': False,
				'error': f'获取用户信息失败：{str(e)[:50]}...',
			}

	@staticmethod
	def _parse_cookies(cookies_data) -> dict[str, str]:
		"""
		解析 cookies 数据

		Args:
		    cookies_data: cookies 数据（字符串或字典格式）

		Returns:
		    dict[str, str]: cookies 字典
		"""
		# 已经是字典格式
		if isinstance(cookies_data, dict):
			return cookies_data

		# 不是字符串格式
		if not isinstance(cookies_data, str):
			return {}

		# 解析字符串格式的 cookies
		cookies_dict = {}
		for cookie in cookies_data.split(';'):
			# cookie 格式不正确
			if '=' not in cookie:
				continue

			key, value = cookie.strip().split('=', 1)
			cookies_dict[key] = value

		return cookies_dict
