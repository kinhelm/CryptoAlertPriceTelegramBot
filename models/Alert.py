from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped

from models.base import Base
from services.coinmarketcap_service import CoinMarketCapService

class Alert(Base):
    __tablename__ = "alert"
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(10))
    direction: Mapped[str] = mapped_column(String(10))
    target_price: Mapped[float]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))

    def __str__(self):
        service = CoinMarketCapService()
        return str(self.id) + ' - When ' + self.symbol + ' is ' + self.direction + ' at ' + str(
            self.target_price) + ' (' + str(service.get_price(self.symbol)) + ')'
