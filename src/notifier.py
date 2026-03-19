from __future__ import annotations

import smtplib
from email.message import EmailMessage

from config import Settings
from strategy import TradeDecision


class EmailNotifier:
    def __init__(self, settings: Settings) -> None:
        self.enabled = settings.email_alerts_enabled
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.alert_from_email = settings.alert_from_email
        self.alert_to_email = settings.alert_to_email

    @property
    def configured(self) -> bool:
        return self.enabled and all(
            [
                self.smtp_host,
                self.smtp_port,
                self.smtp_username,
                self.smtp_password,
                self.alert_from_email,
                self.alert_to_email,
            ]
        )

    def send_message(self, subject: str, body: str) -> None:
        if not self.configured:
            return

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.alert_from_email
        message["To"] = self.alert_to_email
        message.set_content(body)

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20) as server:
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(message)


def format_trade_alert(decision: TradeDecision, context: str) -> tuple[str, str]:
    subject = f"Stock bot alert: {context} [{decision.symbol} {decision.action}]"
    lines = [
        f"Context: {context}",
        f"Symbol: {decision.symbol}",
        f"Action: {decision.action}",
        f"Status: {decision.order_status}",
        f"Confidence: {decision.confidence}",
        f"Rationale: {decision.rationale}",
    ]
    if decision.order_id:
        lines.append(f"Order ID: {decision.order_id}")
    if decision.position_unrealized_pl_pct is not None:
        lines.append(f"Position unrealized P/L: {decision.position_unrealized_pl_pct:.2f}%")
    body = "\n".join(lines)
    return subject, body
