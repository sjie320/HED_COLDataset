"""数据模型 - Data models for the A-share simulator."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class OrderDirection(Enum):
    """交易方向"""
    BUY = "买入"
    SELL = "卖出"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "待成交"
    FILLED = "已成交"
    PARTIAL = "部分成交"
    CANCELLED = "已撤单"
    REJECTED = "已拒绝"


@dataclass
class StockInfo:
    """股票基本信息"""
    code: str           # 股票代码, e.g. "600519"
    name: str           # 股票名称, e.g. "贵州茅台"
    market: str         # 市场: "SH"(沪) / "SZ"(深)
    price: float        # 当前价格
    prev_close: float   # 昨收价
    open_price: float   # 开盘价
    high: float         # 最高价
    low: float          # 最低价
    volume: int = 0     # 成交量(股)
    amount: float = 0.0 # 成交额(元)

    @property
    def change(self) -> float:
        """涨跌额"""
        return self.price - self.prev_close

    @property
    def change_pct(self) -> float:
        """涨跌幅(%)"""
        if self.prev_close == 0:
            return 0.0
        return (self.price - self.prev_close) / self.prev_close * 100

    @property
    def full_code(self) -> str:
        """完整代码 e.g. SH600519"""
        return f"{self.market}{self.code}"

    @property
    def is_limit_up(self) -> bool:
        """是否涨停"""
        limit = 20 if self.code.startswith("3") or self.code.startswith("68") else 10
        return self.change_pct >= limit - 0.01

    @property
    def is_limit_down(self) -> bool:
        """是否跌停"""
        limit = 20 if self.code.startswith("3") or self.code.startswith("68") else 10
        return self.change_pct <= -limit + 0.01


@dataclass
class Order:
    """委托订单"""
    order_id: int
    stock_code: str
    stock_name: str
    direction: OrderDirection
    price: float
    quantity: int           # 委托数量(股)
    filled_quantity: int = 0
    filled_price: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    timestamp: float = field(default_factory=time.time)
    message: str = ""

    @property
    def filled_amount(self) -> float:
        """成交金额"""
        return self.filled_price * self.filled_quantity


@dataclass
class Position:
    """持仓"""
    stock_code: str
    stock_name: str
    quantity: int           # 总持仓(股)
    available: int          # 可卖数量(股) - T+1
    cost_price: float       # 成本价
    current_price: float    # 当前价

    @property
    def market_value(self) -> float:
        """市值"""
        return self.current_price * self.quantity

    @property
    def cost_amount(self) -> float:
        """成本金额"""
        return self.cost_price * self.quantity

    @property
    def profit(self) -> float:
        """浮动盈亏"""
        return self.market_value - self.cost_amount

    @property
    def profit_pct(self) -> float:
        """盈亏比例(%)"""
        if self.cost_amount == 0:
            return 0.0
        return self.profit / self.cost_amount * 100


@dataclass
class TradeRecord:
    """成交记录"""
    trade_id: int
    order_id: int
    stock_code: str
    stock_name: str
    direction: OrderDirection
    price: float
    quantity: int
    amount: float
    commission: float       # 佣金
    stamp_tax: float        # 印花税
    transfer_fee: float     # 过户费
    total_cost: float       # 总费用
    timestamp: float = field(default_factory=time.time)


@dataclass
class Account:
    """资金账户"""
    initial_capital: float      # 初始资金
    available_cash: float       # 可用资金
    frozen_cash: float = 0.0    # 冻结资金(委托未成交)

    @property
    def total_cash(self) -> float:
        """总现金(含冻结)"""
        return self.available_cash + self.frozen_cash
