"""
Example: How to integrate SessionRecorder into your trading script.

This example shows how to add recording capabilities to the alpaca_paper_trading.py script.
"""

from datetime import datetime, timezone
from gambler_ai.trading.session_recorder import SessionRecorder
from gambler_ai.storage.database import get_db_session


# ============================================================================
# STEP 1: Initialize the recorder at the start of your trading session
# ============================================================================

def initialize_recorder(session_id, instance_id, strategy_name, config):
    """
    Initialize the session recorder.

    Args:
        session_id: Current trading session ID
        instance_id: Instance number (1-5)
        strategy_name: Name of the strategy being used
        config: Strategy configuration dictionary

    Returns:
        SessionRecorder instance or None if recording is disabled
    """
    # Check if recording is enabled in config
    enable_recording = config.get('enable_recording', False)

    if not enable_recording:
        return None

    db = next(get_db_session())

    # Extract strategy parameters for recording
    strategy_params = {
        'rsi_threshold': config.get('rsi_threshold', 30),
        'bb_std': config.get('bb_std', 2.5),
        'position_size': config.get('position_size', 10),
        'stop_loss_pct': config.get('stop_loss_pct', 1.0),
        'take_profit_pct': config.get('take_profit_pct', 0.5),
        'max_positions': config.get('max_positions', 3),
        # Add any other relevant parameters
    }

    symbols = config.get('symbols', [])

    recorder = SessionRecorder(
        db_session=db,
        trading_session_id=session_id,
        instance_id=instance_id,
        strategy_name=strategy_name,
        strategy_parameters=strategy_params,
        symbols=symbols,
    )

    print(f"Recording started: {recorder.recording_id}")
    return recorder


# ============================================================================
# STEP 2: Record market data in your trading loop
# ============================================================================

def process_market_data(recorder, symbol, bar, indicators):
    """
    Process a market data bar and record it.

    Args:
        recorder: SessionRecorder instance (or None)
        symbol: Stock symbol
        bar: Market data bar with OHLCV
        indicators: Calculated technical indicators
    """
    if recorder is None:
        return

    recorder.record_market_data(
        symbol=symbol,
        timestamp=bar.timestamp if hasattr(bar, 'timestamp') else datetime.now(timezone.utc),
        open_price=float(bar.open),
        high=float(bar.high),
        low=float(bar.low),
        close=float(bar.close),
        volume=int(bar.volume),
        indicators={
            'rsi': indicators.get('rsi', None),
            'bb_upper': indicators.get('bb_upper', None),
            'bb_middle': indicators.get('bb_middle', None),
            'bb_lower': indicators.get('bb_lower', None),
            'atr': indicators.get('atr', None),
            'volume_ratio': indicators.get('volume_ratio', None),
        }
    )


# ============================================================================
# STEP 3: Record signal detection with full context
# ============================================================================

def handle_signal_detection(recorder, signal, indicators):
    """
    Record when a trading signal is detected.

    Args:
        recorder: SessionRecorder instance (or None)
        signal: Detected signal dictionary
        indicators: Current indicator values
    """
    if recorder is None:
        return

    # Build reasoning string
    reasons = []
    if indicators.get('rsi', 100) < 30:
        reasons.append(f"RSI oversold ({indicators['rsi']:.1f})")
    if signal['entry_price'] < indicators.get('bb_lower', 0):
        reasons.append(f"Price below BB lower ({indicators['bb_lower']:.2f})")
    if indicators.get('volume_ratio', 0) > 3:
        reasons.append(f"High volume ({indicators['volume_ratio']:.1f}x avg)")

    reasoning = "; ".join(reasons)

    recorder.record_signal_detected(
        symbol=signal['symbol'],
        signal_type=signal['type'],
        entry_price=signal['entry_price'],
        stop_loss=signal['stop_loss'],
        take_profit=signal['take_profit'],
        indicators=indicators,
        signal_strength=signal.get('strength', 0.5),
        reasoning=reasoning,
    )


# ============================================================================
# STEP 4: Record order placement and fills
# ============================================================================

def handle_order_placed(recorder, symbol, order):
    """
    Record when an order is placed.

    Args:
        recorder: SessionRecorder instance (or None)
        symbol: Stock symbol
        order: Alpaca order object
    """
    if recorder is None:
        return

    recorder.record_order_placed(
        symbol=symbol,
        order_id=order.id,
        order_type=order.type,
        side=order.side,
        quantity=int(order.qty),
        price=float(order.limit_price) if order.limit_price else None,
    )


def handle_order_filled(recorder, symbol, order):
    """
    Record when an order is filled.

    Args:
        recorder: SessionRecorder instance (or None)
        symbol: Stock symbol
        order: Alpaca order object with fill information
    """
    if recorder is None:
        return

    recorder.record_order_filled(
        symbol=symbol,
        order_id=order.id,
        filled_qty=int(order.filled_qty),
        filled_price=float(order.filled_avg_price),
    )


# ============================================================================
# STEP 5: Record position lifecycle
# ============================================================================

def handle_position_opened(recorder, position):
    """
    Record when a position is opened.

    Args:
        recorder: SessionRecorder instance (or None)
        position: Position object
    """
    if recorder is None:
        return

    recorder.record_position_opened(
        symbol=position.symbol,
        entry_price=position.entry_price,
        quantity=position.qty,
        direction=position.direction,
        stop_loss=position.stop_loss,
        take_profit=position.take_profit,
    )


