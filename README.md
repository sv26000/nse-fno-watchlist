# NSE Symbols Extractor

[![CI](https://github.com/sv26000/nse-symbols-eaxtract/actions/workflows/ci.yml/badge.svg)](https://github.com/sv26000/nse-symbols-eaxtract/actions/workflows/ci.yml)

Fetch the list of NSE (National Stock Exchange of India) Futures &amp; Options
**underlying** symbols and export them as a ready-to-import TradingView
watchlist.

The script pulls the live list straight from NSE's
`underlying-information` API, so there's no more copying JSON out of the
browser by hand. If the network call is blocked, it transparently falls back to
a bundled offline snapshot (`data.json`).

Each symbol is written on its own line with a configurable suffix. The default
`1!` is what TradingView uses for continuous front-month futures:

```
RELIANCE1!
TCS1!
INFY1!
```

## Requirements

- Python 3.9+
- [`requests`](https://pypi.org/project/requests/)

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Fetch the live list and write a timestamped watchlist (output_YYYYMMDD_HHMMSS.txt)
python extract_symbols.py

# Fetch live and also refresh the local data.json snapshot
python extract_symbols.py --save-json

# Work fully offline from the bundled snapshot
python extract_symbols.py --source file --input data.json

# Include index symbols (NIFTY, BANKNIFTY, ...) and drop the suffix
python extract_symbols.py --include-indices --suffix ""

# Write to a specific file
python extract_symbols.py --output my_watchlist.txt
```

### Options

| Option | Default | Description |
| --- | --- | --- |
| `--source {api,file}` | `api` | Read live from NSE (`api`) or from a local JSON file (`file`). |
| `--input PATH` | `data.json` | JSON file used for `--source file`, and as the fallback if the API call fails. |
| `--output PATH` | `output_<timestamp>.txt` | Where to write the watchlist. |
| `--suffix TEXT` | `1!` | Text appended to every symbol. Use `""` for plain symbols. |
| `--include-indices` | off | Also include index symbols from `IndexList`. |
| `--save-json` | off | When fetching live, cache the `UnderlyingList` to `--input` for offline reuse. |

## Importing into TradingView

1. Run the script to generate an `output_*.txt` file.
2. In TradingView, open the **Watchlist** panel.
3. Use **Import list** and select the generated file.

## How it works

NSE rejects API requests that arrive without a valid browser session, so the
script first visits the homepage and the underlyings page to collect the
required cookies, then calls the JSON endpoint:

```
GET https://www.nseindia.com/api/underlying-information
```

The response contains two lists, `UnderlyingList` (single stocks) and
`IndexList` (indices). By default only the underlyings are exported.

## Notes

- The NSE API is unofficial and may change or rate-limit without notice. The
  offline fallback keeps the tool usable if a request is blocked.
- Generated `output_*.txt` files are git-ignored. The `data.json` snapshot is
  committed so the tool works out of the box.
- This project is for personal and educational use. Please respect NSE's
  [terms of use](https://www.nseindia.com/terms-conditions).
