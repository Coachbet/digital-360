"""Adaptateurs HTTP vers les API officielles des régies publicitaires."""

from datetime import date, timedelta
from typing import Any

import httpx

from adgi360.shared.exceptions import ExternalServiceError, ValidationError


def _dates(preset: str) -> tuple[date, date]:
    end = date.today()
    days = {
        "today": 0,
        "yesterday": 0,
        "last_7d": 6,
        "last_14d": 13,
        "last_30d": 29,
        "this_month": end.day - 1,
    }.get(preset, 29)
    if preset == "yesterday":
        end -= timedelta(days=1)
    return end - timedelta(days=days), end


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _normalize(platform: str, preset: str, raw: dict[str, Any]) -> dict[str, Any]:
    spend = _number(raw.get("spend"))
    impressions = int(_number(raw.get("impressions")))
    clicks = int(_number(raw.get("clicks")))
    conversions = _number(raw.get("conversions"))
    conversion_value = _number(raw.get("conversion_value"))
    return {
        "platform": platform,
        "date_preset": preset,
        "currency": raw.get("currency"),
        "spend": spend,
        "impressions": impressions,
        "reach": int(_number(raw.get("reach"))),
        "clicks": clicks,
        "ctr": _number(raw.get("ctr")) or (clicks / impressions * 100 if impressions else 0),
        "cpc": _number(raw.get("cpc")) or (spend / clicks if clicks else 0),
        "cpm": _number(raw.get("cpm")) or (spend / impressions * 1000 if impressions else 0),
        "conversions": conversions,
        "purchase_roas": _number(raw.get("purchase_roas"))
        or (conversion_value / spend if spend else 0),
    }


