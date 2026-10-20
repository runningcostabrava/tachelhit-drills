"""Gemini usage meter and spending caps.

Two limits protect the owner's Gemini key:

1. A monthly money budget (GEMINI_MONTHLY_BUDGET_EUR, default 10 €) over EVERY Gemini call the
   backend makes (tutor, copilot, captures, topics, voices, pictures). Each call's tokens are
   priced from the response's usageMetadata and written to the gemini_usage table; once the
   month's total reaches the budget, calls raise BudgetExceeded until the 1st of next month.
2. A per-person daily cap on the interactive AI features (AI_DAILY_LIMIT, default 20 for a
   signed-in user; AI_DAILY_LIMIT_ANON, default 5 per anonymous client; admins unlimited).

Prices are list prices in USD per million tokens (GEMINI_PRICES_JSON overrides), converted
with GEMINI_USD_EUR (default 0.92). If the key is on the free tier the money is notional, but
it is still the right proxy for "how much of my capacity is this using".
"""
from __future__ import annotations

import contextvars
import json
import os
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from sqlalchemy import func

from gemini_client import BudgetExceeded  # noqa: F401  (re-exported for callers)

# USD per 1M tokens: (input, output). Images: USD per generated image.
_DEFAULT_PRICES: Dict[str, Dict[str, float]] = {
    "gemini-2.5-flash": {"in": 0.30, "out": 2.50},
    "gemini-2.5-flash-lite": {"in": 0.10, "out": 0.40},
    "gemini-2.0-flash": {"in": 0.10, "out": 0.40},
    "gemini-2.0-flash-lite": {"in": 0.075, "out": 0.30},
    "gemini-2.5-pro": {"in": 1.25, "out": 10.00},
    "gemini-2.5-flash-image": {"in": 0.30, "out": 2.50, "image": 0.039},
}
_FALLBACK_PRICE = {"in": 0.30, "out": 2.50, "image": 0.039}

INTERACTIVE_FEATURES = ("ask", "agent", "explain", "analyze", "suggest", "review")

# Set by the endpoint (or a pipeline) so the meter can attribute a call; defaults mean
# "background pipeline, no particular person".
_feature: contextvars.ContextVar[str] = contextvars.ContextVar("ai_feature", default="pipeline")
_actor: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("ai_actor", default=None)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "") or default)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "") or default)
    except ValueError:
        return default


def monthly_budget_eur() -> float:
    return _env_float("GEMINI_MONTHLY_BUDGET_EUR", 10.0)


def daily_limit(is_admin: bool, anonymous: bool) -> Optional[int]:
    if is_admin:
        return None
    return _env_int("AI_DAILY_LIMIT_ANON", 5) if anonymous else _env_int("AI_DAILY_LIMIT", 20)


def prices() -> Dict[str, Dict[str, float]]:
    table = dict(_DEFAULT_PRICES)
    raw = (os.getenv("GEMINI_PRICES_JSON") or "").strip()
    if raw:
        try:
            for k, v in json.loads(raw).items():
                table[k] = {**table.get(k, {}), **v}
        except (ValueError, TypeError, AttributeError):
            pass
    return table


def price_for(model: str) -> Dict[str, float]:
    table = prices()
    m = (model or "").lower()
    if m in table:
        return table[m]
    # "gemini-2.5-flash-preview-05-20" -> longest known prefix
    best = ""
    for k in table:
        if m.startswith(k) and len(k) > len(best):
            best = k
    return table[best] if best else _FALLBACK_PRICE


def cost_micro_eur(model: str, prompt_tokens: int, output_tokens: int, images: int) -> int:
    p = price_for(model)
    usd = (prompt_tokens * p.get("in", 0.0) + output_tokens * p.get("out", 0.0)) / 1_000_000.0
    usd += images * p.get("image", 0.0)
    return int(round(usd * _env_float("GEMINI_USD_EUR", 0.92) * 1_000_000))


def usage_from_response(data: Dict[str, Any]) -> Dict[str, int]:
    """Tokens and generated images out of a generateContent response."""
    meta = (data or {}).get("usageMetadata") or {}
    prompt = int(meta.get("promptTokenCount") or 0)
    out = int(meta.get("candidatesTokenCount") or 0) + int(meta.get("thoughtsTokenCount") or 0)
    images = 0
    for cand in (data or {}).get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            if "inlineData" in part or "inline_data" in part:
                images += 1
    return {"prompt_tokens": prompt, "output_tokens": out, "images": images}


def set_context(feature: str, actor: Optional[str]) -> None:
    _feature.set(feature)
    _actor.set(actor)


def month_start(now: Optional[datetime] = None) -> datetime:
    now = now or datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


