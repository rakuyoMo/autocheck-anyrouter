from dataclasses import dataclass
from typing import Any

from notif.models.notification_template import NotificationTemplate


@dataclass
class PushPlusConfig:
	"""PushPlus 配置参数类"""

	# PushPlus Token
	token: str

	# 平台设置
	platform_settings: dict[str, Any] | None = None

	# 模板内容，如果为空则使用默认模板
	template: NotificationTemplate | None = None
