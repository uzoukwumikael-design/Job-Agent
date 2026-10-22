"""Email / Telegram alert hooks when a high-fit job is scored."""

from __future__ import annotations
import logging
import httpx
from typing import Optional
from app.core.config import get_settings

logger = logging.getLogger("alerts")


async def send_telegram(chat_id: str, text: str, bot_token: Optional[str] = None) -> bool:
    token = bot_token or get_settings().telegram_bot_token
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json={"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": True})
            return r.status_code == 200
    except Exception as e:
        logger.warning("Telegram send failed: %s", e)
        return False


async def send_email_stub(to_email: str, subject: str, body: str) -> bool:
    """Hook for SMTP / Resend / SendGrid. Logs when not configured."""
    settings = get_settings()
    if not settings.smtp_host and not settings.resend_api_key:
        logger.info("Email alert (not sent – no SMTP/Resend): to=%s subject=%s", to_email, subject)
        return False
    if settings.resend_api_key:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                    json={
                        "from": settings.alert_from_email or "alerts@jobagent.local",
                        "to": [to_email],
                        "subject": subject,
                        "text": body,
                    },
                )
                return r.status_code in (200, 201)
        except Exception as e:
            logger.warning("Resend failed: %s", e)
            return False
    # SMTP fallback could go here
    logger.info("SMTP not fully wired; skipped email to %s", to_email)
    return False


async def notify_high_fit(
    *,
    user_email: str,
    telegram_chat_id: Optional[str],
    title: str,
    company: str,
    score: float,
    url: str,
    min_score: float = 4.0,
) -> None:
    if score < min_score:
        return
    text = (
        f"High-fit role ({score:.1f}/5)\n"
        f"{title} @ {company}\n"
        f"{url or '(no url)'}\n"
        f"— AI Advisor Job Agent"
    )
    if telegram_chat_id:
        await send_telegram(telegram_chat_id, text)
    await send_email_stub(user_email, f"High-fit: {title} @ {company}", text)