class Meter:
    """Bound to the app's session factory and the GeminiUsage model at startup."""

    def __init__(self, session_factory: Callable, usage_model):
        self.session_factory = session_factory
        self.Usage = usage_model
        self._spent_cache: tuple[float, int] = (0.0, 0)  # (checked_at_ts, micro_eur)

    # ---- totals -------------------------------------------------------------------
    def month_spent_micro(self, fresh: bool = False) -> int:
        now_ts = datetime.utcnow().timestamp()
        if not fresh and now_ts - self._spent_cache[0] < 30:
            return self._spent_cache[1]
        with self.session_factory() as db:
            total = db.query(func.coalesce(func.sum(self.Usage.cost_micro_eur), 0)).filter(
                self.Usage.at >= month_start()).scalar() or 0
        self._spent_cache = (now_ts, int(total))
        return int(total)

    def month_by_feature(self) -> Dict[str, Dict[str, float]]:
        with self.session_factory() as db:
            rows = db.query(self.Usage.feature, func.count(self.Usage.id), func.sum(self.Usage.cost_micro_eur),
                            func.sum(self.Usage.prompt_tokens), func.sum(self.Usage.output_tokens)
                            ).filter(self.Usage.at >= month_start()).group_by(self.Usage.feature).all()
        return {f: {"calls": int(n), "eur": round((c or 0) / 1_000_000, 4), "prompt_tokens": int(pt or 0),
                    "output_tokens": int(ot or 0)} for f, n, c, pt, ot in rows}

    def today_count(self, actor: str) -> int:
        since = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        with self.session_factory() as db:
            return int(db.query(func.count(self.Usage.id)).filter(
                self.Usage.actor == actor, self.Usage.at >= since,
                self.Usage.feature.in_(INTERACTIVE_FEATURES)).scalar() or 0)

    def budget_remaining_eur(self) -> float:
        return round(monthly_budget_eur() - self.month_spent_micro() / 1_000_000, 4)

    def budget_ok(self) -> bool:
        return self.month_spent_micro() < monthly_budget_eur() * 1_000_000

    def next_reset(self) -> datetime:
        ms = month_start()
        return (ms + timedelta(days=32)).replace(day=1)

    # ---- hooks used by gemini_client ------------------------------------------------
    def before_call(self, model: str) -> None:
        if not self.budget_ok():
            raise BudgetExceeded(
                f"Pressupost mensual d'IA esgotat ({monthly_budget_eur():.0f} €). "
                f"Torna a estar disponible l'1 del mes que ve.")

    def after_call(self, model: str, data: Optional[Dict[str, Any]], ok: bool) -> None:
        u = usage_from_response(data) if (ok and data) else {"prompt_tokens": 0, "output_tokens": 0, "images": 0}
        cost = cost_micro_eur(model, u["prompt_tokens"], u["output_tokens"], u["images"]) if ok else 0
        try:
            with self.session_factory() as db:
                db.add(self.Usage(model=model, feature=_feature.get(), actor=_actor.get(),
                                  prompt_tokens=u["prompt_tokens"], output_tokens=u["output_tokens"],
                                  images=u["images"], cost_micro_eur=cost, ok=ok))
                db.commit()
            # keep the cached month total honest without a query per call
            self._spent_cache = (self._spent_cache[0], self._spent_cache[1] + cost)
        except Exception as e:  # the meter must never break the call it measured
            print(f"[AI-BUDGET] could not record usage: {e}")

    # ---- the per-person gate for interactive features ---------------------------------
    def check_person(self, actor: str, is_admin: bool, anonymous: bool) -> Dict[str, Any]:
        """Raises BudgetExceeded when the month's money or the person's day is used up;
        otherwise returns the counters the client can show."""
        if not self.budget_ok():
            self.before_call("")
        limit = daily_limit(is_admin, anonymous)
        used = self.today_count(actor)
        if limit is not None and used >= limit:
            raise BudgetExceeded(
                f"Has fet servir les {limit} consultes d'IA d'avui"
                + ("; entra amb el teu compte per tenir-ne més." if anonymous else ". Demà en tindràs més."))
        return {"used": used, "limit": limit, "remaining": None if limit is None else limit - used}

    def summary(self, actor: Optional[str], is_admin: bool, anonymous: bool) -> Dict[str, Any]:
        limit = daily_limit(is_admin, anonymous)
        used = self.today_count(actor) if actor else 0
        spent = self.month_spent_micro() / 1_000_000
        out: Dict[str, Any] = {
            "today": {"used": used, "limit": limit, "remaining": None if limit is None else max(0, limit - used)},
            "month": {"spent_eur": round(spent, 4), "budget_eur": monthly_budget_eur(),
                      "remaining_eur": round(max(0.0, monthly_budget_eur() - spent), 4),
                      "resets_at": self.next_reset().isoformat() + "Z"},
            "available": self.budget_ok(),
        }
        if is_admin:
            out["month"]["by_feature"] = self.month_by_feature()
        return out
