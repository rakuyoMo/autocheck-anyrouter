import os
from datetime import datetime
from typing import Any

from core.balance_manager import BalanceManager
from core.models import AccountResult
from core.privacy_handler import PrivacyHandler
from tools.logger import logger


class GitHubReporter:
	"""GitHub Actions 报告生成器"""

	ENV_GITHUB_STEP_SUMMARY = 'GITHUB_STEP_SUMMARY'

	def __init__(
		self,
		balance_manager: BalanceManager,
		privacy_handler: PrivacyHandler,
	):
		"""初始化 GitHub 报告生成器

		Args:
			balance_manager: 余额管理器
			privacy_handler: 隐私保护处理器
		"""
		self.balance_manager = balance_manager
		self.privacy_handler = privacy_handler

	def generate_summary(
		self,
		success_count: int,
		total_count: int,
		current_balances: dict[str, dict[str, float]],
		accounts: list[dict[str, Any]],
	):
		"""生成 GitHub Actions Step Summary

		Args:
			success_count: 成功数量
			total_count: 总数量
			current_balances: 当前余额字典
			accounts: 账号列表
		"""
		# 检查是否在 GitHub Actions 环境中运行
		summary_file = os.getenv(self.ENV_GITHUB_STEP_SUMMARY)
		if not summary_file:
			logger.debug('未检测到 GitHub Actions 环境，跳过 summary 生成', tag='Summary')
			return

		try:
			# 构建所有账号的结果列表
			all_account_results: list[AccountResult] = []
			for i, account in enumerate(accounts):
				api_user = account.get('api_user', '')
				account_key = self.balance_manager.generate_account_key(api_user)
				# 根据隐私设置获取账号名称
				account_name = self.privacy_handler.get_safe_account_name(
					account_info=account, 
					account_index=i
				)

				if account_key in current_balances:
					# 成功获取余额的账号
					account_result = AccountResult(
						name=account_name,
						status='success',
						quota=current_balances[account_key]['quota'],
						used=current_balances[account_key]['used'],
					)
				else:
					# 失败的账号
					account_result = AccountResult(
						name=account_name,
						status='failed',
						error='签到失败',
					)

				all_account_results.append(account_result)

			# 分组账号
			success_accounts = [acc for acc in all_account_results if acc.status == 'success']
			failed_accounts = [acc for acc in all_account_results if acc.status != 'success']

			failed_count = total_count - success_count
			has_success = len(success_accounts) > 0
			has_failed = len(failed_accounts) > 0
			all_success = len(failed_accounts) == 0
			all_failed = len(success_accounts) == 0

			# 构建 markdown 字符串
			lines = []

			# 主标题
			lines.append('## 🎯 AnyRouter 签到任务完成')
			lines.append('')

			# 状态标题
			if all_success:
				lines.append('**✅ 所有账号全部签到成功！**')
			elif has_success and has_failed:
				lines.append('**⚠️ 部分账号签到成功**')
			else:
				lines.append('**❌ 所有账号签到失败**')

			lines.append('')

			# 详细信息
			lines.append('### **详细信息**')
			lines.append(f'- **执行时间**：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
			lines.append(f'- **成功比例**：{success_count}/{total_count}')
			lines.append(f'- **失败比例**：{failed_count}/{total_count}')
			lines.append('')

			# 成功账号表格
			if has_success:
				lines.append('### 成功账号')
				if self.privacy_handler.show_sensitive_info:
					# 显示详细余额信息
					lines.append('| 账号 | 剩余（$） | 已用（$） |')
					lines.append('| :----- | :---- | :---- |')
					for account in success_accounts:
						lines.append(f'|{account.name}|{account.quota}|{account.used}|')
				else:
					# 脱敏模式：只显示账号和状态
					lines.append('| 账号 | 状态 |')
					lines.append('| :----- | :---- |')
					for account in success_accounts:
						lines.append(f'|{account.name}|✅ 签到成功|')
				lines.append('')

			# 失败账号表格
			if has_failed:
				lines.append('### 失败账号')
				if self.privacy_handler.show_sensitive_info:
					# 显示详细错误信息
					lines.append('| 账号 | 错误原因 |')
					lines.append('| :----- | :----- |')
					for account in failed_accounts:
						error_msg = account.error if account.error else '未知错误'
						lines.append(f'|{account.name}|{error_msg}|')
				else:
					# 脱敏模式：只显示账号和简单错误提示
					lines.append('| 账号 | 状态 |')
					lines.append('| :----- | :----- |')
					for account in failed_accounts:
						lines.append(f'|{account.name}|❌ 签到失败|')

			# 拼接成最终字符串
			summary_content = '\n'.join(lines)

			# 写入 summary 文件
			with open(summary_file, 'a', encoding='utf-8') as f:
				f.write(summary_content)
				f.write('\n')

			logger.info('GitHub Actions Step Summary 生成成功', tag='Summary')

		except Exception as e:
			logger.warning(f'生成 GitHub Actions Step Summary 失败：{e}', tag='Summary')
