"""Start the local API and Streamlit demo, and clean up only owned processes."""

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from importlib.resources import files
from urllib.error import URLError
from urllib.request import urlopen


def _port(value):
    number = int(value)
    if not 1 <= number <= 65535:
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535")
    return number


def _require_free_port(port):
    with socket.socket() as listener:
        try:
            listener.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(f"Port {port} is already in use; choose another port") from exc


def _wait_for_api(process, base_url, timeout=300):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Greenr API exited during startup")
        try:
            with urlopen(base_url + "/health", timeout=1) as response:
                health = json.load(response)
            if health.get("status") == "ok" and health.get("synthetic_demo") is True:
                return
        except (URLError, OSError, ValueError):
            pass
        time.sleep(0.15)
    raise RuntimeError("Greenr API did not become healthy within the startup timeout")


def _stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the synthetic Greenr API and UI")
    parser.add_argument("--api-port", type=_port, default=8000)
    parser.add_argument("--ui-port", type=_port, default=8501)
    parser.add_argument("--startup-timeout", type=int, default=300,
                         help="Seconds allowed for API health readiness (default: 300; historical preparation may run separately)")
    args = parser.parse_args(argv)
    processes = []
    try:
        if args.startup_timeout <= 0:
            raise RuntimeError("Startup timeout must be positive")
        if args.api_port == args.ui_port:
            raise RuntimeError("API and UI ports must differ")
        _require_free_port(args.api_port)
        _require_free_port(args.ui_port)
        base_url = f"http://127.0.0.1:{args.api_port}"
        api = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "greenpath.api.main:app",
            "--host", "127.0.0.1", "--port", str(args.api_port),
        ])
        processes.append(api)
        _wait_for_api(api, base_url, timeout=args.startup_timeout)
        environment = dict(os.environ, GREENPATH_API_URL=base_url)
        entrypoint = str(files("greenpath.app").joinpath("main.py"))
        ui = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", entrypoint,
            "--server.address", "127.0.0.1", "--server.port", str(args.ui_port),
            "--server.headless", "true", "--browser.gatherUsageStats", "false",
        ], env=environment)
        processes.append(ui)
        print(f"Greenr UI: http://127.0.0.1:{args.ui_port} | API: {base_url}", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.2)
        return 1
    except KeyboardInterrupt:
        return 0
    except (RuntimeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        for process in reversed(processes):
            _stop(process)


if __name__ == "__main__":
    def stop_on_signal(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop_on_signal)
    raise SystemExit(main())
