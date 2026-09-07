from sqlalchemy import Column, Enum as SAEnum, String, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.core.database import Base


class GenderEnum(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class Person(Base):
    __tablename__ = "persons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)  # Актуальная фамилия
    maiden_name = Column(String(100), nullable=True)  # Девичья фамилия (для женщин)
    middle_name = Column(String(100), nullable=True)
    birth_date = Column(Date, nullable=True)
    birth_place = Column(String(200), nullable=True)
    death_date = Column(Date, nullable=True)
    death_place = Column(String(200), nullable=True)
    burial_place = Column(String(200), nullable=True)
    gender = Column(SAEnum(GenderEnum), nullable=True)
    photo_url = Column(String(500), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    def __repr__(self):
        return f"<Person {self.first_name} {self.last_name}>"

    def get_full_name(self) -> str:
        """
        Возвращает полное имя в формате:
        - Для женщин с девичьей фамилией: "Иванова (Петрова) Мария"
        - Для остальных: "Иванов Иван"
        """
        parts = []

        # Фамилия
        if self.maiden_name and self.gender == GenderEnum.FEMALE:
            parts.append(f"{self.last_name} ({self.maiden_name})")
        else:
            parts.append(self.last_name)

        # Имя
        parts.append(self.first_name)

        # Отчество
        if self.middle_name:
            parts.append(self.middle_name)

        return " ".join(parts)

    def get_last_name_display(self) -> str:
        """Возвращает только фамилию в правильном формате."""
        if self.maiden_name and self.gender == GenderEnum.FEMALE:
            return f"{self.last_name} ({self.maiden_name})"
        return self.last_name