import sys
from collections.abc import Callable
from pathlib import Path

import json5
import pytest

from notif.notify import NotificationKit

# 获取项目根目录
project_root = Path(__file__).parent.parent.parent


@pytest.fixture
def load_platform_template() -> Callable:
	"""加载平台模板配置的工厂函数"""
	def _load(platform: str) -> dict:
		config_path = project_root / 'src' / 'notif' / 'configs' / f'{platform}.json5'
		with open(config_path) as f:
			return json5.load(f)
	return _load


@pytest.fixture
def notification_kit() -> NotificationKit:
	"""创建不依赖环境变量的 NotificationKit 实例"""
	return NotificationKit()
