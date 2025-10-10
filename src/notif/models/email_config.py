from dataclasses import dataclass
from typing import Any


@dataclass
class EmailConfig:
	"""邮件配置参数类"""

	# 发件人邮箱地址
	user: str

	# 发件人邮箱密码或授权码
	password: str

	# 收件人邮箱地址
	to: str

	# 自定义 SMTP 服务器地址（可选），如果不指定则自动从邮箱地址推断
	smtp_server: str | None = None

	# 平台设置
	platform_settings: dict[str, Any] | None = None

	# 模板内容，如果为空则使用默认模板
	template: str | None = None

	# 默认消息类型（'text' 或 'html'），如果不指定则自动检测
	default_msg_type: str | None = None
