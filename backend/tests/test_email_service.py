"""Tests for the email service (SendGrid + Gmail SMTP)."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.email_service import send_email


@pytest.mark.asyncio
class TestSendEmailNoConfig:
    async def test_send_email_no_config(self, caplog):
        """When neither SENDGRID_API_KEY nor GMAIL_USER is set, returns False and logs warning."""
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.sendgrid_api_key = None
            mock_settings.gmail_user = None
            mock_settings.gmail_app_password = None

            with caplog.at_level(logging.WARNING, logger="app.services.email_service"):
                result = await send_email("user@example.com", "Test", "<p>Hello</p>")

            assert result is False
            assert "No email service configured" in caplog.text


@pytest.mark.asyncio
class TestSendEmailSendGrid:
    async def test_send_email_sendgrid_preferred(self):
        """When SENDGRID_API_KEY is set, SendGrid is used even if Gmail is also configured."""
        mock_response = MagicMock()
        mock_response.status_code = 202

        mock_sg_instance = MagicMock()
        mock_sg_instance.send.return_value = mock_response

        mock_sg_cls = MagicMock(return_value=mock_sg_instance)

        # Build a mock sendgrid module with nested helpers
        mock_sendgrid = MagicMock(SendGridAPIClient=mock_sg_cls)
        mock_helpers = MagicMock()

        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.sendgrid_api_key = "SG.fake_key"
            mock_settings.gmail_user = "user@gmail.com"
            mock_settings.gmail_app_password = "app_pass"

            with patch.dict(
                "sys.modules",
                {
                    "sendgrid": mock_sendgrid,
                    "sendgrid.helpers": MagicMock(),
                    "sendgrid.helpers.mail": mock_helpers,
                },
            ):
                result = await send_email("user@example.com", "Test", "<p>Hi</p>")

        assert result is True
        mock_sg_cls.assert_called_once_with("SG.fake_key")
        mock_sg_instance.send.assert_called_once()

    async def test_send_email_sendgrid_failure(self):
        """When SendGrid raises an exception, returns False."""
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.sendgrid_api_key = "SG.fake_key"
            mock_settings.gmail_user = None
            mock_settings.gmail_app_password = None

            with patch.dict(
                "sys.modules",
                {
                    "sendgrid": MagicMock(
                        SendGridAPIClient=MagicMock(side_effect=Exception("API error"))
                    ),
                    "sendgrid.helpers.mail": MagicMock(),
                },
            ):
                result = await send_email("user@example.com", "Test", "<p>Hi</p>")

            assert result is False


@pytest.mark.asyncio
class TestSendEmailGmail:
    async def test_send_email_gmail_fallback(self):
        """When only GMAIL creds are set (no SendGrid), uses Gmail SMTP."""
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.sendgrid_api_key = None
            mock_settings.gmail_user = "bot@gmail.com"
            mock_settings.gmail_app_password = "app_pass"

            mock_server = MagicMock()
            with patch("app.services.email_service.smtplib.SMTP", return_value=mock_server):
                mock_server.__enter__ = MagicMock(return_value=mock_server)
                mock_server.__exit__ = MagicMock(return_value=False)

                result = await send_email("user@example.com", "Subject", "<p>Body</p>")

            assert result is True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("bot@gmail.com", "app_pass")
            mock_server.sendmail.assert_called_once()

    async def test_send_email_gmail_failure(self):
        """When Gmail SMTP raises an exception, returns False."""
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.sendgrid_api_key = None
            mock_settings.gmail_user = "bot@gmail.com"
            mock_settings.gmail_app_password = "app_pass"

            with patch(
                "app.services.email_service.smtplib.SMTP",
                side_effect=Exception("SMTP connection failed"),
            ):
                result = await send_email("user@example.com", "Subject", "<p>Body</p>")

            assert result is False


@pytest.mark.asyncio
class TestSendEmailAttachments:
    async def test_send_email_with_attachments(self, tmp_path):
        """Attachments are properly attached when sending via Gmail."""
        # Create a temp file to attach
        attachment_file = tmp_path / "report.csv"
        attachment_file.write_text("col1,col2\n1,2\n")

        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.sendgrid_api_key = None
            mock_settings.gmail_user = "bot@gmail.com"
            mock_settings.gmail_app_password = "app_pass"

            mock_server = MagicMock()
            mock_server.__enter__ = MagicMock(return_value=mock_server)
            mock_server.__exit__ = MagicMock(return_value=False)

            with patch("app.services.email_service.smtplib.SMTP", return_value=mock_server):
                result = await send_email(
                    "user@example.com",
                    "Report",
                    "<p>See attached</p>",
                    attachments=[attachment_file],
                )

            assert result is True
            # Verify sendmail was called and the message contains the attachment filename
            call_args = mock_server.sendmail.call_args
            raw_message = call_args[0][2]  # third positional arg is the message string
            assert "report.csv" in raw_message


@pytest.mark.asyncio
class TestSendEmailRecipients:
    async def test_send_email_multiple_recipients(self):
        """Multiple recipients are all passed to sendmail."""
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.sendgrid_api_key = None
            mock_settings.gmail_user = "bot@gmail.com"
            mock_settings.gmail_app_password = "app_pass"

            mock_server = MagicMock()
            mock_server.__enter__ = MagicMock(return_value=mock_server)
            mock_server.__exit__ = MagicMock(return_value=False)

            with patch("app.services.email_service.smtplib.SMTP", return_value=mock_server):
                recipients = ["a@example.com", "b@example.com", "c@example.com"]
                result = await send_email(recipients, "Multi", "<p>Hello all</p>")

            assert result is True
            call_args = mock_server.sendmail.call_args
            assert call_args[0][1] == recipients

    async def test_send_email_empty_recipients(self):
        """Empty recipient list returns False immediately."""
        result = await send_email([], "Subject", "<p>Body</p>")
        assert result is False
