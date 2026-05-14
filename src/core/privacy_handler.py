import hashlib
import os
from typing import Any


class PrivacyHandler:
	"""隐私保护处理器"""

	# 环境变量名
	ENV_SHOW_SENSITIVE_INFO = 'SHOW_SENSITIVE_INFO'
	ENV_ACTIONS_RUNNER_DEBUG = 'ACTIONS_RUNNER_DEBUG'
	ENV_REPO_VISIBILITY = 'REPO_VISIBILITY'
	ACCOUNT_ENV_PREFIX = 'ANYROUTER_ACCOUNT_'

	def __init__(self, show_sensitive_info: bool):
		"""
		初始化隐私保护处理器

		Args:
			show_sensitive_info: 是否显示敏感信息
		"""
		self.show_sensitive_info = show_sensitive_info

	@staticmethod
	def should_show_sensitive_info() -> bool:
		"""
		判断是否应该显示敏感信息

		优先级：
		1. SHOW_SENSITIVE_INFO（手动控制，最高优先级）
		2. ACTIONS_RUNNER_DEBUG（调试模式）
		3. REPO_VISIBILITY（仓库可见性，私有仓库显示，公开仓库脱敏）
		4. 本地运行（默认显示）

		Returns:
			是否应该显示敏感信息
		"""
		# 1. 检查用户手动配置（最高优先级）
		manual_config = os.getenv(PrivacyHandler.ENV_SHOW_SENSITIVE_INFO)
		if manual_config is not None:
			return manual_config.lower() == 'true'

		# 2. 检查调试模式
		debug_mode = os.getenv(PrivacyHandler.ENV_ACTIONS_RUNNER_DEBUG, '').lower() == 'true'
		if debug_mode:
			return True

		# 3. 检查仓库可见性
		repo_visibility = os.getenv(PrivacyHandler.ENV_REPO_VISIBILITY, '').lower()
		if repo_visibility:
			# 私有仓库显示，公开仓库脱敏
			return repo_visibility != 'public'

		# 4. 本地运行（无 REPO_VISIBILITY）默认显示
		return True

	def get_full_account_name(self, account_info: dict[str, Any], account_index: int) -> str:
		"""
		获取完整的账号名称（不脱敏）

		Args:
			account_info: 账号信息
			account_index: 账号索引

		Returns:
			完整的账号名称
		"""
		# 获取原始名称并去除首尾空格
		name = account_info.get('name', '').strip()

		# 如果没有配置 name 或者 name 是空字符串（包括纯空格的情况）
		if not name:
			return f'账号 {account_index + 1}'

		return name

	def get_safe_account_name(self, account_info: dict[str, Any], account_index: int) -> str:
		"""
		获取安全的账号名称（根据隐私设置）

		Args:
			account_info: 账号信息
			account_index: 账号索引

		Returns:
			脱敏时返回 "首字符 + hash 后 4 位"，否则返回自定义名称
		"""
		# 获取完整名称
		full_name = self.get_full_account_name(
			account_info=account_info,
			account_index=account_index,
		)

		# 如果不需要脱敏，直接返回完整名称
		if self.show_sensitive_info:
			return full_name

		# 如果是默认名称（"账号 N"），不需要脱敏
		if full_name.startswith('账号 '):
			return full_name

		# 自定义账号名属于敏感信息，这里复用统一的脱敏规则，
		# 避免日志、Step Summary 和其他敏感标识出现多套展示格式。
		return self.get_safe_sensitive_value(full_name)

	def get_safe_account_env_name(self, env_name: str) -> str:
		"""
		获取安全的账号环境变量名称（根据隐私设置）

		Args:
			env_name: 原始环境变量名称

		Returns:
			脱敏时保留固定前缀，只对敏感后缀做统一脱敏
		"""
		# 调试模式或私有仓库下允许展示完整值，便于定位实际配置来源。
		if self.show_sensitive_info:
			return env_name

		# 如果不是账号环境变量，退化为普通敏感值脱敏，避免调用方误传时直接泄露。
		if not env_name.startswith(self.ACCOUNT_ENV_PREFIX):
			return self.get_safe_sensitive_value(env_name)

		# 固定前缀本身不包含账号身份信息，因此保留前缀可以帮助定位配置来源。
		suffix = env_name[len(self.ACCOUNT_ENV_PREFIX) :]
		if not suffix:
			return self.ACCOUNT_ENV_PREFIX

		# 只有后缀包含账号标识，因此仅脱敏后缀，保证日志语义清晰且不暴露原值。
		safe_suffix = self.get_safe_sensitive_value(suffix)
		return f'{self.ACCOUNT_ENV_PREFIX}{safe_suffix}'

	def get_safe_sensitive_value(self, value: str) -> str:
		"""
		获取安全的敏感标识展示（根据隐私设置）

		Args:
			value: 原始敏感值

		Returns:
			脱敏时返回 "首字符 + 哈希前 4 位"，否则返回原值
		"""
		# 显示敏感信息时直接返回原值，保持现有调试行为不变。
		if self.show_sensitive_info:
			return value

		# 空值不包含有效信息，同时也无法按首字符规则脱敏，因此直接返回。
		if not value:
			return value

		# 统一使用“首字符 + 哈希前 4 位”的规则，
		# 这样账号名、环境变量后缀和其他敏感标识在日志中的展示风格完全一致。
		first_char = value[0]
		value_hash = hashlib.sha256(value.encode('utf-8')).hexdigest()[:4]
		return f'{first_char}{value_hash}'

	def get_safe_balance_display(self, quota: float, used: float) -> str:
		"""
		获取安全的余额展示（根据隐私设置）

		Args:
			quota: 总额度
			used: 已使用额度

		Returns:
			脱敏时返回描述，否则返回详细金额
		"""
		if self.show_sensitive_info:
			return f':money: 当前余额: ${quota}, 已用: ${used}'
		return ':money: 余额正常'
