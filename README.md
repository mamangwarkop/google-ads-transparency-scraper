# Google Ads Transparency Scraper & Bulk Domain Ad-Spend Checker (3-in-1)

[![Apify Store](https://img.shields.io/badge/Apify%20Store-Live%20Actor-orange?logo=apify&style=for-the-badge)](https://apify.com/mamang_warkop/google-ads-transparency-scraper) [![GitHub Release](https://img.shields.io/github/v/release/mamangwarkop/google-ads-transparency-scraper?color=purple&style=for-the-badge)](https://github.com/mamangwarkop/google-ads-transparency-scraper/releases) [![n8n Compatible](https://img.shields.io/badge/n8n-Workflow%20Ready-FF6D5A?logo=n8n&style=for-the-badge)](https://mamangwarkop.github.io/n8n-google-ads-lead-enricher.json) [![Clay](https://img.shields.io/badge/Clay-Enrichment%20Ready-6366F1?style=for-the-badge)](https://mamangwarkop.github.io)

> ⚡ **Run in the Cloud without local setup, Python, or managing proxies:**  
> **[👉 Run on Apify Cloud (5,000 Free Results/mo)](https://apify.com/mamang_warkop/google-ads-transparency-scraper)**



Extract active **text, image, and video ad creatives** from the **Google Ads Transparency Center** (Google Ad Library), bulk-qualify **whether thousands of B2B prospect domains are actively paying for Google Ads**, or generate an instant **Competitor Ad Strategy Summary** — with **zero login, zero cookies, and zero headless browser overhead**.

---

## Why Choose This Actor Over Other Google Ads Scrapers?

| Feature | Our Actor (`mamang_warkop`) | Typical Ads Transparency Scrapers |
| :--- | :--- | :--- |
| **Primary Brand Advertiser Resolution** | **Smart Volume & Domain Matching:** Matches the true primary brand advertiser (`shopify.com` &rarr; `Shopify Inc.`, 70,000+ ads) instead of random third-party resellers. | Often returns the first small merchant or affiliate mentioning the domain (`Life and Fork Pty Ltd`). |
| **3-in-1 Modes Included** | **`ads` + `check_domains` + `summary`** in a single Actor. | Requires paying for 2–3 separate Actors. |
| **B2B Ad-Spend Tier & Sales Pitch Angle** | Automatically classifies **`adSpendTier`** (`Enterprise`, `Growth`, `Active`, `Testing`, `None`) + generates **`agencyPitchAngle`** for cold outreach. | Raw numbers only. |
| **Dynamic Placeholder Cleanup** | Automatically cleans `{KeyWord:Running Shoes}` into clean human-readable copy (`Running Shoes`). | Raw unparsed Google internal syntax. |
| **Flexible Input Parsing** | Accepts **domains** (`nike.com`), **full URLs** (`https://www.nike.com/running`), **brand names** (`Nike`), **AR IDs** (`AR1837...`), or **Transparency URLs**. | Breaks if you paste a full URL or brand name. |
| **Speed & Compute Cost** | **Pure HTTP RPC** — finishes in seconds using minimal Apify memory (512 MB). | Heavy Playwright/Puppeteer browsers that eat up your compute credits. |

---

## Step-by-Step Usage Guide (Panduan Penggunaan)

### Option A: Run Directly in Apify Console (No Coding Required)
1. **Enter Target Queries (`queries`):** Type or paste one or more company domains (`nike.com`, `shopify.com`), brand names (`Stripe`), or Google Advertiser IDs (`AR09026146787696115713`).
2. **Select Mode (`mode`):**
   - Choose **`Extract Ad Creatives (ads)`** if you want every individual ad's headline, description, landing page URL, image link, and video URL.
   - Choose **`Bulk Check Domains for Active Google Ads (check_domains)`** if you have a list of B2B lead domains (from Apollo, Clay, or Google Maps) and want to know which companies are actively spending money on Google Ads.
   - Choose **`Advertiser Strategy Summary (summary)`** for a high-level breakdown of ad formats (`text` vs `image` vs `video`) and top destination domains.
3. **Choose Region (`region`):** Leave as `"anywhere"` for global ad activity, or enter a 2-letter ISO country code (`"US"`, `"GB"`, `"DE"`, `"AU"`, `"CA"`, `"ID"`, `"SG"`, `"BR"`, etc.).
4. Click **Start** at the bottom, then download your results in **Excel, CSV, or JSON** from the **Storage / Dataset** tab.

---

### Option B: Automate with Clay.com, n8n, or Make.com
Use the synchronous REST endpoint to enrich leads in real time inside **Clay**, **n8n** (`HTTP Request` node), or **Make.com**:

```bash
curl -X POST "https://api.apify.com/v2/acts/mamang_warkop~google-ads-transparency-scraper/run-sync-get-dataset-items?token=YOUR_APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "queries": ["nike.com", "shopify.com", "gymshark.com"],
    "mode": "check_domains",
    "region": "anywhere"
  }'
```

---

### Option C: Call via Python or JavaScript SDK

#### Python
```python
from apify_client import ApifyClient

client = ApifyClient("YOUR_APIFY_API_TOKEN")
run = client.actor("mamang_warkop/google-ads-transparency-scraper").call(
    run_input={
        "queries": ["nike.com", "shopify.com"],
        "mode": "ads",
        "maxAdsPerQuery": 25,
        "adFormat": "all",
        "region": "US",
    }
)

for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(item["advertiserName"], item["format"], item.get("headline") or item.get("imageUrl"))
```

#### JavaScript / Node.js
```javascript
import { ApifyClient } from 'apify-client';

const client = new ApifyClient({ token: 'YOUR_APIFY_API_TOKEN' });
const run = await client.actor('mamang_warkop/google-ads-transparency-scraper').call({
    queries: ['nike.com', 'shopify.com'],
    mode: 'check_domains',
    region: 'US',
});

const { items } = await client.dataset(run.defaultDatasetId).listItems();
console.log(items);
```

---

## Input Parameters Reference

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `queries` | `array` | `["nike.com", "shopify.com"]` | List of domains, full URLs, brand names, Advertiser IDs (`AR...`), or Google Ads Transparency URLs. |
| `mode` | `string` | `"ads"` | `"ads"` (individual creatives), `"check_domains"` (bulk B2B ad-spend qualifier), or `"summary"` (strategy overview). |
| `maxAdsPerQuery` | `integer` | `10` | Maximum number of creatives to fetch per advertiser (1–500). |
| `adFormat` | `string` | `"all"` | Filter creatives by format: `"all"`, `"text"`, `"image"`, or `"video"`. |
| `region` | `string` | `"US"` | `"anywhere"` for global ads, or ISO-2 country code (`"US"`, `"GB"`, `"DE"`, `"CA"`, `"AU"`, `"ID"`, `"SG"`, etc.). |
| `proxyConfiguration` | `object` | Optional | Optional Apify Proxy configuration for very large multi-hundred domain batches. |

---

## Output Examples

### 1. Mode `ads` (Ad Creative Spy)
```json
{
  "query": "nike.com",
  "advertiserId": "AR18378488041124659201",
  "advertiserName": "Nike Retail BV",
  "advertiserTotalActiveAds": 80000,
  "creativeId": "CR02178781504182681601",
  "format": "text",
  "lastShown": "2026-10-20",
  "region": "US",
  "headline": "Nike Official Store - Free Shipping & Returns",
  "description": "Shop the latest Nike running shoes, apparel, and gear.",
  "destinationUrl": "nike.com",
  "imageUrl": null,
  "videoUrl": null,
  "transparencyUrl": "https://adstransparency.google.com/advertiser/AR18378488041124659201/creative/CR02178781504182681601"
}
```

### 2. Mode `check_domains` (Bulk B2B Ad-Spend Qualifier)
```json
{
  "domain": "shopify.com",
  "runsGoogleAds": true,
  "status": "ok",
  "activeAdsCount": 70000,
  "adSpendTier": "Enterprise Spender (500+ active ads)",
  "agencyPitchAngle": "High-volume Google advertiser (70000 active ads under Shopify Inc.). Pitch landing page CRO, creative testing, or omnichannel attribution.",
  "advertiserId": "AR09026146787696115713",
  "advertiserName": "Shopify Inc.",
  "isParentOrExternalEntity": false,
  "region": "anywhere",
  "advertiserPageUrl": "https://adstransparency.google.com/advertiser/AR09026146787696115713?region=anywhere"
}
```

---

## Transparent Pricing
- **Pay-Per-Event:** `$0.001` per result (`$1.00 per 1,000 results`).
- Covered automatically by Apify's free monthly starter credit (`$5.00/month` = up to **5,000 results/month free**).

## Support & Feature Requests
Have a question, found an edge case, or need a custom field for your agency workflow? Open an issue in the **Issues** tab on this Actor page — we monitor and respond rapidly.