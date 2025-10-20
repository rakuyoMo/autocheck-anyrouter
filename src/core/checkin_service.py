import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from playwright.async_api import async_playwright

from core.balance_manager import BalanceManager
from core.github_reporter import GitHubReporter
from core.models import AccountResult, NotificationData, NotificationStats
from core.privacy_handler import PrivacyHandler
from notif import NotificationKit, NotifyTrigger, NotifyTriggerManager
from tools.logger import logger

# 禁用变量插值以保留模板中的 $ 符号
load_dotenv(interpolate=False)


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

	def __init__(self):
		"""初始化签到服务"""
		# 初始化各个功能模块
		self.privacy_handler = PrivacyHandler(
			show_sensitive_info=PrivacyHandler.should_show_sensitive_info()
		)
		self.balance_manager = BalanceManager(
			balance_hash_file=Path(self.Config.File.BALANCE_HASH_NAME)
		)
		self.notify_trigger_manager = NotifyTriggerManager()
		self.notification_kit = NotificationKit()
		self.github_reporter = GitHubReporter(
			balance_manager=self.balance_manager,
			privacy_handler=self.privacy_handler,
		)

	async def run(self):
		"""执行签到流程"""
		logger.info(
			message='AnyRouter.top 多账号自动签到脚本启动（使用 Playwright）',
			tag='系统',
			show_timestamp=True,
		)

		# 加载账号配置
		accounts = self._load_accounts()
		if not accounts:
			logger.print_multiline([
				'',
				'🚀 配置完成后，请重新运行工作流即可自动签到！',
				'',
				'[INFO] 程序正常退出（等待配置完成）',
			])  # fmt: skip
			sys.exit(0)

		logger.info(f'找到 {len(accounts)} 个账号配置')

		# 加载余额 hash 字典
		last_balance_hash_dict = self.balance_manager.load_balance_hash()

		# 为每个账号执行签到
		success_count = 0
		total_count = len(accounts)
		account_results: list[AccountResult] = []  # 所有账号的结果
		current_balance_hash_dict = {}  # 当前余额 hash 字典
		current_balances = {}  # 当前余额数据（仅内存中使用，用于显示）
		has_any_balance_changed = False  # 是否有任意账号余额变化
		has_any_failed = False  # 是否有任意账号失败

		for i, account in enumerate(accounts):
			api_user = account.get('api_user', '')
			try:
				success, user_info = await self._check_in_account(account, i)
				# 日志使用脱敏名称，通知使用完整名称
				safe_account_name = self.privacy_handler.get_safe_account_name(account, i)
				full_account_name = self.privacy_handler.get_full_account_name(account, i)

				# 初始化结果变量
				quota = None
				used = None
				balance_changed = None
				error = None

				if success:
					success_count += 1
				else:
					# 记录有失败账号
					has_any_failed = True
					logger.notify('失败，将发送通知', safe_account_name)

				# 收集余额数据和处理结果
				if user_info and user_info.get('success'):
					current_quota = user_info['quota']
					current_used = user_info['used_quota']

					# 生成账号标识和余额 hash
					account_key = self.balance_manager.generate_account_key(api_user)
					current_balance_hash = self.balance_manager.generate_balance_hash(
						quota=current_quota,
						used=current_used,
					)
					current_balance_hash_dict[account_key] = current_balance_hash

					# 保存余额数据（仅内存中，用于显示）
					current_balances[account_key] = {
						'quota': current_quota,
						'used': current_used,
					}

					# 判断余额是否变化
					if last_balance_hash_dict and account_key in last_balance_hash_dict:
						# 有历史数据，对比 hash
						last_hash = last_balance_hash_dict[account_key]
						if current_balance_hash != last_hash:
							# 余额发生变化
							balance_changed = True
							has_any_balance_changed = True
							logger.notify('余额发生变化，将发送通知', safe_account_name)
						else:
							# 余额未变化
							balance_changed = False
					else:
						# 首次运行，无历史数据
						balance_changed = False

					# 设置余额信息
					quota = current_quota
					used = current_used

				elif user_info:
					# 获取余额失败，无法判断变化
					balance_changed = None
					error = user_info.get('error', '未知错误')

				# 一次性创建账号结果（通知使用完整名称）
				account_result = AccountResult(
					name=full_account_name,
					status='success' if success else 'failed',
					quota=quota,
					used=used,
					balance_changed=balance_changed,
					error=error,
				)

				# 所有账号都添加到结果列表
				account_results.append(account_result)

			except Exception as e:
				# 日志使用脱敏名称，通知使用完整名称
				safe_account_name = self.privacy_handler.get_safe_account_name(account, i)
				full_account_name = self.privacy_handler.get_full_account_name(account, i)
				logger.error(
					message=f'处理异常：{e}',
					account_name=safe_account_name,
					exc_info=True,
				)
				has_any_failed = True  # 异常也算失败

				# 创建失败的账号结果（通知使用完整名称）
				account_result = AccountResult(
					name=full_account_name,
					status='failed',
					balance_changed=None,
					error=f'异常: {str(e)[:50]}...',
				)
				account_results.append(account_result)

		# 判断是否需要发送通知
		is_first_run = last_balance_hash_dict is None
		need_notify = self.notify_trigger_manager.should_notify(
			has_success=success_count > 0,
			has_failed=has_any_failed,
			has_balance_changed=has_any_balance_changed,
			is_first_run=is_first_run,
		)

		# 记录通知决策的原因
		if need_notify:
			if NotifyTrigger.ALWAYS in self.notify_trigger_manager.triggers:
				logger.notify('配置了 always 触发器，将发送通知')
			else:
				reasons = self.notify_trigger_manager.get_notify_reasons(
					has_success=success_count > 0,
					has_failed=has_any_failed,
					has_balance_changed=has_any_balance_changed,
					is_first_run=is_first_run,
				)

				if reasons:
					logger.notify(f'检测到 {" 和 ".join(reasons)}，将发送通知')
				else:
					logger.notify('满足通知条件，将发送通知')
		else:
			if NotifyTrigger.NEVER in self.notify_trigger_manager.triggers:
				logger.info('配置了 never 触发器，跳过通知')
			else:
				logger.info('未满足通知触发条件，跳过通知')

		# 保存当前余额 hash 字典
		if current_balance_hash_dict:
			self.balance_manager.save_balance_hash(current_balance_hash_dict)

		if need_notify and account_results:
			# 构建结构化通知数据
			stats = NotificationStats(
				success_count=success_count,
				failed_count=total_count - success_count,
				total_count=total_count,
			)

			notification_data = NotificationData(
				accounts=account_results,
				stats=stats,
				timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
			)

			# 发送通知
			await self.notification_kit.push_message(notification_data)
			logger.notify('通知已发送')
		elif not account_results:
			logger.info('没有账号数据，跳过通知')

		# 日志总结
		logger.info(
			message=f'最终结果：成功 {success_count}/{total_count}，失败 {total_count - success_count}/{total_count}',
			tag='结果',
		)

		# 生成 GitHub Actions Step Summary
		self.github_reporter.generate_summary(
			success_count=success_count,
			total_count=total_count,
			current_balances=current_balances,
			accounts=accounts,
		)

		# 设置退出码
		sys.exit(0 if success_count > 0 else 1)

	def _load_accounts(self) -> list[dict[str, Any]]:
		"""从环境变量加载多账号配置"""
		accounts_str = os.getenv(self.Config.Env.ACCOUNTS_KEY)
		if not accounts_str:
			# 未配置账号信息
			self._print_account_config_guide()
			return []

		# JSON 解析失败
		try:
			accounts_data = json.loads(accounts_str)
		except json.JSONDecodeError as e:
			logger.error(
				message=f'账号配置中的 JSON 格式无效：{e}',
				exc_info=True,
			)
			return []

		except Exception as e:
			logger.error(
				message=f'账号配置格式不正确：{e}',
				exc_info=True,
			)
			return []

		# 不是数组格式
		if not isinstance(accounts_data, list):
			logger.error('账号配置必须使用数组格式 [{}]')
			return []

		# 验证账号数据格式
		for i, account in enumerate(accounts_data):
			# 账号不是字典格式
			if not isinstance(account, dict):
				logger.error(f'账号 {i + 1} 配置格式不正确')
				return []

			# 缺少必需字段
			if 'cookies' not in account or 'api_user' not in account:
				logger.error(f'账号 {i + 1} 缺少必需字段 (cookies, api_user)')
				return []

			# name 字段为空字符串
			if 'name' in account and not account['name']:
				logger.error(f'账号 {i + 1} 的名称字段不能为空')
				return []

		return accounts_data

	def _print_account_config_guide(self):
		"""打印账号配置指南"""
		logger.print_banner('👋 欢迎使用 AnyRouter 自动签到工具！')
		logger.print_multiline([
			'',
			'❌ 检测到您还未配置账号信息',
			'',
			'📋 配置步骤：',
			'1. 进入 GitHub 仓库设置页面',
			'2. 点击 "Secrets and variables" > "Actions"',
			'3. 点击 "New repository secret"',
			f'4. 创建名为 {self.Config.Env.ACCOUNTS_KEY} 的 secret',
			'',
			f'📝 {self.Config.Env.ACCOUNTS_KEY} 格式示例：',
			'[',
			'  {',
			'    "name": "账号1",',
			'    "cookies": "cookie1=value1; cookie2=value2",',
			'    "api_user": "your_api_user"',
			'  }',
			']',
			'',
			'💡 提示：',
			'- name 字段为账号显示名称（可选）',
			'- cookies 为登录后的 cookie 字符串',
			'- api_user 为 API 用户标识',
		])  # fmt: skip

	async def _get_waf_cookies_with_playwright(self, account_name: str) -> dict[str, str] | None:
		"""使用 Playwright 获取 WAF cookies（无痕模式）"""
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

	async def _get_user_info(self, client, headers: dict[str, str]) -> dict[str, Any]:
		"""获取用户信息"""
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
				'display': self.privacy_handler.get_safe_balance_display(quota=quota, used=used_quota),
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

	async def _check_in_account(
		self,
		account_info: dict[str, Any],
		account_index: int,
	) -> tuple[bool, dict[str, Any] | None]:
		"""为单个账号执行签到操作"""
		account_name = self.privacy_handler.get_safe_account_name(account_info, account_index)
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
				user_info = await self._get_user_info(client, headers)
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

	@staticmethod
	def _parse_cookies(cookies_data) -> dict[str, str]:
		"""解析 cookies 数据"""
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

