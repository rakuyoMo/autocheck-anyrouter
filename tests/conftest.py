import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# 添加项目根目录到 PATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# 加载环境配置
load_dotenv(project_root / '.env.test', interpolate=False)

# 导入所有 fixtures
from tests.fixtures.data import (
	create_account_result,
	create_notification_data,
	multiple_mixed_data,
	single_failure_data,
	single_success_data,
)
from tests.fixtures.env import accounts_env, clean_notification_env, config_env_setter


def assert_json_contains(actual: dict[str, Any], expected: dict[str, Any]) -> None:
	"""断言 JSON 包含预期的键值对（支持嵌套）

	Args:
	    actual: 实际的 JSON 数据
	    expected: 预期包含的键值对
	"""
	for key, value in expected.items():
		assert key in actual, f'缺少键: {key}'
		if isinstance(value, dict) and isinstance(actual[key], dict):
			assert_json_contains(actual[key], value)
		else:
			assert actual[key] == value, f'键 {key} 的值不匹配: 期望 {value}, 实际 {actual[key]}'


def assert_file_content_contains(file_path: Path, expected_content: str) -> None:
	"""断言文件内容包含预期的字符串

	Args:
	    file_path: 文件路径
	    expected_content: 预期包含的内容
	"""
	assert file_path.exists(), f'文件不存在: {file_path}'
	content = file_path.read_text(encoding='utf-8')
	assert expected_content in content, f'文件内容不包含: {expected_content}'


__all__ = [
	'accounts_env',
	'clean_notification_env',
	'config_env_setter',
	'create_account_result',
	'create_notification_data',
	'multiple_mixed_data',
	'single_failure_data',
	'single_success_data',
	'assert_json_contains',
	'assert_file_content_contains',
]
