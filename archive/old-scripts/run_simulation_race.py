"""
Simple runner script for Simulation Race

Usage:
    python scripts/run_simulation_race.py simulation    # Run simulation
    python scripts/run_simulation_race.py ui            # Launch UI
    python scripts/run_simulation_race.py both          # Run both
"""

import sys
import subprocess
from pathlib import Path


def run_simulation():
    """Run the simulation engine."""
    print("\n" + "="*80)
    print("🏁 STARTING SIMULATION RACE")
    print("="*80 + "\n")
    print("This will test all 40 combinations of scanners and strategies.")
    print("Estimated time: 5-10 minutes\n")

    confirm = input("Continue? (y/n): ")
    if confirm.lower() != 'y':
        print("Cancelled.")
        return

    # Run simulation
    from simulation_race_engine import SimulationRaceEngine

    engine = SimulationRaceEngine(
        initial_capital=100000,
        lookback_days=365,
    )

    results = engine.run_simulation(save_progress=True)

    # Print summary
    print("\n" + "="*80)
    print("✅ SIMULATION COMPLETE")
    print("="*80 + "\n")

    sorted_results = sorted(
        results.items(),
        key=lambda x: x[1].total_pnl,
        reverse=True
    )

    print("TOP 5 PERFORMERS:\n")
    print(f"{'Rank':<6}{'Scanner':<25}{'Strategy':<20}{'Return %':<12}{'P&L':<15}")
    print("-" * 80)

    for i, (name, result) in enumerate(sorted_results[:5], 1):
        print(
            f"{i:<6}{result.scanner_type:<25}{result.strategy_name:<20}"
            f"{result.return_pct:>10.2f}%  ${result.total_pnl:>12,.2f}"
        )

    print("\n" + "-" * 80)
    print(f"\nResults saved to: simulation_results/")
    print(f"To view in UI, run: python scripts/run_simulation_race.py ui\n")


def launch_ui():
    """Launch the Streamlit UI."""
    print("\n" + "="*80)
    print("🎨 LAUNCHING SIMULATION RACE UI")
    print("="*80 + "\n")

    # Check if results exist
    results_dir = Path("simulation_results")
    if not results_dir.exists() or not (results_dir / "all_results.json").exists():
        print("❌ No simulation results found!")
        print("\nPlease run the simulation first:")
        print("  python scripts/run_simulation_race.py simulation\n")
        return

    print("Opening browser at http://localhost:8501")
    print("Press Ctrl+C to stop the UI\n")

    # Launch Streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "scripts/simulation_race_ui.py",
            "--server.headless", "false"
        ])
    except KeyboardInterrupt:
        print("\n\nUI stopped.")


def print_usage():
    """Print usage instructions."""
    print("\n" + "="*80)
    print("🏁 SIMULATION RACE RUNNER")
    print("="*80 + "\n")
    print("Usage:")
    print("  python scripts/run_simulation_race.py simulation    # Run simulation")
    print("  python scripts/run_simulation_race.py ui            # Launch UI")
    print("  python scripts/run_simulation_race.py both          # Run both")
    print("\nCommands:")
    print("  simulation - Run the complete simulation (5-10 minutes)")
    print("  ui         - Launch interactive visualization dashboard")
    print("  both       - Run simulation then launch UI")
    print("\nExamples:")
    print("  python scripts/run_simulation_race.py simulation")
    print("  python scripts/run_simulation_race.py ui\n")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "simulation":
        run_simulation()

    elif command == "ui":
        launch_ui()

    elif command == "both":
        run_simulation()
        print("\n")
        input("Press Enter to launch UI...")
        launch_ui()

    elif command in ["help", "-h", "--help"]:
        print_usage()

    else:
        print(f"\n❌ Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
