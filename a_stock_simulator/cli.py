"""命令行交互界面 - Interactive CLI for the A-share simulator."""

import os
import sys
import time
from typing import Optional

from .models import OrderDirection, OrderStatus
from .market import MarketEngine
from .trading import TradingEngine


# ANSI颜色
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def color_change(value: float, fmt: str = "+.2f") -> str:
    """根据涨跌显示红绿色"""
    if value > 0:
        return f"{RED}{value:{fmt}}{RESET}"
    elif value < 0:
        return f"{GREEN}{value:{fmt}}{RESET}"
    return f"{value:{fmt}}"


def color_pct(value: float) -> str:
    """涨跌幅着色"""
    s = f"{value:+.2f}%"
    if value > 0:
        return f"{RED}{s}{RESET}"
    elif value < 0:
        return f"{GREEN}{s}{RESET}"
    return s


class SimulatorCLI:
    """A股模拟交易器 命令行界面"""

    HELP_TEXT = f"""
{BOLD}═══════════════════ A股模拟交易器 帮助 ═══════════════════{RESET}

{CYAN}行情命令:{RESET}
  market / m          查看全部行情
  quote <代码> / q    查看个股详情 + 买卖五档
  search <关键字>     搜索股票(代码/名称)

{CYAN}交易命令:{RESET}
  buy <代码> <价格> <数量>   委托买入 (数量须为100的整数倍)
  sell <代码> <价格> <数量>  委托卖出
  cancel <订单号>            撤单

{CYAN}查询命令:{RESET}
  position / pos      查看持仓
  orders / od         查看委托记录
  trades / td         查看成交记录
  account / acc       查看资金账户
  summary             查看账户总览

{CYAN}模拟控制:{RESET}
  tick [N]            推进N个时间步 (默认1)
  next / nd           进入下一个交易日
  auto [N]            自动推进N步并显示行情变化

{CYAN}其他:{RESET}
  help / h            显示帮助
  clear / cls         清屏
  quit / exit / q!    退出

{DIM}提示: A股规则 - T+1(当日买入次日才能卖出), 买入须为100股整数倍{RESET}
{DIM}      沪深主板涨跌停±10%, 创业板/科创板涨跌停±20%{RESET}
"""

    def __init__(self, initial_capital: float = 1_000_000.0):
        self.market = MarketEngine()
        self.engine = TradingEngine(self.market, initial_capital)
        self.trading_day = 1

    def run(self):
        """主循环"""
        self._print_banner()
        while True:
            try:
                raw = input(f"\n{CYAN}[第{self.trading_day}日]{RESET} >> ").strip()
                if not raw:
                    continue
                parts = raw.split()
                cmd = parts[0].lower()
                args = parts[1:]
                self._dispatch(cmd, args)
            except KeyboardInterrupt:
                print("\n使用 quit 退出")
            except EOFError:
                break

    def _dispatch(self, cmd: str, args: list):
        """命令分发"""
        commands = {
            "help": self._cmd_help, "h": self._cmd_help,
            "market": self._cmd_market, "m": self._cmd_market,
            "quote": self._cmd_quote, "q": self._cmd_quote,
            "search": self._cmd_search,
            "buy": self._cmd_buy,
            "sell": self._cmd_sell,
            "cancel": self._cmd_cancel,
            "position": self._cmd_position, "pos": self._cmd_position,
            "orders": self._cmd_orders, "od": self._cmd_orders,
            "trades": self._cmd_trades, "td": self._cmd_trades,
            "account": self._cmd_account, "acc": self._cmd_account,
            "summary": self._cmd_summary,
            "tick": self._cmd_tick,
            "next": self._cmd_next_day, "nd": self._cmd_next_day,
            "auto": self._cmd_auto,
            "clear": self._cmd_clear, "cls": self._cmd_clear,
            "quit": self._cmd_quit, "exit": self._cmd_quit, "q!": self._cmd_quit,
        }

        handler = commands.get(cmd)
        if handler:
            try:
                handler(args)
            except Exception as e:
                print(f"{RED}错误: {e}{RESET}")
        else:
            print(f"未知命令: {cmd}, 输入 help 查看帮助")

    def _print_banner(self):
        """打印启动横幅"""
        capital = self.engine.account.initial_capital
        print(f"""
{BOLD}╔══════════════════════════════════════════════════════╗
║          A股模拟交易器 v1.0  (A-Share Simulator)     ║
║══════════════════════════════════════════════════════║
║  初始资金: {capital:>14,.2f} 元                      ║
║  股票数量: {len(self.market.stocks):>5} 只                                ║
║  输入 help 查看帮助                                  ║
╚══════════════════════════════════════════════════════╝{RESET}
""")

    # ─── 行情命令 ───

    def _cmd_help(self, args):
        print(self.HELP_TEXT)

    def _cmd_market(self, args):
        """查看全部行情"""
        stocks = self.market.get_all_stocks()
        # 按涨跌幅排序
        stocks.sort(key=lambda s: s.change_pct, reverse=True)

        print(f"\n{BOLD}{'代码':<10} {'名称':<10} {'最新价':>10} {'涨跌幅':>10} "
              f"{'涨跌额':>10} {'最高':>10} {'最低':>10} {'成交量(万手)':>12}{RESET}")
        print("─" * 92)

        for s in stocks:
            pct = color_pct(s.change_pct)
            chg = color_change(s.change)
            vol_wan = s.volume / 10000
            tag = ""
            if s.is_limit_up:
                tag = f" {RED}↑涨停{RESET}"
            elif s.is_limit_down:
                tag = f" {GREEN}↓跌停{RESET}"
            print(f"{s.full_code:<10} {s.name:<10} {s.price:>10.2f} {pct:>20} "
                  f"{chg:>20} {s.high:>10.2f} {s.low:>10.2f} {vol_wan:>12.1f}{tag}")

    def _cmd_quote(self, args):
        """个股详情"""
        if not args:
            print("用法: quote <股票代码>")
            return
        code = args[0]
        stock = self.market.get_stock(code)
        bid_ask = self.market.get_bid_ask(code)

        print(f"\n{BOLD}══ {stock.name} ({stock.full_code}) ══{RESET}")
        print(f"  最新价: {stock.price:.2f}   涨跌: {color_change(stock.change)} ({color_pct(stock.change_pct)})")
        print(f"  开盘: {stock.open_price:.2f}   昨收: {stock.prev_close:.2f}")
        print(f"  最高: {stock.high:.2f}   最低: {stock.low:.2f}")
        print(f"  成交量: {stock.volume:,} 股   成交额: {stock.amount:,.0f} 元")

        # 涨跌停价
        limit = 0.20 if code.startswith("3") or code.startswith("68") else 0.10
        up_limit = round(stock.prev_close * (1 + limit), 2)
        dn_limit = round(stock.prev_close * (1 - limit), 2)
        print(f"  涨停: {RED}{up_limit:.2f}{RESET}   跌停: {GREEN}{dn_limit:.2f}{RESET}")

        # 买卖五档
        print(f"\n  {BOLD}{'卖盘':>20}{'买盘':>24}{RESET}")
        print(f"  {'─' * 44}")
        asks = list(reversed(bid_ask["asks"]))
        bids = bid_ask["bids"]
        for i in range(5):
            a_price, a_vol = asks[i]
            b_price, b_vol = bids[i]
            a_label = f"卖{5-i}"
            b_label = f"买{i+1}"
            print(f"  {a_label} {RED}{a_price:>8.2f}{RESET} {a_vol:>6}   "
                  f"{b_label} {GREEN}{b_price:>8.2f}{RESET} {b_vol:>6}")

        # 如有持仓, 显示持仓信息
        pos = self.engine.positions.get(code)
        if pos:
            print(f"\n  {YELLOW}持仓: {pos.quantity}股 (可卖{pos.available}股) "
                  f"成本{pos.cost_price:.2f} 盈亏{color_change(pos.profit)}{RESET}")

    def _cmd_search(self, args):
        """搜索股票"""
        if not args:
            print("用法: search <关键字>")
            return
        keyword = " ".join(args)
        results = self.market.search(keyword)
        if not results:
            print(f"未找到匹配 '{keyword}' 的股票")
            return
        for s in results:
            print(f"  {s.full_code} {s.name:<8} {s.price:>10.2f} {color_pct(s.change_pct)}")

    # ─── 交易命令 ───

    def _cmd_buy(self, args):
        """买入"""
        if len(args) < 3:
            print("用法: buy <代码> <价格> <数量>")
            print("示例: buy 600519 1680.00 100")
            # 显示可买数量提示
            if len(args) >= 2:
                code, price = args[0], float(args[1])
                max_qty = self.engine.max_buy_quantity(code, price)
                print(f"  当前可买: {max_qty} 股")
            return

        code = args[0]
        price = float(args[1])
        qty = int(args[2])

        order = self.engine.buy(code, price, qty)
        self._print_order_result(order)

    def _cmd_sell(self, args):
        """卖出"""
        if len(args) < 3:
            print("用法: sell <代码> <价格> <数量>")
            pos = self.engine.positions.get(args[0]) if args else None
            if pos:
                print(f"  持仓: {pos.quantity}股, 可卖: {pos.available}股")
            return

        code = args[0]
        price = float(args[1])
        qty = int(args[2])

        order = self.engine.sell(code, price, qty)
        self._print_order_result(order)

    def _cmd_cancel(self, args):
        """撤单"""
        if not args:
            print("用法: cancel <订单号>")
            return
        order_id = int(args[0])
        if self.engine.cancel_order(order_id):
            print(f"订单 {order_id} 已撤单")
        else:
            print(f"撤单失败: 订单 {order_id} 不存在或无法撤销")

    def _print_order_result(self, order):
        """打印委托结果"""
        dir_str = order.direction.value
        if order.status == OrderStatus.FILLED:
            print(f"{GREEN}✓ 已成交{RESET} [{dir_str}] {order.stock_name}({order.stock_code}) "
                  f"{order.filled_quantity}股 @ {order.filled_price:.2f}")
            # 显示费用
            trade = self.engine.trades[-1]
            print(f"  金额: {trade.amount:,.2f}  "
                  f"佣金: {trade.commission:.2f}  "
                  f"印花税: {trade.stamp_tax:.2f}  "
                  f"过户费: {trade.transfer_fee:.2f}")
        elif order.status == OrderStatus.PENDING:
            print(f"{YELLOW}⏳ 已挂单{RESET} [{dir_str}] {order.stock_name}({order.stock_code}) "
                  f"{order.quantity}股 @ {order.price:.2f}  (订单号: {order.order_id})")
        elif order.status == OrderStatus.REJECTED:
            print(f"{RED}✗ 已拒绝{RESET} [{dir_str}] {order.stock_name}({order.stock_code}) "
                  f"原因: {order.message}")

    # ─── 查询命令 ───

    def _cmd_position(self, args):
        """持仓查询"""
        self.engine.update_positions_price()
        positions = self.engine.positions

        if not positions:
            print("当前无持仓")
            return

        print(f"\n{BOLD}{'代码':<10} {'名称':<10} {'数量':>8} {'可卖':>8} "
              f"{'成本价':>10} {'现价':>10} {'盈亏':>12} {'盈亏%':>10}{RESET}")
        print("─" * 88)

        total_value = 0
        total_profit = 0
        for pos in positions.values():
            profit_str = color_change(pos.profit, "+,.2f")
            pct_str = color_pct(pos.profit_pct)
            print(f"{pos.stock_code:<10} {pos.stock_name:<10} {pos.quantity:>8} {pos.available:>8} "
                  f"{pos.cost_price:>10.2f} {pos.current_price:>10.2f} {profit_str:>22} {pct_str:>20}")
            total_value += pos.market_value
            total_profit += pos.profit

        print("─" * 88)
        print(f"{'合计':<20} {'':>16} {'':>20} {f'市值: {total_value:,.2f}':>12} "
              f"{color_change(total_profit, '+,.2f'):>22}")

    def _cmd_orders(self, args):
        """委托记录"""
        orders = self.engine.orders
        if not orders:
            print("无委托记录")
            return

        # 最近20条
        recent = orders[-20:]
        print(f"\n{BOLD}{'ID':>5} {'方向':<6} {'代码':<10} {'名称':<10} "
              f"{'委托价':>10} {'数量':>8} {'成交价':>10} {'状态':<10}{RESET}")
        print("─" * 80)
        for o in recent:
            status_color = {
                OrderStatus.FILLED: GREEN,
                OrderStatus.REJECTED: RED,
                OrderStatus.PENDING: YELLOW,
                OrderStatus.CANCELLED: DIM,
            }.get(o.status, "")
            print(f"{o.order_id:>5} {o.direction.value:<6} {o.stock_code:<10} {o.stock_name:<10} "
                  f"{o.price:>10.2f} {o.quantity:>8} {o.filled_price:>10.2f} "
                  f"{status_color}{o.status.value:<10}{RESET}")
            if o.message:
                print(f"      {DIM}{o.message}{RESET}")

    def _cmd_trades(self, args):
        """成交记录"""
        trades = self.engine.trades
        if not trades:
            print("无成交记录")
            return

        recent = trades[-20:]
        print(f"\n{BOLD}{'ID':>5} {'方向':<6} {'代码':<10} {'名称':<10} "
              f"{'成交价':>10} {'数量':>8} {'金额':>14} {'费用':>10}{RESET}")
        print("─" * 84)
        for t in recent:
            print(f"{t.trade_id:>5} {t.direction.value:<6} {t.stock_code:<10} {t.stock_name:<10} "
                  f"{t.price:>10.2f} {t.quantity:>8} {t.amount:>14,.2f} {t.total_cost:>10.2f}")

    def _cmd_account(self, args):
        """资金账户"""
        acc = self.engine.account
        total = self.engine.get_total_assets()
        profit = self.engine.get_total_profit()
        profit_pct = self.engine.get_total_profit_pct()

        market_value = sum(p.market_value for p in self.engine.positions.values())

        print(f"\n{BOLD}══ 资金账户 ══{RESET}")
        print(f"  初始资金:   {acc.initial_capital:>16,.2f}")
        print(f"  可用资金:   {acc.available_cash:>16,.2f}")
        print(f"  冻结资金:   {acc.frozen_cash:>16,.2f}")
        print(f"  持仓市值:   {market_value:>16,.2f}")
        print(f"  ─────────────────────────────")
        print(f"  总资产:     {total:>16,.2f}")
        print(f"  总盈亏:     {color_change(profit, '>+16,.2f')}")
        print(f"  收益率:     {color_pct(profit_pct)}")

    def _cmd_summary(self, args):
        """账户总览"""
        self._cmd_account(args)
        print()
        self._cmd_position(args)

    # ─── 模拟控制 ───

    def _cmd_tick(self, args):
        """推进时间步"""
        n = int(args[0]) if args else 1
        for _ in range(n):
            self.market.tick()
            self.engine.try_match_pending()
        self.engine.update_positions_price()
        print(f"已推进 {n} 步")

    def _cmd_next_day(self, args):
        """下一交易日"""
        # 推进若干tick模拟当日剩余行情
        for _ in range(20):
            self.market.tick()
            self.engine.try_match_pending()

        self.trading_day += 1
        self.engine.new_trading_day()
        print(f"\n{BOLD}═══ 第 {self.trading_day} 个交易日 ═══{RESET}")
        print("T+1限制已重置, 昨日买入股票今日可卖出")
        self._cmd_account([])

    def _cmd_auto(self, args):
        """自动推进并显示"""
        n = int(args[0]) if args else 10
        for i in range(n):
            self.market.tick()
            self.engine.try_match_pending()
        self.engine.update_positions_price()
        print(f"已自动推进 {n} 步")
        self._cmd_market([])

    def _cmd_clear(self, args):
        os.system("clear" if os.name != "nt" else "cls")

    def _cmd_quit(self, args):
        print("\n再见! 投资有风险, 入市需谨慎!")
        sys.exit(0)
