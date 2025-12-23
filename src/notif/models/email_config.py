from dataclasses import dataclass
from typing import Any

from notif.models.notification_template import NotificationTemplate


@dataclass
class EmailConfig:
	"""邮件配置参数类"""

	# SMTP 登录用户（通常是邮箱地址）
	user: str

	# SMTP 登录密码或授权码
	password: str

	# 收件人邮箱地址
	to: str

	# 发件人地址（可选），如果不指定则使用 user
	# 用于 SMTP 登录用户与发件人地址不同的场景（如 Resend 服务）
	sender: str | None = None

	# 自定义 SMTP 服务器地址（可选），如果不指定则自动从邮箱地址推断
	smtp_server: str | None = None

	# 平台设置
	platform_settings: dict[str, Any] | None = None

	# 模板内容，如果为空则使用默认模板
	template: NotificationTemplate | None = None
