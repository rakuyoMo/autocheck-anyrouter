from datetime import datetime

from core.models import AccountResult, NotificationData, NotificationStats


def build_account_result(
	name: str = '测试账号',
	status: str = 'success',
	quota: float | None = None,
	used: float | None = None,
	balance_changed: bool | None = None,
	error: str | None = None,
) -> AccountResult:
	"""
	构建账号结果数据

	Args:
		name: 账号名称
		status: 状态（success/failed）
		quota: 总额度
		used: 已使用额度
		balance_changed: 余额是否变化
		error: 错误信息

	Returns:
		AccountResult 对象
	"""
	return AccountResult(
		name=name,
		status=status,
		quota=quota if status == 'success' and quota is not None else (25.0 if status == 'success' else None),
		used=used if status == 'success' and used is not None else (5.0 if status == 'success' else None),
		balance_changed=balance_changed,
		error=error,
	)


def build_notification_data(
	accounts: list[AccountResult],
	timestamp: str | None = None,
) -> NotificationData:
	"""
	构建通知数据

	Args:
		accounts: 账号结果列表
		timestamp: 时间戳

	Returns:
		NotificationData 对象
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
		timestamp=timestamp or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
	)
