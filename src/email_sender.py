"""
邮件发送模块

通过 SMTP 发送报告邮件, 默认适配 QQ 邮箱。
支持纯文本和 HTML 两种格式。
"""

from __future__ import annotations
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr
from datetime import datetime
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from .config import Config


def markdown_to_html(md: str) -> str:
    """
    Markdown -> HTML 转换 (东方神秘学 × 编辑式排版)

    设计方向:
    - 墨黑底 + 米白字 + 烫金强调色
    - 思源宋体 + 衬线大字
    - 印章式卦象 + 烫金细线分隔
    - 编辑式分栏、留白、节奏
    """
    import re

    # ====== 抽取特殊块 ======
    # 提取 H1 标题
    h1_match = re.search(r'^# (.+)$', md, re.MULTILINE)
    h1_text = h1_match.group(1).strip() if h1_match else "今日市场风水研报"

    # 提取首行 metadata (日期/生成时间)
    date_match = re.search(r'\*\*日期\*\*:?\s*(.+)', md)
    date_line = date_match.group(1).strip() if date_match else ""

    # 清理 H1 和首段 meta
    body = re.sub(r'^# .+\n', '', md, count=1, flags=re.MULTILINE)
    body = re.sub(r'^\*\*日期\*\*:?.+\n', '', body, count=1, flags=re.MULTILINE)
    body = re.sub(r'^\*\*生成时间\*\*:?.+\n', '', body, count=1, flags=re.MULTILINE)

    # ====== 块转换 ======
    # H2 - 章节标题 (烫金细线 + 序号)
    h2_idx = 0
    def _h2_replace(m):
        nonlocal h2_idx
        h2_idx += 1
        title = m.group(1).strip()
        return (
            f'<div class="chapter" style="margin:48px 0 24px;">'
            f'<div class="chapter-num" style="font-family:\'Cormorant Garamond\',\'Times New Roman\',serif;font-size:11px;letter-spacing:0.4em;color:#c8a96a;text-transform:uppercase;margin-bottom:8px;">CHAPTER · {h2_idx:02d}</div>'
            f'<h2 style="font-family:\'Noto Serif SC\',\'Source Han Serif SC\',serif;font-size:26px;font-weight:600;color:#f4ede0;margin:0;letter-spacing:0.05em;line-height:1.3;">{title}</h2>'
            f'<div style="width:48px;height:1px;background:linear-gradient(90deg,#c8a96a 0%,transparent 100%);margin-top:14px;"></div>'
            f'</div>'
        )
    body = re.sub(r'^## (.+)$', _h2_replace, body, flags=re.MULTILINE)

    # H3 - 子节 (左侧金色竖线)
    def _h3_replace(m):
        title = m.group(1).strip()
        return f'<h3 style="font-family:\'Noto Serif SC\',serif;font-size:17px;font-weight:500;color:#c8a96a;margin:28px 0 14px;padding-left:14px;border-left:2px solid #c8a96a;letter-spacing:0.05em;">{title}</h3>'
    body = re.sub(r'^### (.+)$', _h3_replace, body, flags=re.MULTILINE)

    # 粗体 -> 金色
    body = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#e8c87a;font-weight:600;">\1</strong>', body)

    # 引用块 (古书引文样式)
    def _quote_replace(m):
        text = m.group(1).strip()
        return (
            f'<blockquote style="margin:18px 0;padding:18px 24px;background:rgba(200,169,106,0.06);'
            f'border-left:2px solid #c8a96a;font-family:\'Noto Serif SC\',serif;font-style:italic;'
            f'color:#d4c4a0;font-size:15px;line-height:1.8;letter-spacing:0.05em;">'
            f'<span style="color:#c8a96a;font-size:18px;margin-right:8px;">"</span>{text}'
            f'<span style="color:#c8a96a;font-size:18px;margin-left:4px;">"</span>'
            f'</blockquote>'
        )
    body = re.sub(r'^> (.+)$', _quote_replace, body, flags=re.MULTILINE)

    # 分隔线
    body = re.sub(
        r'^---$',
        '<div style="text-align:center;margin:36px 0;color:#c8a96a;font-size:14px;letter-spacing:1em;">❋ · ❋ · ❋</div>',
        body, flags=re.MULTILINE,
    )

    # 列表项 (无序) - 用中式圆点
    def _li_replace(m):
        text = m.group(1).strip()
        return f'<li style="margin:8px 0;line-height:1.8;color:#e8dfd0;padding-left:4px;"><span style="color:#c8a96a;margin-right:10px;">·</span>{text}</li>'
    body = re.sub(r'^- (.+)$', _li_replace, body, flags=re.MULTILINE)

    # 包裹连续 li 为 ul
    body = re.sub(
        r'((?:<li[^>]*>.*?</li>\n?)+)',
        r'<ul style="list-style:none;padding:0;margin:14px 0;">\1</ul>',
        body,
    )

    # 数字列表
    def _ol_replace(m):
        text = m.group(1).strip()
        return f'<li style="margin:8px 0;line-height:1.8;color:#e8dfd0;">{text}</li>'
    body = re.sub(r'^\d+\. (.+)$', _ol_replace, body, flags=re.MULTILINE)
    body = re.sub(
        r'((?:<li style="margin:8px 0;line-height:1.8;color:#e8dfd0;">.*?</li>\n?)+)',
        r'<ol style="list-style:none;padding:0;margin:14px 0;counter-reset:item;">\1</ol>',
        body,
    )

    # 段落
    lines = body.split('\n')
    new_lines = []
    in_para = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_para:
                new_lines.append('</p>')
                in_para = False
            continue
        is_block = (
            stripped.startswith('<div') or
            stripped.startswith('<h') or
            stripped.startswith('<ul') or
            stripped.startswith('<ol') or
            stripped.startswith('<li') or
            stripped.startswith('<blockquote') or
            stripped.startswith('<hr') or
            stripped.endswith('</li>') or
            stripped.endswith('</ul>') or
            stripped.endswith('</ol>') or
            stripped.endswith('</h2>') or
            stripped.endswith('</h3>')
        )
        if not is_block:
            if not in_para:
                new_lines.append(
                    '<p style="font-family:\'Noto Serif SC\',serif;font-size:15px;line-height:1.9;'
                    'color:#d4c8b0;margin:14px 0;letter-spacing:0.03em;">'
                )
                in_para = True
            new_lines.append(line)
        else:
            if in_para:
                new_lines.append('</p>')
                in_para = False
            new_lines.append(line)
    if in_para:
        new_lines.append('</p>')
    body = '\n'.join(new_lines)

    # ====== 顶部 hero ======
    hero_html = f'''
    <div class="hero" style="padding:60px 40px 50px;text-align:center;border-bottom:1px solid rgba(200,169,106,0.2);position:relative;">
      <div style="font-family:'Cormorant Garamond','Times New Roman',serif;font-size:11px;letter-spacing:0.5em;color:#c8a96a;text-transform:uppercase;margin-bottom:24px;">Daily Almanac Report</div>
      <div style="font-family:'Noto Serif SC','Source Han Serif SC',serif;font-size:42px;font-weight:700;color:#f4ede0;letter-spacing:0.08em;line-height:1.2;margin-bottom:18px;">{h1_text}</div>
      <div style="width:60px;height:1px;background:#c8a96a;margin:0 auto 20px;"></div>
      <div style="font-family:'Cormorant Garamond',serif;font-size:14px;color:#a89878;letter-spacing:0.2em;font-style:italic;">{date_line}</div>
      <div style="position:absolute;top:30px;left:30px;font-family:'Noto Serif SC',serif;font-size:60px;color:rgba(200,169,106,0.08);line-height:1;">⿰</div>
      <div style="position:absolute;bottom:30px;right:30px;font-family:'Noto Serif SC',serif;font-size:60px;color:rgba(200,169,106,0.08);line-height:1;">⿱</div>
    </div>
    '''

    # ====== 底部页脚 (极简, 无免责声明) ======
    footer_html = '''
    <div style="margin-top:60px;padding-top:30px;border-top:1px solid rgba(200,169,106,0.15);text-align:center;">
      <div style="font-family:'Noto Serif SC',serif;font-size:18px;color:#c8a96a;letter-spacing:0.5em;margin-bottom:12px;">☷ ☵ ☲ ☳ ☴ ☵ ☶ ☷</div>
      <div style="font-family:'Cormorant Garamond',serif;font-size:11px;color:#6b5d4a;letter-spacing:0.3em;text-transform:uppercase;">oh-my-trader</div>
    </div>
    '''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>今日市场风水研报</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Noto+Serif+SC:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:'Noto Serif SC','Source Han Serif SC',serif;-webkit-font-smoothing:antialiased;">
