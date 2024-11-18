import math

import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class CoinMarketCapService:
    def __init__(self):
        self.api_key = os.getenv('COINMARKETCAP_API_KEY')
        self.base_url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        self.headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.api_key,
        }

    def get_price(self, symbol: str) -> float:
        params = {
            'symbol': symbol,
        }
        response = requests.get(self.base_url, headers=self.headers, params=params)
        if response.status_code == 200:
            data = response.json()
            return math.trunc(float(data['data'][symbol]['quote']['USD']['price']) * 1000) / 1000
        else:
            response.raise_for_status()
