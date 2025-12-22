import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from core.balance_manager import BalanceManager
from core.checkin_service import CheckinService
from core.github_reporter import GitHubReporter
from core.models import AccountResult, NotificationData, NotificationStats
from core.privacy_handler import PrivacyHandler
from notif import NotificationKit, NotifyTrigger, NotifyTriggerManager
from tools.logger import logger


class Application:
	"""应用编排层，负责协调所有服务"""

	# 默认时区
	DEFAULT_TIMEZONE = 'Asia/Shanghai'

	# 默认时间戳格式
	DEFAULT_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

	def __init__(self):
		"""初始化应用及所有服务"""
		# 初始化各个功能模块
		self.checkin_service = CheckinService()
		self.privacy_handler = PrivacyHandler(PrivacyHandler.should_show_sensitive_info())
		self.balance_manager = BalanceManager(Path(CheckinService.Config.File.BALANCE_HASH_NAME))
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
				success, user_info = await self.checkin_service.check_in_account(account, i)
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
			# 获取时区配置（处理空字符串的情况）
			timezone_name = os.getenv('TZ') or self.DEFAULT_TIMEZONE
			try:
				timezone = ZoneInfo(timezone_name)
			except Exception:
				# 如果时区无效，使用默认时区
				logger.warning(f'时区 {timezone_name} 无效，使用默认时区 {self.DEFAULT_TIMEZONE}')
				timezone = ZoneInfo(self.DEFAULT_TIMEZONE)

			# 获取时间戳格式配置（处理空字符串的情况）
			timestamp_format = os.getenv('TIMESTAMP_FORMAT') or self.DEFAULT_TIMESTAMP_FORMAT

			# 生成带时区的时间戳
			now = datetime.now(timezone)
			timestamp = now.strftime(timestamp_format)
			timezone_abbr = now.strftime('%Z')

			# 构建结构化通知数据
			stats = NotificationStats(
				success_count=success_count,
				failed_count=total_count - success_count,
				total_count=total_count,
			)

			notification_data = NotificationData(
				accounts=account_results,
				stats=stats,
				timestamp=timestamp,
				timezone=timezone_abbr,
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
		"""
		从环境变量加载多账号配置

		支持两种配置方式：
		1. ANYROUTER_ACCOUNTS: JSON 数组格式，包含多个账号
		2. ANYROUTER_ACCOUNT_*: 多个环境变量，每个包含单个账号的 JSON 对象

		两种方式可以同时使用，会自动合并并去重。
		"""
		accounts: list[dict[str, Any]] = []

		# 1. 从 ANYROUTER_ACCOUNTS 加载账号列表
		accounts_from_array = self._load_accounts_from_array()
		accounts.extend(accounts_from_array)

		# 2. 从 ANYROUTER_ACCOUNT_* 加载单个账号
		accounts_from_prefix = self._load_accounts_from_prefix()
		accounts.extend(accounts_from_prefix)

		# 未找到任何账号配置
		if not accounts:
			self._print_account_config_guide()
			return []

		# 去重
		accounts = self._deduplicate_accounts(accounts)

		# 验证账号数据格式
		for i, account in enumerate(accounts):
			if not self._validate_account(account, i):
				return []

		return accounts

	def _load_accounts_from_array(self) -> list[dict[str, Any]]:
		"""从 ANYROUTER_ACCOUNTS 环境变量加载账号列表"""
		accounts_str = os.getenv(CheckinService.Config.Env.ACCOUNTS_KEY)
		if not accounts_str:
			return []

		try:
			accounts_data = json.loads(accounts_str)
		except json.JSONDecodeError as e:
			logger.error(
				message=f'ANYROUTER_ACCOUNTS 的 JSON 格式无效：{e}',
				exc_info=True,
			)
			return []
		except Exception as e:
			logger.error(
				message=f'ANYROUTER_ACCOUNTS 格式不正确：{e}',
				exc_info=True,
			)
			return []

		# 不是数组格式
		if not isinstance(accounts_data, list):
			logger.error('ANYROUTER_ACCOUNTS 必须使用数组格式 [{}]')
			return []

		return accounts_data

	def _load_accounts_from_prefix(self) -> list[dict[str, Any]]:
		"""从 ANYROUTER_ACCOUNT_* 环境变量加载单个账号"""
		accounts: list[dict[str, Any]] = []
		prefix = CheckinService.Config.Env.ACCOUNT_PREFIX

		# 扫描所有以 ANYROUTER_ACCOUNT_ 开头的环境变量
		for key, value in os.environ.items():
			if not key.startswith(prefix):
				continue

			try:
				account_data = json.loads(value)
			except json.JSONDecodeError as e:
				logger.error(
					message=f'{key} 的 JSON 格式无效：{e}',
					exc_info=True,
				)
				continue
			except Exception as e:
				logger.error(
					message=f'{key} 格式不正确：{e}',
					exc_info=True,
				)
				continue

			# 不是字典格式
			if not isinstance(account_data, dict):
				logger.error(f'{key} 必须使用对象格式 {{}}')
				continue

			accounts.append(account_data)

		return accounts

	def _deduplicate_accounts(self, accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
		"""
		对账号列表进行去重

		去重条件：name + cookies + api_user 完全一致
		"""
		seen: set[str] = set()
		unique_accounts: list[dict[str, Any]] = []

		for account in accounts:
			# 生成唯一标识
			key = self._generate_account_key(account)
			if key in seen:
				continue

			seen.add(key)
			unique_accounts.append(account)

		# 记录去重结果
		removed_count = len(accounts) - len(unique_accounts)
		if removed_count > 0:
			logger.info(f'去重后移除了 {removed_count} 个重复账号')

		return unique_accounts

	def _generate_account_key(self, account: dict[str, Any]) -> str:
		"""
		生成账号的唯一标识

		基于 name + cookies + api_user 生成
		"""
		name = account.get('name', '')
		cookies = account.get('cookies', '')
		api_user = account.get('api_user', '')

		# cookies 可能是字典，需要序列化为字符串
		if isinstance(cookies, dict):
			cookies = json.dumps(cookies, sort_keys=True)

		return f'{name}|{cookies}|{api_user}'

	def _validate_account(self, account: dict[str, Any], index: int) -> bool:
		"""
		验证单个账号的格式

		Args:
		    account: 账号配置
		    index: 账号索引

		Returns:
		    bool: 验证是否通过
		"""
		# 账号不是字典格式
		if not isinstance(account, dict):
			logger.error(f'账号 {index + 1} 配置格式不正确')
			return False

		# 缺少必需字段
		if 'cookies' not in account or 'api_user' not in account:
			logger.error(f'账号 {index + 1} 缺少必需字段 (cookies, api_user)')
			return False

		# name 字段为空字符串
		if 'name' in account and not account['name']:
			logger.error(f'账号 {index + 1} 的名称字段不能为空')
			return False

		return True

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
			'4. 使用以下任一方式配置账号：',
			'',
			f'📝 方式一：使用 {CheckinService.Config.Env.ACCOUNTS_KEY}（数组格式）',
			'[',
			'  {',
			'    "name": "账号1",',
			'    "cookies": "cookie1=value1; cookie2=value2",',
			'    "api_user": "your_api_user"',
			'  }',
			']',
			'',
			f'📝 方式二：使用 {CheckinService.Config.Env.ACCOUNT_PREFIX}* 前缀（单账号格式）',
			f'   例如：{CheckinService.Config.Env.ACCOUNT_PREFIX}ALICE',
			'{',
			'  "name": "Alice",',
			'  "cookies": "cookie1=value1; cookie2=value2",',
			'  "api_user": "your_api_user"',
			'}',
			'',
			'💡 提示：',
			'- 两种方式可以同时使用，账号会自动合并',
			'- name 字段为账号显示名称（可选）',
			'- cookies 为登录后的 cookie 字符串',
			'- api_user 为 API 用户标识',
		])  # fmt: skip
