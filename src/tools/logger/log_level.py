from enum import Enum


class LogLevel(Enum):
	"""日志级别枚举 - 参考常见的日志级别设置"""

	DEBUG = ('DEBUG', '调试')
	INFO = ('INFO', '信息')
	WARNING = ('WARNING', '警告')
	ERROR = ('ERROR', '错误')

	def __init__(self, value: str, tag: str):
		"""
		初始化日志级别枚举

		Args:
			value: 日志级别的字符串值
			tag: 日志级别的中文标签
		"""
		self._value_ = value
		self._tag = tag

	def get_tag(self) -> str:
		"""
		获取日志级别对应的中文标签

		Returns:
			日志级别的中文标签
		"""
		return self._tag
