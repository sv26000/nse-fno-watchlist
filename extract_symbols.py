"""Extract NSE F&O underlying symbols into a TradingView-ready watchlist.

By default the script fetches the live list of equity-derivative underlyings
directly from the NSE "underlying-information" API, so you no longer need to
copy the JSON response from the website by hand. If the network request fails
(NSE occasionally blocks automated traffic), it falls back to a local JSON
file.

Each symbol is written on its own line with a configurable suffix (``1!`` by
default, which TradingView uses for continuous front-month futures), e.g.::

    RELIANCE1!
    TCS1!
    INFY1!

Usage examples
--------------
    # Fetch live and write a timestamped watchlist
    python extract_symbols.py

    # Fetch live, also refresh the local data.json cache
    python extract_symbols.py --save-json

    # Work entirely offline from a saved JSON file
    python extract_symbols.py --source file --input data.json

    # Include index symbols (NIFTY, BANKNIFTY, ...) and use no suffix
    python extract_symbols.py --include-indices --suffix ""
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover - handled at runtime
    requests = None  # type: ignore[assignment]


# --- NSE endpoint configuration ---------------------------------------------

API_URL = "https://www.nseindia.com/api/underlying-information"
HOME_URL = "https://www.nseindia.com"
REFERER_URL = (
    "https://www.nseindia.com/products-services/"
    "equity-derivatives-list-underlyings-information"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 15  # seconds


def fetch_from_api() -> dict:
    """Fetch the underlying-information payload from the live NSE API.

    NSE rejects requests that arrive without a valid session cookie, so we
    first visit the homepage and the referring page to obtain cookies, then
    call the JSON endpoint.

    Returns the parsed JSON payload as a dict.
    Raises RuntimeError if ``requests`` is unavailable or the call fails.
    """
    if requests is None:
        raise RuntimeError(
            "The 'requests' package is required for live fetching. "
            "Install it with 'pip install requests' or use --source file."
        )

    session = requests.Session()
    session.headers.update(
        {
            "user-agent": USER_AGENT,
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        }
    )

    try:
        # Warm up the session to collect the cookies NSE expects.
        session.get(HOME_URL, timeout=REQUEST_TIMEOUT)
        session.get(REFERER_URL, timeout=REQUEST_TIMEOUT)
        response = session.get(
            API_URL,
            headers={"referer": REFERER_URL},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # noqa: BLE001 - surface a single clear message
        raise RuntimeError(f"Failed to fetch data from NSE API: {exc}") from exc


def load_from_file(json_path: Path) -> dict | list:
    """Load and parse a JSON payload from a local file."""
    with json_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def extract_symbols(payload: dict | list, include_indices: bool = False) -> list[str]:
    """Pull the ordered list of symbols out of an NSE payload.

    Handles three shapes so the script works with both the raw API response
    and a hand-saved snippet:

    * Full API response: ``{"data": {"UnderlyingList": [...], "IndexList": [...]}}``
    * Just the ``data`` object: ``{"UnderlyingList": [...], "IndexList": [...]}``
    * A bare list of ``{"symbol": ..., "underlying": ...}`` objects
    """
    # Unwrap the top-level "data" key if present.
    if isinstance(payload, dict) and "data" in payload:
        payload = payload["data"]

    records: list[dict] = []
    if isinstance(payload, dict):
        if include_indices:
            records.extend(payload.get("IndexList", []))
        records.extend(payload.get("UnderlyingList", []))
    elif isinstance(payload, list):
        records = payload
    else:
        raise ValueError("Unrecognized JSON structure: expected a dict or list.")

    symbols: list[str] = []
    for item in records:
        if isinstance(item, dict) and item.get("symbol"):
            symbols.append(item["symbol"])
        else:
            print(f"Warning: skipping item without a 'symbol' key: {item!r}")
    return symbols


def write_watchlist(symbols: list[str], output_path: Path, suffix: str) -> None:
    """Write one symbol per line, each with the given suffix appended."""
    with output_path.open("w", encoding="utf-8") as handle:
        for symbol in symbols:
            handle.write(f"{symbol}{suffix}\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract NSE F&O underlying symbols into a TradingView watchlist.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        choices=["api", "file"],
        default="api",
        help="Where to read data from. 'api' fetches live from NSE (default); "
        "'file' reads a local JSON file.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data.json"),
        help="Local JSON file to read when --source=file, and the fallback "
        "when an API fetch fails (default: data.json).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path. Defaults to a timestamped output_YYYYMMDD_HHMMSS.txt.",
    )
    parser.add_argument(
        "--suffix",
        default="1!",
        help="Text appended to every symbol (default: '1!' for TradingView "
        "continuous futures). Pass an empty string for plain symbols.",
    )
    parser.add_argument(
        "--include-indices",
        action="store_true",
        help="Also include index symbols (NIFTY, BANKNIFTY, ...) from IndexList.",
    )
    parser.add_argument(
        "--save-json",
        action="store_true",
        help="When fetching from the API, also save the raw UnderlyingList to "
        "the --input path so it can be reused offline.",
    )
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="Fail instead of falling back to the local file if the live API "
        "fetch does not succeed. Useful in CI to surface NSE blocking.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    payload: dict | list
    if args.source == "api":
        try:
            payload = fetch_from_api()
            print("Fetched live data from the NSE API.")
        except RuntimeError as exc:
            print(f"Warning: {exc}")
            if args.require_live:
                print("Error: --require-live set and the live fetch failed.")
                return 1
            if args.input.exists():
                print(f"Falling back to local file: {args.input}")
                payload = load_from_file(args.input)
            else:
                print(f"Error: no fallback file found at {args.input}.")
                return 1
    else:
        if not args.input.exists():
            print(f"Error: input file not found: {args.input}")
            return 1
        payload = load_from_file(args.input)
        print(f"Loaded data from {args.input}.")

    # Optionally cache the freshly fetched underlying list for offline reuse.
    if args.source == "api" and args.save_json and isinstance(payload, dict):
        data = payload.get("data", payload)
        underlying = data.get("UnderlyingList", []) if isinstance(data, dict) else []
        if underlying:
            with args.input.open("w", encoding="utf-8") as handle:
                json.dump(underlying, handle, indent=4)
            print(f"Saved UnderlyingList to {args.input} ({len(underlying)} records).")

    try:
        symbols = extract_symbols(payload, include_indices=args.include_indices)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    if not symbols:
        print("Error: no symbols were extracted.")
        return 1

    output_path = args.output
    if output_path is None:
        timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"output_{timestamp}.txt")

    write_watchlist(symbols, output_path, args.suffix)
    print(f"Success: wrote {len(symbols)} symbols to {output_path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
