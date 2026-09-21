import pytest

from adgi360.infrastructure.meta.client import MetaClient


@pytest.mark.asyncio
async def test_meta_insights_are_normalized(monkeypatch):
    async def fake_request(*args, **kwargs):
        return {
            "data": [
                {
                    "account_currency": "EUR",
                    "spend": "120.50",
                    "impressions": "10000",
                    "reach": "7200",
                    "clicks": "250",
                    "ctr": "2.5",
                    "cpc": "0.482",
                    "cpm": "12.05",
                    "actions": [
                        {"action_type": "lead", "value": "12"},
                        {"action_type": "link_click", "value": "250"},
                    ],
                    "purchase_roas": [{"action_type": "omni_purchase", "value": "4.2"}],
                }
            ]
        }

    client = MetaClient()
    monkeypatch.setattr(client, "_request", fake_request)

    result = await client.get_ad_kpis("123", "token", "last_30d")

    assert result["currency"] == "EUR"
    assert result["spend"] == 120.5
    assert result["impressions"] == 10000
    assert result["conversions"] == 12
    assert result["purchase_roas"] == 4.2
