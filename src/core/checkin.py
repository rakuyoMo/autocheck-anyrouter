#!/usr/bin/env python3

import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import httpx
from dotenv import load_dotenv
from playwright.async_api import async_playwright

from notif import notify
from core.models import NotificationData, AccountResult, NotificationStats
from tools.logger import logger

# 禁用变量插值以保留模板中的 $ 符号
load_dotenv(interpolate=False)

# 使用用户主目录存储余额 hash 文件，确保路径一致性
BALANCE_HASH_FILE = Path.home() / '.autocheck-anyrouter-balance-hash.txt'


def load_accounts() -> Optional[List[Dict[str, Any]]]:
	"""从环境变量加载多账号配置"""
	accounts_str = os.getenv('ANYROUTER_ACCOUNTS')
	if not accounts_str:
		logger.print_banner('👋 欢迎使用 AnyRouter 自动签到工具！')
		logger.print_multiline([
			'',
			'❌ 检测到您还未配置账号信息',
			'',
			'📋 配置步骤：',
			'1. 进入 GitHub 仓库设置页面',
			'2. 点击 "Secrets and variables" > "Actions"',
			'3. 点击 "New repository secret"',
			'4. 创建名为 ANYROUTER_ACCOUNTS 的 secret',
			'',
			'📝 ANYROUTER_ACCOUNTS 格式示例：',
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
		])
		return None

	try:
		accounts_data = json.loads(accounts_str)

		# 检查是否为数组格式
		if not isinstance(accounts_data, list):
			logger.error("账号配置必须使用数组格式 [{}]")
			return None

		# 验证账号数据格式
		for i, account in enumerate(accounts_data):
			if not isinstance(account, dict):
				logger.error(f"账号 {i + 1} 配置格式不正确")
				return None

			if 'cookies' not in account or 'api_user' not in account:
				logger.error(f"账号 {i + 1} 缺少必需字段 (cookies, api_user)")
				return None

			# 如果有 name 字段，确保它不是空字符串
			if 'name' in account and not account['name']:
				logger.error(f"账号 {i + 1} 的名称字段不能为空")
				return None

		return accounts_data
	except json.JSONDecodeError as e:
		logger.error(f"账号配置中的 JSON 格式无效：{e}")
		return None
		
	except Exception as e:
		logger.error(f"账号配置格式不正确：{e}")
		return None


def load_balance_hash() -> Optional[str]:
	"""加载余额hash"""
	try:
		if BALANCE_HASH_FILE.exists():
			with open(BALANCE_HASH_FILE, 'r', encoding='utf-8') as f:
				return f.read().strip()

	except (OSError, IOError) as e:
		logger.warning(f"加载余额哈希失败：{e}")

	except Exception as e:
		logger.warning(f"加载余额哈希时发生意外错误：{e}")

	return None


def save_balance_hash(balance_hash: str):
	"""保存余额hash"""
	try:
		# 确保父目录存在
		BALANCE_HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
		with open(BALANCE_HASH_FILE, 'w', encoding='utf-8') as f:
			f.write(balance_hash)

	except (OSError, IOError) as e:
		logger.warning(f"保存余额哈希失败：{e}")

	except Exception as e:
		logger.warning(f"保存余额哈希时发生意外错误：{e}")


def generate_balance_hash(balances: Optional[Dict[str, Dict[str, float]]]) -> Optional[str]:
	"""生成余额数据的hash"""
	if not balances:
		return None

	# 将包含 quota 和 used 的结构转换为简单的 quota 值用于 hash 计算
	simple_balances = {k: v['quota'] for k, v in balances.items()} if balances else {}
	balance_json = json.dumps(simple_balances, sort_keys=True, separators=(',', ':'))
	return hashlib.sha256(balance_json.encode('utf-8')).hexdigest()[:16]


def get_account_display_name(account_info: Dict[str, Any], account_index: int) -> str:
	"""获取账号显示名称"""
	return account_info.get('name', f'账号 {account_index + 1}')


def parse_cookies(cookies_data) -> Dict[str, str]:
	"""解析 cookies 数据"""
	if isinstance(cookies_data, dict):
		return cookies_data

	if isinstance(cookies_data, str):
		cookies_dict = {}
		for cookie in cookies_data.split(';'):
			if '=' in cookie:
				key, value = cookie.strip().split('=', 1)
				cookies_dict[key] = value
		return cookies_dict
	return {}


