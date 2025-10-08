from dataclasses import dataclass


@dataclass
class NotificationStats:
    """通知统计信息"""

    # 成功数量
    success_count: int

    # 失败数量
    failed_count: int

    # 总数量
    total_count: int

