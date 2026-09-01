from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Mascot(Base):
    __tablename__ = "mascots"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    blurb: Mapped[str] = mapped_column(String(160), nullable=False)
    asset_path: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    starter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
