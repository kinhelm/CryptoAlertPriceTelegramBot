import requests
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped

from models.base import Base

binance_url = "https://api.binance.com/api/v3/ticker/price?symbol="

class Alert(Base):
    __tablename__ = "alert"
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(10))
    direction: Mapped[str] = mapped_column(String(10))
    target_price: Mapped[float]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))

    def __str__(self):
        return str(self.id) + ' - When ' + self.symbol + ' is ' + self.direction + ' at ' + str(
            self.target_price) + ' (' + str(self.getCurrentPrice()) + ')'

    def getCurrentPrice(self) -> float:
        print(binance_url + self.symbol + 'USDT')
        resp = requests.get(binance_url + self.symbol + 'USDT')
        if resp.status_code == 200:
            data = resp.json()
            return float(data['price'])
        return -1
