"""
Single-process supervisor for deploying EventPulse as one Railway service.

Runs the trading cycle (main.py) on a repeating interval in a background
thread, and launches the Streamlit dashboard in the foreground bound to
Railway's assigned $PORT. Both processes share the same container disk
(and therefore the same attached Volume), so the dashboard always reads
whatever the trading cycle most recently wrote — no cross-service data
sharing required.

Configure the interval with the TRADING_CYCLE_INTERVAL_SECONDS env var
(default: 900 seconds / 15 minutes).
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time


INTERVAL_SECONDS = int(
    os.environ.get("TRADING_CYCLE_INTERVAL_SECONDS", "900")
)


def run_trading_cycle_loop() -> None:
    while True:
        print(
            f"[scheduler] Starting trading cycle "
            f"(next run in {INTERVAL_SECONDS}s)...",
            flush=True,
        )

        try:
            result = subprocess.run(
                [sys.executable, "main.py"],
                check=False,
            )

            if result.returncode != 0:
                print(
                    f"[scheduler] main.py exited with code "
                    f"{result.returncode}",
                    flush=True,
                )

        except Exception as exc:
            print(
                f"[scheduler] Trading cycle raised an exception: {exc}",
                flush=True,
            )

        time.sleep(INTERVAL_SECONDS)


def main() -> None:
    scheduler_thread = threading.Thread(
        target=run_trading_cycle_loop,
        daemon=True,
    )
    scheduler_thread.start()

    port = os.environ.get("PORT", "8501")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app/dashboard.py",
            "--server.port",
            port,
            "--server.address",
            "0.0.0.0",
            "--server.headless",
            "true",
        ]
    )


if __name__ == "__main__":
    main()

