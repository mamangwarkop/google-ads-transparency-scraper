"""Core logic: query Google Ads Transparency Center (public data) and flatten results.

Supports:
- Mode 'ads': extract individual ad creatives (text, image, video) with decoded headlines/descriptions/assets.
- Mode 'check_domains': bulk B2B lead-gen checker (does a domain run Google Ads? how many active ads? verified advertiser entity).
- Mode 'summary': competitor strategy summary (format breakdown, destination domains, sample copy).
- Smart query parsing & resolution: accepts domains, full URLs, Google Ads Transparency URLs, Advertiser IDs (AR...), or brand names, and selects the primary advertiser account with the highest active ad volume when multiple entities match.
"""
from __future__ import annotations

import re
import urllib.parse
from typing import Any

from google_ads_transparency_mcp import (
    GoogleAdsTransparency,
    is_parent_entity,
    normalize_domain,
    summarize_ads,
)

_KW = re.compile(r"\{KeyWord:([^}]*)\}", re.IGNORECASE)
_AR_ID = re.compile(r"(AR\d{10,25})")


def clean_text(s: str | None) -> str | None:
    """Resolve Google's dynamic keyword placeholders, e.g. {KeyWord:Nike Shoes} -> Nike Shoes."""
    if s is None:
        return None
    return _KW.sub(lambda m: m.group(1), s).strip()


def parse_query(raw: str) -> str:
    """Accept raw domain, brand name, AR... advertiser ID, website URL, or adstransparency.google.com URL."""
    s = (raw or "").strip()
    if not s:
        return ""
    m = _AR_ID.search(s)
    if m:
        return m.group(1)
    if "://" in s:
        parsed = urllib.parse.urlparse(s)
        qs = urllib.parse.parse_qs(parsed.query)
        for key in ("domain", "q", "query", "advertiser"):
            if key in qs and qs[key]:
                return qs[key][0].strip()
        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if host and "adstransparency.google" not in host:
            return host
    return s


def _best_suggestion_by_brand(g: GoogleAdsTransparency, brand: str) -> dict[str, Any] | None:
    """Search advertiser suggestions for `brand` and pick the matching entity with the highest ad_count."""
    b = brand.strip().lower()
    if not b:
        return None
    suggestions = g.search_suggestions(b)
    candidates: list[dict[str, Any]] = []
    fallback: list[dict[str, Any]] = []
    for s in suggestions:
        if "1" not in s:
            continue
        adv = g._suggestion_to_advertiser(s["1"])
        name_l = (adv.get("name") or "").lower()
        fallback.append(adv)
        if b in name_l or not is_parent_entity(b + ".com", adv.get("name") or ""):
            candidates.append(adv)
    pool = candidates or fallback
    if not pool:
        return None
    return max(pool, key=lambda x: x.get("ad_count") or 0)


def smart_resolve_advertiser(g: GoogleAdsTransparency, raw_query: str) -> dict[str, Any] | None:
    """Resolve AR ID, domain, or brand name to the primary advertiser account."""
    q = parse_query(raw_query)
    if not q:
        return None
    if _AR_ID.fullmatch(q):
        return {"advertiser_id": q, "name": "", "ad_count": 0}
    if "." in q and " " not in q:
        dom = normalize_domain(q)
        adv = g.search_advertiser_by_domain(dom)
        brand_token = dom.split(".")[0]
        if adv and not is_parent_entity(dom, adv.get("name") or ""):
            return adv
        # Domain search matched an unrelated/reseller entity or nothing; check brand suggestions
        by_brand = _best_suggestion_by_brand(g, brand_token)
        if by_brand and not is_parent_entity(dom, by_brand.get("name") or ""):
            return by_brand
        return adv
    return _best_suggestion_by_brand(g, q)


def flatten_ad(
    ad: dict[str, Any],
    query: str,
    resolved_adv: dict[str, Any] | None = None,
    region: str = "anywhere",
) -> dict[str, Any]:
    c = ad.get("content") or {}
    adv_id = ad.get("advertiser_id") or (resolved_adv or {}).get("advertiser_id")
    adv_name = ad.get("advertiser_name") or (resolved_adv or {}).get("name")
    creative_id = ad.get("creative_id")
    return {
        "query": query,
        "advertiserId": adv_id,
        "advertiserName": adv_name,
        "advertiserTotalActiveAds": (resolved_adv or {}).get("ad_count"),
        "creativeId": creative_id,
        "format": ad.get("format"),
        "lastShown": ad.get("last_shown"),
        "region": region,
        "headline": clean_text(c.get("headline")),
        "description": clean_text(c.get("description")),
        "destinationUrl": c.get("destination_url"),
        "imageUrl": c.get("image_url"),
        "videoUrl": c.get("video_url"),
        "previewUrl": c.get("preview_url"),
        "transparencyUrl": (
            f"https://adstransparency.google.com/advertiser/{adv_id}/creative/{creative_id}"
            if adv_id and creative_id
            else None
        ),
    }