async def get_waf_cookies_with_playwright(account_name: str) -> Optional[Dict[str, str]]:
	"""使用 Playwright 获取 WAF cookies（无痕模式）"""
	logger.processing("正在启动浏览器获取 WAF cookies...", account_name)

	browser = None
	context = None

	try:
		async with async_playwright() as p:
			# 使用标准无痕模式，避免临时目录的潜在问题
			browser = await p.chromium.launch(
				headless=False,
				args=[
					'--disable-blink-features=AutomationControlled',
					'--disable-dev-shm-usage',
					'--disable-web-security',
					'--disable-features=VizDisplayCompositor',
					'--no-sandbox',
				],
			)

			context = await browser.new_context(
				user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
				viewport={'width': 1920, 'height': 1080},
			)

			page = await context.new_page()

			logger.processing("步骤 1: 访问登录页面获取初始 cookies...", account_name)

			await page.goto('https://anyrouter.top/login', wait_until='networkidle')

			try:
				await page.wait_for_function('document.readyState === "complete"', timeout=5000)
			except Exception:
				await page.wait_for_timeout(3000)

			cookies = await context.cookies()

			waf_cookies = {}
			for cookie in cookies:
				cookie_name = cookie.get('name')
				cookie_value = cookie.get('value')
				if cookie_name in ['acw_tc', 'cdn_sec_tc', 'acw_sc__v2'] and cookie_value is not None:
					waf_cookies[cookie_name] = cookie_value

			logger.info(f"步骤 1 后获得 {len(waf_cookies)} 个 WAF cookies", account_name)

			required_cookies = ['acw_tc', 'cdn_sec_tc', 'acw_sc__v2']
			missing_cookies = [c for c in required_cookies if c not in waf_cookies]

			if missing_cookies:
				logger.error(f"缺少 WAF cookies: {missing_cookies}", account_name)
				return None

			logger.success("成功获取所有 WAF cookies", account_name)

			return waf_cookies

	except Exception as e:
		logger.error(f"获取 WAF cookies 时发生错误：{e}", account_name)
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


async def get_user_info(client, headers: Dict[str, str]) -> Dict[str, Any]:
	"""获取用户信息"""
	try:
		response = await client.get('https://anyrouter.top/api/user/self', headers=headers, timeout=30)

		if response.status_code == 200:
			data = response.json()
			if data.get('success'):
				user_data = data.get('data', {})
				quota = round(user_data.get('quota', 0) / 500000, 2)
				used_quota = round(user_data.get('used_quota', 0) / 500000, 2)
				return {
					'success': True,
					'quota': quota,
					'used_quota': used_quota,
					'display': f':money: Current balance: ${quota}, Used: ${used_quota}'
				}
		return {
			'success': False, 
			'error': f'Failed to get user info: HTTP {response.status_code}'
		}

	except httpx.TimeoutException:
		return {
			'success': False,
			'error': '获取用户信息失败：请求超时'
		}

	except httpx.RequestError:
		return {
			'success': False,
			'error': '获取用户信息失败：网络错误'
		}

	except Exception as e:
		return {
			'success': False,
			'error': f'获取用户信息失败：{str(e)[:50]}...'
		}


async def check_in_account(account_info: Dict[str, Any], account_index: int) -> tuple[bool, Optional[Dict[str, Any]]]:
	"""为单个账号执行签到操作"""
	account_name = get_account_display_name(account_info, account_index)
	logger.processing(f"开始处理 {account_name}")

	# 解析账号配置
	cookies_data = account_info.get('cookies', {})
	api_user = account_info.get('api_user', '')

	if not api_user:
		logger.error("未找到 API 用户标识符", account_name)
		return False, None

	# 解析用户 cookies
	user_cookies = parse_cookies(cookies_data)
	if not user_cookies:
		logger.error("配置格式无效", account_name)
		return False, None

	# 步骤1：获取 WAF cookies
	waf_cookies = await get_waf_cookies_with_playwright(account_name)
	if not waf_cookies:
		logger.error("无法获取 WAF cookies", account_name)
		return False, None

	# 步骤2：使用 httpx 进行 API 请求
	async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
		try:
			# 合并 WAF cookies 和用户 cookies
			all_cookies = {**waf_cookies, **user_cookies}
			client.cookies.update(all_cookies)

			headers = {
				'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
				'Accept': 'application/json, text/plain, */*',
				'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
				'Accept-Encoding': 'gzip, deflate, br, zstd',
				'Referer': 'https://anyrouter.top/console',
				'Origin': 'https://anyrouter.top',
				'Connection': 'keep-alive',
				'Sec-Fetch-Dest': 'empty',
				'Sec-Fetch-Mode': 'cors',
				'Sec-Fetch-Site': 'same-origin',
				'new-api-user': api_user,
			}

			user_info = await get_user_info(client, headers)
			if user_info and user_info.get('success'):
				print(user_info['display'])
			elif user_info:
				print(user_info.get('error', '未知错误'))

			logger.debug(
				message="执行签到",
				tag="网络",
				account_name=account_name
			)

			# 更新签到请求头
			checkin_headers = headers.copy()
			checkin_headers.update({
				'Content-Type': 'application/json',
				'X-Requested-With': 'XMLHttpRequest'
			})

			response = await client.post('https://anyrouter.top/api/user/sign_in', headers=checkin_headers, timeout=30)

			logger.debug(
				message=f"响应状态码 {response.status_code}",
				tag="响应",
				account_name=account_name
			)

			if response.status_code == 200:
				try:
					result = response.json()
					if result.get('ret') == 1 or result.get('code') == 0 or result.get('success'):
						logger.success("签到成功!", account_name)
						return True, user_info
					else:
						error_msg = result.get('msg', result.get('message', '未知错误'))
						logger.error(f"Check-in failed - {error_msg}", account_name)
						return False, user_info
				except json.JSONDecodeError:
					# 如果不是 JSON 响应，检查是否包含成功标识
					if 'success' in response.text.lower():
						logger.success("签到成功!", account_name)
						return True, user_info
					else:
						logger.error("Check-in failed - Invalid response format", account_name)
						return False, user_info
			else:
				logger.error(f"Check-in failed - HTTP {response.status_code}", account_name)
				return False, user_info

		except Exception as e:
			logger.error(f"签到过程中发生错误 - {str(e)[:50]}...", account_name)
			return False, None