<div style="max-width:680px;margin:0 auto;background:linear-gradient(180deg,#0d0d0d 0%,#0a0a0a 100%);min-height:100vh;">

  <!-- 背景纹理 -->
  <div style="position:relative;">
    <div style="position:absolute;top:0;left:0;right:0;bottom:0;background-image:radial-gradient(circle at 20% 10%,rgba(200,169,106,0.04) 0%,transparent 40%),radial-gradient(circle at 80% 80%,rgba(200,169,106,0.03) 0%,transparent 40%);pointer-events:none;"></div>

    <!-- 顶部 -->
    <div style="padding:18px 30px;border-bottom:1px solid rgba(200,169,106,0.1);display:flex;justify-content:space-between;align-items:center;font-family:'Cormorant Garamond',serif;font-size:10px;letter-spacing:0.3em;color:#6b5d4a;text-transform:uppercase;">
      <span>DAILY · 8:30</span>
      <span style="color:#c8a96a;">❋</span>
      <span>EST. 二〇二六</span>
    </div>

    <!-- Hero -->
    {hero_html}

    <!-- 主体 -->
    <div style="padding:20px 40px 50px;">
      {body}
    </div>

    <!-- 页脚 -->
    {footer_html}
  </div>
</div>
</body>
</html>'''


def send_email(
    subject: str,
    content_md: str,
    config: Config,
    to_addr: Optional[str] = None,
) -> bool:
    """
    发送邮件

    Args:
        subject: 邮件主题
        content_md: 报告内容 (Markdown)
        config: 配置
        to_addr: 收件人, 默认使用 config.email_to

    Returns:
        发送是否成功
    """
    if not config.email_user or not config.email_pass:
        print("❌ 邮件配置缺失 (EMAIL_USER / EMAIL_PASS)")
        return False

    to_addr = to_addr or config.email_to
    if not to_addr:
        print("❌ 未指定收件人")
        return False

    # 构造邮件
    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr(["oh-my-trader", config.email_user])
    msg["To"] = formataddr(["User", to_addr])
    msg["Subject"] = Header(subject, "utf-8").encode()

    # 纯文本 + HTML 双版本
    text_part = MIMEText(content_md, "plain", "utf-8")
    html_content = markdown_to_html(content_md)
    html_part = MIMEText(html_content, "html", "utf-8")
    msg.attach(text_part)
    msg.attach(html_part)

    # SMTP 发送
    try:
        if config.email_port == 465:
            # SSL
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(config.email_host, config.email_port, context=context, timeout=30) as server:
                server.login(config.email_user, config.email_pass)
                server.sendmail(config.email_user, [to_addr], msg.as_string())
        else:
            # STARTTLS (587)
            with smtplib.SMTP(config.email_host, config.email_port, timeout=30) as server:
                server.starttls()
                server.login(config.email_user, config.email_pass)
                server.sendmail(config.email_user, [to_addr], msg.as_string())

        print(f"✅ 邮件发送成功 -> {to_addr}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ 邮件认证失败: {e}")
        print("   请检查: 1) 授权码是否正确 2) 是否开启SMTP服务 3) 端口是否正确")
        return False
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False


def send_report_email(report_md: str, config: Config, date_str: Optional[str] = None) -> bool:
    """发送报告邮件 (便捷方法)"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    subject = f"{config.email_subject_prefix} {date_str}"
    return send_email(subject, report_md, config)


if __name__ == "__main__":
    from config import Config
    cfg = Config.from_env()
    missing = cfg.validate()
    if "EMAIL_USER" in missing or "EMAIL_PASS" in missing or "EMAIL_TO" in missing:
        print("请先在 .env 中配置邮件信息")
        print("缺失项:", [m for m in missing if m.startswith("EMAIL_")])
    else:
        test_md = """# 测试报告

这是一封测试邮件。

## 章节1
- 项目1
- 项目2

**重要**: 这只是测试。
"""
        send_report_email(test_md, cfg, "测试")
