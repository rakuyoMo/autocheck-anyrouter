from dataclasses import dataclass
from typing import Any


@dataclass
class ServerPushConfig:
    """Server 酱配置参数类"""

    # Server 酱 SendKey
    send_key: str

    # 平台设置
    platform_settings: dict[str, Any] | None = None

    # 模板内容，如果为空则使用默认模板
    template: str | None = None
