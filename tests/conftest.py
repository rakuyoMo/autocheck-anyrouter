import sys
from pathlib import Path

from dotenv import load_dotenv

# 添加项目根目录到 PATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# 加载环境配置
load_dotenv(project_root / '.env.test', interpolate=False)

# 导入所有 fixtures
from tests.fixtures import (
	accounts_env,
	clean_notification_env,
	config_env_setter,
	create_account_result,
	create_notification_data,
	load_platform_template,
	mocked_service_dependencies,
	multiple_mixed_data,
	notification_kit,
	single_failure_data,
	single_success_data,
	temp_balance_hash_file,
	temp_file_manager,
	temp_summary_file,
)

__all__ = [
	'accounts_env',
	'clean_notification_env',
	'config_env_setter',
	'create_account_result',
	'create_notification_data',
	'load_platform_template',
	'mocked_service_dependencies',
	'multiple_mixed_data',
	'notification_kit',
	'single_failure_data',
	'single_success_data',
	'temp_balance_hash_file',
	'temp_file_manager',
	'temp_summary_file',
]
