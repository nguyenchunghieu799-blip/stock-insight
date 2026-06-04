#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""多策略回测框架

内置策略：MA金叉死叉 / MACD金叉死叉 / RSI超买超卖 / 布林带突破 /
        均线趋势 / 动量突破 / 双均线通道 / 网格交易

支持：参数网格优化、多策略对比、权益曲线、绩效指标
"""
import numpy as np
import pandas as pd
from datetime import datetime


# ═══════════════════════════════════════════
# 内置策略集
# ═══════════════════════════════════════════

def strategy_ma_cross(df, fast=5, slow=20):
    """MA 金叉死叉：快线上穿慢线买入，下穿卖出"""
    signals = pd.DataFrame(index=df.index)
    signals['signal'] = 0
    signals['MA_fast'] = df['收盘'].rolling(fast).mean()
    signals['MA_slow'] = df['收盘'].rolling(slow).mean()
    # 金叉
    cross_up = (signals['MA_fast'] > signals['MA_slow']) & (signals['MA_fast'].shift(1) <= signals['MA_slow'].shift(1))
    # 死叉
    cross_down = (signals['MA_fast'] < signals['MA_slow']) & (signals['MA_fast'].shift(1) >= signals['MA_slow'].shift(1))
    signals.loc[cross_up, 'signal'] = 1
    signals.loc[cross_down, 'signal'] = -1
    return signals


def strategy_macd_cross(df, fast=12, slow=26, sig=9):
    """MACD 金叉死叉：DIF上穿DEA买入，下穿卖出"""
    signals = pd.DataFrame(index=df.index)
    signals['signal'] = 0
    ema_fast = df['收盘'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['收盘'].ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=sig, adjust=False).mean()
    macd_bar = 2 * (dif - dea)
    signals['DIF'] = dif
    signals['DEA'] = dea
    signals['MACD'] = macd_bar
    cross_up = (dif > dea) & (dif.shift(1) <= dea.shift(1))
    cross_down = (dif < dea) & (dif.shift(1) >= dea.shift(1))
    signals.loc[cross_up, 'signal'] = 1
    signals.loc[cross_down, 'signal'] = -1
    return signals


def strategy_rsi_reversal(df, period=14, oversold=30, overbought=70):
    """RSI 均值回归：超卖买入，超买卖出"""
    signals = pd.DataFrame(index=df.index)
    signals['signal'] = 0
    delta = df['收盘'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    signals['RSI'] = rsi
    signals.loc[rsi < oversold, 'signal'] = 1
    signals.loc[rsi > overbought, 'signal'] = -1
    return signals


def strategy_bollinger_breakout(df, period=20, std=2):
    """布林带突破：跌破下轨买入，突破上轨卖出"""
    signals = pd.DataFrame(index=df.index)
    signals['signal'] = 0
    ma = df['收盘'].rolling(period).mean()
    std_dev = df['收盘'].rolling(period).std()
    signals['upper'] = ma + std * std_dev
    signals['lower'] = ma - std * std_dev
    signals['middle'] = ma
    signals.loc[df['收盘'] < signals['lower'], 'signal'] = 1
    signals.loc[df['收盘'] > signals['upper'], 'signal'] = -1
    return signals


def strategy_ma_trend(df, short=5, mid=20, long=60):
    """均线多头排列趋势：三线多头持有，空头清仓"""
    signals = pd.DataFrame(index=df.index)
    signals['signal'] = 0
    ma_s = df['收盘'].rolling(short).mean()
    ma_m = df['收盘'].rolling(mid).mean()
    ma_l = df['收盘'].rolling(long).mean()
    signals['MA_S'] = ma_s
    signals['MA_M'] = ma_m
    signals['MA_L'] = ma_l
    # 多头排列
    bull = (ma_s > ma_m) & (ma_m > ma_l)
    signals.loc[bull & ~bull.shift(1).fillna(False), 'signal'] = 1
    # 空头排列
    bear = (ma_s < ma_m) & (ma_m < ma_l)
    signals.loc[bear, 'signal'] = -1
    return signals


def strategy_momentum_breakout(df, lookback=20, atr_mult=2):
    """动量通道突破：突破N日最高买入，跌破N日最低卖出"""
    signals = pd.DataFrame(index=df.index)
    signals['signal'] = 0
    signals['high_n'] = df['最高'].rolling(lookback).max()
    signals['low_n'] = df['最低'].rolling(lookback).min()
    signals.loc[df['收盘'] > signals['high_n'].shift(1), 'signal'] = 1
    signals.loc[df['收盘'] < signals['low_n'].shift(1), 'signal'] = -1
    return signals


def strategy_grid(df, grid_pct=0.05, base_position=0.2):
    """网格交易：每跌grid_pct加仓，每涨grid_pct减仓"""
    signals = pd.DataFrame(index=df.index)
    signals['signal'] = 0
    base = df['收盘'].iloc[0]
    for i in range(1, len(df)):
        change = (df['收盘'].iloc[i] - base) / base
        if change < -grid_pct:
            signals.iloc[i, signals.columns.get_loc('signal')] = 1  # 买入
            base = df['收盘'].iloc[i]
        elif change > grid_pct:
            signals.iloc[i, signals.columns.get_loc('signal')] = -1  # 卖出
            base = df['收盘'].iloc[i]
    return signals


# ═══════════════════════════════════════════
# 策略注册表
# ═══════════════════════════════════════════

STRATEGIES = {
    'ma_cross': {
        'name': 'MA金叉死叉',
        'fn': strategy_ma_cross,
        'params': {'fast': [5, 10, 20], 'slow': [20, 30, 60]},
        'default': {'fast': 5, 'slow': 20},
    },
    'macd_cross': {
        'name': 'MACD金叉死叉',
        'fn': strategy_macd_cross,
        'params': {'fast': [12], 'slow': [26], 'sig': [9]},
        'default': {'fast': 12, 'slow': 26, 'sig': 9},
    },
    'rsi_reversal': {
        'name': 'RSI超买超卖',
        'fn': strategy_rsi_reversal,
        'params': {'period': [14], 'oversold': [25, 30, 35], 'overbought': [65, 70, 75]},
        'default': {'period': 14, 'oversold': 30, 'overbought': 70},
    },
    'bollinger': {
        'name': '布林带突破',
        'fn': strategy_bollinger_breakout,
        'params': {'period': [20], 'std': [2, 2.5]},
        'default': {'period': 20, 'std': 2},
    },
    'ma_trend': {
        'name': '均线多头趋势',
        'fn': strategy_ma_trend,
        'params': {'short': [5], 'mid': [10, 20], 'long': [30, 60]},
        'default': {'short': 5, 'mid': 20, 'long': 60},
    },
    'momentum_breakout': {
        'name': '动量通道突破',
        'fn': strategy_momentum_breakout,
        'params': {'lookback': [10, 20, 30]},
        'default': {'lookback': 20},
    },
    'grid': {
        'name': '网格交易',
        'fn': strategy_grid,
        'params': {'grid_pct': [0.03, 0.05, 0.08]},
        'default': {'grid_pct': 0.05},
    },
}


# ═══════════════════════════════════════════
# 回测引擎
# ═══════════════════════════════════════════

def run_backtest(df, strategy_fn, strategy_params=None, initial_capital=100000,
                 commission=0.0003, slippage=0.001, position_pct=1.0):
    """通用回测引擎

    参数:
        df: K线DataFrame（需含'收盘'列）
        strategy_fn: 策略函数，返回含'signal'列的DataFrame
        strategy_params: 策略参数字典
        initial_capital: 初始资金
        commission: 手续费率
        slippage: 滑点
        position_pct: 仓位比例

    返回:
        dict: {trades, equity_curve, metrics, summary}
    """
    if strategy_params is None:
        strategy_params = {}

    signals = strategy_fn(df, **strategy_params)
    if signals is None or signals.empty:
        return None

    # 模拟交易
    capital = initial_capital
    position = 0  # 持股数量
    trades = []
    equity = [capital]

    for i in range(len(df)):
        price = float(df['收盘'].iloc[i])
        sig = int(signals['signal'].iloc[i])

        if sig == 1 and position == 0:  # 买入
            max_shares = int(capital * position_pct / (price * (1 + slippage)))
            if max_shares > 0:
                cost = max_shares * price * (1 + slippage)
                commission_fee = cost * commission
                capital -= (cost + commission_fee)
                position = max_shares
                trades.append({
                    'date': str(df['日期'].iloc[i])[:10] if '日期' in df.columns else i,
                    'action': 'BUY', 'price': round(price, 2),
                    'shares': position, 'capital': round(capital, 2),
                })

        elif sig == -1 and position > 0:  # 卖出
            revenue = position * price * (1 - slippage)
            commission_fee = revenue * commission
            capital += (revenue - commission_fee)
            pnl = revenue - (trades[-1]['price'] * position if trades else 0) - commission_fee
            trades.append({
                'date': str(df['日期'].iloc[i])[:10] if '日期' in df.columns else i,
                'action': 'SELL', 'price': round(price, 2),
                'shares': 0, 'capital': round(capital, 2), 'pnl': round(pnl, 2),
            })
            position = 0

        # 权益曲线（含持仓市值）
        market_value = position * price
        equity.append(capital + market_value)

    # 清仓
    if position > 0:
        last_price = float(df['收盘'].iloc[-1])
        revenue = position * last_price * (1 - slippage)
        capital += (revenue - revenue * commission)
        position = 0

    # 绩效指标
    equity_series = pd.Series(equity)
    returns = equity_series.pct_change().dropna()

    total_return = (equity[-1] / initial_capital - 1) * 100
    n_trades = len([t for t in trades if t['action'] == 'SELL'])
    win_trades = len([t for t in trades if t['action'] == 'SELL' and t.get('pnl', 0) > 0])
    win_rate = (win_trades / n_trades * 100) if n_trades > 0 else 0

    # 夏普
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 0 and returns.std() > 0 else 0

    # 最大回撤
    peak = equity_series.expanding().max()
    drawdown = (equity_series - peak) / peak * 100
    max_dd = drawdown.min()

    # 盈亏比
    avg_win = np.mean([t['pnl'] for t in trades if t.get('pnl', 0) > 0]) if win_trades > 0 else 0
    avg_loss = abs(np.mean([t['pnl'] for t in trades if t.get('pnl', 0) < 0])) if (n_trades - win_trades) > 0 else 1
    profit_factor = avg_win / avg_loss if avg_loss > 0 else 0

    metrics = {
        '总收益率%': round(total_return, 2),
        '年化收益率%': round(total_return / max(len(df) / 252, 0.5), 2),
        '夏普比率': round(sharpe, 2),
        '最大回撤%': round(max_dd, 2),
        '交易次数': n_trades,
        '胜率%': round(win_rate, 1),
        '盈亏比': round(profit_factor, 2),
        '最终资金': round(equity[-1], 2),
    }

    return {
        'trades': trades,
        'equity_curve': equity,
        'metrics': metrics,
        'summary': f"收益率{total_return:.1f}% | 夏普{sharpe:.2f} | "
                   f"回撤{max_dd:.1f}% | 胜率{win_rate:.0f}% | 交易{n_trades}次",
    }


def compare_strategies(df, strategies=None, initial_capital=100000):
    """多策略对比回测"""
    if strategies is None:
        strategies = ['ma_cross', 'macd_cross', 'rsi_reversal', 'bollinger', 'ma_trend']

    results = {}
    for s_name in strategies:
        if s_name not in STRATEGIES:
            continue
        s_info = STRATEGIES[s_name]
        result = run_backtest(df, s_info['fn'], s_info['default'], initial_capital)
        if result:
            results[s_name] = {
                'name': s_info['name'],
                'metrics': result['metrics'],
                'summary': result['summary'],
            }

    return results


def optimize_strategy(df, strategy_name, param_grid=None):
    """策略参数网格优化"""
    if strategy_name not in STRATEGIES:
        return None

    s_info = STRATEGIES[strategy_name]
    if param_grid is None:
        param_grid = s_info['params']

    # 生成参数组合
    from itertools import product
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combinations = [dict(zip(keys, combo)) for combo in product(*values)]

    best = None
    best_sharpe = -999

    for params in combinations:
        result = run_backtest(df, s_info['fn'], params)
        if result and result['metrics']['夏普比率'] > best_sharpe:
            best_sharpe = result['metrics']['夏普比率']
            best = {'params': params, 'metrics': result['metrics'], 'summary': result['summary']}

    return best
