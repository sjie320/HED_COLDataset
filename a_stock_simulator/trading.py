"""交易引擎 - Trading engine with A-share rules."""

import time
from typing import Dict, List, Optional

from .models import (
    Account, Order, OrderDirection, OrderStatus,
    Position, TradeRecord,
)
from .market import MarketEngine


class TradingEngine:
    """交易引擎

    实现A股交易规则:
    - T+1: 当日买入次日才能卖出
    - 买入最小单位100股(1手), 卖出可以不足100股(碎股一次卖出)
    - 涨跌停限制: 主板±10%, 创业板/科创板±20%
    - 交易费用: 佣金万2.5(最低5元) + 印花税千1(仅卖出) + 过户费万0.2
    """

    COMMISSION_RATE = 0.00025      # 佣金费率 万2.5
    MIN_COMMISSION = 5.0           # 最低佣金 5元
    STAMP_TAX_RATE = 0.001         # 印花税 千1 (仅卖出)
    TRANSFER_FEE_RATE = 0.00002    # 过户费 万0.2

    def __init__(self, market: MarketEngine, initial_capital: float = 1_000_000.0):
        self.market = market
        self.account = Account(
            initial_capital=initial_capital,
            available_cash=initial_capital,
        )
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[TradeRecord] = []
        self._next_order_id = 1
        self._next_trade_id = 1
        self._today_bought: set = set()  # 今日买入的股票代码(T+1限制)

    def buy(self, stock_code: str, price: float, quantity: int) -> Order:
        """委托买入

        Args:
            stock_code: 股票代码
            price: 委托价格
            quantity: 委托数量(股), 必须为100的整数倍
        """
        stock = self.market.get_stock(stock_code)

        # 验证数量: 必须为100的整数倍
        if quantity <= 0 or quantity % 100 != 0:
            return self._rejected_order(stock_code, stock.name,
                                        OrderDirection.BUY, price, quantity,
                                        "买入数量必须为100的整数倍")

        # 验证价格: 不能超过涨停价
        limit = 0.20 if stock_code.startswith("3") or stock_code.startswith("68") else 0.10
        max_price = round(stock.prev_close * (1 + limit), 2)
        min_price = round(stock.prev_close * (1 - limit), 2)
        if price > max_price or price < min_price:
            return self._rejected_order(stock_code, stock.name,
                                        OrderDirection.BUY, price, quantity,
                                        f"委托价格超出涨跌停限制 [{min_price}, {max_price}]")

        # 验证资金: 含预估手续费
        total_cost = price * quantity
        est_commission = max(total_cost * self.COMMISSION_RATE, self.MIN_COMMISSION)
        est_transfer = total_cost * self.TRANSFER_FEE_RATE
        required = total_cost + est_commission + est_transfer

        if required > self.account.available_cash:
            return self._rejected_order(stock_code, stock.name,
                                        OrderDirection.BUY, price, quantity,
                                        f"资金不足, 需要 {required:.2f}, 可用 {self.account.available_cash:.2f}")

        # 冻结资金
        self.account.available_cash -= required
        self.account.frozen_cash += required

        order = Order(
            order_id=self._next_order_id,
            stock_code=stock_code,
            stock_name=stock.name,
            direction=OrderDirection.BUY,
            price=price,
            quantity=quantity,
        )
        self._next_order_id += 1
        self.orders.append(order)

        # 立即尝试撮合
        self._try_match(order)
        return order

    def sell(self, stock_code: str, price: float, quantity: int) -> Order:
        """委托卖出"""
        stock = self.market.get_stock(stock_code)

        # 验证持仓
        pos = self.positions.get(stock_code)
        if not pos or pos.available <= 0:
            return self._rejected_order(stock_code, stock.name,
                                        OrderDirection.SELL, price, quantity,
                                        "无可卖持仓(注意T+1规则: 当日买入次日才能卖出)")

        if quantity > pos.available:
            return self._rejected_order(stock_code, stock.name,
                                        OrderDirection.SELL, price, quantity,
                                        f"可卖数量不足, 可卖 {pos.available} 股")

        # 卖出可以不足100股(碎股), 但如果超过100股则必须是100的整数倍
        if quantity > 100 and quantity % 100 != 0:
            remainder = pos.available % 100
            if quantity != remainder:
                return self._rejected_order(stock_code, stock.name,
                                            OrderDirection.SELL, price, quantity,
                                            "卖出数量须为100的整数倍(碎股须一次性全部卖出)")

        # 验证价格
        limit = 0.20 if stock_code.startswith("3") or stock_code.startswith("68") else 0.10
        max_price = round(stock.prev_close * (1 + limit), 2)
        min_price = round(stock.prev_close * (1 - limit), 2)
        if price > max_price or price < min_price:
            return self._rejected_order(stock_code, stock.name,
                                        OrderDirection.SELL, price, quantity,
                                        f"委托价格超出涨跌停限制 [{min_price}, {max_price}]")

        # 冻结可卖数量
        pos.available -= quantity

        order = Order(
            order_id=self._next_order_id,
            stock_code=stock_code,
            stock_name=stock.name,
            direction=OrderDirection.SELL,
            price=price,
            quantity=quantity,
        )
        self._next_order_id += 1
        self.orders.append(order)

        self._try_match(order)
        return order

    def cancel_order(self, order_id: int) -> bool:
        """撤单"""
        for order in self.orders:
            if order.order_id == order_id and order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                order.message = "用户撤单"

                # 解冻资金/数量
                if order.direction == OrderDirection.BUY:
                    unfilled = order.quantity - order.filled_quantity
                    est_cost = order.price * unfilled
                    est_fee = max(est_cost * self.COMMISSION_RATE, self.MIN_COMMISSION) + \
                              est_cost * self.TRANSFER_FEE_RATE
                    refund = est_cost + est_fee
                    self.account.frozen_cash -= refund
                    self.account.available_cash += refund
                else:
                    unfilled = order.quantity - order.filled_quantity
                    pos = self.positions.get(order.stock_code)
                    if pos:
                        pos.available += unfilled

                return True
        return False

    def _try_match(self, order: Order):
        """撮合委托 (简化模型: 如果委托价格合理，立即全部成交)"""
        stock = self.market.get_stock(order.stock_code)
        current_price = stock.price

        if order.direction == OrderDirection.BUY:
            # 买入: 委托价 >= 当前价 即成交, 成交价取当前价
            if order.price >= current_price:
                fill_price = current_price
            else:
                # 限价单未达到, 暂挂单
                return
        else:
            # 卖出: 委托价 <= 当前价 即成交
            if order.price <= current_price:
                fill_price = current_price
            else:
                return

        fill_qty = order.quantity
        self._execute_trade(order, fill_price, fill_qty)

    def try_match_pending(self):
        """尝试撮合所有挂单 (每个tick调用)"""
        for order in self.orders:
            if order.status == OrderStatus.PENDING:
                self._try_match(order)

    def _execute_trade(self, order: Order, fill_price: float, fill_qty: int):
        """执行成交"""
        amount = fill_price * fill_qty

        # 计算费用
        commission = max(amount * self.COMMISSION_RATE, self.MIN_COMMISSION)
        stamp_tax = amount * self.STAMP_TAX_RATE if order.direction == OrderDirection.SELL else 0.0
        transfer_fee = amount * self.TRANSFER_FEE_RATE
        total_cost = commission + stamp_tax + transfer_fee

        # 更新订单状态
        order.filled_quantity = fill_qty
        order.filled_price = fill_price
        order.status = OrderStatus.FILLED

        # 记录成交
        trade = TradeRecord(
            trade_id=self._next_trade_id,
            order_id=order.order_id,
            stock_code=order.stock_code,
            stock_name=order.stock_name,
            direction=order.direction,
            price=fill_price,
            quantity=fill_qty,
            amount=amount,
            commission=commission,
            stamp_tax=stamp_tax,
            transfer_fee=transfer_fee,
            total_cost=total_cost,
        )
        self._next_trade_id += 1
        self.trades.append(trade)

        # 更新持仓和资金
        if order.direction == OrderDirection.BUY:
            self._process_buy(order, trade)
        else:
            self._process_sell(order, trade)

    def _process_buy(self, order: Order, trade: TradeRecord):
        """处理买入成交"""
        code = order.stock_code
        actual_cost = trade.amount + trade.total_cost

        # 解冻并扣除资金
        est_cost = order.price * order.quantity
        est_fee = max(est_cost * self.COMMISSION_RATE, self.MIN_COMMISSION) + \
                  est_cost * self.TRANSFER_FEE_RATE
        frozen = est_cost + est_fee
        self.account.frozen_cash -= frozen
        # 退回多冻结的部分
        refund = frozen - actual_cost
        self.account.available_cash += max(refund, 0)

        # 更新持仓
        if code in self.positions:
            pos = self.positions[code]
            total_cost = pos.cost_price * pos.quantity + trade.amount
            pos.quantity += trade.quantity
            pos.cost_price = total_cost / pos.quantity if pos.quantity > 0 else 0
            # T+1: 今日买入不增加可卖数量
        else:
            self.positions[code] = Position(
                stock_code=code,
                stock_name=order.stock_name,
                quantity=trade.quantity,
                available=0,  # T+1: 今日不可卖
                cost_price=trade.amount / trade.quantity,
                current_price=trade.price,
            )

        self._today_bought.add(code)

    def _process_sell(self, order: Order, trade: TradeRecord):
        """处理卖出成交"""
        code = order.stock_code
        proceeds = trade.amount - trade.total_cost
        self.account.available_cash += proceeds

        # 更新持仓
        pos = self.positions[code]
        pos.quantity -= trade.quantity
        if pos.quantity <= 0:
            del self.positions[code]

    def new_trading_day(self):
        """新的交易日: 重置T+1限制, 更新可卖数量"""
        for code, pos in self.positions.items():
            pos.available = pos.quantity
        self._today_bought.clear()

        # 随机调整市场趋势
        self.market.randomize_trends()

    def update_positions_price(self):
        """更新持仓的当前价格"""
        for code, pos in self.positions.items():
            try:
                stock = self.market.get_stock(code)
                pos.current_price = stock.price
            except ValueError:
                pass

    def get_total_assets(self) -> float:
        """总资产 = 现金 + 持仓市值"""
        self.update_positions_price()
        market_value = sum(pos.market_value for pos in self.positions.values())
        return self.account.total_cash + market_value

    def get_total_profit(self) -> float:
        """总盈亏"""
        return self.get_total_assets() - self.account.initial_capital

    def get_total_profit_pct(self) -> float:
        """总收益率(%)"""
        if self.account.initial_capital == 0:
            return 0.0
        return self.get_total_profit() / self.account.initial_capital * 100

    def max_buy_quantity(self, stock_code: str, price: float) -> int:
        """计算最大可买数量"""
        if price <= 0:
            return 0
        est_fee_rate = self.COMMISSION_RATE + self.TRANSFER_FEE_RATE
        max_amount = self.account.available_cash / (1 + est_fee_rate)
        max_shares = int(max_amount / price)
        return (max_shares // 100) * 100

    def _rejected_order(self, code, name, direction, price, qty, msg) -> Order:
        """创建被拒绝的订单"""
        order = Order(
            order_id=self._next_order_id,
            stock_code=code,
            stock_name=name,
            direction=direction,
            price=price,
            quantity=qty,
            status=OrderStatus.REJECTED,
            message=msg,
        )
        self._next_order_id += 1
        self.orders.append(order)
        return order
