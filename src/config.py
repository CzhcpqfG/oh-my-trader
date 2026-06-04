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


# 支持的 LLM provider
LLM_PROVIDERS = ("deepseek", "openai", "tongyi", "zhipu", "claude", "custom")

# 支持的市场 key
SUPPORTED_MARKETS = ("a_share", "us_stock", "macro", "crypto", "futures", "forex")

# 默认启用的市场
DEFAULT_ENABLED_MARKETS = ("a_share", "us_stock", "macro", "crypto")


@dataclass
class Config:
    # LLM (通用)
    llm_provider: str
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    llm_claude_api_key: str
    llm_claude_model: str
    llm_temperature: float

    # 市场选择
    enabled_markets: list[str]

    # 邮件
    email_host: str
    email_port: int
    email_user: str
    email_pass: str
    email_to: list[str]
    email_subject_prefix: str

    @classmethod
    def from_env(cls) -> "Config":
        def _get(key: str, default: str = "") -> str:
            val = os.environ.get(key, default)
            return val if val else default

        def _get_int(key: str, default: int) -> int:
            val = os.environ.get(key, "")
            if not val:
                return default
            try:
                return int(val)
            except ValueError:
                return default

        def _get_float(key: str, default: float) -> float:
            val = os.environ.get(key, "")
            if not val:
                return default
            try:
                return float(val)
            except ValueError:
                return default

        def _get_list(key: str) -> list[str]:
            val = os.environ.get(key, "")
            if not val:
                return []
            return [s.strip() for s in val.replace(";", ",").split(",") if s.strip()]

        # 兼容旧的 DEEPSEEK_* 环境变量
        # 如果用户没设 LLM_PROVIDER 但有 DEEPSEEK_API_KEY, 推断为 deepseek
        legacy_deepseek_key = _get("DEEPSEEK_API_KEY", "")
        llm_provider = _get("LLM_PROVIDER", "")
        if not llm_provider and legacy_deepseek_key:
            llm_provider = "deepseek"
        if not llm_provider:
            llm_provider = "deepseek"

        llm_api_key = _get("LLM_API_KEY", "") or _get("DEEPSEEK_API_KEY", "")
        llm_base_url = _get("LLM_BASE_URL", "") or _get("DEEPSEEK_BASE_URL", "") or "https://api.deepseek.com"
        llm_model = _get("LLM_MODEL", "") or _get("DEEPSEEK_MODEL", "") or "deepseek-chat"

        # 启用的市场
        raw_markets = _get_list("ENABLED_MARKETS")
        if not raw_markets:
            enabled_markets = list(DEFAULT_ENABLED_MARKETS)
        else:
            # 过滤掉不支持的 key, 防止用户写错
            enabled_markets = [m for m in raw_markets if m in SUPPORTED_MARKETS]
            if not enabled_markets:
                enabled_markets = list(DEFAULT_ENABLED_MARKETS)

        return cls(
            llm_provider=llm_provider,
            llm_api_key=llm_api_key,
            llm_base_url=llm_base_url,
            llm_model=llm_model,
            llm_claude_api_key=_get("LLM_CLAUDE_API_KEY", ""),
            llm_claude_model=_get("LLM_CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            llm_temperature=_get_float("LLM_TEMPERATURE", 0.8),
            enabled_markets=enabled_markets,
            email_host=_get("EMAIL_HOST", "smtp.qq.com"),
            email_port=_get_int("EMAIL_PORT", 465),
            email_user=_get("EMAIL_USER", ""),
            email_pass=_get("EMAIL_PASS", ""),
            email_to=_get_list("EMAIL_TO"),
            email_subject_prefix=_get("EMAIL_SUBJECT_PREFIX", "[今日风水报告]"),
        )

    def validate(self) -> list[str]:
        missing = []
        # 验证 LLM 凭据 (按 provider)
        if self.llm_provider == "claude":
            if not self.llm_claude_api_key:
                missing.append("LLM_CLAUDE_API_KEY")
        else:
            if not self.llm_api_key:
                missing.append("LLM_API_KEY (或 DEEPSEEK_API_KEY 兼容)")
        if not self.email_user:
            missing.append("EMAIL_USER")
        if not self.email_pass:
            missing.append("EMAIL_PASS")
        if not self.email_to:
            missing.append("EMAIL_TO")
        return missing
