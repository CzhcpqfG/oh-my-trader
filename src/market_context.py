"""
市场上下文模块

策略: 优先拉实时数据,任一数据源失败则回退到季度模板对应字段。
- A股: akshare (国内可直连,数据可靠)
- 美股: yfinance (海外源,国内可能限流,失败回退)
- 加密: CoinGecko 公共 API (国内访问困难,失败回退)
- 宏观: 始终使用季度模板 (最难自动化,无免费稳定数据源)
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


# 默认市场背景 (按季度, 作为回退兜底)
DEFAULT_CONTEXTS = {
    "Q1": {
        "a_share": "北向资金动向、两会政策预期、年报预告密集披露期。关注成长股春季躁动机会。",
        "us_stock": "美股Q4财报季尾声, 1月底议息会议为关键事件, 关注科技股七巨头表现。",
        "macro": "国内春节前后流动性, 美联储利率路径, 美元指数走势。",
        "crypto": "BTC ETF资金流入情况, 减半周期叙事延续, 山寨币轮动机会。",
    },
    "Q2": {
        "a_share": "年报与一季报集中披露, 4月政治局会议定调, 5月端午后关注消费数据。",
        "us_stock": "美股一季报披露, 6月FOMC会议, 夏季行情预期。",
        "macro": "国内政策落地节奏, 美联储降息预期, 中美利差。",
        "crypto": "减半后周期, 关注BTC现货ETF资金流向, 山寨币季节性行情。",
    },
    "Q3": {
        "a_share": "中报披露期, 7月底政治局会议, 金九银十预期。",
        "us_stock": "Jackson Hole央行年会, 美股Q2财报, 9月议息会议。",
        "macro": "国内经济复苏力度, 美联储政策转向信号, 美元走势。",
        "crypto": "BTC传统Q3疲软季节性, 关注ETF资金能否扭转格局。",
    },
    "Q4": {
        "a_share": "国庆后政策预期, 中央经济工作会议, 年末机构调仓。",
        "us_stock": "美股Q3财报, 大选不确定性, 年末反弹行情。",
        "macro": "国内财政政策发力, 美联储议息节奏, 跨年流动性。",
        "crypto": "Q4历史上强势, 关注BTC创新高行情与山寨币补涨。",
    },
}


def _get_quarter(dt: datetime) -> str:
    if dt.month <= 3:
        return "Q1"
    if dt.month <= 6:
        return "Q2"
    if dt.month <= 9:
        return "Q3"
    return "Q4"


def get_fallback_context(dt: datetime | None = None) -> MarketContext:
    """获取季度回退上下文"""
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


# ============ 实时数据拉取 (lazy import + try/except) ============

def _fetch_a_share() -> str:
    """拉 A 股主要指数, 失败抛异常"""
    import akshare as ak

    indices = [
        ("sh000001", "上证"),
        ("sz399001", "深证"),
        ("sh000300", "沪深300"),
        ("sz399006", "创业板"),
    ]
    parts = []
    for sym, name in indices:
        try:
            df = ak.stock_zh_index_daily(symbol=sym)
            if len(df) < 2:
                continue
            last = df.iloc[-1]
            prev = df.iloc[-2]
            chg = (last["close"] - prev["close"]) / prev["close"] * 100
            parts.append(f"{name} {last['close']:.0f}({chg:+.2f}%)")
        except Exception:
            continue

    if not parts:
        raise RuntimeError("akshare 拉不到任何 A 股指数")

    return " | ".join(parts)


def _fetch_us_stock() -> str:
    """拉美股指数, 失败抛异常"""
    import yfinance as yf

    symbols = {
        "^GSPC": "标普500",
        "^IXIC": "纳指",
        "^DJI": "道指",
    }
    parts = []
    for sym, name in symbols.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="5d")
            if len(hist) < 2:
                continue
            last = float(hist.iloc[-1]["Close"])
            prev = float(hist.iloc[-2]["Close"])
            chg = (last - prev) / prev * 100
            parts.append(f"{name} {last:.0f}({chg:+.2f}%)")
        except Exception:
            continue

    if not parts:
        raise RuntimeError("yfinance 拉不到任何美股指数")

    return " | ".join(parts)


def _fetch_crypto() -> str:
    """拉加密货币, 失败抛异常"""
    import requests
    r = requests.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={
            "ids": "bitcoin,ethereum",
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        },
        timeout=8,
    )
    r.raise_for_status()
    data = r.json()
    btc = data.get("bitcoin", {})
    eth = data.get("ethereum", {})
    if not btc or not eth:
        raise RuntimeError("CoinGecko 返回数据不完整")
    return (
        f"BTC ${btc['usd']:,.0f}({btc.get('usd_24h_change', 0):+.1f}%) "
        f"ETH ${eth['usd']:,.0f}({eth.get('usd_24h_change', 0):+.1f}%)"
    )


# ============ 组合入口 ============

def load_context(custom_path: str | None = None) -> MarketContext:
    """
    加载市场上下文

    优先级: 自定义 JSON > 实时数据(成功部分) + 季度模板(失败部分)

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
                print(f"  [warn] 自定义上下文加载失败: {e}, 使用默认")

    # 实时 + 回退 组合
    fallback = get_fallback_context()
    date_str = datetime.now().strftime("%Y-%m-%d")

    a_share = fallback.a_share
    us_stock = fallback.us_stock
    crypto = fallback.crypto
    # macro 始终用模板 (无稳定免费数据源)

    try:
        a_share = _fetch_a_share()
    except Exception as e:
        print(f"  [warn] A股实时数据拉取失败, 用回退: {e}")

    try:
        us_stock = _fetch_us_stock()
    except Exception as e:
        print(f"  [warn] 美股实时数据拉取失败, 用回退: {e}")

    try:
        crypto = _fetch_crypto()
    except Exception as e:
        print(f"  [warn] 加密实时数据拉取失败, 用回退: {e}")

    return MarketContext(
        date=date_str,
        a_share=a_share,
        us_stock=us_stock,
        macro=fallback.macro,
        crypto=crypto,
    )


if __name__ == "__main__":
    ctx = load_context()
    print(f"[A] {ctx.a_share}")
    print(f"[U] {ctx.us_stock}")
    print(f"[M] {ctx.macro}")
    print(f"[C] {ctx.crypto}")
