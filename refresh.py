from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


DATA_PATH = Path("data/radar.json") if Path("data/radar.json").exists() else Path("site/data/radar.json")
DEAL_SOURCES = [
    {"name": "PE Hub Europe", "url": "https://www.pehub.com/regions_and_countries/europe/", "region": "Europe", "tier": "deal_news"},
    {"name": "DealStreetAsia", "url": "https://www.dealstreetasia.com/", "region": "Asia", "tier": "deal_news"},
]
TARGET_SOURCES = [
    {"name": "Golden Goose official news", "company_name": "Golden Goose", "url": "https://we.goldengoose.com/we-are-golden/media/press-releases/", "region": "Europe / Asia", "tier": "priority_target_official"},
    {"name": "Guala Closures investor relations", "company_name": "Guala Closures", "url": "https://www.gualaclosures.com/investors", "region": "Europe", "tier": "priority_target_ir"},
    {"name": "Mammut official press", "company_name": "Mammut", "url": "https://pr.mammut.com/en", "region": "Europe / Asia", "tier": "priority_target_official"},
    {"name": "Dainese investor relations", "company_name": "Dainese", "url": "https://www.dainese.com/li/de/legal/investors-relation.html", "region": "Europe", "tier": "generated_target_ir"},
    {"name": "Kersia official news", "company_name": "Kersia", "url": "https://www.kersia-group.com/newsroom/", "region": "Europe / Asia", "tier": "generated_target_official"},
    {"name": "Nemera official news", "company_name": "Nemera", "url": "https://www.nemera.net/news/", "region": "Europe / Asia", "tier": "generated_target_official"},
    {"name": "Schleich official press", "company_name": "Schleich", "url": "https://www.mynewsdesk.com/schleich/pressreleases", "region": "Europe", "tier": "generated_target_official"},
    {"name": "AMMEGA official portfolio", "company_name": "AMMEGA", "url": "https://www.partnersgroup.com/en/our-investments/private-equity/ammega", "region": "Europe / Asia", "tier": "candidate_official"},
    {"name": "Engel & Volkers official portfolio", "company_name": "Engel & Völkers", "url": "https://www.permira.com/portfolio/our-portfolio/engels-voelkers", "region": "Europe", "tier": "candidate_official"},
    {"name": "ADB SAFEGATE official portfolio", "company_name": "ADB SAFEGATE", "url": "https://www.carlyle.com/our-business/portfolio-of-investments/adb-safegate", "region": "Europe", "tier": "candidate_official"},
    {"name": "nLighten official portfolio", "company_name": "nLighten", "url": "https://isquaredcapital.com/cpt_invest/nlighten/", "region": "Europe", "tier": "ai_infrastructure_official"},
    {"name": "Trench Group official portfolio", "company_name": "Trench Group", "url": "https://www.triton-partners.com/portfolio/trench-group", "region": "Europe / Asia", "tier": "ai_infrastructure_official"},
]
FUND_SOURCES = [
    ("EQT", "Europe / Asia", "https://eqtgroup.com/about/current-portfolio", "current", "headings"),
    ("KKR", "Global", "https://www.kkr.com/invest/portfolio", "current selected", "headings"),
    ("CVC Capital Partners", "Europe / Asia", "https://www.cvc.com/portfolio/our-portfolio/", "selected", "headings"),
    ("Permira", "Europe / Asia", "https://www.permira.com/portfolio/our-portfolio", "current and realised", "headings"),
    ("Advent International", "Europe / Asia / Global", "https://www.adventinternational.com/investments/", "current and realised", "headings"),
    ("Cinven", "Europe", "https://www.cinven.com/portfolio/", "current and realised", "headings"),
    ("Bridgepoint", "Europe", "https://www.bridgepoint.eu/portfolio", "current and realised", "headings"),
    ("PAI Partners", "Europe", "https://www.paipartners.com/portfolio/", "current and realised", "headings"),
    ("Hg", "Europe", "https://hgcapital.com/portfolio/", "current and realised", "headings"),
    ("Triton Partners", "Europe", "https://www.triton-partners.com/portfolio/", "current and realised", "headings"),
    ("PAG", "Asia", "https://www.pag.com/private-equity", "selected active", "headings"),
    ("Navis Capital", "Asia", "https://www.naviscapital.com/portfolio-tag/current-investments/", "current", "headings"),
    ("Affinity Equity Partners", "Asia", "https://www.affinityequity.com/", "official firm site", "headings"),
    ("Bain Capital", "Europe / Asia / Global", "https://www.baincapitalprivateequity.com/portfolio", "current", "name_labels"),
    ("TPG", "Europe / Asia / Global", "https://www.tpg.com/portfolio", "selected", "headings"),
    ("Warburg Pincus", "Europe / Asia / Global", "https://warburgpincus.com/investments/", "selected", "headings"),
    ("BC Partners", "Europe / Global", "https://www.bcpartners.com/portfolio/", "recent flagship funds", "headings"),
    ("Ardian", "Europe / Global", "https://www.ardian.com/expertise/our-portfolio", "current and realised", "headings"),
    ("Investindustrial", "Europe / Global", "https://www.investindustrial.com/our-business/portfolio-overview/current-portfolio.html", "current", "headings"),
    ("Jacobs Capital", "Europe / Global", "https://telemoscapital.com/company/mammut/", "current priority asset", "headings"),
    ("TA Associates", "Asia / Europe / Global", "https://www.ta.com/portfolio/", "current and past", "headings"),
    ("Astorg", "Europe / Global", "https://www.astorg.com/investments", "current and realised", "headings"),
    ("IK Partners", "Europe", "https://ikpartners.com/investments/", "current and realised", "headings"),
    ("Partners Group", "Europe / Asia / Global", "https://www.partnersgroup.com/en/our-investments/private-equity", "selected current", "headings"),
]
CREDIT_SOURCES = [
    ("FINRA TRACE Corporate & Agency", "United States / 144A", "https://www.finra.org/finra-data/fixed-income/corp-and-agency", "CUSIP", "executed trade price and yield", "trade_history"),
    ("Euronext Bonds / Nordic ABM", "Europe", "https://live.euronext.com/en/products/bonds/list", "ISIN", "venue dependent", "exchange_directory"),
    ("Luxembourg Stock Exchange", "Europe / Global", "https://www.luxse.com/market-overview/official-list", "ISIN", "listing and reference data", "exchange_directory"),
    ("HKEX Debt Securities", "Asia", "https://www.hkex.com.hk/products/securities/debt-securities?sc_lang=en", "ISIN or stock code", "listing and disclosure", "exchange_directory"),
    ("SGX Fixed Income", "Asia", "https://www.sgx.com/fixed-income/retail-fixed-income-securities?code=retailbonds", "ISIN", "delayed retail last price", "exchange_trade_directory"),
    ("Boerse Frankfurt Bonds", "Europe", "https://live.deutsche-boerse.com/anleihen/suche", "ISIN", "delayed exchange price", "exchange_trade_directory"),
    ("BME Fixed Income / MARF", "Europe", "https://www.bolsasymercados.es/en/bme-exchange/prices-and-markets/fixed-income/issues.html", "ISIN", "listing reference and venue data", "exchange_trade_directory"),
]
DEAL_PATTERN = re.compile(r"\b(exit|sale|sell|acquir|buyout|stake|strategic review|continuation|valuation|portfolio|majority|minority|auction|mandate|ipo)\b", re.I)
PRIORITY_PATTERN = re.compile(r"\b(sale|sell|auction|adviser|advisor|banker|bidder|refinanc|bond|notes|results|revenue|acquir|distribution|expan|management|ceo|ownership|investor|continuation|recap)\w*\b", re.I)
NOISE = {
    "about", "about us", "careers", "case studies", "companies", "contact", "contact us",
    "current investments", "current portfolio", "discover", "filter", "focus portfolio", "follow us",
    "access", "archives", "businesses", "categories", "deal team", "employees", "featured news",
    "focused on partnership", "get in touch", "highlight investments", "ideas", "in revenue",
    "legal/regulatory", "local networks, international expertise", "global reach", "home", "insights", "investments",
    "investment portfolio", "legal", "locations", "local sites", "main navigation", "media", "meet our team",
    "news", "no records found.", "our companies", "our firm", "our investments", "our portfolio",
    "our team", "people", "portfolio", "portfolio companies", "portfolio stories", "press", "press releases",
    "posts navigation", "private credit", "private equity", "private wealth", "read more", "recent comments",
    "our investing strategies", "recent posts", "responsibility", "search", "sector expertise", "sectors", "select investments",
    "select your experience", "share this page", "shareholders", "sign on to your account", "status", "strategies",
    "sustainability", "sustainable value", "team", "view all", "website", "who we are",
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.capture_tag: str | None = None
        self.parts: list[str] = []
        self.headings: list[str] = []
        self.links_and_headings: list[str] = []
        self.all_text: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"a", "h1", "h2", "h3", "h4"}:
            self.capture_tag = tag
            self.parts = []

    def handle_data(self, data: str) -> None:
        self.all_text.append(data)
        if self.capture_tag:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.capture_tag == tag:
            value = clean_text(" ".join(self.parts))
            if value:
                self.links_and_headings.append(value)
                if tag in {"h2", "h3", "h4"}:
                    self.headings.append(value)
            self.capture_tag = None
            self.parts = []


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def fetch_page(url: str) -> tuple[str, str, int]:
    request = urllib.request.Request(url, headers={"User-Agent": "PE-Radar/2.0 public research monitor"})
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=18) as response:
        html = response.read().decode("utf-8", errors="ignore")
        status = str(response.getcode() or 200)
    return html, status, round((time.monotonic() - started) * 1000)


