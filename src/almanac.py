"""
黄历模块 — 简化版本

基于日干支与建除十二星, 给出当日的:
- 吉凶属性
- 五行宜忌补充
- 市场操作建议

本模块的宜忌由 cnlunar 库提供原始数据,
本模块的职责是补充基于五行生克的衍生推演和市场映射。
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.ganzhi_data import (
    STEM_WUXING, BRANCH_WUXING, WUXING_SHENG, WUXING_KE, BUILDING_STARS,
)

if TYPE_CHECKING:
    from .calendar_utils import CalendarInfo


@dataclass
class AlmanacResult:
    """黄历分析结果"""
    # 基础属性
    jianchu: str  # 建除十二星: 建/除/满...
    jixiong: str  # 大吉/吉/平/凶/大凶
    day_type: str  # 黄道日/黑道日
    god: str  # 十二神: 天刑/月德...

    # 宜忌 (来自 cnlunar)
    yi: list[str]
    ji: list[str]

    # 五行关系
    day_wuxing: str  # 日柱五行
    day_element_ke: str  # 日柱所克的五行
    day_element_sheng: str  # 生日柱的五行
    ke_day: str  # 克制日柱的五行

    # 市场映射
    market_friendly: list[str]  # 五行对应利好板块
    market_unfriendly: list[str]  # 五行对应利空板块

    # 文字解读
    brief: str  # 一句话总结


# 五行对应市场板块
WUXING_SECTORS = {
    "木": ["医药生物", "教育传媒", "环保", "新能源", "科技成长"],
    "火": ["电力能源", "光伏", "新能源汽车", "消费", "传媒娱乐"],
    "土": ["房地产", "基建", "农业", "建材", "稀土有色"],
    "金": ["金融银行", "证券", "军工", "半导体硬件", "汽车制造"],
    "水": ["酒旅酒店", "航运港口", "物流", "水利环保", "互联网"],
}


def _classify_luck(jianchu: str) -> tuple[str, str]:
    """根据建除星给出吉凶分类"""
    lucky_stars = {"成", "开", "定", "收", "除"}
    neutral_stars = {"建", "满", "平", "执"}
    unlucky_stars = {"破", "危", "闭"}
    if jianchu in lucky_stars:
        return ("吉", "黄道日")
    if jianchu in unlucky_stars:
        return ("凶", "黑道日")
    return ("中", "平道日")


def analyze_almanac(cal: "CalendarInfo") -> AlmanacResult:
    """
    综合分析当日的黄历信息

    Args:
        cal: 历法信息 (由 calendar_utils.calc_calendar() 返回)

    Returns:
        AlmanacResult
    """
    # 基础属性
    jianchu = cal.jianchu
    jixiong, day_type = _classify_luck(jianchu)

    # 日柱五行
    day_godist_wx = STEM_WUXING.get(cal.day_godist, "")
    day_branch_wx = BRANCH_WUXING.get(cal.day_branch, "")
    # 天干为主, 若不同取地支
    if day_godist_wx == day_branch_wx:
        day_wx = day_godist_wx
    else:
        day_wx = day_godist_wx or day_branch_wx

    # 五行生克关系
    ke_day = WUXING_KE.get(day_wx, "")  # 什么克日柱
    day_ke = ""  # 日柱克什么 (反向找)
    for k, v in WUXING_KE.items():
        if v == day_wx:
            day_ke = k
            break
    sheng_day = WUXING_SHENG.get(day_wx, "")  # 反向: 什么生日柱
    # reverse of SHENG
    day_sheng = ""
    for k, v in WUXING_SHENG.items():
        if v == day_wx:
            day_sheng = k
            break

    # 市场映射: 日柱五行所对应板块为中性/吉利
    # (日柱五行本身的板块受益)
    market_friendly = WUXING_SECTORS.get(day_wx, [])
    # 克制日柱的五行板块利空
    market_unfriendly = WUXING_SECTORS.get(ke_day, [])

    # 一句话总结
    jianchu_meta = BUILDING_STARS.get(jianchu, {})
    interpretation = jianchu_meta.get("市场解读", "")
    brief = f"今日{day_type}, 建除{jianchu}日 ({cal.jianchu_12god}), {interpretation}。日柱五行属{day_wx}, 受{sheng_day}生, 被{ke_day}克。"

    return AlmanacResult(
        jianchu=jianchu,
        jixiong=jixiong,
        day_type=day_type,
        god=cal.jianchu_12god,
        yi=cal.yi,
        ji=cal.ji,
        day_wuxing=day_wx,
        day_element_ke=day_ke,
        day_element_sheng=sheng_day,
        ke_day=ke_day,
        market_friendly=market_friendly,
        market_unfriendly=market_unfriendly,
        brief=brief,
    )


if __name__ == "__main__":
    from calendar_utils import calc_calendar
    info = calc_calendar()
    result = analyze_almanac(info)
    print(f"建除: {result.jianchu}, 性质: {result.jixiong}, 类型: {result.day_type}")
    print(f"日柱五行: {result.day_wuxing}, 利好板块: {result.market_friendly}")
    print(f"利空板块: {result.market_unfriendly}")
    print(f"总结: {result.brief}")
