"""入口文件 - 运行 python -m a_stock_simulator 启动模拟交易器"""

import argparse
from .cli import SimulatorCLI


def main():
    parser = argparse.ArgumentParser(description="A股模拟交易器")
    parser.add_argument(
        "--capital", "-c",
        type=float,
        default=1_000_000.0,
        help="初始资金(默认100万)",
    )
    args = parser.parse_args()

    cli = SimulatorCLI(initial_capital=args.capital)
    cli.run()


if __name__ == "__main__":
    main()