def is_company_candidate(value: str) -> bool:
    lower = value.lower().strip(" .:-")
    if lower in NOISE or not 2 <= len(value) <= 80:
        return False
    if len(value.split()) > 9 or value.endswith(("?", ":")):
        return False
    if re.search(r"\b(learn more|read more|view portfolio|filter by|our approach|latest news)\b", lower):
        return False
    if re.match(r"^(why\b|we\b|unlocking\b|bloomberg deals\b|bc partners promotes\b)", lower):
        return False
    return sum(character.isalpha() for character in value) >= 2


def portfolio_names(html: str, parser_name: str) -> list[str]:
    parser = PageParser()
    parser.feed(html)
    candidates = list(parser.headings) if parser_name != "name_labels" else []
    if parser_name == "name_labels":
        page_text = clean_text(" ".join(parser.all_text))
        candidates.extend(re.findall(r"\bName:\s*(.{2,80}?)(?=\s+(?:REGIONS?|INDUSTRY|YEAR):)", page_text, re.I))
    result: list[str] = []
    seen = set()
    for candidate in candidates:
        value = clean_text(candidate)
        key = value.casefold()
        if key not in seen and is_company_candidate(value):
            seen.add(key)
            result.append(value)
    return result


def infer_type(headline: str) -> str:
    if re.search(r"continuation|gp-led", headline, re.I):
        return "continuation_vehicle"
    if re.search(r"strategic review|auction|mandate|to exit|seeks buyer", headline, re.I):
        return "sale_process"
    if re.search(r"ipo|listing", headline, re.I):
        return "ipo_prep"
    if re.search(r"refinanc|bond|notes|recap", headline, re.I):
        return "refinancing"
    if re.search(r"valuation|valued|million|billion|\$|€|£", headline, re.I):
        return "valuation_marker"
    return "exit_completed" if re.search(r"acquir|sale|sold|buyout", headline, re.I) else "portfolio_update"


