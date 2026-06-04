"""
市场上下文模块

策略: 优先拉实时数据,任一数据源失败则回退到季度模板对应字段。
- A股: akshare (国内可直连,数据可靠)
- 美股: yfinance (海外源,国内可能限流,失败回退)
- 加密: CoinGecko 公共 API (国内访问困难,失败回退)
- 期货: akshare 新浪接口 (国内可直连)
- 外汇: akshare 中行接口 (国内可直连,数据可能不稳定,失败回退)
- 宏观: 始终使用季度模板 (最难自动化,无免费稳定数据源)

市场选择由 config.enabled_markets 控制, 列表外的市场不会被加载。
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MarketContext:
    """各市场当前状态背景"""
    date: str
    sections: dict[str, str]  # key = market 标识, value = 市场背景文本

    def get(self, market: str) -> str:
        return self.sections.get(market, "")


# 默认市场背景 (按季度, 作为回退兜底)
# keys 必须包含所有 SUPPORTED_MARKETS
DEFAULT_CONTEXTS = {
    "Q1": {
        "a_share": "北向资金动向、两会政策预期、年报预告密集披露期。关注成长股春季躁动机会。",
        "us_stock": "美股Q4财报季尾声, 1月底议息会议为关键事件, 关注科技股七巨头表现。",
        "macro": "国内春节前后流动性, 美联储利率路径, 美元指数走势。",
        "crypto": "BTC ETF资金流入情况, 减半周期叙事延续, 山寨币轮动机会。",
        "futures": "国内大宗商品春节前持仓下降, 关注工业品补库行情。",
        "forex": "美元指数震荡, 人民币汇率受春节结汇影响, 关注中美利差。",
    },
    "Q2": {
        "a_share": "年报与一季报集中披露, 4月政治局会议定调, 5月端午后关注消费数据。",
        "us_stock": "美股一季报披露, 6月FOMC会议, 夏季行情预期。",
        "macro": "国内政策落地节奏, 美联储降息预期, 中美利差。",
        "crypto": "减半后周期, 关注BTC现货ETF资金流向, 山寨币季节性行情。",
        "futures": "工业品旺季需求验证, 农产品关注种植期天气, 贵金属避险情绪回落。",
        "forex": "美元受降息预期承压, 日元干预风险, 人民币双向波动加大。",
    },
    "Q3": {
        "a_share": "中报披露期, 7月底政治局会议, 金九银十预期。",
        "us_stock": "Jackson Hole央行年会, 美股Q2财报, 9月议息会议。",
        "macro": "国内经济复苏力度, 美联储政策转向信号, 美元走势。",
        "crypto": "BTC传统Q3疲软季节性, 关注ETF资金能否扭转格局。",
        "futures": "工业品消费旺季尾声, 关注库存周期与海外需求。",
        "forex": "美债收益率与美元联动, 人民币汇率稳定预期。",
    },
    "Q4": {
        "a_share": "国庆后政策预期, 中央经济工作会议, 年末机构调仓。",
        "us_stock": "美股Q3财报, 大选不确定性, 年末反弹行情。",
        "macro": "国内财政政策发力, 美联储议息节奏, 跨年流动性。",
        "crypto": "Q4历史上强势, 关注BTC创新高行情与山寨币补涨。",
        "futures": "冬季工业品需求边际走弱, 农产品(油脂/粕类)季节性强势, 贵金属避险溢价。",
        "forex": "跨年流动性收紧, 美元年底结算, 关注汇率波动率放大。",
    },
}


# 支持的市场 key
SUPPORTED_MARKETS = ("a_share", "us_stock", "macro", "crypto", "futures", "forex")
DEFAULT_ENABLED_MARKETS = ("a_share", "us_stock", "macro", "crypto")


def _get_quarter(dt: datetime) -> str:
    if dt.month <= 3:
        return "Q1"
    if dt.month <= 6:
        return "Q2"
    if dt.month <= 9:
        return "Q3"
    return "Q4"


def get_fallback_context(dt: datetime | None = None) -> MarketContext:
    """获取季度回退上下文 (含所有 SUPPORTED_MARKETS)"""
    if dt is None:
        dt = datetime.now()
    q = _get_quarter(dt)
    ctx = DEFAULT_CONTEXTS[q]
    return MarketContext(
        date=dt.strftime("%Y-%m-%d"),
        sections=dict(ctx),
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


# 国内主要期货品种
_FUTURES_SYMBOLS = {
    "AU0": "沪金",
    "AG0": "沪银",
    "CU0": "沪铜",
    "RB0": "螺纹",
    "I0":  "铁矿",
    "M0":  "豆粕",
}


def _fetch_futures() -> str:
    """拉国内期货主要品种, 失败抛异常"""
    import akshare as ak

    parts = []
    for sym, name in _FUTURES_SYMBOLS.items():
        try:
            df = ak.futures_main_sina(symbol=sym)
            if len(df) < 2:
                continue
            last = df.iloc[-1]
            prev = df.iloc[-2]
            # 不同品种字段名: 收盘价/settlement
            close = float(last.get("收盘价") or last.get("动态结算价") or 0)
            prev_close = float(prev.get("收盘价") or prev.get("动态结算价") or 0)
            if close == 0 or prev_close == 0:
                continue
            chg = (close - prev_close) / prev_close * 100
            parts.append(f"{name} {close:.0f}({chg:+.2f}%)")
        except Exception:
            continue

    if not parts:
        raise RuntimeError("akshare 拉不到任何期货数据")

    return " | ".join(parts)


def _fetch_forex() -> str:
    """拉主要货币对, 失败抛异常"""
    import akshare as ak

    parts = []
    pairs = [
        ("USDCNY", "USD/CNY"),
        ("EURCNY", "EUR/CNY"),
        ("JPYCNY", "JPY/CNY"),
        ("HKDCNY", "HKD/CNY"),
    ]
    for sym, name in pairs:
        try:
            df = ak.currency_latest(symbols=sym)
            if df is None or len(df) < 1:
                continue
            # 简单取最后一行的中行买入价/卖出价
            row = df.iloc[0]
            # 字段不固定, 简单尝试
            for col in df.columns:
                if "中行" in str(col) and "汇买" in str(col):
                    bid = float(row[col])
                    parts.append(f"{name} {bid:.4f}")
                    break
        except Exception:
            continue

    if not parts:
        raise RuntimeError("akshare 拉不到任何外汇数据")

    return " | ".join(parts)


# fetcher 字典, key 是 market 标识
_FETCHERS = {
    "a_share": _fetch_a_share,
    "us_stock": _fetch_us_stock,
    "crypto": _fetch_crypto,
    "futures": _fetch_futures,
    "forex": _fetch_forex,
    # macro: 没有 fetcher, 始终用模板
}


# ============ 组合入口 ============

def _load_single_market(market: str, fallback_sections: dict[str, str]) -> str:
    """加载单个市场的文本: 优先实时, 失败回退到模板"""
    fallback_text = fallback_sections.get(market, "")
    fetcher = _FETCHERS.get(market)
    if fetcher is None:
        return fallback_text
    try:
        return fetcher()
    except Exception as e:
        print(f"  [warn] {market} 实时数据拉取失败, 用回退: {e}")
        return fallback_text


def load_context(
    custom_path: str | None = None,
    enabled_markets: Optional[list[str]] = None,
) -> MarketContext:
    """
    加载市场上下文

    优先级: 自定义 JSON > 实时数据(成功部分) + 季度模板(失败部分)

    Args:
        custom_path: 自定义市场 JSON 文件路径
        enabled_markets: 启用的市场 key 列表, 默认 DEFAULT_ENABLED_MARKETS

    自定义 JSON 格式:
    {
        "a_share": "...",
        "us_stock": "...",
        "macro": "...",
        "crypto": "...",
        "futures": "...",
        "forex": "..."
    }
    """
    import json
    from pathlib import Path

    if enabled_markets is None:
        enabled_markets = list(DEFAULT_ENABLED_MARKETS)
    # 过滤未知 key
    enabled_markets = [m for m in enabled_markets if m in SUPPORTED_MARKETS]
    if not enabled_markets:
        enabled_markets = list(DEFAULT_ENABLED_MARKETS)

    if custom_path:
        path = Path(custom_path)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                sections = {k: data[k] for k in enabled_markets if k in data}
                # 缺失的用回退填
                fallback = get_fallback_context()
                for k in enabled_markets:
                    sections.setdefault(k, fallback.sections.get(k, ""))
                return MarketContext(
                    date=datetime.now().strftime("%Y-%m-%d"),
                    sections=sections,
                )
            except Exception as e:
                print(f"  [warn] 自定义上下文加载失败: {e}, 使用默认")

    # 实时 + 回退 组合
    fallback = get_fallback_context()
    date_str = datetime.now().strftime("%Y-%m-%d")
    sections = {}

    for market in enabled_markets:
        sections[market] = _load_single_market(market, fallback.sections)

    return MarketContext(date=date_str, sections=sections)


if __name__ == "__main__":
    ctx = load_context()
    print(f"Markets: {list(ctx.sections.keys())}")
    for k, v in ctx.sections.items():
        print(f"  [{k}] {v[:80]}")
