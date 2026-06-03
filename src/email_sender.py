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
    """简易 Markdown -> HTML 转换 (够用即可)"""
    import re

    html = md

    # 标题
    html = re.sub(r'^# (.+)$', r'<h1 style="color:#2c3e50;border-bottom:2px solid #34495e;padding-bottom:8px;">\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2 style="color:#34495e;border-left:4px solid #3498db;padding-left:10px;margin-top:30px;">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3 style="color:#16a085;">\1</h3>', html, flags=re.MULTILINE)

    # 粗体
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

    # 引用
    html = re.sub(r'^> (.+)$', r'<blockquote style="border-left:3px solid #95a5a6;color:#7f8c8d;padding-left:10px;margin:10px 0;">\1</blockquote>', html, flags=re.MULTILINE)

    # 列表
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*</li>\n?)+', lambda m: '<ul style="margin:10px 0;padding-left:25px;">' + m.group(0) + '</ul>', html)

    # 数字列表
    html = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

    # 分隔线
    html = re.sub(r'^---$', r'<hr style="border:none;border-top:1px solid #bdc3c7;margin:20px 0;">', html, flags=re.MULTILINE)

    # 段落
    lines = html.split('\n')
    new_lines = []
    in_para = False
    for line in lines:
        if line.strip() and not line.strip().startswith('<') and not line.strip().startswith('---'):
            if not in_para:
                new_lines.append('<p style="line-height:1.7;margin:10px 0;">')
                in_para = True
            new_lines.append(line)
        else:
            if in_para:
                new_lines.append('</p>')
                in_para = False
            new_lines.append(line)
    if in_para:
        new_lines.append('</p>')

    html = '\n'.join(new_lines)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>今日市场风水研报</title>
</head>
<body style="font-family:'Microsoft YaHei',Arial,sans-serif;max-width:800px;margin:0 auto;padding:20px;color:#2c3e50;background:#fafafa;">
<div style="background:white;padding:30px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
{html}
<div style="margin-top:30px;padding-top:20px;border-top:1px solid #ecf0f1;text-align:center;color:#95a5a6;font-size:12px;">
  oh-my-trader · 每日市场风水研报 · {datetime.now().strftime("%Y-%m-%d %H:%M")}
</div>
</div>
</body>
</html>"""


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
