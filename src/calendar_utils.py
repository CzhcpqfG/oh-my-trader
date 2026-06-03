"""
历法计算模块

封装 cnlunar 库, 提供统一的历法数据接口。
所有日期/干支/五行/纳音/生肖等数据均由库计算, 严禁由 LLM 推算。
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any
import cnlunar


# 星期映射
WEEKDAY_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


@dataclass
class CalendarInfo:
    """某一时辰下的完整历法信息"""
    # 公历
    solar_date: str  # 2026-06-03
    weekday: str  # 星期三
    hour: int  # 8 (24小时制)
    twohour_branch: str  # 时辰地支: 辰

    # 农历
    lunar_year_cn: str  # 二零二六
    lunar_month_cn: str  # 四月
    lunar_day_cn: str  # 十八
    lunar_year: int
    lunar_month: int
    lunar_day: int
    is_leap_month: bool

    # 干支
    year_ganzhi: str  # 丙午
    month_ganzhi: str  # 癸巳
    day_ganzhi: str  # 戊申
    hour_ganzhi: str  # 丙辰
    year_godist: str  # 丙 (年天干)
    year_branch: str  # 午 (年地支)
    month_godist: str
    month_branch: str
    day_godist: str
    day_branch: str
    hour_godist: str
    hour_branch: str

    # 纳音
    nayin: str  # 大驿土
    wuxing: str  # 五行分类

    # 生肖
    zodiac: str  # 马
    clash: str  # 冲猴

    # 节气
    solar_term: str  # 芒种 / 空

    # 建除
    jianchu: str  # 平
    jianchu_12god: str  # 天刑
    day_type: str  # 黑道日

    # 28宿 / 九星
    star_28: str  # 箕水豹
    fly_9star: str  # 九星飞星数

    # 彭祖百忌
    pengzu: str  # 戊不受田...

    # 胎神
    fetal_god: str  # 房床炉...

    # 宜忌
    yi: list[str]
    ji: list[str]
    good_gods: list[str]
    bad_gods: list[str]

    # 时辰吉凶 (12时辰)
    hour_luck_list: list[str]  # 12个: 凶/吉

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_attr(obj: Any, *names: str, default: str = "") -> str:
    """按顺序尝试多个属性名/方法, 取首个有效值"""
    for name in names:
        if not hasattr(obj, name):
            continue
        val = getattr(obj, name)
        if callable(val):
            try:
                val = val()
            except Exception:
                continue
        if val:
            return str(val)
    return default


def _flatten_cn(val: Any) -> str:
    """cnlunar 的 lunarXXXCN 返回值可能是元组, 扁平化处理"""
    if val is None:
        return ""
    if isinstance(val, tuple):
        return "".join(str(x) for x in val)
    return str(val)


def _dedup_cn(val: Any) -> str:
    """cnlunar 的 lunarYearCN 有时会返回重复字符串 (如 '二零二六二零二六'),
    去重一半长度, 还原为标准农历年份显示"""
    s = _flatten_cn(val)
    if not s:
        return ""
    n = len(s)
    if n > 0 and n % 2 == 0 and s[:n // 2] == s[n // 2:]:
        return s[:n // 2]
    return s


def _lunar_day_cn(val: Any) -> str:
    """cnlunar 的 lunarCn 返回 ('二...二', '四月小', '十八') 元组,
    只取第三段(农历日)即可"""
    if val is None:
        return ""
    if isinstance(val, tuple):
        if len(val) >= 3:
            return str(val[2])
        return "".join(str(x) for x in val)
    return str(val)


def get_twohour_branch(hour: int) -> str:
    """根据 24 小时制返回地支"""
    branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    # 子时: 23:00-00:59, 即 hour==23 or hour<1
    if hour == 23 or hour == 0:
        return "子"
    return branches[(hour + 1) // 2]


def calc_calendar(dt: datetime | None = None) -> CalendarInfo:
    """
    计算给定时刻的完整历法信息

    Args:
        dt: 目标时间, 默认为当前时间
    """
    if dt is None:
        dt = datetime.now()

    # cnlunar 接收 datetime 对象
    a = cnlunar.Lunar(dt)

    # 宜忌: cnlunar 给出的是嵌套结构, 提取首层
    yi = _safe_attr(a, "goodThing", default="[]")
    ji = _safe_attr(a, "badThing", default="[]")
    # goodThing/badThing 可能是 list/str, 统一转 list
    if isinstance(yi, str):
        # 字符串里可能含引号
        yi = [x.strip().strip("'\"") for x in yi.strip("[]").split(",") if x.strip()]
    if isinstance(ji, str):
        ji = [x.strip().strip("'\"") for x in ji.strip("[]").split(",") if x.strip()]

    # 吉神凶煞: ((good_list, bad_list), (yi_list, ji_list))
    angel_demon = a.get_AngelDemon()
    good_gods: list[str] = []
    bad_gods: list[str] = []
    if isinstance(angel_demon, tuple) and len(angel_demon) >= 1:
        first = angel_demon[0]
        if isinstance(first, tuple) and len(first) >= 2:
            good_gods = list(first[0]) if first[0] else []
            bad_gods = list(first[1]) if first[1] else []

    # 时辰吉凶
    hour_luck = a.get_twohourLuckyList()
    hour_luck_list = [str(x) for x in hour_luck] if hour_luck else []

    # 日柱拆解
    day8 = a.get_day8Char() or ""
    month8 = a.get_month8Char() or ""
    year8 = a.get_year8Char() or ""
    hour8 = a.get_twohour8Char() or ""

    # 建除
    jianchu_tuple = a.get_today12DayOfficer()
    jianchu = jianchu_tuple[0] if isinstance(jianchu_tuple, tuple) and len(jianchu_tuple) >= 1 else str(jianchu_tuple)
    jianchu_12god = jianchu_tuple[1] if isinstance(jianchu_tuple, tuple) and len(jianchu_tuple) >= 2 else ""
    day_type = jianchu_tuple[2] if isinstance(jianchu_tuple, tuple) and len(jianchu_tuple) >= 3 else ""

    # 五行描述
    wuxing = a.get_today5Elements()
    wuxing_str = "、".join(str(x) for x in wuxing) if wuxing else ""

    # 农历闰月
    is_leap = bool(_safe_attr(a, "isLunarLeapMonth", default=False) or
                   (_safe_attr(a, "lunarMonthType", default="") == "闰"))

    return CalendarInfo(
        solar_date=dt.strftime("%Y-%m-%d"),
        weekday=WEEKDAY_CN[dt.weekday()],
        hour=dt.hour,
        twohour_branch=get_twohour_branch(dt.hour),

        lunar_year_cn=_dedup_cn(a.get_lunarYearCN()),
        lunar_month_cn=_flatten_cn(a.get_lunarMonthCN()),
        lunar_day_cn=_lunar_day_cn(a.get_lunarCn()),
        lunar_year=a.lunarYear,
        lunar_month=a.lunarMonth,
        lunar_day=a.lunarDay,
        is_leap_month=is_leap,

        year_ganzhi=year8,
        month_ganzhi=month8,
        day_ganzhi=day8,
        hour_ganzhi=hour8,
        year_godist=year8[0] if year8 else "",
        year_branch=year8[1] if year8 else "",
        month_godist=month8[0] if month8 else "",
        month_branch=month8[1] if month8 else "",
        day_godist=day8[0] if day8 else "",
        day_branch=day8[1] if day8 else "",
        hour_godist=hour8[0] if hour8 else "",
        hour_branch=hour8[1] if hour8 else "",

        nayin=a.get_nayin(),
        wuxing=wuxing_str,

        zodiac=a.get_chineseYearZodiac(),
        clash=a.get_chineseZodiacClash(),

        solar_term=a.get_todaySolarTerms() or "无",

        jianchu=jianchu,
        jianchu_12god=jianchu_12god,
        day_type=day_type,

        star_28=a.get_the28Stars(),
        fly_9star=a.get_the9FlyStar(),

        pengzu=a.get_pengTaboo(),
        fetal_god=a.get_fetalGod(),

        yi=yi,
        ji=ji,
        good_gods=good_gods,
        bad_gods=bad_gods,

        hour_luck_list=hour_luck_list,
    )


if __name__ == "__main__":
    # 自测
    import json
    info = calc_calendar()
    print(json.dumps(info.to_dict(), ensure_ascii=False, indent=2))
