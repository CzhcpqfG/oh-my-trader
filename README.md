# 每日市场风水研报 · oh-my-trader

> 一份结合国学风水、天道命理、传统术数、黄历、周易的每日市场分析报告
> GitHub Actions 定时触发, 邮件自动送达

## 核心特点

- **防 LLM 日期幻觉**: 所有历法/干支/宜忌/卦象均由 Python 库精确计算, LLM 只做推演和文案
- **GitHub Actions 托管**: 免费、零运维、零服务器
- **每日 8:30 定时发送**: 北京时间, 早盘前送达
- **DeepSeek API**: 国内直连, 低成本
- **QQ 邮箱 SMTP**: 主流邮箱, 配置简单

## 报告内容

每天邮件包含:
1. **历法档案** — 公历、农历、干支四柱、纳音、生肖、节气
2. **黄历研判** — 建除十二星、五行宜忌、利好/利空板块
3. **卦象解读** — 周易起卦、卦辞象传、动爻、市场寓意
4. **市场分析** — A 股 / 美股 / 宏观 / 加密货币 分项推演
5. **操作建议** — 吉时、规避事项、综合评分

> ⚠️ 报告基于传统术数推演, **仅供娱乐参考, 不构成投资建议**

## 快速开始

### 1. Fork 或 Clone 本仓库

```bash
git clone https://github.com/your-username/oh-my-trader.git
cd oh-my-trader
```

### 2. 本地测试

```bash
# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板
cp .env.example .env

# 编辑 .env 填入真实配置
# - DEEPSEEK_API_KEY: 从 https://platform.deepseek.com/ 获取
# - EMAIL_USER/PASS: QQ邮箱 + 授权码 (非登录密码)
# - EMAIL_TO: 收件人邮箱

# 本地运行一次 (生成报告 + 发送邮件)
python -m src.main
```

### 3. 配置 GitHub Secrets

在 GitHub 仓库页面: **Settings → Secrets and variables → Actions → New repository secret**

添加以下 Secrets:

| Secret 名称 | 说明 |
|------------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key (必填) |
| `DEEPSEEK_BASE_URL` | 默认为 `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 默认为 `deepseek-chat` |
| `EMAIL_HOST` | 默认为 `smtp.qq.com` |
| `EMAIL_PORT` | 默认为 `465` |
| `EMAIL_USER` | QQ 邮箱地址 (必填) |
| `EMAIL_PASS` | QQ 邮箱授权码 (必填) |
| `EMAIL_TO` | 收件人邮箱 (可与 EMAIL_USER 相同) |
| `EMAIL_SUBJECT_PREFIX` | 邮件主题前缀, 默认 `[今日风水报告]` |

### 4. QQ 邮箱授权码获取

1. 登录 QQ 邮箱网页版
2. 设置 → 账户 → POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务
3. 开启 **SMTP 服务** (需短信验证)
4. 生成 **授权码** (16位字母数字, 非 QQ 密码)
5. 把授权码填到 `EMAIL_PASS`

### 5. 启用 GitHub Actions

推送代码到 GitHub 后:

1. 进入仓库的 **Actions** 页面
2. 启用 workflows (如果有提示)
3. 选择 **Daily Market Report** workflow
4. 点击 **Run workflow** 手动测试一次
5. 之后每天北京时间 08:30 自动触发

## 项目结构

```
oh-my-trader/
├── src/
│   ├── main.py                # 主入口
│   ├── config.py              # 配置管理
│   ├── calendar_utils.py      # 历法计算 (cnlunar)
│   ├── almanac.py             # 黄历研判
│   ├── i_ching.py             # 周易起卦
│   ├── market_context.py      # 市场背景
│   ├── report_generator.py    # LLM 报告生成
│   └── email_sender.py        # 邮件发送
├── data/
│   ├── ganzhi_data.py         # 干支纳音基础表
│   └── i_ching_data.py        # 64卦数据库
├── tests/
│   └── test_calendar.py       # 历法测试
├── .github/workflows/
│   └── daily-report.yml       # GitHub Actions
├── .env.example
├── requirements.txt
└── README.md
```

## 关键设计: 防 LLM 日期幻觉

LLM 对日期、农历、干支等有严重的幻觉问题, 本项目通过**分层架构**解决:

```
┌─────────────────────────┐
│ LLM (DeepSeek)          │  ← 只做推演和文案
│ 任务: 把数据组织成报告   │     不对日期做任何判断
└──────────┬──────────────┘
           │ 输入: 100% 确定的历法数据
┌──────────▼──────────────┐
│ Python 库 (cnlunar)     │  ← 计算所有历法数据
│ 任务: 公历→农历→干支    │
└──────────┬──────────────┘
           │ 输入: 系统时间
┌──────────▼──────────────┐
│ GitHub Actions Cron     │  ← 调度
│ 每天 8:30 (北京时间)    │
└─────────────────────────┘
```

所有传 给 LLM 的数据 (日期、干支、宜忌、卦象) 都已**逐字段校验**, Prompt 中明确要求"不得自行修改"。

## 自定义

### 修改市场背景

编辑 `src/market_context.py` 中的 `DEFAULT_CONTEXTS`, 或提供 JSON 文件:

```bash
python -m src.main --market-config my_context.json
```

JSON 格式:
```json
{
  "a_share": "当前A股特殊关注点...",
  "us_stock": "当前美股特殊关注点...",
  "macro": "当前宏观环境...",
  "crypto": "当前加密市场..."
}
```

### 修改起卦方式

编辑 `src/i_ching.py` 中的 `cast_daily_hex()`, 切换不同的起卦算法。

### 修改报告 Prompt

编辑 `src/report_generator.py` 中的 `SYSTEM_PROMPT`。

## 测试

```bash
# 历法计算测试
python -m pytest tests/

# 手动测试 (无需 API key, 只验证历法部分)
python -c "
import sys; sys.stdout.reconfigure(encoding='utf-8')
from src.calendar_utils import calc_calendar
from src.almanac import analyze_almanac
from src.i_ching import cast_daily_hex
cal = calc_calendar()
print('历法:', cal.lunar_year_cn, cal.day_ganzhi, cal.nayin)
alm = analyze_almanac(cal)
print('黄历:', alm.jianchu, alm.day_type)
ich = cast_daily_hex(cal)
print('卦象:', ich.hexagram_name, ich.hexagram_text)
"
```

## 常见问题

### 1. 邮件没收到?

- 检查 GitHub Actions 日志, 看是否 SMTP 报错
- 确认授权码正确 (16 位, 不是 QQ 密码)
- 确认 SMTP 服务已开启
- 检查垃圾邮件箱

### 2. GitHub Actions 没按时触发?

- GitHub Actions 的 cron **不保证准时**, 可能延迟 5-30 分钟
- 私有仓库每月有 2000 分钟免费额度, 足够每日一次
- 可手动触发: Actions → Daily Market Report → Run workflow

### 3. 时区问题?

- GitHub Actions 服务器在 UTC, cron 表达式用 UTC 时间
- 北京时间 8:30 = UTC 0:30 (冬令时) / UTC 0:30 (夏令时, 中国无夏令时)
- 脚本内 `TZ=Asia/Shanghai` 已设置

### 4. DeepSeek 报错?

- 401: API Key 错误或失效
- 429: 调用频率超限, 加 retry 逻辑
- 余额不足: 充值

## License

MIT

## 免责声明

本项目是**文化娱乐工具**, 所有报告内容不构成任何投资建议。传统术数 (黄历、周易、五行) 是中华文化遗产, 但不应作为投资决策依据。投资有风险, 入市需谨慎。