def deal_job(source: dict) -> dict:
    html, status, elapsed_ms = fetch_page(source["url"])
    parser = PageParser()
    parser.feed(html)
    headlines = [value for value in parser.links_and_headings if 28 <= len(value) <= 220 and DEAL_PATTERN.search(value)]
    return {"source": source, "status": status, "elapsed_ms": elapsed_ms, "headlines": list(dict.fromkeys(headlines))[:24]}


def priority_job(source: dict) -> dict:
    html, status, elapsed_ms = fetch_page(source["url"])
    parser = PageParser()
    parser.feed(html)
    headlines = [
        value for value in parser.links_and_headings
        if 20 <= len(value) <= 220 and PRIORITY_PATTERN.search(value)
    ]
    return {"source": source, "status": status, "elapsed_ms": elapsed_ms, "headlines": list(dict.fromkeys(headlines))[:30]}


def fund_job(source: tuple[str, str, str, str, str]) -> dict:
    sponsor, region, url, scope, parser_name = source
    html, status, elapsed_ms = fetch_page(url)
    return {"sponsor": sponsor, "region": region, "url": url, "scope": scope, "status": status, "elapsed_ms": elapsed_ms, "names": portfolio_names(html, parser_name)}


def credit_job(source: tuple[str, str, str, str, str, str], aliases: dict[str, str]) -> dict:
    name, region, url, identifier, capability, source_type = source
    html, status, elapsed_ms = fetch_page(url)
    text = clean_text(re.sub(r"<[^>]+>", " ", html)).casefold()
    matches = sorted({company for alias, company in aliases.items() if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text)})
    return {"name": name, "region": region, "url": url, "identifier": identifier, "capability": capability, "source_type": source_type, "status": status, "elapsed_ms": elapsed_ms, "matches": matches}


