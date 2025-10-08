import sys
from pathlib import Path

from dotenv import load_dotenv

# 添加项目根目录到 PATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# 加载环境变量
# 禁用变量插值以保留模板中的 $ 符号
load_dotenv(project_root / '.env.local', interpolate=False)
load_dotenv(project_root / '.env', interpolate=False)
