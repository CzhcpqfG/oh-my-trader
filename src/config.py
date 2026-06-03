"""
全局配置

支持从环境变量或 .env 文件加载
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 在生产环境 GitHub Actions 不用 dotenv


@dataclass
class Config:
    # LLM
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str

    # 邮件
    email_host: str
    email_port: int
    email_user: str
    email_pass: str
    email_to: str
    email_subject_prefix: str

    # 报告
    timezone: str
    target_time: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
            deepseek_base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            email_host=os.environ.get("EMAIL_HOST", "smtp.qq.com"),
            email_port=int(os.environ.get("EMAIL_PORT", "465")),
            email_user=os.environ.get("EMAIL_USER", ""),
            email_pass=os.environ.get("EMAIL_PASS", ""),
            email_to=os.environ.get("EMAIL_TO", ""),
            email_subject_prefix=os.environ.get("EMAIL_SUBJECT_PREFIX", "[今日风水报告]"),
            timezone=os.environ.get("TIMEZONE", "Asia/Shanghai"),
            target_time=os.environ.get("TARGET_TIME", "08:30"),
        )

    def validate(self) -> list[str]:
        """校验必填字段, 返回缺失项列表"""
        missing = []
        if not self.deepseek_api_key:
            missing.append("DEEPSEEK_API_KEY")
        if not self.email_user:
            missing.append("EMAIL_USER")
        if not self.email_pass:
            missing.append("EMAIL_PASS")
        if not self.email_to:
            missing.append("EMAIL_TO")
        return missing
