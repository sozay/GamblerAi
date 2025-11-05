"""
Command-line interface for analysts to run analysis tasks.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import click

from gambler_ai.analysis import MomentumDetector, PatternAnalyzer, StatisticsEngine
from gambler_ai.data_ingestion import DataValidator, HistoricalDataCollector
from gambler_ai.storage import init_databases
from gambler_ai.utils.config import get_config
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


@click.group()
def cli():
    """GamblerAI CLI - Stock momentum analysis tools for analysts."""
    pass


@cli.command()
def init_db():
    """Initialize databases and create tables."""
    click.echo("Initializing databases...")
    try:
        init_databases()
        click.echo("✓ Databases initialized successfully")
    except Exception as e:
        click.echo(f"✗ Error initializing databases: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--symbol",
    "-s",
    help="Stock symbol (e.g., AAPL). Use --symbols for multiple.",
)
@click.option(
    "--symbols",
    help="Comma-separated list of stock symbols (e.g., AAPL,MSFT,GOOGL)",
)
@click.option(
    "--start",
    required=True,
    help="Start date (YYYY-MM-DD)",
)
@click.option(
    "--end",
    help="End date (YYYY-MM-DD). Default: today",
)
@click.option(
    "--timeframe",
    "-t",
    default="5min",
    help="Timeframe (1min, 5min, 15min, 1hour, 1day). Default: 5min",
)
@click.option(
    "--interval",
    "-i",
    default="5m",
    help="Yahoo Finance interval (1m, 5m, 15m, 1h, 1d). Default: 5m",
)
def collect(symbol, symbols, start, end, timeframe, interval):
    """
    Collect historical stock price data.

    Examples:
        gambler-cli collect --symbol AAPL --start 2024-01-01 --end 2024-12-31

        gambler-cli collect --symbols AAPL,MSFT,GOOGL --start 2024-01-01
    """
    try:
        # Parse symbols
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
        elif symbol:
            symbol_list = [symbol.upper()]
        else:
            click.echo("Error: Must provide --symbol or --symbols", err=True)
            sys.exit(1)

        # Parse dates
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d") if end else datetime.now()

        click.echo(f"Collecting data for {len(symbol_list)} symbols...")
        click.echo(f"Date range: {start_date.date()} to {end_date.date()}")
        click.echo(f"Interval: {interval}")

        collector = HistoricalDataCollector()
        stats = collector.collect_and_save(
            symbols=symbol_list,
            start_date=start_date,
            end_date=end_date,
            intervals=[interval],
        )

        click.echo(f"\n✓ Collection complete!")
        click.echo(f"  Symbols processed: {stats['symbols_processed']}")
        click.echo(f"  Total rows saved: {stats['total_rows']}")

        if stats["errors"]:
            click.echo(f"\n⚠ Errors encountered: {len(stats['errors'])}")
            for error in stats["errors"]:
                click.echo(f"  - {error}")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        logger.error(f"Collection error: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option("--symbol", "-s", required=True, help="Stock symbol")
@click.option("--start", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end", help="End date (YYYY-MM-DD). Default: today")
@click.option(
    "--timeframe", "-t", default="5min", help="Timeframe. Default: 5min"
)
@click.option(
    "--threshold",
    default=2.0,
    help="Minimum price change percentage. Default: 2.0",
)
def detect_momentum(symbol, start, end, timeframe, threshold):
    """
    Detect momentum events for a symbol.

    Example:
        gambler-cli detect-momentum --symbol AAPL --start 2024-01-01 --threshold 2.5
    """
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d") if end else datetime.now()

        click.echo(f"Detecting momentum events for {symbol.upper()}...")
        click.echo(f"Date range: {start_date.date()} to {end_date.date()}")
        click.echo(f"Threshold: {threshold}%")

        detector = MomentumDetector()
        detector.min_price_change_pct = threshold  # Override config

        events = detector.detect_events(
            symbol=symbol.upper(),
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            save_to_db=True,
        )

        click.echo(f"\n✓ Detection complete!")
        click.echo(f"  Events detected: {len(events)}")

        if events:
            # Show sample events
            click.echo(f"\nSample events:")
            for event in events[:5]:
                click.echo(
                    f"  {event['start_time']} | {event['direction']} | "
                    f"{event['max_move_percentage']:.2f}%"
                )

            if len(events) > 5:
                click.echo(f"  ... and {len(events) - 5} more")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        logger.error(f"Detection error: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option("--symbol", "-s", help="Filter by symbol (optional)")
@click.option(
    "--timeframe", "-t", help="Filter by timeframe (optional)"
)
@click.option(
    "--min-samples",
    default=100,
    help="Minimum samples for pattern. Default: 100",
)
@click.option(
    "--output",
    "-o",
    help="Output file path (JSON)",
)
def analyze_patterns(symbol, timeframe, min_samples, output):
    """
    Analyze momentum patterns from detected events.

    Example:
        gambler-cli analyze-patterns --symbol AAPL --min-samples 50

        gambler-cli analyze-patterns --output patterns.json
    """
    try:
        click.echo("Analyzing patterns...")

        if symbol:
            click.echo(f"  Symbol: {symbol.upper()}")
        if timeframe:
            click.echo(f"  Timeframe: {timeframe}")
        click.echo(f"  Minimum samples: {min_samples}")

        analyzer = PatternAnalyzer()
        patterns = analyzer.analyze_patterns(
            symbol=symbol.upper() if symbol else None,
            timeframe=timeframe,
            min_samples=min_samples,
        )

        if not patterns:
            click.echo("\n⚠ No patterns found matching criteria")
            return

        # Save patterns to database
        analyzer.save_pattern_statistics(patterns)

        click.echo(f"\n✓ Analysis complete!")
        click.echo(f"  Patterns found: {len(patterns)}")

        # Display summary
        click.echo(f"\nPattern Summary:")
        for pattern in patterns[:10]:
            click.echo(
                f"  {pattern['pattern_type']} | {pattern['direction']} | "
                f"Samples: {pattern['sample_size']} | "
                f"Win Rate: {pattern['win_rate']:.2%}"
            )

        if len(patterns) > 10:
            click.echo(f"  ... and {len(patterns) - 10} more")

        # Save to file if requested
        if output:
            import json

            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(patterns, f, indent=2, default=str)

            click.echo(f"\n✓ Saved to {output}")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        logger.error(f"Pattern analysis error: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option("--symbol", "-s", required=True, help="Stock symbol")
@click.option("--move-pct", required=True, type=float, help="Price move percentage")
@click.option(
    "--volume-ratio", required=True, type=float, help="Volume vs average ratio"
)
@click.option(
    "--timeframe", "-t", default="5min", help="Timeframe. Default: 5min"
)
@click.option(
    "--direction",
    "-d",
    type=click.Choice(["UP", "DOWN"], case_sensitive=False),
    help="Direction (optional)",
)
def predict(symbol, move_pct, volume_ratio, timeframe, direction):
    """
    Predict continuation probability for a momentum event.

    Example:
        gambler-cli predict --symbol AAPL --move-pct 2.5 --volume-ratio 3.2
    """
    try:
        click.echo(f"Predicting continuation for {symbol.upper()}...")
        click.echo(f"  Initial move: {move_pct}%")
        click.echo(f"  Volume ratio: {volume_ratio}x")

        engine = StatisticsEngine()
        prediction = engine.predict_continuation(
            symbol=symbol.upper(),
            initial_move_pct=move_pct,
            volume_ratio=volume_ratio,
            timeframe=timeframe,
            direction=direction.upper() if direction else None,
        )

        if "error" in prediction:
            click.echo(f"\n⚠ {prediction['error']}")
            return

        click.echo(f"\n✓ Prediction Results:")
        click.echo(
            f"  Continuation probability: "
            f"{prediction['continuation_probability']:.0%}"
        )
        click.echo(
            f"  Expected continuation: "
            f"{prediction.get('expected_continuation_minutes', 0):.1f} minutes"
        )
        click.echo(
            f"  Expected reversal: "
            f"{prediction.get('expected_reversal_pct', 0):.2f}%"
        )
        click.echo(
            f"  Reversal timing: "
            f"{prediction.get('expected_reversal_time_minutes', 0):.1f} minutes"
        )
        click.echo(f"  Confidence: {prediction['confidence']:.0%}")
        click.echo(f"  Sample size: {prediction['sample_size']}")
        click.echo(
            f"\n  Recommendation: {prediction['recommendation']}"
        )

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        logger.error(f"Prediction error: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option("--symbol", "-s", required=True, help="Stock symbol")
@click.option("--start", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end", help="End date (YYYY-MM-DD). Default: today")
@click.option(
    "--timeframe", "-t", default="5min", help="Timeframe. Default: 5min"
)
def validate(symbol, start, end, timeframe):
    """
    Validate data quality for a symbol.

    Example:
        gambler-cli validate --symbol AAPL --start 2024-01-01 --end 2024-12-31
    """
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d") if end else datetime.now()

        click.echo(f"Validating data for {symbol.upper()}...")

        validator = DataValidator()
        results = validator.validate_data(
            symbol=symbol.upper(),
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
        )

        # Log results
        validator.log_quality_check(results)

        click.echo(f"\n✓ Validation complete!")
        click.echo(f"  Quality score: {results['quality_score']:.2%}")
        click.echo(f"  Expected periods: {results['total_expected']}")
        click.echo(f"  Actual periods: {results['total_actual']}")
        click.echo(f"  Missing periods: {results['missing_periods']}")

        if results["issues"]:
            click.echo(f"\n⚠ Issues found:")
            for issue in results["issues"]:
                click.echo(f"  - {issue}")
        else:
            click.echo(f"\n✓ No issues found")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        logger.error(f"Validation error: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
def config():
    """Display current configuration."""
    try:
        cfg = get_config()

        click.echo("GamblerAI Configuration:")
        click.echo(f"\nDatabase:")
        click.echo(f"  TimescaleDB: {cfg.timeseries_db_url}")
        click.echo(f"  Analytics DB: {cfg.analytics_db_url}")

        click.echo(f"\nRedis:")
        click.echo(f"  URL: {cfg.redis_url}")

        click.echo(f"\nMomentum Detection:")
        click.echo(
            f"  Min price change: "
            f"{cfg.get('analysis.momentum_detection.min_price_change_pct')}%"
        )
        click.echo(
            f"  Min volume ratio: "
            f"{cfg.get('analysis.momentum_detection.min_volume_ratio')}x"
        )
        click.echo(
            f"  Window: "
            f"{cfg.get('analysis.momentum_detection.window_minutes')} minutes"
        )

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
