from dataclasses import dataclass
from typing import Any


@dataclass
class NotificationTemplate:
	"""通知模板类，支持标题和内容分离"""

	# 模板标题，None 或空字符串表示不展示标题
	title: str | None = None

	# 模板内容
	content: str = ''

	@classmethod
	def from_value(cls, value: Any) -> 'NotificationTemplate | None':
		"""
		从配置值创建 NotificationTemplate 实例，支持向后兼容

		Args:
			value: 配置值，可能是字符串或字典

		Returns:
			NotificationTemplate 实例，如果为 None 则返回 None
		"""
		# 提前判断并退出
		if value is None or not isinstance(value, (str, dict)):
			return None

		# 根据类型构建 title 和 content
		if isinstance(value, dict):
			title = value.get('title')
			content = value.get('content', '')
		else:
			title = 'AnyRouter 签到提醒'
			content = value

		return cls(
			title=title,
			content=content,
		)
