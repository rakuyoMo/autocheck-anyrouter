from core.models import AccountResult, NotificationData, NotificationStats


def create_account_result_data(
	name: str = '测试账号',
	status: str = 'success',
	quota: float = 25.0,
	used: float = 5.0,
	error: str | None = None,
	balance_changed: bool | None = None,
) -> AccountResult:
	"""
	创建账号结果数据的辅助函数

	Args:
		name: 账号名称
		status: 状态 ('success' 或 'failed')
		quota: 余额配额
		used: 已使用配额
		error: 错误信息
		balance_changed: 余额是否变化（None 表示无法判断）

	Returns:
		AccountResult 实例
	"""
	return AccountResult(
		name=name,
		status=status,
		quota=quota if status == 'success' else None,
		used=used if status == 'success' else None,
		balance_changed=balance_changed,
		error=error if status != 'success' else None,
	)


def create_notification_data(
	accounts: list[AccountResult],
	timestamp: str = '2024-01-01 12:00:00',
) -> NotificationData:
	"""
	创建通知数据的辅助函数

	Args:
		accounts: 账号结果列表
		timestamp: 时间戳

	Returns:
		NotificationData 实例
	"""
	success_count = sum(1 for acc in accounts if acc.status == 'success')
	failed_count = len(accounts) - success_count

	stats = NotificationStats(
		success_count=success_count,
		failed_count=failed_count,
		total_count=len(accounts),
	)

	return NotificationData(
		accounts=accounts,
		stats=stats,
		timestamp=timestamp,
	)
