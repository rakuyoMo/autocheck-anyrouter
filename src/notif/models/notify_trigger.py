from enum import Enum


class NotifyTrigger(Enum):
	"""通知触发器枚举"""

	# 余额变化（包括首次运行）
	BALANCE_CHANGED = 'balance_changed'

	# 任意账号失败
	FAILED = 'failed'

	# 任意账号成功
	SUCCESS = 'success'

	# 总是发送
	ALWAYS = 'always'

	# 从不发送
	NEVER = 'never'
