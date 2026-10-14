import asyncio
import os
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")
load_dotenv(ROOT / ".env")

URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = os.getenv("LLM_MODEL", "nvidia/nemotron-3.5-lightning:free")
FALLBACK_MODELS = [
    m.strip() for m in os.getenv("LLM_FALLBACK_MODELS", "").split(",") if m.strip()
]

# OpenRouter's account limits and upstream provider limits vary. Keep all calls in
# this process serialized with a modest spacing; retries also honor Retry-After.
_request_lock = asyncio.Lock()
_last_request_at = 0.0
MIN_REQUEST_INTERVAL = float(os.getenv("OPENROUTER_MIN_INTERVAL", "3.1"))


class LLMError(RuntimeError):
    pass


async def chat(
    system: str,
    messages: list[dict],
    model: str | None = None,
    max_tokens: int = 1500,
    timeout: float = 60.0,
    retries: int | None = None,
    seed: int | None = None,
    temperature: float | None = None,
    models: list[str] | None = None,
) -> str:
    retries = (
        retries if retries is not None else int(os.getenv("OPENROUTER_RETRIES", "5"))
    )
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise LLMError("OPENROUTER_API_KEY is not set")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "X-Title": "UPSC Interview Mock",
    }
    requested_model = model or DEFAULT_MODEL
    routed_models = models or (
        [requested_model, *FALLBACK_MODELS] if FALLBACK_MODELS else None
    )
    body = {
        **({"models": routed_models} if routed_models else {"model": requested_model}),
        "messages": [{"role": "system", "content": system}, *messages],
        "max_tokens": max_tokens,
        "reasoning": {"enabled": False},
    }
    if seed is not None:
        body["seed"] = seed
    if temperature is not None:
        body["temperature"] = temperature
    last = "unknown error"
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(retries):
            try:
                async with _request_lock:
                    global _last_request_at
                    delay = MIN_REQUEST_INTERVAL - (time.monotonic() - _last_request_at)
                    if delay > 0:
                        await asyncio.sleep(delay)
                    _last_request_at = time.monotonic()
                    r = await client.post(URL, headers=headers, json=body)
            except httpx.HTTPError as e:
                last = f"network error: {e}"
                await asyncio.sleep(min(60, 2**attempt) + random.random())
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"HTTP {r.status_code} (rate limit or provider busy)"
                retry_after = r.headers.get("Retry-After")
                try:
                    wait_s = (
                        float(retry_after) if retry_after else min(90, 5 * 2**attempt)
                    )
                except ValueError:
                    try:
                        retry_at = parsedate_to_datetime(retry_after)
                        wait_s = max(
                            0, (retry_at - datetime.now(timezone.utc)).total_seconds()
                        )
                    except (TypeError, ValueError, OverflowError):
                        wait_s = min(90, 5 * 2**attempt)
                await asyncio.sleep(max(0, wait_s) + random.random())
                continue
            if r.status_code != 200:
                raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
            try:
                text = (r.json()["choices"][0]["message"].get("content") or "").strip()
            except Exception as e:
                last = f"unexpected response shape: {e}"
                continue
            if text:
                return text
            last = "empty reply"
    raise LLMError(last)
