"""One-line DentAssure notice under chat answers."""

from __future__ import annotations

AI_IDENTITY = "AI assistant for DentAssure Health Plans"

CUSTOMER_CARE_PHONE = "+91 888 668 6850"
CUSTOMER_CARE_EMAIL = "support@dentassureplans.com"
CUSTOMER_CARE_WEB = "https://www.dentassureplans.co.in"

COMPOSER_DISCLAIMER = (
    f"AI can make mistakes. Confirm a plan with DentAssure Customer Care {CUSTOMER_CARE_PHONE}."
)

NOTICE_MARKDOWN = f"\n\n*{COMPOSER_DISCLAIMER}*"


def with_customer_care_notice(text: str) -> str:
    """Append the customer-care line once."""
    body = (text or "").rstrip()
    if "DentAssure Customer Care" in body:
        return body
    return f"{body}{NOTICE_MARKDOWN}"
