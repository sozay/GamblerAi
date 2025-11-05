"""
Performance metrics calculator for backtesting.
"""

from typing import List, Dict
import numpy as np
import pandas as pd
from datetime import datetime

from gambler_ai.backtesting.trade import Trade


class PerformanceMetrics:
    """Calculate performance metrics for backtesting results."""

    def __init__(self, trades: List[Trade], initial_capital: float, final_capital: float):
        """
        Initialize performance calculator.

        Args:
            trades: List of closed trades
            initial_capital: Starting capital
            final_capital: Ending capital
        """
        self.trades = trades
        self.initial_capital = initial_capital
        self.final_capital = final_capital

        self.winning_trades = [t for t in trades if t.pnl > 0]
        self.losing_trades = [t for t in trades if t.pnl <= 0]

    def calculate_all_metrics(self) -> Dict:
        """Calculate all performance metrics."""
        if not self.trades:
            return {
                "error": "No trades to analyze",
                "total_trades": 0,
            }

        metrics = {
            # Basic metrics
            "total_trades": len(self.trades),
            "winning_trades": len(self.winning_trades),
            "losing_trades": len(self.losing_trades),

            # P&L metrics
            "total_pnl": self.calculate_total_pnl(),
            "total_return_pct": self.calculate_total_return_pct(),
            "avg_trade_pnl": self.calculate_avg_trade_pnl(),
            "avg_trade_return_pct": self.calculate_avg_trade_return_pct(),

            # Win rate
            "win_rate": self.calculate_win_rate(),
            "win_rate_pct": self.calculate_win_rate() * 100,

            # Risk metrics
            "profit_factor": self.calculate_profit_factor(),
            "avg_win": self.calculate_avg_win(),
            "avg_loss": self.calculate_avg_loss(),
            "avg_win_loss_ratio": self.calculate_avg_win_loss_ratio(),
            "largest_win": self.calculate_largest_win(),
            "largest_loss": self.calculate_largest_loss(),

            # Drawdown
            "max_drawdown_pct": self.calculate_max_drawdown(),
            "max_consecutive_losses": self.calculate_max_consecutive_losses(),
            "max_consecutive_wins": self.calculate_max_consecutive_wins(),

            # Risk-adjusted returns
            "sharpe_ratio": self.calculate_sharpe_ratio(),
            "sortino_ratio": self.calculate_sortino_ratio(),

            # Trade duration
            "avg_trade_duration_minutes": self.calculate_avg_trade_duration(),
            "avg_winning_duration_minutes": self.calculate_avg_winning_duration(),
            "avg_losing_duration_minutes": self.calculate_avg_losing_duration(),

            # Excursion metrics
            "avg_mae": self.calculate_avg_mae(),  # Max Adverse Excursion
            "avg_mfe": self.calculate_avg_mfe(),  # Max Favorable Excursion

            # Capital metrics
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
        }

        # Add score (overall quality score 0-100)
        metrics["performance_score"] = self.calculate_performance_score(metrics)

        return metrics

    def calculate_total_pnl(self) -> float:
        """Calculate total P&L."""
        return sum(trade.pnl for trade in self.trades)

    def calculate_total_return_pct(self) -> float:
        """Calculate total return percentage."""
        return (self.final_capital - self.initial_capital) / self.initial_capital * 100

    def calculate_avg_trade_pnl(self) -> float:
        """Calculate average P&L per trade."""
        if not self.trades:
            return 0.0
        return sum(trade.pnl for trade in self.trades) / len(self.trades)

    def calculate_avg_trade_return_pct(self) -> float:
        """Calculate average return % per trade."""
        if not self.trades:
            return 0.0
        return sum(trade.return_pct for trade in self.trades) / len(self.trades)

    def calculate_win_rate(self) -> float:
        """Calculate win rate (0-1)."""
        if not self.trades:
            return 0.0
        return len(self.winning_trades) / len(self.trades)

    def calculate_profit_factor(self) -> float:
        """
        Calculate profit factor (gross profit / gross loss).

        Values:
        - > 2.0: Excellent
        - 1.5-2.0: Good
        - 1.0-1.5: Acceptable
        - < 1.0: Losing strategy
        """
        gross_profit = sum(t.pnl for t in self.winning_trades)
        gross_loss = abs(sum(t.pnl for t in self.losing_trades))

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    def calculate_avg_win(self) -> float:
        """Calculate average winning trade."""
        if not self.winning_trades:
            return 0.0
        return sum(t.pnl for t in self.winning_trades) / len(self.winning_trades)

    def calculate_avg_loss(self) -> float:
        """Calculate average losing trade."""
        if not self.losing_trades:
            return 0.0
        return sum(t.pnl for t in self.losing_trades) / len(self.losing_trades)

    def calculate_avg_win_loss_ratio(self) -> float:
        """Calculate average win / average loss ratio."""
        avg_win = abs(self.calculate_avg_win())
        avg_loss = abs(self.calculate_avg_loss())

        if avg_loss == 0:
            return float('inf') if avg_win > 0 else 0.0

        return avg_win / avg_loss

    def calculate_largest_win(self) -> float:
        """Get largest winning trade."""
        if not self.winning_trades:
            return 0.0
        return max(t.pnl for t in self.winning_trades)

    def calculate_largest_loss(self) -> float:
        """Get largest losing trade."""
        if not self.losing_trades:
            return 0.0
        return min(t.pnl for t in self.losing_trades)

    def calculate_max_drawdown(self) -> float:
        """
        Calculate maximum drawdown percentage.

        Drawdown = (Peak - Trough) / Peak * 100
        """
        if not self.trades:
            return 0.0

        # Build equity curve
        equity = self.initial_capital
        equity_curve = [equity]

        for trade in sorted(self.trades, key=lambda t: t.exit_time):
            equity += trade.pnl
            equity_curve.append(equity)

        # Calculate drawdown
        peak = equity_curve[0]
        max_dd = 0.0

        for value in equity_curve:
            if value > peak:
                peak = value

            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def calculate_max_consecutive_losses(self) -> int:
        """Calculate maximum consecutive losing trades."""
        if not self.trades:
            return 0

        max_consecutive = 0
        current_consecutive = 0

        for trade in sorted(self.trades, key=lambda t: t.exit_time):
            if trade.pnl <= 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def calculate_max_consecutive_wins(self) -> int:
        """Calculate maximum consecutive winning trades."""
        if not self.trades:
            return 0

        max_consecutive = 0
        current_consecutive = 0

        for trade in sorted(self.trades, key=lambda t: t.exit_time):
            if trade.pnl > 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sharpe ratio (annualized).

        Sharpe = (Return - RiskFreeRate) / StdDev

        Values:
        - > 2.0: Excellent
        - 1.0-2.0: Good
        - 0.5-1.0: Acceptable
        - < 0.5: Poor
        """
        if not self.trades:
            return 0.0

        # Get returns
        returns = [t.return_pct / 100 for t in self.trades]

        if len(returns) < 2:
            return 0.0

        # Calculate metrics
        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # Annualize (assume ~250 trading days)
        # If avg trade is 1 day, we have 250 trades/year
        avg_duration_days = self.calculate_avg_trade_duration() / (60 * 24)  # Convert minutes to days
        if avg_duration_days == 0:
            avg_duration_days = 1

        trades_per_year = 250 / avg_duration_days

        sharpe = (avg_return - (risk_free_rate / trades_per_year)) / std_return
        annualized_sharpe = sharpe * np.sqrt(trades_per_year)

        return annualized_sharpe

    def calculate_sortino_ratio(self, risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sortino ratio (like Sharpe but only penalizes downside volatility).
        """
        if not self.trades:
            return 0.0

        returns = [t.return_pct / 100 for t in self.trades]

        if len(returns) < 2:
            return 0.0

        avg_return = np.mean(returns)

        # Calculate downside deviation (only negative returns)
        negative_returns = [r for r in returns if r < 0]
        if not negative_returns:
            return float('inf') if avg_return > 0 else 0.0

        downside_std = np.std(negative_returns)

        if downside_std == 0:
            return 0.0

        avg_duration_days = self.calculate_avg_trade_duration() / (60 * 24)
        if avg_duration_days == 0:
            avg_duration_days = 1
        trades_per_year = 250 / avg_duration_days

        sortino = (avg_return - (risk_free_rate / trades_per_year)) / downside_std
        annualized_sortino = sortino * np.sqrt(trades_per_year)

        return annualized_sortino

    def calculate_avg_trade_duration(self) -> float:
        """Calculate average trade duration in minutes."""
        if not self.trades:
            return 0.0

        durations = []
        for trade in self.trades:
            if trade.entry_time and trade.exit_time:
                duration = (trade.exit_time - trade.entry_time).total_seconds() / 60
                durations.append(duration)

        return np.mean(durations) if durations else 0.0

    def calculate_avg_winning_duration(self) -> float:
        """Calculate average winning trade duration."""
        if not self.winning_trades:
            return 0.0

        durations = [
            (t.exit_time - t.entry_time).total_seconds() / 60
            for t in self.winning_trades
            if t.entry_time and t.exit_time
        ]

        return np.mean(durations) if durations else 0.0

    def calculate_avg_losing_duration(self) -> float:
        """Calculate average losing trade duration."""
        if not self.losing_trades:
            return 0.0

        durations = [
            (t.exit_time - t.entry_time).total_seconds() / 60
            for t in self.losing_trades
            if t.entry_time and t.exit_time
        ]

        return np.mean(durations) if durations else 0.0

    def calculate_avg_mae(self) -> float:
        """Calculate average Maximum Adverse Excursion."""
        if not self.trades:
            return 0.0
        return np.mean([abs(t.max_adverse_excursion) for t in self.trades])

    def calculate_avg_mfe(self) -> float:
        """Calculate average Maximum Favorable Excursion."""
        if not self.trades:
            return 0.0
        return np.mean([t.max_favorable_excursion for t in self.trades])

    def calculate_performance_score(self, metrics: Dict) -> float:
        """
        Calculate overall performance score (0-100).

        Weighted scoring:
        - Win Rate (20 points): 60%+ = full points
        - Profit Factor (25 points): 2.0+ = full points
        - Sharpe Ratio (25 points): 2.0+ = full points
        - Max Drawdown (20 points): <10% = full points
        - Total Return (10 points): >20% = full points
        """
        score = 0.0

        # Win rate score (20 points)
        win_rate = metrics.get("win_rate", 0)
        score += min(win_rate / 0.60, 1.0) * 20

        # Profit factor score (25 points)
        profit_factor = metrics.get("profit_factor", 0)
        if profit_factor != float('inf'):
            score += min(profit_factor / 2.0, 1.0) * 25
        else:
            score += 25

        # Sharpe ratio score (25 points)
        sharpe = metrics.get("sharpe_ratio", 0)
        score += min(max(sharpe, 0) / 2.0, 1.0) * 25

        # Drawdown score (20 points) - inverse scoring
        max_dd = metrics.get("max_drawdown_pct", 0)
        dd_score = max(1.0 - (max_dd / 20.0), 0)  # 20%+ DD = 0 points
        score += dd_score * 20

        # Return score (10 points)
        total_return = metrics.get("total_return_pct", 0)
        score += min(total_return / 20.0, 1.0) * 10

        return round(score, 1)

    def generate_report(self) -> str:
        """Generate a formatted performance report."""
        metrics = self.calculate_all_metrics()

        report = """
╔══════════════════════════════════════════════════════════════╗
║           BACKTEST PERFORMANCE REPORT                        ║
╚══════════════════════════════════════════════════════════════╝

═══ OVERALL METRICS ═══
Performance Score:      {performance_score}/100
Total Return:           {total_return_pct:.2f}%
Total P&L:             ${total_pnl:,.2f}
Initial Capital:       ${initial_capital:,.2f}
Final Capital:         ${final_capital:,.2f}

═══ TRADE STATISTICS ═══
Total Trades:          {total_trades}
Winning Trades:        {winning_trades} ({win_rate_pct:.1f}%)
Losing Trades:         {losing_trades}
Win Rate:              {win_rate_pct:.1f}%

═══ PROFITABILITY ═══
Profit Factor:         {profit_factor:.2f}
Avg Trade P&L:        ${avg_trade_pnl:.2f}
Avg Trade Return:      {avg_trade_return_pct:.2f}%
Avg Win:              ${avg_win:.2f}
Avg Loss:             ${avg_loss:.2f}
Win/Loss Ratio:        {avg_win_loss_ratio:.2f}
Largest Win:          ${largest_win:.2f}
Largest Loss:         ${largest_loss:.2f}

═══ RISK METRICS ═══
Max Drawdown:          {max_drawdown_pct:.2f}%
Sharpe Ratio:          {sharpe_ratio:.2f}
Sortino Ratio:         {sortino_ratio:.2f}
Max Consecutive Wins:  {max_consecutive_wins}
Max Consecutive Loss:  {max_consecutive_losses}

═══ TRADE DURATION ═══
Avg Duration:          {avg_trade_duration_minutes:.1f} minutes
Avg Win Duration:      {avg_winning_duration_minutes:.1f} minutes
Avg Loss Duration:     {avg_losing_duration_minutes:.1f} minutes

═══ EXCURSION ANALYSIS ═══
Avg MAE (Adverse):     {avg_mae:.2f}%
Avg MFE (Favorable):   {avg_mfe:.2f}%

═══ RATING ═══
""".format(**metrics)

        # Add rating
        score = metrics["performance_score"]
        if score >= 80:
            rating = "⭐⭐⭐⭐⭐ EXCELLENT"
        elif score >= 70:
            rating = "⭐⭐⭐⭐ VERY GOOD"
        elif score >= 60:
            rating = "⭐⭐⭐ GOOD"
        elif score >= 50:
            rating = "⭐⭐ ACCEPTABLE"
        else:
            rating = "⭐ NEEDS IMPROVEMENT"

        report += f"Strategy Rating:       {rating}\n"

        return report
