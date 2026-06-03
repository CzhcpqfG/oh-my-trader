"""
市场上下文模块

提供当前各市场的背景信息模板, 供 LLM 推演时参考。

本模块的定位:
- 不抓取实时数据 (避免 LLM 幻觉 + API 限流)
- 提供人工维护的"宏观背景"模板
- 默认使用通用背景, 用户可手动更新

如需接入实时数据, 可在此模块添加 akshare/yfinance/coinmarketcap 等
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MarketContext:
    """各市场当前状态背景"""
    date: str
    a_share: str
    us_stock: str
    macro: str
    crypto: str

    def to_markdown(self) -> str:
        return (
            f"### A股市场\n{self.a_share}\n\n"
            f"### 美股市场\n{self.us_stock}\n\n"
            f"### 宏观环境\n{self.macro}\n\n"
            f"### 加密货币\n{self.crypto}\n"
        )


# 默认市场背景 (按月度季节性更新)
DEFAULT_CONTEXTS = {
    "Q1": {  # 1-3月 春季躁动
        "a_share": "北向资金动向、两会政策预期、年报预告密集披露期。关注成长股春季躁动机会。",
        "us_stock": "美股Q4财报季尾声, 1月底议息会议为关键事件, 关注科技股七巨头表现。",
        "macro": "国内春节前后流动性, 美联储利率路径, 美元指数走势。",
        "crypto": "BTC ETF资金流入情况, 减半周期叙事延续, 山寨币轮动机会。",
    },
    "Q2": {  # 4-6月
        "a_share": "年报与一季报集中披露, 4月政治局会议定调, 5月端午后关注消费数据。",
        "us_stock": "美股一季报披露, 6月FOMC会议, 夏季行情预期。",
        "macro": "国内政策落地节奏, 美联储降息预期, 中美利差。",
        "crypto": "减半后周期, 关注BTC现货ETF资金流向, 山寨币季节性行情。",
    },
    "Q3": {  # 7-9月
        "a_share": "中报披露期, 7月底政治局会议, 金九银十预期。",
        "us_stock": "Jackson Hole央行年会, 美股Q2财报, 9月议息会议。",
        "macro": "国内经济复苏力度, 美联储政策转向信号, 美元走势。",
        "crypto": "BTC传统Q3疲软季节性, 关注ETF资金能否扭转格局。",
    },
    "Q4": {  # 10-12月
        "a_share": "国庆后政策预期, 中央经济工作会议, 年末机构调仓。",
        "us_stock": "美股Q3财报, 大选不确定性, 年末反弹行情。",
        "macro": "国内财政政策发力, 美联储议息节奏, 跨年流动性。",
        "crypto": "Q4历史上强势, 关注BTC创新高行情与山寨币补涨。",
    },
}


def _get_quarter(dt: datetime) -> str:
    month = dt.month
    if month <= 3:
        return "Q1"
    if month <= 6:
        return "Q2"
    if month <= 9:
        return "Q3"
    return "Q4"


def get_default_context(dt: datetime | None = None) -> MarketContext:
    """获取默认市场上下文 (按季度变化)"""
    if dt is None:
        dt = datetime.now()
    q = _get_quarter(dt)
    ctx = DEFAULT_CONTEXTS[q]
    return MarketContext(
        date=dt.strftime("%Y-%m-%d"),
        a_share=ctx["a_share"],
        us_stock=ctx["us_stock"],
        macro=ctx["macro"],
        crypto=ctx["crypto"],
    )


def load_context(custom_path: str | None = None) -> MarketContext:
    """
    加载市场上下文

    如果 custom_path 提供, 尝试从该 JSON 文件加载自定义上下文。
    否则使用默认按季度的模板。

    自定义 JSON 格式:
    {
        "a_share": "...",
        "us_stock": "...",
        "macro": "...",
        "crypto": "..."
    }
    """
    import json
    from pathlib import Path

    if custom_path:
        path = Path(custom_path)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return MarketContext(
                    date=datetime.now().strftime("%Y-%m-%d"),
                    a_share=data.get("a_share", ""),
                    us_stock=data.get("us_stock", ""),
                    macro=data.get("macro", ""),
                    crypto=data.get("crypto", ""),
                )
            except Exception as e:
                print(f"加载自定义上下文失败: {e}, 使用默认")

    return get_default_context()


if __name__ == "__main__":
    ctx = get_default_context()
    print(ctx.to_markdown())
