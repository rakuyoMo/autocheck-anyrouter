from typing import List, Optional
from dataclasses import dataclass

from .account_result import AccountResult
from .notification_stats import NotificationStats


@dataclass
class NotificationData:
    """通知数据结构"""

    # 账号列表和处理结果
    accounts: List[AccountResult]

    # 统计信息
    stats: NotificationStats

    # 执行时间戳
    timestamp: Optional[str] = None

    @property
    def all_success(self) -> bool:
        """是否全部成功"""
        return self.stats.failed_count == 0

    @property
    def all_failed(self) -> bool:
        """是否全部失败"""
        return self.stats.success_count == 0

    @property
    def partial_success(self) -> bool:
        """是否部分成功"""
        return self.stats.success_count > 0 and self.stats.failed_count > 0

