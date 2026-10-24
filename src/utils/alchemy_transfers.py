"""Alchemy getAssetTransfers explorer client — pengganti API akun Etherscan
untuk Robinhood chain setelah free plan Etherscan dicabut utk chain 4663
("Free API access is not supported for this chain", 2026-10-24).

Basis: alchemy_getAssetTransfers (erc20/external/internal, pageKey pagination,
withMetadata=true → blockTimestamp). Mengekspos METHOD YANG SAMA dengan
EtherscanV2Client dan mengembalikan item berbentuk Blockscout
(tx_to_blockscout_shape / tx_to_funding_shape) sehingga pipeline tidak berubah.

Key: env ALCHEMY_API_KEYS (comma-separated) — bila kosong, di-derive dari URL
g.alchemy.com di EVM_RPC_ENDPOINTS (sudah ada di .env, tanpa kredensial baru).
Rotasi key round-robin per request.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from aiolimiter import AsyncLimiter

from config.settings import settings
from src.utils.etherscan_client import (
    SEL_DECIMALS,
    SEL_NAME,
    SEL_SYMBOL,
    decode_abi_string,
    decode_abi_uint,
)

log = logging.getLogger("walletintel.alchemy")

BASE = "https://robinhood-mainnet.g.alchemy.com/v2/{}"
MAX_COUNT = "0x3e8"  # 1000 transfer per halaman (maks Alchemy)


def _keys_from_env() -> list[str]:
    import os
    explicit = os.getenv("ALCHEMY_API_KEYS", "")
    keys = [k.strip() for k in explicit.split(",") if k.strip()]
    if keys:
        return keys
    # derive dari endpoint RPC .env: https://robinhood-mainnet.g.alchemy.com/v2/<key>
    for url in settings.evm_rpc_endpoints:
        p = urlparse(url)
        if p.hostname and p.hostname.endswith("g.alchemy.com"):
            k = p.path.lstrip("/v2/").strip("/")
            if k:
                keys.append(k)
    # unik, urut stabil
    return list(dict.fromkeys(keys))


def _iso_to_epoch(ts: str | None) -> int:
    if not ts:
        return 0
    try:
        return int(datetime.fromisoformat(ts.replace("Z", "+00:00"))
                   .astimezone(timezone.utc).timestamp())
    except ValueError:
        return 0


class AlchemyTransfersClient:
    """Drop-in utk EtherscanV2Client di atas getAssetTransfers."""

    def __init__(self, rps: float | None = None):
        self.keys = _keys_from_env()
        if not self.keys:
            raise ValueError("ALCHEMY_API_KEYS kosong & tidak ada URL alchemy di EVM_RPC_ENDPOINTS")
        self._idx = random.randrange(len(self.keys))
        self._limiter = AsyncLimiter(rps or settings.etherscan_rps * len(self.keys), 1.0)
        self._client: httpx.AsyncClient | None = None
        self._consec_err = 0

    # ---------------- infra ----------------

    @property
    def is_etherscan(self) -> bool:
        return False

    @property
    def is_degraded(self) -> bool:
        return self._consec_err >= 5

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0),
                                             headers={"User-Agent": "WalletIntel/0.1"})
        return self._client

    async def _rpc(self, method: str, params: list[Any]) -> dict | None:
        """POST JSON-RPC dgn rotasi key; return envelope dict atau None."""
        last_err = ""
        for attempt in range(5):
            self._idx = (self._idx + 1) % len(self.keys)
            url = BASE.format(self.keys[self._idx])
            try:
                client = await self._http()
                async with self._limiter:
                    resp = await client.post(url, json={
                        "jsonrpc": "2.0", "id": 1, "method": method, "params": params})
                if resp.status_code in (401, 403, 429):
                    last_err = f"http {resp.status_code}"
                    await asyncio.sleep(min(30.0, 2.0 * (2 ** attempt)))
                    continue
                data = resp.json()
                if isinstance(data, dict) and data.get("error"):
                    last_err = str(data["error"])[:120]
                    await asyncio.sleep(min(30.0, 1.5 * (2 ** attempt)))
                    continue
                self._consec_err = 0
                return data
            except (httpx.HTTPError, ValueError) as e:
                last_err = f"{type(e).__name__}: {str(e)[:80]}"
                await asyncio.sleep(min(30.0, 2.0 * (2 ** attempt)))
        self._consec_err += 1
        log.warning("alchemy %s gagal setelah retry: %s", method, last_err)
        return None

    async def _transfers(self, params: dict, max_pages: int,
                         sorter_desc: bool) -> list[dict]:
        """Loop pageKey; return list transfer mentah Alchemy."""
        out: list[dict] = []
        page_key: str | None = None
        order = "desc" if sorter_desc else "asc"
        for _ in range(max(1, max_pages)):
            p = dict(params)
            p["maxCount"] = MAX_COUNT
            p["order"] = order
            p["withMetadata"] = True
            if page_key:
                p["pageKey"] = page_key
            data = await self._rpc("alchemy_getAssetTransfers", [p])
            res = (data or {}).get("result") or {}
            out.extend(res.get("transfers") or [])
            page_key = res.get("pageKey")
            if not page_key or not res.get("transfers"):
                break
        return out

    # ---------------- transfers (bentuk Blockscout, identik Etherscan) ---

    @staticmethod
    def _to_transfer_shape(t: dict) -> dict:
        raw = t.get("rawContract") or {}
        dec_hex = raw.get("decimal")
        try:
            decimals = int(dec_hex, 16) if dec_hex else 18
        except (TypeError, ValueError):
            decimals = 18
        val_hex = raw.get("value")
        try:
            value = str(int(val_hex, 16)) if val_hex else "0"
        except (TypeError, ValueError):
            value = str(int(t.get("value") or 0))
        return {
            "from": {"hash": (t.get("from") or "").lower(), "is_contract": False},
            "to": {"hash": (t.get("to") or "").lower(), "is_contract": False},
            "token": {
                "address": ((raw.get("address") or "")).lower(),
                "decimals": decimals,
                "symbol": t.get("asset") or "",
                "name": t.get("asset") or "",
            },
            "total": {"value": value},
            "block_number": int(t.get("blockNum") or "0x0", 16),
            "timestamp": str(_iso_to_epoch((t.get("metadata") or {}).get("blockTimestamp"))),
            "transaction_hash": (t.get("hash") or "").lower(),
        }

    @staticmethod
    def _to_funding_shape(t: dict, internal: bool) -> dict:
        raw = t.get("rawContract") or {}
        val_hex = raw.get("value")
        try:
            value = str(int(val_hex, 16)) if val_hex else "0"
        except (TypeError, ValueError):
            value = "0"
        return {
            "from": {"hash": (t.get("from") or "").lower(), "is_contract": False, "name": ""},
            "to": {"hash": (t.get("to") or "").lower(), "is_contract": False},
            "value": value,
            "hash": (t.get("hash") or "").lower(),
            "block_number": int(t.get("blockNum") or "0x0", 16),
            "timestamp": _iso_to_epoch((t.get("metadata") or {}).get("blockTimestamp")),
            "internal": internal,
        }

    async def address_token_transfers(self, wallet: str, max_pages: int,
                                      token_filter: str | None = None,
                                      sort: str = "asc") -> list[dict]:
        """ERC-20 transfer wallet KEDUA arah (from+to) — setara tokentx."""
        items: list[dict] = []
        for direction in ("fromAddress", "toAddress"):
            p: dict[str, Any] = {"category": ["erc20"], direction: wallet.lower()}
            if token_filter:
                p["contractAddresses"] = [token_filter.lower()]
            raw = await self._transfers(p, max_pages, sorter_desc=(sort == "desc"))
            items.extend(self._to_transfer_shape(t) for t in raw)
        items.sort(key=lambda x: x["block_number"])
        return items

    async def address_transactions(self, wallet: str, max_pages: int,
                                   sort: str = "asc") -> list[dict]:
        """Tx native ETH masuk/keluar — funding shape. Kategori 'internal'
        TIDAK didukung getAssetTransfers di network ini (-32602); hanya
        external (first-touch funding tetap terjangkau — transfer internal
        via kontrak dilewati, dicatat sebagai keterbatasan)."""
        out: list[dict] = []
        for direction in ("fromAddress", "toAddress"):
            p: dict[str, Any] = {"category": ["external"], direction: wallet.lower()}
            raw = await self._transfers(p, max_pages, sorter_desc=(sort == "desc"))
            out.extend(self._to_funding_shape(t, False) for t in raw)
        out.sort(key=lambda x: x["block_number"])
        return out

    async def token_transfers(self, ca: str, max_pages: int) -> list[dict]:
        """Semua transfer sebuah token (discovery trader)."""
        p: dict[str, Any] = {"category": ["erc20"], "contractAddresses": [ca.lower()]}
        raw = await self._transfers(p, max_pages, sorter_desc=True)
        return [self._to_transfer_shape(t) for t in raw]

    async def token_holders(self, ca: str, max_items: int) -> list[dict]:
        """Sama spt EtherscanV2Client: derivasi dari trader aktif token."""
        items = await self.token_transfers(ca, max_pages=max(1, max_items // 100))
        seen: dict[str, dict] = {}
        for it in items:
            for side in ("from", "to"):
                a = (it.get(side) or {}).get("hash") or ""
                if a and a not in seen and a != "0x" + "0" * 40:
                    seen[a] = {"address": {"hash": a}, "is_contract": False}
            if len(seen) >= max_items:
                break
        return list(seen.values())[:max_items]

    # ---------------- metadata ----------------

    async def token_info(self, ca: str) -> dict:
        """decimals/symbol/name via eth_call JSON-RPC (native Alchemy)."""
        info: dict[str, Any] = {"address": ca.lower()}

        async def call(sel: str) -> str:
            data = await self._rpc("eth_call", [{"to": ca.lower(), "data": sel}, "latest"])
            return (data or {}).get("result") or ""

        dec_hex, sym_hex = await asyncio.gather(call(SEL_DECIMALS), call(SEL_SYMBOL))
        n = decode_abi_uint(dec_hex)
        if n is not None and 0 <= n <= 36:
            info["decimals"] = str(n)
        sym = decode_abi_string(sym_hex)
        if sym:
            info["symbol"] = sym
            info["name"] = sym
        return info

    async def chain_tokens(self, max_pages: int = 8) -> list[dict]:
        return []

    async def stats(self) -> dict:
        """Harga ETH — CoinGecko public (tanpa key); gagal = {}."""
        try:
            client = await self._http()
            async with self._limiter:
                r = await client.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": "ethereum", "vs_currencies": "usd"})
            usd = float(r.json()["ethereum"]["usd"])
            return {"coin_price": usd}
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return {}

    async def close(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None
