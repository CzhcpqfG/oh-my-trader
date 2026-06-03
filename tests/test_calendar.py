"""
历法模块测试
"""

import sys
from datetime import datetime
from pathlib import Path

# 允许从项目根目录直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.calendar_utils import calc_calendar, get_twohour_branch
from src.almanac import analyze_almanac
from src.i_ching import cast_daily_hex, cast_by_datetime
from data.ganzhi_data import get_nayin, get_wuxing, NAYIN_60
from data.i_ching_data import HEXAGRAMS, get_hexagram_name


def test_twohour_branch():
    """测试时辰地支计算"""
    assert get_twohour_branch(0) == "子"
    assert get_twohour_branch(1) == "丑"
    assert get_twohour_branch(2) == "丑"
    assert get_twohour_branch(3) == "寅"
    assert get_twohour_branch(7) == "辰"
    assert get_twohour_branch(12) == "午"
    assert get_twohour_branch(13) == "未"
    assert get_twohour_branch(22) == "亥"
    assert get_twohour_branch(23) == "子"
    print("[PASS] test_twohour_branch")


def test_calendar_2024_chinese_new_year():
    """2024年2月10日是甲辰龙年正月初一"""
    cal = calc_calendar(datetime(2024, 2, 10, 12, 0))
    assert cal.year_ganzhi == "甲辰", f"expected 甲辰, got {cal.year_ganzhi}"
    assert cal.zodiac == "龙", f"expected 龙, got {cal.zodiac}"
    assert "正" in cal.lunar_month_cn, f"expected 正月, got {cal.lunar_month_cn}"
    assert "初" in cal.lunar_day_cn or "一" in cal.lunar_day_cn, f"expected 初一, got {cal.lunar_day_cn}"
    print(f"[PASS] test_calendar_2024_chinese_new_year: {cal.year_ganzhi} {cal.lunar_month_cn}{cal.lunar_day_cn} {cal.zodiac}年")


def test_calendar_basic():
    """基本历法字段完整性"""
    cal = calc_calendar()
    assert cal.solar_date
    assert cal.weekday
    assert cal.year_ganzhi
    assert cal.month_ganzhi
    assert cal.day_ganzhi
    assert cal.hour_ganzhi
    assert cal.nayin
    assert cal.zodiac
    assert cal.jianchu
    assert cal.jixiong if hasattr(cal, 'jixiong') else True
    print(f"[PASS] test_calendar_basic: {cal.solar_date} {cal.day_ganzhi} {cal.nayin}")


def test_nayin_table():
    """测试 60 甲子纳音表完整性"""
    assert len(NAYIN_60) == 60, f"expected 60 entries, got {len(NAYIN_60)}"
    assert get_nayin("甲子") == "海中金"
    assert get_nayin("戊申") == "大驿土"
    assert get_nayin("丙午") == "天河水"
    assert get_wuxing("甲子") == "金"
    assert get_wuxing("戊申") == "土"
    print(f"[PASS] test_nayin_table: {len(NAYIN_60)} entries verified")


def test_hexagram_table():
    """测试 64 卦表完整性"""
    assert len(HEXAGRAMS) == 64, f"expected 64, got {len(HEXAGRAMS)}"
    assert get_hexagram_name("乾", "乾") == "乾"
    assert get_hexagram_name("坤", "乾") == "泰"
    assert get_hexagram_name("乾", "坤") == "否"
    assert get_hexagram_name("坎", "离") == "既济"
    assert get_hexagram_name("离", "坎") == "未济"
    print(f"[PASS] test_hexagram_table: {len(HEXAGRAMS)} hexagrams verified")


def test_almanac():
    """黄历分析"""
    cal = calc_calendar()
    alm = analyze_almanac(cal)
    assert alm.jianchu
    assert alm.day_wuxing
    assert alm.brief
    print(f"[PASS] test_almanac: {alm.jianchu} {alm.day_type} {alm.day_wuxing}")


def test_iching():
    """起卦测试"""
    cal = calc_calendar()
    ich = cast_daily_hex(cal)
    assert ich.hexagram_name
    assert ich.hexagram_text
    assert 1 <= ich.moving_line <= 6
    print(f"[PASS] test_iching: {ich.hexagram_name} ({ich.upper_trigram}上{ich.lower_trigram}下), 动爻{ich.moving_line}")


def test_iching_datetime():
    """公历数字起卦"""
    ich = cast_by_datetime(datetime(2026, 6, 3, 8, 30))
    assert ich.hexagram_name
    assert 1 <= ich.moving_line <= 6
    print(f"[PASS] test_iching_datetime: {ich.hexagram_name}")


def test_calendar_multiple_dates():
    """多个日期的历法数据"""
    test_dates = [
        (2024, 1, 1),   # 农历2023年冬月二十
        (2024, 6, 3),   # 农历四月廿七
        (2025, 1, 29),  # 春节
        (2026, 2, 17),  # 春节
    ]
    for y, m, d in test_dates:
        cal = calc_calendar(datetime(y, m, d, 12, 0))
        assert cal.solar_date == f"{y:04d}-{m:02d}-{d:02d}"
        assert cal.year_ganzhi
        print(f"  - {cal.solar_date}: {cal.lunar_year_cn} {cal.lunar_month_cn}{cal.lunar_day_cn} ({cal.year_ganzhi} {cal.day_ganzhi})")
    print(f"[PASS] test_calendar_multiple_dates: {len(test_dates)} dates verified")


if __name__ == "__main__":
    print("=" * 60)
    print("Running tests...")
    print("=" * 60)
    test_twohour_branch()
    test_calendar_2024_chinese_new_year()
    test_calendar_basic()
    test_nayin_table()
    test_hexagram_table()
    test_almanac()
    test_iching()
    test_iching_datetime()
    test_calendar_multiple_dates()
    print("=" * 60)
    print("All tests passed!")
    print("=" * 60)