async def main():
	"""主函数"""
	logger.info(
		message="AnyRouter.top 多账号自动签到脚本启动（使用 Playwright）",
		tag="系统",
		show_timestamp=True
	)

	# 加载账号配置
	accounts = load_accounts()
	if not accounts:
		logger.print_multiline([
			'',
			'🚀 配置完成后，请重新运行工作流即可自动签到！',
			'',
			'[INFO] 程序正常退出（等待配置完成）',
		])
		sys.exit(0)

	logger.info(f"找到 {len(accounts)} 个账号配置")

	# 加载余额hash
	last_balance_hash = load_balance_hash()

	# 为每个账号执行签到
	success_count = 0
	total_count = len(accounts)
	account_results: List[AccountResult] = []  # 使用结构化数据存储结果
	current_balances = {}
	need_notify = False  # 是否需要发送通知
	balance_changed = False  # 余额是否有变化

	for i, account in enumerate(accounts):
		account_key = f'account_{i + 1}'
		try:
			success, user_info = await check_in_account(account, i)
			account_name = get_account_display_name(account, i)

			# 创建账号结果
			account_result = AccountResult(
				name=account_name,
				status="success" if success else "failed"
			)

			if success:
				success_count += 1

			# 检查是否需要通知
			should_notify_this_account = False

			# 如果签到失败，需要通知
			if not success:
				should_notify_this_account = True
				need_notify = True
				logger.notify(f"失败，将发送通知", account_name)

			# 收集余额数据和处理结果
			if user_info and user_info.get('success'):
				current_quota = user_info['quota']
				current_used = user_info['used_quota']
				current_balances[account_key] = {'quota': current_quota, 'used': current_used}

				# 设置账号结果的余额信息
				account_result.quota = current_quota
				account_result.used = current_used
			elif user_info:
				# 设置错误信息
				account_result.error = user_info.get('error', '未知错误')

			# 只有需要通知的账号才添加到结果列表
			if should_notify_this_account:
				account_results.append(account_result)

		except Exception as e:
			account_name = get_account_display_name(account, i)
			logger.error(f"处理异常：{e}", account_name)
			need_notify = True  # 异常也需要通知

			# 创建失败的账号结果
			account_result = AccountResult(
				name=account_name,
				status="failed",
				error=f'异常: {str(e)[:50]}...'
			)
			account_results.append(account_result)

	# 检查余额变化
	current_balance_hash = generate_balance_hash(current_balances) if current_balances else None
	if current_balance_hash:
		if last_balance_hash is None:
			# 首次运行
			balance_changed = True
			need_notify = True
			logger.notify("检测到首次运行，将发送包含当前余额的通知")

		elif current_balance_hash != last_balance_hash:
			# 余额有变化
			balance_changed = True
			need_notify = True
			logger.notify("检测到余额变化，将发送通知")

		else:
			logger.info("未检测到余额变化")

	# 为有余额变化的情况添加所有成功账号到通知内容
	if balance_changed:
		for i, account in enumerate(accounts):
			account_key = f'account_{i + 1}'
			if account_key in current_balances:
				account_name = get_account_display_name(account, i)
				# 检查是否已经在结果列表中（避免重复）
				if not any(result.name == account_name for result in account_results):
					account_result = AccountResult(
						name=account_name,
						status="success",
						quota=current_balances[account_key]["quota"],
						used=current_balances[account_key]["used"]
					)
					account_results.append(account_result)

	# 保存当前余额hash
	if current_balance_hash:
		save_balance_hash(current_balance_hash)

	if need_notify and account_results:
		# 构建结构化通知数据
		stats = NotificationStats(
			success_count=success_count,
			failed_count=total_count - success_count,
			total_count=total_count
		)

		notification_data = NotificationData(
			accounts=account_results,
			stats=stats,
			timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
		)

		# 发送通知
		notify.push_message('AnyRouter 签到提醒', notification_data, msg_type='text')
		logger.notify("因失败或余额变化已发送通知")
	else:
		logger.info("所有账号成功且未检测到余额变化，跳过通知")

	# 日志总结
	logger.info(
		message=f"最终结果：成功 {success_count}/{total_count}，失败 {total_count - success_count}/{total_count}",
		tag="结果"
	)

	# 设置退出码
	sys.exit(0 if success_count > 0 else 1)


def run_main():
	"""运行主函数的包装函数"""
	try:
		asyncio.run(main())

	except KeyboardInterrupt:
		logger.warning("程序被用户中断")
		sys.exit(1)

	except Exception as e:
		logger.error(f"程序执行过程中发生错误：{e}")
		sys.exit(1)


if __name__ == '__main__':
	run_main()
