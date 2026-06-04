"""
主入口 — 编排全流程

执行流程:
1. 加载配置
2. 计算历法 (calendar_utils)
3. 分析黄历 (almanac)
4. 起卦 (i_ching)
5. 加载市场背景 (market_context)
6. 调用 LLM 生成报告 (report_generator)
7. 保存报告到本地
8. 发送邮件
"""

from __future__ import annotations
import sys
import os
import traceback
from datetime import datetime
from pathlib import Path

# 允许作为脚本直接执行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.calendar_utils import calc_calendar
from src.almanac import analyze_almanac
from src.i_ching import cast_daily_hex
from src.market_context import load_context
from src.report_generator import generate_report, save_report
from src.email_sender import send_report_email


def run(
    save_local: bool = True,
    send_mail: bool = True,
    custom_market_path: str | None = None,
) -> int:
    """
    执行完整流程

    Args:
        save_local: 是否保存报告到本地文件
        send_mail: 是否发送邮件
        custom_market_path: 自定义市场上下文 JSON 文件路径

    Returns:
        0 成功, 非0 失败
    """
    print("=" * 60)
    print(f"oh-my-trader - Daily Market Almanac Report")
    print(f"   Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 加载配置
    config = Config.from_env()
    missing = config.validate()
    if missing:
        print(f"[ERROR] Missing config: {', '.join(missing)}")
        print("   Check .env file or environment variables")
        if "DEEPSEEK_API_KEY" in missing:
            return 1
        if not send_mail or all(m.startswith("EMAIL_") for m in missing):
            print("   Email config missing, will skip sending")
            send_mail = False

    # 2. 历法计算
    print("\n[1/5] Computing calendar info...")
    cal = calc_calendar()
    print(f"   Solar: {cal.solar_date} {cal.weekday}")
    print(f"   Lunar: {cal.lunar_year_cn} {cal.lunar_month_cn}{cal.lunar_day_cn}")
    print(f"   GZ: {cal.year_ganzhi}/{cal.month_ganzhi}/{cal.day_ganzhi}/{cal.hour_ganzhi}")
    print(f"   Nayin: {cal.nayin}")
    print(f"   Clash: {cal.clash}")

    # 3. 黄历分析
    print("\n[2/5] Almanac analysis...")
    almanac = analyze_almanac(cal)
    print(f"   Build/Remove: {almanac.jianchu} ({almanac.god}) - {almanac.jixiong} / {almanac.day_type}")
    print(f"   Day Wuxing: {almanac.day_wuxing}")
    print(f"   Bullish sectors: {' / '.join(almanac.market_friendly[:3])}")

    # 4. 起卦
    print("\n[3/5] I-Ching casting...")
    iching = cast_daily_hex(cal)
    print(f"   Method: {iching.method}")
    print(f"   Hexagram: {iching.upper_trigram} over {iching.lower_trigram} -> {iching.hexagram_name}")
    print(f"   Judgment: {iching.hexagram_text}")
    print(f"   Moving line: {iching.moving_line}")
    print(f"   Market tendency: {iching.market_tendency}")

    # 5. 市场背景
    print("\n[4/5] Loading market context...")
    market = load_context(custom_market_path, enabled_markets=config.enabled_markets)
    print(f"   Date: {market.date}")
    print(f"   Markets: {list(market.sections.keys())}")
    for k, v in market.sections.items():
        preview = v[:60].replace('\n', ' ')
        print(f"     [{k}] {preview}...")

    # 6. 生成报告
    print("\n[5/5] Calling LLM to generate report...")
    try:
        report = generate_report(cal, almanac, iching, market, config)
        print(f"   Report generated ({len(report)} chars)")
    except Exception as e:
        print(f"[ERROR] Report generation failed: {e}")
        traceback.print_exc()
        return 2

    # 7. 保存本地
    if save_local:
        fpath = save_report(report)
        print(f"   Saved: {fpath}")

    # 8. 发送邮件
    if send_mail:
        print("\nSending email...")
        ok = send_report_email(report, config, cal.solar_date)
        if not ok:
            return 3
    else:
        print("\nSkipping email (config missing or disabled)")

    print("\n" + "=" * 60)
    print("[DONE] All tasks completed!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="oh-my-trader 每日市场风水研报")
    parser.add_argument("--no-save", action="store_true", help="不保存到本地")
    parser.add_argument("--no-mail", action="store_true", help="不发送邮件")
    parser.add_argument("--market-config", type=str, help="自定义市场上下文 JSON 路径")
    args = parser.parse_args()

    code = run(
        save_local=not args.no_save,
        send_mail=not args.no_mail,
        custom_market_path=args.market_config,
    )
    sys.exit(code)
