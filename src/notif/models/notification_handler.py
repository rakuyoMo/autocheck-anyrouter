from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class NotificationHandler:
	"""
	通知处理器 - 封装单个通知平台的完整配置和行为

	Args:
		name: 平台名称
		config: 配置对象（包含 template 等属性）
		send_func: 发送方法（bound method）
	"""

	# 平台名称
	name: str

	# 配置对象（包含 template 等）
	config: Any | None

	# 发送方法（bound method）
	send_func: Callable

	def is_available(self) -> bool:
		"""
		检查该通知平台是否可用

		Returns:
			如果配置存在则返回 True，否则返回 False
		"""
		return self.config is not None
