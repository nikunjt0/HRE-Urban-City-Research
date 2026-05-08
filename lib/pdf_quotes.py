"""City-keyed quote extraction from the academic PDFs in /docs.

Scans each PDF page-by-page, locates sentences that mention any of a list of
city names (with German/English aliases), and returns up to N short quotes per
(city, source) pair. Results are cached in a JSON file so reruns skip re-extraction.

Usage:
    from lib.pdf_quotes import extract_city_quotes
    quotes = extract_city_quotes(
        pdf_paths=[...],
        city_aliases={"Cologne (Köln)": ["Cologne", "Köln", "Koln"], ...},
        cache_path=Path("output/report_quotes_cache.json"),
    )
    # quotes["Cologne (Köln)"] -> list of {source, page, quote}
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

MAX_QUOTES_PER_PAIR = 5
MAX_QUOTE_CHARS = 320

# Sentence boundary that tolerates abbreviations reasonably well for our purposes.
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])")
# Collapse whitespace
_WS = re.compile(r"\s+")


@dataclass
class Quote:
    source: str   # filename only (no path)
    page: int     # 1-indexed
    quote: str


def _clean(s: str) -> str:
    return _WS.sub(" ", s).strip()


def _extract_pdf_text(path: Path) -> list[str]:
    """Return per-page text. Empty string for pages that fail to extract."""
    pages: list[str] = []
    try:
        reader = PdfReader(str(path))
    except Exception as e:
        print(f"  [warn] could not open {path.name}: {e}")
        return pages
    for i, page in enumerate(reader.pages):
        try:
            pages.append(page.extract_text() or "")
        except Exception as e:
            print(f"  [warn] page {i+1} of {path.name}: {e}")
            pages.append("")
    return pages


def _find_quotes_for_city(
    page_texts: list[str],
    aliases: list[str],
    source: str,
) -> list[Quote]:
    """For one PDF and one city, return up to MAX_QUOTES_PER_PAIR quotes."""
    # Build one big regex matching any alias as a whole word.
    # Use lookarounds so we hit "Cologne" inside "Cologne's" but not inside "Eulogne".
    escaped = "|".join(re.escape(a) for a in aliases)
    pattern = re.compile(rf"(?<![A-Za-zäöüÄÖÜ]){escaped}(?![A-Za-zäöüÄÖÜ])", re.IGNORECASE)

    found: list[Quote] = []
    seen_quotes: set[str] = set()
    for page_idx, raw in enumerate(page_texts):
        if not raw:
            continue
        # Split into sentences. Keep paragraph context by looking ±1 sentence.
        sentences = _SENT_SPLIT.split(_clean(raw))
        for s_idx, sentence in enumerate(sentences):
            if not pattern.search(sentence):
                continue
            # Build a quote: include neighboring sentences for context, capped.
            chunk_parts = []
            if s_idx > 0:
                chunk_parts.append(sentences[s_idx - 1])
            chunk_parts.append(sentence)
            if s_idx + 1 < len(sentences):
                chunk_parts.append(sentences[s_idx + 1])
            chunk = _clean(" ".join(chunk_parts))
            # Truncate at a clause boundary near MAX_QUOTE_CHARS
            if len(chunk) > MAX_QUOTE_CHARS:
                cut = chunk[:MAX_QUOTE_CHARS]
                # back up to last sentence-ending punctuation if possible
                m = re.search(r"[.!?]\s", cut[::-1])
                if m:
                    cut = cut[: len(cut) - m.start()]
                chunk = cut.rstrip() + "…"
            # Dedup near-identical quotes
            key = chunk[:80]
            if key in seen_quotes:
                continue
            seen_quotes.add(key)
            found.append(Quote(source=source, page=page_idx + 1, quote=chunk))
            if len(found) >= MAX_QUOTES_PER_PAIR:
                return found
    return found


def extract_city_quotes(
    pdf_paths: list[Path],
    city_aliases: dict[str, list[str]],
    cache_path: Path | None = None,
    skip_pdfs: list[str] | None = None,
) -> dict[str, list[dict]]:
    """Extract quotes for each city from each PDF.

    Returns: {city_display_name: [{"source": str, "page": int, "quote": str}, ...]}
    Cached on disk if cache_path is provided.
    """
    skip_pdfs = set(skip_pdfs or [])

    if cache_path and cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text())
            # Sanity check the cache covers the same cities and PDFs we asked for.
            cached_cities = set(cached.keys())
            asked_cities = set(city_aliases.keys())
            if asked_cities.issubset(cached_cities):
                cached_sources = {q["source"] for qs in cached.values() for q in qs}
                asked_sources = {p.name for p in pdf_paths if p.name not in skip_pdfs}
                if asked_sources.issubset(cached_sources) or not cached_sources:
                    print(f"[pdf_quotes] using cache: {cache_path}")
                    return {c: cached.get(c, []) for c in asked_cities}
            print("[pdf_quotes] cache stale; re-extracting")
        except Exception as e:
            print(f"[pdf_quotes] cache unreadable ({e}); re-extracting")

    results: dict[str, list[dict]] = {city: [] for city in city_aliases}

    for pdf in pdf_paths:
        if pdf.name in skip_pdfs:
            continue
        if not pdf.exists():
            print(f"[pdf_quotes] missing: {pdf}")
            continue
        print(f"[pdf_quotes] extracting {pdf.name} ({pdf.stat().st_size // 1024} KB) ...")
        pages = _extract_pdf_text(pdf)
        if not any(pages):
            print(f"  [warn] no text extracted from {pdf.name}")
            continue
        for city, aliases in city_aliases.items():
            qs = _find_quotes_for_city(pages, aliases, pdf.name)
            if qs:
                results[city].extend([{"source": q.source, "page": q.page,
                                       "quote": q.quote} for q in qs])
        # tally
        per_city = {c: sum(1 for q in results[c] if q["source"] == pdf.name)
                    for c in city_aliases}
        hits = sum(per_city.values())
        print(f"  {hits} quotes across {sum(1 for v in per_city.values() if v)} cities")

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))
        print(f"[pdf_quotes] cached -> {cache_path}")

    return results


# Default city alias set for the 13 priority cities
PRIORITY_CITY_ALIASES: dict[str, list[str]] = {
    "Leipzig":                  ["Leipzig"],
    "Cologne (Köln)":           ["Cologne", "Köln", "Koln", "Colonia"],
    "Nuremberg (Nürnberg)":     ["Nuremberg", "Nürnberg", "Nurnberg", "Nuernberg"],
    "Frankfurt am Main":        ["Frankfurt"],
    "Augsburg":                 ["Augsburg"],
    "Bamberg":                  ["Bamberg"],
    "Würzburg":                 ["Würzburg", "Wurzburg", "Wuerzburg"],
    "Regensburg":               ["Regensburg", "Ratisbon"],
    "Erfurt":                   ["Erfurt"],
    "Ulm":                      ["Ulm"],
    "Magdeburg":                ["Magdeburg"],
    "Rothenburg ob der Tauber": ["Rothenburg"],
    "Speyer":                   ["Speyer", "Spires", "Speier"],
}
