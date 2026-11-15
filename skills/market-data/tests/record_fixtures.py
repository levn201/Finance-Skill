# /// script
# requires-python = ">=3.11"
# dependencies = ["yfinance>=1.0"]
# ///
"""Re-record the Yahoo fixtures from live data (needs network). The tests never call this.

    uv run --script skills/market-data/tests/record_fixtures.py

The EDGAR and Finnhub fixtures are hand-written from the providers' documented response formats,
because recording them needs a SEC contact / an API key.
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import providers  # noqa: E402

SYMBOLS = {"sap_de": "SAP.DE", "aapl": "AAPL", "eunl_de": "EUNL.DE"}
DROP = {"longBusinessSummary", "companyOfficers", "executiveTeam", "address1", "phone", "fax", "zip", "city", "website"}


def jsonable(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    return value


for name, symbol in SYMBOLS.items():
    fixture = {
        "symbol": symbol,
        "recorded_on": date.today().isoformat(),
        "info": {k: v for k, v in providers.yahoo_info(symbol).items() if k not in DROP},
        "calendar": jsonable(providers.yahoo_calendar(symbol)),
        "history_1y": providers.yahoo_history(symbol, "1y"),
    }
    (HERE / "fixtures" / f"yahoo_{name}.json").write_text(json.dumps(fixture, indent=1, default=str) + "\n")
    print("recorded", symbol)