def refresh_idea_queue(payload: dict, signals: list[dict], new_candidates: list[dict], now: str) -> None:
    queue = payload.get("idea_queue", [])
    rejected = {re.sub(r"[^a-z0-9]+", "", str(item.get("company_name", "")).casefold()) for item in payload.get("idea_sync", {}).get("rejected_memory", [])}
    target_names = {re.sub(r"[^a-z0-9]+", "", str(item.get("company_name", "")).casefold()) for item in payload.get("targets", [])}
    by_name = {re.sub(r"[^a-z0-9]+", "", str(item.get("company_name", "")).casefold()): item for item in queue}
    for candidate in new_candidates:
        key = re.sub(r"[^a-z0-9]+", "", str(candidate.get("company_name", "")).casefold())
        if not key or key in by_name or key in target_names or key in rejected:
            continue
        row = dict(candidate)
        row.update({
            "origin": "official_portfolio_delta",
            "status": "new_official_addition",
            "first_seen_at": now,
            "last_reviewed_at": now,
            "estimated_ev_usd_m": None,
            "entry_date": None,
            "themes": [],
            "business_model": "Official portfolio addition; business model not yet classified.",
            "why_now": "Newly observed on a monitored sponsor website and awaiting qualification.",
            "next_action": "Verify current ownership, entry date, enterprise value, business quality and exit signals.",
            "evidence_gaps": ["entry date", "enterprise value", "business quality", "exit signal"],
            "base_triage_score": 55,
            "triage_score": 55,
            "promote_ready": False,
        })
        queue.append(row)
        by_name[key] = row
    for row in queue:
        names = [str(row.get("company_name", "")).casefold(), *[str(alias).casefold() for alias in row.get("aliases", []) or []]]
        related = [signal for signal in signals if str(signal.get("company_name", "")).casefold() in names or any(name and name in str(signal.get("excerpt", "")).casefold() for name in names)]
        row["related_signals"] = related[:8]
        row["signal_count"] = len(related)
        row["last_reviewed_at"] = now
        base = int(row.get("base_triage_score", row.get("triage_score", 55)))
        row["base_triage_score"] = base
        row["triage_score"] = min(100, base + min(8, len(related) * 2))
        if related and row.get("status") == "new_official_addition":
            row["status"] = "research_now"
    status_rank = {"research_now": 0, "monitor": 1, "new_official_addition": 2}
    queue.sort(key=lambda item: (status_rank.get(str(item.get("status")), 3), -int(item.get("triage_score", 0)), str(item.get("company_name", ""))))
    payload["idea_queue"] = queue[:100]
    payload["idea_sync"] = {
        **payload.get("idea_sync", {}),
        "generated_at": now,
        "candidate_count": len(queue),
        "research_now_count": sum(1 for item in queue if item.get("status") == "research_now"),
        "new_official_addition_count": sum(1 for item in queue if item.get("status") == "new_official_addition"),
        "promote_ready_count": sum(1 for item in queue if item.get("promote_ready")),
        "ai_theme_count": sum(1 for item in queue if item.get("themes")),
    }


