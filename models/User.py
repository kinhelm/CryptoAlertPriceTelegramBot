from typing import Any, List

from sqlalchemy import String
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    id_telegram: Mapped[int] = mapped_column(unique=True)
    firstname: Mapped[str] = mapped_column(String(30))
    chat_id: Mapped[int]
    alerts: Mapped[List["Alert"]] = relationship()

    def __str__(self):
        return 'User  ' + self.firstname

    def __init__(self, id_telegram, firstname, chat_id, **kw: Any):
        super().__init__(**kw)
        self.id_telegram = id_telegram
        self.firstname = firstname
        self.chat_id = chat_id

