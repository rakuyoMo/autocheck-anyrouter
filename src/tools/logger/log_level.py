from enum import Enum


class LogLevel(Enum):
    """日志级别枚举 - 参考常见的日志级别设置"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

    # 日志级别对应的中文标签
    _TAGS = {
        DEBUG: "调试",
        INFO: "信息",
        WARNING: "警告",
        ERROR: "错误",
    }

    def get_tag(self) -> str:
        """获取日志级别对应的中文标签

        Returns:
            日志级别的中文标签
        """
        return self._TAGS[self]
