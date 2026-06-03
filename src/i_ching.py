"""
周易起卦模块

提供基于:
1. 数字起卦法 (年月日数字之和取卦)
2. 干支起卦法 (年月日时三柱天干地支数)
3. 随机起卦法 (固定时间种子)

三种起卦方式。每日报告默认使用干支起卦法。
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.i_ching_data import HEXAGRAMS, get_hexagram_name, TRIGRAMS

if TYPE_CHECKING:
    from .calendar_utils import CalendarInfo


# 地支对应数字 (子=1, 丑=2, ..., 亥=12)
BRANCH_NUM = {
    "子": 1, "丑": 2, "寅": 3, "卯": 4, "辰": 5, "巳": 6,
    "午": 7, "未": 8, "申": 9, "酉": 10, "戌": 11, "亥": 12,
}

# 天干对应数字
STEM_NUM = {
    "甲": 1, "乙": 2, "丙": 3, "丁": 4, "戊": 5,
    "己": 6, "庚": 7, "辛": 8, "壬": 9, "癸": 10,
}

# 八卦序数字 (先天八卦): 乾1兑2离3震4巽5坎6艮7坤8
TRIGRAM_NUM = {
    "乾": 1, "兑": 2, "离": 3, "震": 4,
    "巽": 5, "坎": 6, "艮": 7, "坤": 8,
}

# 八卦序反向
NUM_TO_TRIGRAM = {v: k for k, v in TRIGRAM_NUM.items()}


@dataclass
class IChingResult:
    """起卦结果"""
    method: str  # 起卦方法
    upper_trigram: str  # 上卦
    lower_trigram: str  # 下卦
    hexagram_name: str  # 64卦名
    hexagram_text: str  # 卦辞
    hexagram_image: str  # 象传
    wuxing: str  # 五行倾向
    market_tendency: str  # 市场倾向
    moving_line: int  # 动爻 (1-6)
    raw_numbers: str  # 原始起卦数


def _branch_to_trigram(branch: str) -> str:
    """根据地支映射到八卦 (简化: 用地支序数对8取模)"""
    num = BRANCH_NUM.get(branch, 1)
    # 子丑寅卯辰巳午未申酉戌亥 -> 1-12
    # 映射: 1->乾, 2->兑, 3->离, 4->震, 5->巽, 6->坎, 7->艮, 8->坤
    # 9->乾(循环), 10->兑, 11->离, 12->震
    trigram_num = ((num - 1) % 8) + 1
    return NUM_TO_TRIGRAM[trigram_num]


def cast_by_ganzhi(cal: "CalendarInfo", method: str = "branch") -> IChingResult:
    """
    通过日干支起卦

    Args:
        cal: 历法信息
        method: 起卦方式
            - "branch": 上下卦都由日柱地支数决定 (变爻用日干数)
            - "year": 年月日地支分别取上下卦 (上卦=年支+月支, 下卦=日支+时支)
            - "stem_branch": 上卦=年支, 下卦=日支

    简化版起卦算法, 保证每日卦象确定且有可解释性
    """
    raw = ""

    if method == "branch":
        # 上卦: 日支数对8取余
        day_branch_num = BRANCH_NUM.get(cal.day_branch, 1)
        upper_num = ((day_branch_num - 1) % 8) + 1
        # 下卦: 时支数对8取余
        hour_branch_num = BRANCH_NUM.get(cal.hour_branch, 1)
        lower_num = ((hour_branch_num - 1) % 8) + 1
        # 动爻: (年干数+日干数)对6取余
        moving = ((STEM_NUM.get(cal.year_godist, 1) + STEM_NUM.get(cal.day_godist, 1)) % 6) or 6
        raw = f"日支{cal.day_branch}({day_branch_num})/时支{cal.hour_branch}({hour_branch_num})"

    elif method == "year":
        # 上卦: 年支+月支
        year_branch_num = BRANCH_NUM.get(cal.year_branch, 1)
        month_branch_num = BRANCH_NUM.get(cal.month_branch, 1)
        upper_num = ((year_branch_num + month_branch_num - 2) % 8) + 1
        # 下卦: 日支+时支
        day_branch_num = BRANCH_NUM.get(cal.day_branch, 1)
        hour_branch_num = BRANCH_NUM.get(cal.hour_branch, 1)
        lower_num = ((day_branch_num + hour_branch_num - 2) % 8) + 1
        moving = ((STEM_NUM.get(cal.day_godist, 1) + STEM_NUM.get(cal.hour_godist, 1)) % 6) or 6
        raw = f"年支{cal.year_branch}+月支{cal.month_branch}/日支{cal.day_branch}+时支{cal.hour_branch}"

    else:  # stem_branch
        upper_num = ((BRANCH_NUM.get(cal.year_branch, 1) - 1) % 8) + 1
        lower_num = ((BRANCH_NUM.get(cal.day_branch, 1) - 1) % 8) + 1
        moving = ((STEM_NUM.get(cal.month_godist, 1)) % 6) or 6
        raw = f"年支{cal.year_branch}/日支{cal.day_branch}"

    upper = NUM_TO_TRIGRAM[upper_num]
    lower = NUM_TO_TRIGRAM[lower_num]
    name = get_hexagram_name(upper, lower) or f"未识({upper}上{lower}下)"

    info = HEXAGRAMS.get(name)
    if info:
        _, _, text, image, wuxing, market = info
    else:
        text, image, wuxing, market = "", "", "", ""

    return IChingResult(
        method=f"日干支起卦({method})",
        upper_trigram=upper,
        lower_trigram=lower,
        hexagram_name=name,
        hexagram_text=text,
        hexagram_image=image,
        wuxing=wuxing,
        market_tendency=market,
        moving_line=moving,
        raw_numbers=raw,
    )


def cast_by_datetime(dt: datetime | None = None) -> IChingResult:
    """
    通过公历年月日数字起卦 (传统梅花易数法)

    上卦 = (年数 + 月数 + 日数) % 8
    下卦 = (年数 + 月数 + 日数 + 时数) % 8
    动爻 = (年数 + 月数 + 日数 + 时数) % 6
    """
    if dt is None:
        dt = datetime.now()

    year = dt.year
    month = dt.month
    day = dt.day
    hour = dt.hour
    # 农历转换: 简化使用公历数字
    s1 = year + month + day
    s2 = s1 + hour

    upper_num = (s1 % 8) or 8
    lower_num = (s2 % 8) or 8
    moving = (s2 % 6) or 6

    upper = NUM_TO_TRIGRAM[upper_num]
    lower = NUM_TO_TRIGRAM[lower_num]
    name = get_hexagram_name(upper, lower) or f"未识({upper}上{lower}下)"

    info = HEXAGRAMS.get(name)
    if info:
        _, _, text, image, wuxing, market = info
    else:
        text, image, wuxing, market = "", "", "", ""

    return IChingResult(
        method="梅花易数(公历)",
        upper_trigram=upper,
        lower_trigram=lower,
        hexagram_name=name,
        hexagram_text=text,
        hexagram_image=image,
        wuxing=wuxing,
        market_tendency=market,
        moving_line=moving,
        raw_numbers=f"{year}+{month}+{day}={s1} / +{hour}={s2}",
    )


def cast_daily_hex(cal: "CalendarInfo", dt: datetime | None = None) -> IChingResult:
    """
    每日报告默认起卦: 干支起卦 (主) + 梅花易数 (副) 取主卦
    """
    return cast_by_ganzhi(cal, method="branch")


if __name__ == "__main__":
    from calendar_utils import calc_calendar
    info = calc_calendar()
    result = cast_daily_hex(info)
    print(f"起卦法: {result.method}")
    print(f"上卦: {result.upper_trigram}, 下卦: {result.lower_trigram}")
    print(f"卦名: {result.hexagram_name}")
    print(f"卦辞: {result.hexagram_text}")
    print(f"象传: {result.hexagram_image}")
    print(f"五行: {result.wuxing}, 市场倾向: {result.market_tendency}")
    print(f"动爻: 第{result.moving_line}爻")
    print(f"原始数: {result.raw_numbers}")
