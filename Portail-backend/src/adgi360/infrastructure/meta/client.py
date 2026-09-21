"""Appels aux API officielles Meta Ads et Instagram."""

from typing import Any

import httpx

from adgi360.infrastructure.config.settings import settings
from adgi360.shared.exceptions import ExternalServiceError


class MetaClient:
    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout
        self._version = settings.meta_graph_api_version

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            error = response.json().get("error", {})
            return error.get("error_user_msg") or error.get("message") or response.text
        except (ValueError, AttributeError):
            return response.text or response.reason_phrase

    async def _request(
        self, method: str, url: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(method, url, params=params)
        except httpx.RequestError as exc:
            raise ExternalServiceError(f"Meta est indisponible : {exc}") from exc
        if response.is_error:
            raise ExternalServiceError(f"Erreur Meta : {self._error_message(response)}")
        try:
            return response.json()
        except ValueError as exc:
            raise ExternalServiceError("Meta a renvoyé une réponse illisible") from exc

    async def get_ad_kpis(
        self, ad_account_id: str, access_token: str, date_preset: str
    ) -> dict[str, Any]:
        account = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        url = f"https://graph.facebook.com/{self._version}/{account}/insights"
        payload = await self._request(
            "GET",
            url,
            params={
                "access_token": access_token,
                "date_preset": date_preset,
                "level": "account",
                "fields": (
                    "spend,impressions,reach,clicks,ctr,cpc,cpm,actions,"
                    "purchase_roas,account_currency"
                ),
            },
        )
        rows = payload.get("data") or []
        row = rows[0] if rows else {}

        conversion_types = {
            "purchase",
            "offsite_conversion.fb_pixel_purchase",
            "lead",
            "onsite_conversion.lead_grouped",
        }
        conversions = sum(
            float(action.get("value", 0))
            for action in row.get("actions", [])
            if action.get("action_type") in conversion_types
        )
        roas_rows = row.get("purchase_roas") or []
        purchase_roas = float(roas_rows[0].get("value", 0)) if roas_rows else 0.0
        return {
            "date_preset": date_preset,
            "currency": row.get("account_currency"),
            "spend": float(row.get("spend", 0)),
            "impressions": int(row.get("impressions", 0)),
            "reach": int(row.get("reach", 0)),
            "clicks": int(row.get("clicks", 0)),
            "ctr": float(row.get("ctr", 0)),
            "cpc": float(row.get("cpc", 0)),
            "cpm": float(row.get("cpm", 0)),
            "conversions": conversions,
            "purchase_roas": purchase_roas,
        }

    async def publish_instagram_image(
        self, instagram_user_id: str, access_token: str, image_url: str, caption: str
    ) -> str:
        base = f"https://graph.instagram.com/{self._version}/{instagram_user_id}"
        container = await self._request(
            "POST",
            f"{base}/media",
            params={
                "access_token": access_token,
                "image_url": image_url,
                "caption": caption,
            },
        )
        creation_id = container.get("id")
        if not creation_id:
            raise ExternalServiceError("Meta n'a pas créé le média Instagram")
        published = await self._request(
            "POST",
            f"{base}/media_publish",
            params={"access_token": access_token, "creation_id": creation_id},
        )
        post_id = published.get("id")
        if not post_id:
            raise ExternalServiceError("Meta n'a pas confirmé la publication Instagram")
        return str(post_id)


def get_meta_client() -> MetaClient:
    return MetaClient()
