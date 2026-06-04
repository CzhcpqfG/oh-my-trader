# oh-my-trader

每日市场风水研报 — 结合黄历、周易、五行与 A 股 / 美股 / 宏观 / 加密 / 期货 / 外汇的推演分析, GitHub Actions 定时邮件送达。

## 特点

- **防 LLM 日期幻觉**: 所有历法/干支/宜忌/卦象由 `cnlunar` 精确计算, LLM 只做推演和文案
- **多 LLM 厂商**: 抽象 provider 层, 同一份 Prompt 可喂 DeepSeek / OpenAI / 通义千问 / 智谱 / Claude
- **动态市场数据**: A 股 / 期货 / 外汇走 akshare 实时拉取, 美股 / 加密失败时回退到季度模板
- **可配置市场**: 通过 `ENABLED_MARKETS` 选择 6 个市场中的任意子集
- **零运维**: GitHub Actions 托管, 免费 cron, 无需服务器
- **API 重试**: 3 次指数退避, 容忍瞬时网络抖动

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env  # 填 LLM_API_KEY + 邮箱授权码
python -m src.main
```

部署到 GitHub: 配置 Secrets (见 `.env.example`), Actions 会自动每天 8:00 北京时间触发。

## 配置项

### LLM 厂商选择

| Provider | 配置示例 | 备注 |
|----------|---------|------|
| `deepseek` (默认) | `LLM_PROVIDER=deepseek` + `LLM_API_KEY=sk-...` | 国内直连 |
| `tongyi` 通义千问 | `LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1` `LLM_MODEL=qwen-plus` | 国内直连 |
| `zhipu` 智谱 | `LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4` `LLM_MODEL=glm-4-plus` | 国内直连 |
| `openai` | `LLM_BASE_URL=https://api.openai.com/v1` | 需翻墙 |
| `claude` | `LLM_PROVIDER=claude` + `LLM_CLAUDE_API_KEY=sk-ant-...` | 需 `pip install anthropic` |
| `custom` | 任意 OpenAI 兼容端点 | 自填 `LLM_BASE_URL` + `LLM_MODEL` |

> 旧 `DEEPSEEK_*` 字段仍可继续使用 (自动 fallback), 无需迁移。

### 市场选择

```
ENABLED_MARKETS=a_share,us_stock,macro,crypto,futures,forex
```

| Key | 数据源 | 实时 |
|-----|--------|------|
| `a_share` | akshare | ✅ |
| `us_stock` | yfinance | ✅ (国内常失败, 自动回退) |
| `macro` | 季度模板 | — |
| `crypto` | CoinGecko | ✅ (国内常失败, 自动回退) |
| `futures` | akshare 新浪 | ✅ |
| `forex` | akshare 中行 | ✅ |

不填默认 4 个 (`a_share,us_stock,macro,crypto`), 与旧版完全一致。

### 邮件

| 必填 | 字段 | 说明 |
|------|------|------|
| ✅ | `EMAIL_USER` | QQ 邮箱地址 |
| ✅ | `EMAIL_PASS` | QQ 邮箱**授权码** (设置 → 账户 → 开启 SMTP 服务) |
| ✅ | `EMAIL_TO` | 收件邮箱, 多个用逗号分隔 |
| ⬜ | `EMAIL_HOST/PORT/SUBJECT_PREFIX` | 默认 QQ/465/`[今日风水报告]` |
| ⬜ | `LLM_TEMPERATURE` | 默认 0.8 |

## 自定义

```bash
# 自定义市场背景 (覆盖默认季度模板)
python -m src.main --market-config my_context.json

# 只跑数据流不调 API / 不发邮件
python -m src.main --no-mail --no-save
```

修改报告风格改 `src/report_generator.py:build_system_prompt()`, 修改起卦改 `src/i_ching.py:cast_daily_hex()`, 修改市场→板块映射改 `data/ganzhi_data.py`。

## 测试

```bash
python tests/test_calendar.py
```

## 已知行为

- **GitHub Actions cron 可能延迟数小时** (平台限制). cron 设为 UTC 00:00 = 北京 8:00, 提前进队列缓解
- 美股 / 加密 / 外汇数据源在国内网络时常不可用, 会自动回退到季度模板, 报告不中断
- cron 实际触发时间与预期不符时, 看 [Actions 历史](https://github.com/CzhcpqfG/oh-my-trader/actions) 排查

## License

MIT
