"""Call cost from the per-token prices of a catalog model.

``None`` when there is no price: the signal of "no price" the report counts
apart. Estimating from a similar model would give a number that looks right
and is not, and the report exists to be trusted.

``TRIPAULX["AI_PRICE_OVERRIDES"]`` maps ``"provider:identifier"`` to
``{"input", "cached", "output"}`` (USD per 1M tokens) and wins over the
catalog row, so a project can follow a price change before the catalog does.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from tripaulx.ai.conf import app_settings

ONE_MILLION = Decimal(1_000_000)
QUANTUM = Decimal("0.000001")


@dataclass(frozen=True)
class Prices:
    """USD per 1M tokens; ``None`` means no price for that part."""

    input: Decimal | None
    cached: Decimal | None
    output: Decimal | None


def _decimal(value: Any) -> Decimal | None:
    return Decimal(str(value)) if value not in (None, "") else None


def prices_for(model: Any) -> Prices | None:
    """Return the prices of ``model`` (override first), or ``None``."""
    if model is None:
        return None
    key = f"{getattr(model, 'provider', '')}:{getattr(model, 'identifier', '')}"
    override = (app_settings.AI_PRICE_OVERRIDES or {}).get(key)
    if override:
        prices = Prices(
            input=_decimal(override.get("input")),
            cached=_decimal(override.get("cached")),
            output=_decimal(override.get("output")),
        )
    else:
        prices = Prices(
            input=model.input_price_usd_1m,
            cached=model.cached_price_usd_1m,
            output=model.output_price_usd_1m,
        )
    if prices.input is None and prices.output is None:
        return None
    return prices


def cost_usd(
    model: Any,
    input_tokens: int | None,
    output_tokens: int | None,
    *,
    cached_tokens: int | None = 0,
) -> Decimal | None:
    """USD spent: uncached input + cached input + output, each at its price.

    ``input_tokens`` includes the cached ones; cached tokens are billed at
    the cached price, or at the input price when there is none.
    """
    prices = prices_for(model)
    if prices is None:
        return None
    entry = Decimal(input_tokens or 0)
    out = Decimal(output_tokens or 0)
    cached = min(Decimal(cached_tokens or 0), entry)
    total = Decimal(0)
    if prices.input is not None:
        total += (entry - cached) / ONE_MILLION * prices.input
        cached_price = prices.cached if prices.cached is not None else prices.input
        total += cached / ONE_MILLION * cached_price
    if prices.output is not None:
        total += out / ONE_MILLION * prices.output
    return total.quantize(QUANTUM)


def web_search_price() -> Decimal:
    """Price of one web search (USD)."""
    return Decimal(str(app_settings.AI_WEB_SEARCH_PRICE_USD))
