from datetime import datetime
from typing import Optional

from .log_level import LogLevel


class Logger:
    """日志工具类，用于统一格式化输出日志"""

    def debug(self, message: str, tag: Optional[str] = None, account_name: Optional[str] = None, show_timestamp: bool = False):
        """输出调试级别日志"""
        formatted_message = self._format_message(
            level=LogLevel.DEBUG,
            message=message,
            tag=tag,
            account_name=account_name,
            show_timestamp=show_timestamp
        )
        self._print(formatted_message)

    def info(self, message: str, tag: Optional[str] = None, account_name: Optional[str] = None, show_timestamp: bool = False):
        """输出信息级别日志"""
        formatted_message = self._format_message(
            level=LogLevel.INFO,
            message=message,
            tag=tag,
            account_name=account_name,
            show_timestamp=show_timestamp
        )
        self._print(formatted_message)

    def warning(self, message: str, tag: Optional[str] = None, account_name: Optional[str] = None, show_timestamp: bool = False):
        """输出警告级别日志"""
        formatted_message = self._format_message(
            level=LogLevel.WARNING,
            message=message,
            tag=tag,
            account_name=account_name,
            show_timestamp=show_timestamp
        )
        self._print(formatted_message)

    def error(self, message: str, tag: Optional[str] = None, account_name: Optional[str] = None, show_timestamp: bool = False):
        """输出错误级别日志"""
        formatted_message = self._format_message(
            level=LogLevel.ERROR,
            message=message,
            tag=tag,
            account_name=account_name,
            show_timestamp=show_timestamp
        )
        self._print(formatted_message)

    def success(self, message: str, account_name: Optional[str] = None, show_timestamp: bool = False):
        """输出成功级别日志 - 便捷方法，使用 INFO 级别和成功标签"""
        self.info(
            message=message,
            tag="成功",
            account_name=account_name,
            show_timestamp=show_timestamp
        )

    def processing(self, message: str, account_name: Optional[str] = None, show_timestamp: bool = False):
        """输出处理中日志 - 便捷方法，使用 INFO 级别和处理中标签"""
        self.info(
            message=message,
            tag="处理中",
            account_name=account_name,
            show_timestamp=show_timestamp
        )

    def notify(self, message: str, account_name: Optional[str] = None, show_timestamp: bool = False):
        """输出通知相关日志 - 便捷方法，使用 INFO 级别和通知标签"""
        self.info(
            message=message, 
            tag="通知", 
            account_name=account_name, 
            show_timestamp=show_timestamp
        )

    def print_banner(self, title: str, width: int = 60, show_timestamp: bool = False):
        """打印横幅样式的内容

        Args:
            title: 横幅标题
            width: 横幅宽度
            show_timestamp: 是否显示时间戳
        """
        border = '=' * width

        # 如果需要显示时间戳，在开头添加
        if show_timestamp:
            self._print(f"[{self._timestamp()}]")

        self._print(border)
        self._print(title)
        self._print(border)

    def print_multiline(self, messages: list[str], show_timestamp: bool = False):
        """打印多行消息，每行都会被原样输出

        Args:
            messages: 消息列表
            show_timestamp: 是否显示时间戳
        """
        # 如果需要显示时间戳，在开头添加
        if show_timestamp and messages:
            self._print(f"[{self._timestamp()}]")

        for message in messages:
            self._print(message)

    def _print(self, message: str):
        """封装日志输出函数，便于未来统一替换日志基底

        Args:
            message: 要打印的消息
        """
        print(message)

    def _timestamp(self) -> str:
        """获取格式化的时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _format_message(
        self,
        level: LogLevel,
        message: str,
        tag: Optional[str] = None,
        account_name: Optional[str] = None,
        show_timestamp: bool = False
    ) -> str:
        """格式化日志消息

        Args:
            level: 日志级别
            message: 日志消息
            account_name: 可选的账号名称
            show_timestamp: 是否显示时间戳
            tag: 可选的自定义标签

        Returns:
            格式化后的日志字符串
        """
        # 构建消息组件数组
        message_parts = []

        # 添加时间戳
        if show_timestamp:
            message_parts.append(f'[{self._timestamp()}]')

        # 使用自定义标签或级别标签
        display_tag = tag if tag else level.get_tag()
        message_parts.append(f'[{display_tag}]')

        # 添加账号名称
        if account_name:
            message_parts.append(f'{account_name}:')

        message_parts.append(message)

        return ' '.join(message_parts)
