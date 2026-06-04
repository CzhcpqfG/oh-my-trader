# oh-my-trader

每日市场风水研报 — 结合黄历、周易、五行与 A 股 / 美股 / 宏观 / 加密的推演分析, GitHub Actions 定时邮件送达。

## 特点

- **防 LLM 日期幻觉**: 所有历法/干支/宜忌/卦象由 `cnlunar` 精确计算, LLM 只做推演和文案
- **动态市场数据**: A 股用 akshare 实时拉取,美股/加密失败时回退到季度模板
- **零运维**: GitHub Actions 托管,免费 cron,无需服务器
- **API 重试**: DeepSeek 3 次指数退避,容忍瞬时网络抖动

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env  # 填入 DEEPSEEK_API_KEY + 邮箱授权码
python -m src.main
```

部署到 GitHub: 配置 8 个 Secrets (见 `.env.example`), Actions 会自动每天 8:00 北京时间触发。

## 配置项

| 必填 | 字段 | 说明 |
|------|------|------|
| ✅ | `DEEPSEEK_API_KEY` | platform.deepseek.com 申请 |
| ✅ | `EMAIL_USER` | QQ 邮箱地址 |
| ✅ | `EMAIL_PASS` | QQ 邮箱**授权码** (设置 → 账户 → 开启 SMTP 服务) |
| ✅ | `EMAIL_TO` | 收件邮箱 |
| ⬜ | `EMAIL_HOST/PORT/SUBJECT_PREFIX` | 默认 QQ/465/`[今日风水报告]` |
| ⬜ | `DEEPSEEK_BASE_URL/MODEL` | 默认官方 + `deepseek-chat` |
| ⬜ | `LLM_TEMPERATURE` | 默认 0.8 |

## 自定义

```bash
# 自定义市场背景 (覆盖默认季度模板)
python -m src.main --market-config my_context.json

# 只跑数据流不调 API / 不发邮件
python -m src.main --no-mail --no-save
```

修改报告风格改 `src/report_generator.py:SYSTEM_PROMPT`, 修改起卦改 `src/i_ching.py:cast_daily_hex()`。

## 测试

```bash
python tests/test_calendar.py
```

## 已知行为

- **GitHub Actions cron 可能延迟数小时** (平台限制, 非项目问题). 设为 8:00 提前进队列以缓解
- 美股/加密数据源在国内网络时常不可用, 会自动回退到季度模板, 报告不中断
- cron 实际触发时间与预期不符时, 看 [Actions 历史](https://github.com/CzhcpqfG/oh-my-trader/actions) 排查

## License

MIT
