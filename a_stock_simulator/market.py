"""行情模拟引擎 - Simulated market data engine for A-shares."""

import random
import math
from typing import Dict, List

from .models import StockInfo

# 预设股票池 - 涵盖各板块代表性股票
DEFAULT_STOCKS = [
    # 沪市主板
    ("600519", "贵州茅台", "SH", 1680.00),
    ("601318", "中国平安", "SH", 48.50),
    ("600036", "招商银行", "SH", 35.20),
    ("601012", "隆基绿能", "SH", 25.80),
    ("600900", "长江电力", "SH", 28.60),
    ("601888", "中国中免", "SH", 98.50),
    ("600276", "恒瑞医药", "SH", 42.30),
    ("600030", "中信证券", "SH", 22.10),
    ("600809", "山西汾酒", "SH", 218.50),
    ("601166", "兴业银行", "SH", 18.90),
    # 深市主板
    ("000858", "五粮液",   "SZ", 158.60),
    ("000333", "美的集团", "SZ", 62.40),
    ("000001", "平安银行", "SZ", 12.80),
    ("000651", "格力电器", "SZ", 38.50),
    ("002714", "牧原股份", "SZ", 42.60),
    ("002594", "比亚迪",   "SZ", 265.00),
    ("000725", "京东方A",  "SZ", 4.85),
    ("002415", "海康威视", "SZ", 35.80),
    # 创业板 (涨跌幅20%)
    ("300750", "宁德时代", "SZ", 198.50),
    ("300059", "东方财富", "SZ", 16.80),
    ("300015", "爱尔眼科", "SZ", 28.50),
    ("300760", "迈瑞医疗", "SZ", 285.00),
    # 科创板 (涨跌幅20%)
    ("688981", "中芯国际", "SH", 48.50),
    ("688111", "金山办公", "SH", 298.00),
]


class MarketEngine:
    """行情模拟引擎

    使用随机游走 + 均值回归模型模拟股价波动，
    同时模拟成交量和盘口数据。
    """

    def __init__(self):
        self.stocks: Dict[str, StockInfo] = {}
        self._tick_count = 0
        self._trends: Dict[str, float] = {}  # 各股趋势因子
        self._volatility: Dict[str, float] = {}  # 各股波动率
        self._init_stocks()

    def _init_stocks(self):
        """初始化股票池"""
        for code, name, market, base_price in DEFAULT_STOCKS:
            # 模拟一个随机的昨收价偏移
            prev_close = base_price * (1 + random.uniform(-0.02, 0.02))
            prev_close = round(prev_close, 2)

            # 开盘价在昨收附近
            open_price = prev_close * (1 + random.uniform(-0.01, 0.01))
            open_price = round(open_price, 2)

            stock = StockInfo(
                code=code,
                name=name,
                market=market,
                price=open_price,
                prev_close=prev_close,
                open_price=open_price,
                high=max(open_price, prev_close),
                low=min(open_price, prev_close),
                volume=random.randint(10000, 500000) * 100,
                amount=0.0,
            )
            self.stocks[code] = stock

            # 随机分配趋势和波动率
            self._trends[code] = random.uniform(-0.3, 0.3)
            base_vol = 0.015 if code.startswith("3") or code.startswith("68") else 0.01
            self._volatility[code] = base_vol * random.uniform(0.5, 2.0)

    def tick(self):
        """推进一个时间步，更新所有股价"""
        self._tick_count += 1
        for code, stock in self.stocks.items():
            self._update_price(stock)

    def _update_price(self, stock: StockInfo):
        """更新单只股票价格

        模型: 几何布朗运动 + 均值回归 + 随机冲击
        """
        code = stock.code
        trend = self._trends[code]
        vol = self._volatility[code]

        # 均值回归力度: 偏离昨收越远，回归力越强
        deviation = (stock.price - stock.prev_close) / stock.prev_close
        mean_revert = -deviation * 0.05

        # 随机冲击
        shock = random.gauss(0, 1) * vol

        # 偶尔突发大波动 (模拟消息面冲击)
        if random.random() < 0.02:
            shock *= random.uniform(2, 4)

        # 趋势缓慢漂移
        drift = trend * 0.001

        # 综合收益率
        ret = drift + mean_revert + shock

        # 涨跌停限制
        limit = 0.20 if code.startswith("3") or code.startswith("68") else 0.10
        max_price = round(stock.prev_close * (1 + limit), 2)
        min_price = round(stock.prev_close * (1 - limit), 2)

        new_price = stock.price * (1 + ret)
        new_price = max(min_price, min(max_price, new_price))
        new_price = round(new_price, 2)

        # 最低价不能低于0.01
        new_price = max(0.01, new_price)

        # 更新成交量
        tick_volume = random.randint(100, 5000) * 100
        tick_amount = tick_volume * new_price

        stock.price = new_price
        stock.high = max(stock.high, new_price)
        stock.low = min(stock.low, new_price)
        stock.volume += tick_volume
        stock.amount += tick_amount

    def get_stock(self, code: str) -> StockInfo:
        """获取股票信息"""
        if code not in self.stocks:
            raise ValueError(f"股票代码 {code} 不存在")
        return self.stocks[code]

    def get_all_stocks(self) -> List[StockInfo]:
        """获取所有股票"""
        return list(self.stocks.values())

    def search(self, keyword: str) -> List[StockInfo]:
        """搜索股票 (按代码或名称)"""
        keyword = keyword.strip().upper()
        results = []
        for stock in self.stocks.values():
            if keyword in stock.code or keyword in stock.name.upper():
                results.append(stock)
        return results

    def get_bid_ask(self, code: str, levels: int = 5) -> dict:
        """获取买卖五档盘口数据"""
        stock = self.get_stock(code)
        price = stock.price
        tick = 0.01

        asks = []  # 卖盘 (价格从低到高)
        bids = []  # 买盘 (价格从高到低)

        for i in range(1, levels + 1):
            ask_price = round(price + tick * i * random.randint(1, 3), 2)
            ask_vol = random.randint(1, 200) * 100
            asks.append((ask_price, ask_vol))

            bid_price = round(price - tick * i * random.randint(1, 3), 2)
            bid_price = max(0.01, bid_price)
            bid_vol = random.randint(1, 200) * 100
            bids.append((bid_price, bid_vol))

        return {"asks": asks, "bids": bids, "last": price}

    def randomize_trends(self):
        """随机调整趋势 (模拟市场情绪变化)"""
        for code in self._trends:
            self._trends[code] += random.uniform(-0.1, 0.1)
            self._trends[code] = max(-1.0, min(1.0, self._trends[code]))