def handle_position_closed(recorder, position):
    """
    Record when a position is closed.

    Args:
        recorder: SessionRecorder instance (or None)
        position: Position object with exit information
    """
    if recorder is None:
        return

    duration = int((position.exit_time - position.entry_time).total_seconds())

    recorder.record_position_closed(
        symbol=position.symbol,
        exit_price=position.exit_price,
        quantity=position.qty,
        exit_reason=position.exit_reason,
        pnl=position.pnl,
        pnl_pct=position.pnl_pct,
        duration_seconds=duration,
    )


# ============================================================================
# STEP 6: Record scan cycles
# ============================================================================

def handle_scan_cycle(recorder, scan_number, symbols):
    """
    Record completion of a scan cycle.

    Args:
        recorder: SessionRecorder instance (or None)
        scan_number: Scan cycle number
        symbols: List of symbols scanned
    """
    if recorder is None:
        return

    recorder.record_scan_cycle(
        scan_number=scan_number,
        symbols_scanned=symbols,
    )


# ============================================================================
# STEP 7: Stop recording and save summary
# ============================================================================

def finalize_recording(recorder, session_stats):
    """
    Stop recording and save summary statistics.

    Args:
        recorder: SessionRecorder instance (or None)
        session_stats: Dictionary with session statistics
    """
    if recorder is None:
        return

    # Update summary stats
    recorder.update_summary_stats(
        total_trades=session_stats.get('total_trades', 0),
        total_pnl=session_stats.get('total_pnl', 0),
        win_rate=session_stats.get('win_rate', 0),
    )

    # Stop recording with description
    recorder.stop_recording(
        description=f"Instance {session_stats.get('instance_id')} session",
        tags=['paper_trading', session_stats.get('strategy_name', 'unknown')],
    )

    print(f"Recording completed: {recorder.recording_id}")
    print(f"Recorded {recorder.market_data_sequence} bars and {recorder.event_sequence} events")


# ============================================================================
# EXAMPLE: Full integration in trading script
# ============================================================================

def example_trading_script():
    """
    Example showing full integration in a trading script.
    """
    # Configuration
    config = {
        'enable_recording': True,  # Enable/disable recording
        'instance_id': 1,
        'strategy_name': 'Mean Reversion + Relative Strength',
        'symbols': ['AAPL', 'MSFT', 'GOOGL'],
        'rsi_threshold': 30,
        'bb_std': 2.5,
        'position_size': 10,
    }

    session_id = "example-session-id"

    # Step 1: Initialize recorder
    recorder = initialize_recorder(
        session_id=session_id,
        instance_id=config['instance_id'],
        strategy_name=config['strategy_name'],
        config=config,
    )

    try:
        # Trading loop
        scan_number = 0
        while True:
            scan_number += 1

            # Get market data for all symbols
            for symbol in config['symbols']:
                # Fetch bar data (example)
                bar = fetch_market_data(symbol)  # Your data fetching logic

                # Calculate indicators (example)
                indicators = calculate_indicators(bar)  # Your indicator logic

                # Step 2: Record market data
                process_market_data(recorder, symbol, bar, indicators)

                # Check for signals (example)
                signal = detect_signal(symbol, bar, indicators)  # Your signal logic

                if signal:
                    # Step 3: Record signal
                    handle_signal_detection(recorder, signal, indicators)

                    # Place order (example)
                    order = place_order(signal)  # Your order logic

                    # Step 4: Record order
                    handle_order_placed(recorder, symbol, order)

                    # Wait for fill and record
                    filled_order = wait_for_fill(order)
                    handle_order_filled(recorder, symbol, filled_order)

                    # Step 5: Record position opened
                    position = create_position(filled_order)
                    handle_position_opened(recorder, position)

            # Check existing positions for exits
            for position in get_active_positions():
                if should_close_position(position):
                    close_position(position)
                    # Step 5: Record position closed
                    handle_position_closed(recorder, position)

            # Step 6: Record scan cycle
            handle_scan_cycle(recorder, scan_number, config['symbols'])

            # Sleep until next scan
            time.sleep(60)

    except KeyboardInterrupt:
        print("Stopping trading...")
    finally:
        # Step 7: Finalize recording
        session_stats = {
            'instance_id': config['instance_id'],
            'strategy_name': config['strategy_name'],
            'total_trades': get_total_trades(),
            'total_pnl': get_total_pnl(),
            'win_rate': get_win_rate(),
        }
        finalize_recording(recorder, session_stats)


# ============================================================================
# Helper functions (placeholders - implement based on your system)
# ============================================================================

def fetch_market_data(symbol):
    """Fetch latest market data bar."""
    pass

def calculate_indicators(bar):
    """Calculate technical indicators."""
    pass

def detect_signal(symbol, bar, indicators):
    """Detect trading signals."""
    pass

def place_order(signal):
    """Place order with broker."""
    pass

def wait_for_fill(order):
    """Wait for order to be filled."""
    pass

def create_position(order):
    """Create position object from filled order."""
    pass

def get_active_positions():
    """Get all active positions."""
    pass

def should_close_position(position):
    """Check if position should be closed."""
    pass

def close_position(position):
    """Close position."""
    pass

def get_total_trades():
    """Get total number of trades."""
    return 0

def get_total_pnl():
    """Get total P&L."""
    return 0

def get_win_rate():
    """Get win rate."""
    return 0


if __name__ == '__main__':
    example_trading_script()
