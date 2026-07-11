from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


DATA_PATH = Path("data/radar.json")
SOURCES = [
    {"name": "PE Hub Europe", "url": "https://www.pehub.com/regions_and_countries/europe/", "region": "Europe", "tier": "deal_news"},
    {"name": "DealStreetAsia", "url": "https://www.dealstreetasia.com/", "region": "Asia", "tier": "deal_news"},
]
DEAL_PATTERN = re.compile(r"\b(exit|sale|sell|acquir|buyout|stake|strategic review|continuation|valuation|portfolio|majority|minority|auction|mandate|ipo)\b", re.I)


class HeadlineParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.capture = False
        self.parts: list[str] = []
        self.items: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"a", "h1", "h2", "h3", "h4"}:
            self.capture = True
            self.parts = []

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.capture and tag in {"a", "h1", "h2", "h3", "h4"}:
            value = re.sub(r"\s+", " ", unescape(" ".join(self.parts))).strip()
            if 28 <= len(value) <= 220 and DEAL_PATTERN.search(value):
                self.items.append(value)
            self.capture = False
            self.parts = []


def infer_type(headline: str) -> str:
    if re.search(r"continuation|gp-led", headline, re.I):
        return "continuation_vehicle"
    if re.search(r"strategic review|auction|mandate|to exit|seeks buyer", headline, re.I):
        return "sale_process"
    if re.search(r"ipo|listing", headline, re.I):
        return "ipo_prep"
    if re.search(r"valuation|valued|million|billion|\$|€|£", headline, re.I):
        return "valuation_marker"
    return "exit_completed" if re.search(r"acquir|sale|sold|buyout", headline, re.I) else "portfolio_update"


def fetch_headlines(source: dict) -> list[str]:
    request = urllib.request.Request(source["url"], headers={"User-Agent": "PE-Radar/1.0 public research monitor"})
    with urllib.request.urlopen(request, timeout=15) as response:
        parser = HeadlineParser()
        parser.feed(response.read().decode("utf-8", errors="ignore"))
    return list(dict.fromkeys(parser.items))[:24]


def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat()
    signals = payload.get("signals", [])
    existing = {signal.get("id") or signal.get("excerpt", "").lower() for signal in signals}
    targets = payload.get("targets", [])
    fetched, errors = [], []
    new_count = 0

    for source in SOURCES:
        try:
            headlines = fetch_headlines(source)
            fetched.append({"url": source["url"], "status": "200"})
            for headline in headlines:
                signal_id = "live-" + hashlib.sha256(f'{source["name"]}:{headline}'.encode()).hexdigest()[:20]
                if signal_id in existing:
                    continue
                target = next((item for item in targets if item.get("company_name", "").lower() in headline.lower()), None)
                signals.insert(0, {
                    "id": signal_id,
                    "company_name": target.get("company_name") if target else None,
                    "confidence": "machine_found",
                    "created_at": now,
                    "excerpt": headline,
                    "matched_sponsors": [],
                    "matched_terms": [],
                    "region": source["region"],
                    "signal_type": infer_type(headline),
                    "source_name": source["name"],
                    "source_tier": source["tier"],
                    "source_url": source["url"],
                })
                existing.add(signal_id)
                new_count += 1
        except Exception as exc:
            errors.append({"source_name": source["name"], "url": source["url"], "error": str(exc)})

    payload["generated_at"] = now
    payload["signals"] = signals[:150]
    payload["sync"] = {
        "generated_at": now,
        "new_signal_count": new_count,
        "total_signal_count": len(payload["signals"]),
        "fetched": fetched,
        "errors": errors,
    }
    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