def fetch_ads(
    raw_query: str,
    max_ads: int = 20,
    region: str = "anywhere",
    ad_format: str = "all",
    client: GoogleAdsTransparency | None = None,
) -> list[dict[str, Any]]:
    """Resolve domain/ID/brand and fetch flattened ads."""
    g = client or GoogleAdsTransparency(region=region)
    adv = smart_resolve_advertiser(g, raw_query)
    if not adv or not adv.get("advertiser_id"):
        return []
    adv_id = adv["advertiser_id"]
    adv_name = adv.get("name") or parse_query(raw_query)
    fetch_count = max_ads if ad_format == "all" else min(max_ads * 3, 500)
    creative_ids = g.get_creative_ids(adv_id, fetch_count)
    results: list[dict[str, Any]] = []
    for cid in creative_ids:
        detail = g.get_ad_detail(adv_id, cid)
        detail["advertiser_name"] = adv_name
        fmt = (detail.get("format") or "").lower()
        if ad_format != "all" and fmt != ad_format.lower():
            continue
        results.append(flatten_ad(detail, raw_query, adv, region=region))
        if len(results) >= max_ads:
            break
    return results


def check_domains(
    raw_queries: list[str],
    region: str = "anywhere",
    client: GoogleAdsTransparency | None = None,
) -> list[dict[str, Any]]:
    """Bulk check whether each domain/brand runs Google Ads and return active ad counts."""
    g = client or GoogleAdsTransparency(region=region)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_queries:
        q = parse_query(raw)
        if not q or q in seen:
            continue
        seen.add(q)
        dom = normalize_domain(q) if "." in q and " " not in q else q
        try:
            adv = smart_resolve_advertiser(g, q)
        except Exception as exc:
            out.append({
                "domain": dom,
                "runsGoogleAds": False,
                "status": "error",
                "activeAdsCount": 0,
                "advertiserId": None,
                "advertiserName": None,
                "isParentOrExternalEntity": False,
                "region": region,
                "advertiserPageUrl": None,
                "note": str(exc)[:300],
            })
            continue
        if not adv or not adv.get("advertiser_id"):
            out.append({
                "domain": dom,
                "runsGoogleAds": False,
                "status": "absent",
                "activeAdsCount": 0,
                "advertiserId": None,
                "advertiserName": None,
                "isParentOrExternalEntity": False,
                "region": region,
                "advertiserPageUrl": None,
                "note": "no Google advertiser found for this domain",
            })
            continue
        adv_id = adv["advertiser_id"]
        adv_name = adv.get("name") or ""
        ad_cnt = int(adv.get("ad_count") or 0)
        parent = is_parent_entity(dom, adv_name) if "." in dom else False
        if ad_cnt >= 500:
            spend_tier = "Enterprise Spender (500+ active ads)"
            pitch = f"High-volume Google advertiser ({ad_cnt} active ads under {adv_name}). Pitch landing page CRO, creative testing, or omnichannel attribution."
        elif ad_cnt >= 50:
            spend_tier = "Growth Spender (50-499 active ads)"
            pitch = f"Scaling Google Ads spender ({ad_cnt} active ads). Pitch ROAS optimization, YouTube/Performance Max expansion, or competitor conquesting."
        elif ad_cnt >= 10:
            spend_tier = "Active Advertiser (10-49 active ads)"
            pitch = f"Active Google Ads budget ({ad_cnt} active ads). Pitch ad creative refresh and conversion tracking audit."
        elif ad_cnt >= 1:
            spend_tier = "Testing (1-9 active ads)"
            pitch = f"Early/testing Google Ads presence ({ad_cnt} active ads). Pitch full campaign setup and keyword scaling."
        else:
            spend_tier = "No Active Google Ads"
            pitch = "Verified advertiser profile with 0 active ads currently running — pitch campaign reactivation."
        out.append({
            "domain": dom,
            "runsGoogleAds": ad_cnt > 0,
            "status": "ok",
            "activeAdsCount": ad_cnt,
            "adSpendTier": spend_tier,
            "agencyPitchAngle": pitch,
            "advertiserId": adv_id,
            "advertiserName": adv_name,
            "isParentOrExternalEntity": parent,
            "region": region,
            "advertiserPageUrl": f"https://adstransparency.google.com/advertiser/{adv_id}?region={region}",
            "note": (
                f"resolves to {adv_name!r} (parent company or external advertiser mentioning {dom!r})"
                if parent
                else None
            ),
        })
    return out


def fetch_summary(
    raw_query: str,
    sample_size: int = 30,
    region: str = "anywhere",
    client: GoogleAdsTransparency | None = None,
) -> dict[str, Any]:
    """Summarize an advertiser's ad formats, landing domains, and sample copy."""
    q = parse_query(raw_query)
    g = client or GoogleAdsTransparency(region=region)
    adv = smart_resolve_advertiser(g, raw_query)
    if not adv or not adv.get("advertiser_id"):
        return {
            "query": raw_query,
            "parsedQuery": q,
            "status": "absent",
            "advertiserId": None,
            "advertiserName": None,
            "totalActiveAds": 0,
            "region": region,
            "summary": None,
            "note": "no advertiser matched this id, domain or name",
        }
    sample = max(1, min(sample_size, 100))
    creative_ids = g.get_creative_ids(adv["advertiser_id"], sample)
    ads = [g.get_ad_detail(adv["advertiser_id"], cid) for cid in creative_ids]
    return {
        "query": raw_query,
        "parsedQuery": q,
        "status": "ok",
        "advertiserId": adv["advertiser_id"],
        "advertiserName": adv.get("name"),
        "totalActiveAds": adv.get("ad_count", 0),
        "region": region,
        "summary": summarize_ads(ads),
        "note": None,
    }
