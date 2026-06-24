from typing import Optional
from sqlalchemy import String, CheckConstraint, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('Learner', 'Manager', 'Admin')",
            name="ck_user_role",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    manager_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    track_states: Mapped[list["UserTrackState"]] = relationship("UserTrackState", back_populates="user", foreign_keys="UserTrackState.user_id")
    reports: Mapped[list["User"]] = relationship("User", foreign_keys="User.manager_id", back_populates="manager")
    manager: Mapped[Optional["User"]] = relationship("User", foreign_keys=[manager_id], back_populates="reports", remote_side="User.id")


class UserTrackState(Base):
    __tablename__ = "user_track_states"
    __table_args__ = (
        CheckConstraint(
            "status IN ('In Progress', 'Completed')",
            name="ck_uts_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    track_id: Mapped[str] = mapped_column(String(36), ForeignKey("tracks.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    current_module_id: Mapped[str] = mapped_column(String(36), ForeignKey("modules.id"), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="track_states", foreign_keys=[user_id])