class AdvertisingApiClient:
    def __init__(self, timeout: float = 45.0) -> None:
        self.timeout = timeout

    async def fetch(
        self, platform: str, account_id: str, credentials: dict[str, str], preset: str
    ) -> dict[str, Any]:
        method = getattr(self, f"_{platform}", None)
        if method is None:
            raise ValidationError(f"Plateforme publicitaire inconnue : {platform}")
        try:
            raw = await method(account_id, credentials, preset)
        except httpx.HTTPError as exc:
            detail = exc.response.text[:500] if isinstance(exc, httpx.HTTPStatusError) else str(exc)
            raise ExternalServiceError(f"{platform} est indisponible : {detail}") from exc
        return _normalize(platform, preset, raw)

    @staticmethod
    def _token(credentials: dict[str, str]) -> str:
        token = credentials.get("access_token", "").strip()
        if not token:
            raise ValidationError("Le jeton d’accès est requis")
        return token

    async def _google_ads(self, account_id: str, c: dict[str, str], preset: str) -> dict:
        start, end = _dates(preset)
        customer = "".join(ch for ch in account_id if ch.isdigit())
        headers = {
            "Authorization": f"Bearer {self._token(c)}",
            "developer-token": c.get("developer_token", ""),
            "Content-Type": "application/json",
        }
        if c.get("login_customer_id"):
            headers["login-customer-id"] = "".join(ch for ch in c["login_customer_id"] if ch.isdigit())
        query = (
            "SELECT customer.currency_code, metrics.cost_micros, metrics.impressions, "
            "metrics.clicks, metrics.conversions, metrics.conversions_value "
            f"FROM customer WHERE segments.date BETWEEN '{start}' AND '{end}'"
        )
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"https://googleads.googleapis.com/v25/customers/{customer}/googleAds:searchStream",
                headers=headers,
                json={"query": query},
            )
            response.raise_for_status()
        rows = [row for batch in response.json() for row in batch.get("results", [])]
        return {
            "currency": next((r.get("customer", {}).get("currencyCode") for r in rows if r.get("customer")), None),
            "spend": sum(_number(r.get("metrics", {}).get("costMicros")) for r in rows) / 1_000_000,
            "impressions": sum(_number(r.get("metrics", {}).get("impressions")) for r in rows),
            "clicks": sum(_number(r.get("metrics", {}).get("clicks")) for r in rows),
            "conversions": sum(_number(r.get("metrics", {}).get("conversions")) for r in rows),
            "conversion_value": sum(_number(r.get("metrics", {}).get("conversionsValue")) for r in rows),
        }

    async def _linkedin(self, account_id: str, c: dict[str, str], preset: str) -> dict:
        start, end = _dates(preset)
        version = c.get("api_version") or "202604"
        params = {
            "q": "analytics",
            "pivot": "ACCOUNT",
            "timeGranularity": "ALL",
            "accounts": f"List(urn:li:sponsoredAccount:{account_id})",
            "dateRange": (
                f"(start:(day:{start.day},month:{start.month},year:{start.year}),"
                f"end:(day:{end.day},month:{end.month},year:{end.year}))"
            ),
            "fields": "costInLocalCurrency,impressions,clicks,externalWebsiteConversions,conversionValueInLocalCurrency",
        }
        headers = {
            "Authorization": f"Bearer {self._token(c)}",
            "Linkedin-Version": version,
            "X-Restli-Protocol-Version": "2.0.0",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get("https://api.linkedin.com/rest/adAnalytics", params=params, headers=headers)
            response.raise_for_status()
        rows = response.json().get("elements", [])
        return {
            "spend": sum(_number(r.get("costInLocalCurrency")) for r in rows),
            "impressions": sum(_number(r.get("impressions")) for r in rows),
            "clicks": sum(_number(r.get("clicks")) for r in rows),
            "conversions": sum(_number(r.get("externalWebsiteConversions")) for r in rows),
            "conversion_value": sum(_number(r.get("conversionValueInLocalCurrency")) for r in rows),
        }

    async def _tiktok(self, account_id: str, c: dict[str, str], preset: str) -> dict:
        start, end = _dates(preset)
        params = {
            "advertiser_id": account_id,
            "service_type": "AUCTION",
            "report_type": "BASIC",
            "data_level": "AUCTION_ADVERTISER",
            "dimensions": '["advertiser_id"]',
            "metrics": '["spend","impressions","reach","clicks","ctr","cpc","cpm","conversion","total_purchase_value"]',
            "start_date": str(start),
            "end_date": str(end),
            "page_size": 1000,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/",
                params=params,
                headers={"Access-Token": self._token(c)},
            )
            response.raise_for_status()
        rows = response.json().get("data", {}).get("list", [])
        metrics = [r.get("metrics", {}) for r in rows]
        return {
            "spend": sum(_number(r.get("spend")) for r in metrics),
            "impressions": sum(_number(r.get("impressions")) for r in metrics),
            "reach": sum(_number(r.get("reach")) for r in metrics),
            "clicks": sum(_number(r.get("clicks")) for r in metrics),
            "conversions": sum(_number(r.get("conversion")) for r in metrics),
            "conversion_value": sum(_number(r.get("total_purchase_value")) for r in metrics),
        }

    async def _snapchat(self, account_id: str, c: dict[str, str], preset: str) -> dict:
        start, end = _dates(preset)
        params = {
            "granularity": "TOTAL",
            "start_time": f"{start}T00:00:00.000Z",
            "end_time": f"{end + timedelta(days=1)}T00:00:00.000Z",
            "fields": "spend,impressions,reach,swipes,total_conversions,purchase_value",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"https://adsapi.snapchat.com/v1/adaccounts/{account_id}/stats",
                params=params,
                headers={"Authorization": f"Bearer {self._token(c)}"},
            )
            response.raise_for_status()
        root = response.json()
        rows = root.get("total_stats", root.get("timeseries_stats", []))
        if isinstance(rows, dict):
            rows = [rows]
        stats = [r.get("stats", r) for r in rows]
        return {
            "spend": sum(_number(r.get("spend")) for r in stats) / 1_000_000,
            "impressions": sum(_number(r.get("impressions")) for r in stats),
            "reach": sum(_number(r.get("reach")) for r in stats),
            "clicks": sum(_number(r.get("swipes")) for r in stats),
            "conversions": sum(_number(r.get("total_conversions")) for r in stats),
            "conversion_value": sum(_number(r.get("purchase_value")) for r in stats) / 1_000_000,
        }
