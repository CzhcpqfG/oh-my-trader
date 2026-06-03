"""
报告生成器

职责:
1. 组装历法 + 黄历 + 卦象 + 市场背景为 Prompt
2. 调用 DeepSeek API 生成分析报告
3. 加上免责声明等元信息
"""

from __future__ import annotations
import json
import requests
from datetime import datetime
from typing import TYPE_CHECKING

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from .config import Config
from .calendar_utils import CalendarInfo
from .almanac import AlmanacResult
from .i_ching import IChingResult
from .market_context import MarketContext

if TYPE_CHECKING:
    pass


SYSTEM_PROMPT = """你是一位资深的中国传统文化研究者, 同时精通现代金融市场分析。

你的任务是基于下方提供的"今日确定性历法数据"和"市场背景", 撰写一份今日市场风水研报。

【重要原则】
1. 所有历法/干支/宜忌/卦象数据已由系统计算好, 你必须**严格使用**提供的数据, 不得自行推算、补充或修改。
2. 不要对日期、农历、星期、干支等做任何"纠正", 即便你觉得与某来源不同。
3. 推演部分要基于"五行生克"、"卦象精神"、"建除十二星寓意"等传统术数逻辑。
4. 报告用语要稳重、有文化底蕴, 可以有观点、有判断, 但避免过度神化或绝对化。
5. 报告末尾**不要**添加免责声明、风险提示、"仅供娱乐参考"等说教性文字。

【报告结构】
请按以下结构组织 Markdown 报告:
1. 历法档案 (日期、农历、干支、纳音、生肖、节气)
2. 黄历研判 (建除十二星、黄道/黑道、五行宜忌、市场板块映射)
3. 卦象解读 (上卦下卦、卦辞、象传、动爻、市场寓意)
4. 今日综合研判 (整体市场氛围一句话定性)
5. A股市场分析
6. 美股市场分析
7. 宏观环境分析
8. 加密货币市场分析
9. 操作建议 (吉时、规避事项)
10. 综合评分 (满分100, 给个倾向分)

【语言风格】
- 使用简体中文
- 引用传统经典时保持原文, 但解释用现代汉语
- 不用"玄学/迷信"等自贬词汇, 但需明确非投资建议
"""


def build_user_prompt(
    cal: CalendarInfo,
    almanac: AlmanacResult,
    iching: IChingResult,
    market: MarketContext,
) -> str:
    """组装用户消息"""

    # 历法档案
    calendar_section = f"""【今日历法档案】(由历法系统计算, 不得修改)
- 公历日期: {cal.solar_date} {cal.weekday}
- 农历: {cal.lunar_year_cn}年 {cal.lunar_month_cn} {cal.lunar_day_cn}
- 节气: {cal.solar_term}
- 生肖: {cal.zodiac}
- 干支: 年{cal.year_ganzhi} 月{cal.month_ganzhi} 日{cal.day_ganzhi} 时{cal.hour_ganzhi}
- 纳音: {cal.nayin}
- 二十八宿: {cal.star_28}
- 彭祖百忌: {cal.pengzu}
- 胎神: {cal.fetal_god}
- 冲煞: {cal.clash}
"""

    # 黄历
    yi_str = "、".join(cal.yi)
    ji_str = "、".join(cal.ji)
    good_gods_str = "、".join(cal.good_gods)
    bad_gods_str = "、".join(cal.bad_gods)

    almanac_section = f"""【黄历研判】
- 建除十二星: {almanac.jianchu} ({almanac.god})
- 性质: {almanac.jixiong} · {almanac.day_type}
- 日柱五行: {almanac.day_wuxing}
- 受生五行: {almanac.day_element_sheng}
- 受克五行: {almanac.ke_day}
- 宜: {yi_str}
- 忌: {ji_str}
- 吉神: {good_gods_str}
- 凶煞: {bad_gods_str}
- 利好板块: {almanac.market_friendly}
- 利空板块: {almanac.market_unfriendly}
- 一句话: {almanac.brief}
"""

    # 卦象
    iching_section = f"""【周易卦象】
- 起卦法: {iching.method}
- 上卦: {iching.upper_trigram} ({TRIGRAM_DESCRIPTIONS.get(iching.upper_trigram, '')})
- 下卦: {iching.lower_trigram} ({TRIGRAM_DESCRIPTIONS.get(iching.lower_trigram, '')})
- 卦名: {iching.hexagram_name}
- 卦辞: {iching.hexagram_text}
- 象传: {iching.hexagram_image}
- 动爻: 第{iching.moving_line}爻
- 五行倾向: {iching.wuxing}
- 市场倾向: {iching.market_tendency}
"""

    # 市场背景
    market_section = f"""【市场背景】
- 日期: {market.date}
- A股: {market.a_share}
- 美股: {market.us_stock}
- 宏观: {market.macro}
- 加密: {market.crypto}
"""

    # 时辰吉凶 (12时辰)
    hour_luck_str = " ".join(f"时{i+1}:{luck}" for i, luck in enumerate(cal.hour_luck_list[:12]))

    additional = f"""【时辰吉凶列表】(12时辰)
{hour_luck_str}

请基于以上确定数据, 撰写今日市场风水研报。
"""

    return calendar_section + "\n" + almanac_section + "\n" + iching_section + "\n" + market_section + "\n" + additional


# 用于 Prompt 中描述八卦自然属性
TRIGRAM_DESCRIPTIONS = {
    "乾": "天-刚健", "兑": "泽-悦",
    "离": "火-光明", "震": "雷-动",
    "巽": "风-入", "坎": "水-险",
    "艮": "山-止", "坤": "地-顺",
}


def call_deepseek(
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: int = 120,
) -> str:
    """调用 DeepSeek API"""
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 4096,
        "stream": False,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def generate_report(
    cal: CalendarInfo,
    almanac: AlmanacResult,
    iching: IChingResult,
    market: MarketContext,
    config: Config,
) -> str:
    """生成完整报告 (含头部, 不含免责声明)"""
    user_prompt = build_user_prompt(cal, almanac, iching, market)

    print(f"正在调用 DeepSeek API ({config.deepseek_model}) 生成报告...")
    body = call_deepseek(
        api_key=config.deepseek_api_key,
        base_url=config.deepseek_base_url,
        model=config.deepseek_model,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    # 组装完整报告 (无免责声明)
    header = f"""# 今日市场风水研报

**日期**: {cal.solar_date} {cal.weekday} ({cal.lunar_year_cn} {cal.lunar_month_cn}{cal.lunar_day_cn})
**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

"""

    return header + body


def save_report(report: str, output_dir: str = "output") -> str:
    """保存报告到本地文件"""
    from pathlib import Path
    p = Path(output_dir)
    p.mkdir(parents=True, exist_ok=True)
    fname = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    fpath = p / fname
    fpath.write_text(report, encoding="utf-8")
    return str(fpath)


if __name__ == "__main__":
    from .config import Config
    from .calendar_utils import calc_calendar
    from .almanac import analyze_almanac
    from .i_ching import cast_daily_hex
    from .market_context import get_default_context

    cfg = Config.from_env()
    missing = cfg.validate()
    if "DEEPSEEK_API_KEY" in missing:
        print("请先设置 DEEPSEEK_API_KEY 环境变量")
        exit(1)

    info = calc_calendar()
    almanac = analyze_almanac(info)
    iching = cast_daily_hex(info)
    market = get_default_context()

    # 打印 prompt
    prompt = build_user_prompt(info, almanac, iching, market)
    print(prompt)
    print("=" * 60)
    print("以上为 Prompt, 设置 API_KEY 后可生成完整报告")
