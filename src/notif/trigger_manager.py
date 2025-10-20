import os

from notif.models.notify_trigger import NotifyTrigger
from tools.logger import logger


class NotifyTriggerManager:
	"""通知触发器管理器"""

	# 默认触发器：余额变化或失败时发送通知
	DEFAULT_TRIGGERS = {NotifyTrigger.BALANCE_CHANGED, NotifyTrigger.FAILED}
	ENV_KEY = 'NOTIFY_TRIGGERS'

	def __init__(self):
		"""初始化通知触发器管理器"""
		self.triggers = self._parse_triggers()

	def should_notify(
		self,
		has_success: bool,
		has_failed: bool,
		has_balance_changed: bool,
		is_first_run: bool,
	) -> bool:
		"""
		判断是否应该发送通知

		Args:
			has_success: 是否有成功的账号
			has_failed: 是否有失败的账号
			has_balance_changed: 是否有余额变化
			is_first_run: 是否是首次运行

		Returns:
			是否应该发送通知
		"""
		# never 优先级最高
		if NotifyTrigger.NEVER in self.triggers:
			return False

		# always 会忽略其他条件
		if NotifyTrigger.ALWAYS in self.triggers:
			return True

		# 检查是否满足任一触发条件（OR 关系）
		if NotifyTrigger.BALANCE_CHANGED in self.triggers:
			# 余额变化包括首次运行或实际余额变化
			if is_first_run or has_balance_changed:
				return True

		if NotifyTrigger.FAILED in self.triggers and has_failed:
			return True

		if NotifyTrigger.SUCCESS in self.triggers and has_success:
			return True

		return False

	def get_notify_reasons(
		self,
		has_success: bool,
		has_failed: bool,
		has_balance_changed: bool,
		is_first_run: bool,
	) -> list[str]:
		"""
		获取通知触发的原因列表

		Args:
			has_success: 是否有成功的账号
			has_failed: 是否有失败的账号
			has_balance_changed: 是否有余额变化
			is_first_run: 是否是首次运行

		Returns:
			触发原因列表
		"""
		reasons = []

		if is_first_run and NotifyTrigger.BALANCE_CHANGED in self.triggers:
			reasons.append('首次运行')

		if has_balance_changed and NotifyTrigger.BALANCE_CHANGED in self.triggers:
			reasons.append('余额变化')

		if has_failed and NotifyTrigger.FAILED in self.triggers:
			reasons.append('账号失败')

		if has_success and NotifyTrigger.SUCCESS in self.triggers:
			reasons.append('账号成功')

		return reasons

	def _parse_triggers(self) -> set[NotifyTrigger]:
		"""
		解析通知触发器配置

		Returns:
			通知触发器集合
		"""
		env_value = os.getenv(self.ENV_KEY, '').strip()

		# 如果没有配置，使用默认值
		if not env_value:
			return self.DEFAULT_TRIGGERS.copy()

		# 解析逗号分隔的字符串
		trigger_strings = [s.strip().lower() for s in env_value.split(',') if s.strip()]

		# 如果解析后为空，使用默认值
		if not trigger_strings:
			return self.DEFAULT_TRIGGERS.copy()

		# 转换为枚举
		triggers = set()
		valid_values = {trigger.value for trigger in NotifyTrigger}

		for trigger_str in trigger_strings:
			if trigger_str in valid_values:
				# 找到对应的枚举值
				for trigger in NotifyTrigger:
					if trigger.value == trigger_str:
						triggers.add(trigger)
						break
			else:
				logger.warning(f'未知的通知触发器：{trigger_str}，将被忽略')

		# 如果解析后没有有效的触发器，使用默认值
		if not triggers:
			logger.warning('没有有效的通知触发器配置，使用默认值')
			return self.DEFAULT_TRIGGERS.copy()

		return triggers
