from typing import Optional
from dataclasses import dataclass


@dataclass
class AccountResult:
    """单个账号的处理结果"""

    # 账号名称
    name: str

    # 处理状态：success 或 failed
    status: str

    # 当前余额，成功时才有
    quota: Optional[float] = None

    # 已使用余额，成功时才有
    used: Optional[float] = None

    # 错误信息，失败时才有
    error: Optional[str] = None