def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat()
    signals = payload.get("signals", [])
    existing_signals = {signal.get("id") or signal.get("excerpt", "").lower() for signal in signals}
    targets = payload.get("targets", [])
    existing_universe = {(item.get("sponsor", "").casefold(), item.get("company_name", "").casefold()): item for item in payload.get("sponsor_universe", [])}
    universe_by_key = dict(existing_universe)
    aliases = {item.get("company_name", "").casefold(): item.get("company_name") for item in targets if len(item.get("company_name", "")) >= 4}
    for item in targets:
        for alias in item.get("aliases", []) or []:
            if len(alias) >= 4:
                aliases[alias.casefold()] = item.get("company_name")
    for item in payload.get("idea_queue", []):
        if len(item.get("company_name", "")) >= 4:
            aliases[item.get("company_name", "").casefold()] = item.get("company_name")
        for alias in item.get("aliases", []) or []:
            if len(alias) >= 4:
                aliases[alias.casefold()] = item.get("company_name")

    deal_health, deal_errors, new_count = [], [], 0
    fund_health, fund_errors, new_candidates = [], [], []
    credit_health, credit_errors, directory_matches = [], [], []

    jobs = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        jobs.extend(("deal", source, executor.submit(deal_job, source)) for source in DEAL_SOURCES)
        jobs.extend(("priority", source, executor.submit(priority_job, source)) for source in TARGET_SOURCES)
        jobs.extend(("fund", source, executor.submit(fund_job, source)) for source in FUND_SOURCES)
        jobs.extend(("credit", source, executor.submit(credit_job, source, aliases)) for source in CREDIT_SOURCES)
        for kind, source, future in jobs:
            try:
                result = future.result()
                if kind in {"deal", "priority"}:
                    deal_health.append({"url": result["source"]["url"], "status": result["status"], "elapsed_ms": result["elapsed_ms"]})
                    for headline in result["headlines"]:
                        signal_id = "live-" + hashlib.sha256(f'{result["source"]["name"]}:{headline}'.encode()).hexdigest()[:20]
                        if signal_id in existing_signals:
                            continue
                        target = next((item for item in targets if item.get("company_name", "").lower() in headline.lower()), None)
                        if kind == "priority":
                            target = next((item for item in targets if item.get("company_name") == result["source"].get("company_name")), target)
                        company_name = target.get("company_name") if target else (result["source"].get("company_name") if kind == "priority" else None)
                        signals.insert(0, {"id": signal_id, "company_name": company_name, "confidence": "machine_found", "created_at": now, "excerpt": headline, "matched_sponsors": [], "matched_terms": [], "region": result["source"]["region"], "signal_type": infer_type(headline), "source_name": result["source"]["name"], "source_tier": result["source"]["tier"], "source_url": result["source"]["url"]})
                        existing_signals.add(signal_id)
                        new_count += 1
                elif kind == "fund":
                    fund_health.append({"name": result["sponsor"], "sponsor": result["sponsor"], "url": result["url"], "status": result["status"], "elapsed_ms": result["elapsed_ms"], "candidate_count": len(result["names"]), "preserved_previous": not bool(result["names"])})
                    if result["names"]:
                        universe_by_key = {key: item for key, item in universe_by_key.items() if item.get("source_url") != result["url"]}
                    for company in result["names"]:
                        key = (result["sponsor"].casefold(), company.casefold())
                        previous = existing_universe.get(key, {})
                        row = {"company_name": company, "sponsor": result["sponsor"], "region": result["region"], "portfolio_scope": result["scope"], "source_name": f'{result["sponsor"]} official portfolio', "source_url": result["url"], "first_seen_at": previous.get("first_seen_at", now), "last_seen_at": now, "verification_status": "website_heading_candidate"}
                        universe_by_key[key] = row
                        if key not in existing_universe:
                            new_candidates.append(row)
                else:
                    credit_health.append({"name": result["name"], "url": result["url"], "status": result["status"], "elapsed_ms": result["elapsed_ms"], "matched_company_count": len(result["matches"])})
                    for company in result["matches"]:
                        directory_matches.append({"company_name": company, "issuer_name": None, "isin": None, "cusip": None, "source_name": result["name"], "source_url": result["url"], "source_type": result["source_type"], "price_capability": result["capability"], "observed_at": now, "verification_status": "directory_name_match_unverified"})
            except Exception as exc:
                if kind in {"deal", "priority"}:
                    deal_errors.append({"source_name": source["name"], "url": source["url"], "error": str(exc)})
                elif kind == "fund":
                    fund_errors.append({"name": source[0], "sponsor": source[0], "url": source[2], "error": str(exc)})
                else:
                    credit_errors.append({"name": source[0], "url": source[2], "error": str(exc)})

    universe = sorted(universe_by_key.values(), key=lambda item: (item["sponsor"].casefold(), item["company_name"].casefold()))
    refresh_idea_queue(payload, signals, new_candidates, now)
    payload["generated_at"] = now
    payload["signals"] = signals[:150]
    payload["sync"] = {"generated_at": now, "new_signal_count": new_count, "total_signal_count": len(payload["signals"]), "fetched": deal_health, "errors": deal_errors}
    payload["fund_sources"] = [{"name": f"{sponsor} official portfolio", "sponsor": sponsor, "url": url, "region": region, "scope": scope, "source_type": "fund_website", "kind": "fund_website"} for sponsor, region, url, scope, _ in FUND_SOURCES]
    payload["sponsor_universe"] = universe
    payload["fund_sync"] = {"generated_at": now, "source_count": len(FUND_SOURCES), "company_candidate_count": len(universe), "new_candidate_count": len(new_candidates), "new_candidates": new_candidates, "health": fund_health, "errors": fund_errors}
    payload["credit_sources"] = [{"name": name, "url": url, "region": region, "identifier": identifier, "price_capability": capability, "source_type": source_type, "kind": "credit_market"} for name, region, url, identifier, capability, source_type in CREDIT_SOURCES]
    payload["credit"] = {"verified_instruments": payload.get("credit", {}).get("verified_instruments", []), "directory_matches": directory_matches, "generated_at": now}
    payload["credit_sync"] = {"generated_at": now, "source_count": len(CREDIT_SOURCES), "verified_instrument_count": len(payload["credit"]["verified_instruments"]), "directory_match_count": len(directory_matches), "health": credit_health, "errors": credit_errors}
    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
