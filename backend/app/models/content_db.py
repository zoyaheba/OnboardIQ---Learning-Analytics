from sqlalchemy import String, Text, Integer, CheckConstraint, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    modules: Mapped[list["Module"]] = relationship("Module", back_populates="track")


class Module(Base):
    __tablename__ = "modules"
    __table_args__ = (
        CheckConstraint(
            "difficulty_level IN ('Beginner', 'Intermediate', 'Advanced')",
            name="ck_module_difficulty",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    track_id: Mapped[str] = mapped_column(String(36), ForeignKey("tracks.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    difficulty_level: Mapped[str] = mapped_column(String(20), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)

    track: Mapped["Track"] = relationship("Track", back_populates="modules")
    concepts: Mapped[list["Concept"]] = relationship("Concept", back_populates="module")
    quiz_questions: Mapped[list["QuizQuestion"]] = relationship("QuizQuestion", back_populates="module")


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    module_id: Mapped[str] = mapped_column(String(36), ForeignKey("modules.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=True)
    youtube_video_id: Mapped[str] = mapped_column(String(11), nullable=True)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)

    module: Mapped["Module"] = relationship("Module", back_populates="concepts")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (
        CheckConstraint(
            "correct_option IN ('A', 'B', 'C', 'D')",
            name="ck_quiz_correct_option",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    module_id: Mapped[str] = mapped_column(String(36), ForeignKey("modules.id"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict] = mapped_column(JSON, nullable=False)
    correct_option: Mapped[str] = mapped_column(String(1), nullable=False)

    module: Mapped["Module"] = relationship("Module", back_populates="quiz_questions")
