"""Agent audit log — records every tool call made by any agent."""
from typing import Any, Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AgentAuditLog(Base, TimestampMixin):
    __tablename__ = "agent_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_input: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    tool_result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_result": self.tool_result,
            "confirmed": self.confirmed,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
