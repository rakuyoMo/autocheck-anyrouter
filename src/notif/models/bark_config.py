from dataclasses import dataclass
from typing import Any

from notif.models.notification_template import NotificationTemplate


@dataclass
class BarkConfig:
	"""Bark 配置参数类"""

	# Bark 服务器地址（如：https://api.day.app）
	server_url: str

	# 设备密钥
	device_key: str

	# 平台设置
	platform_settings: dict[str, Any] | None = None

	# 模板内容，如果为空则使用默认模板
	template: NotificationTemplate | None = None
