#!/usr/bin/env python3
import os
import sys
import json
import asyncio
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from custom_components.hass_cudy_router.router import CudyRouter
from custom_components.hass_cudy_router.const import (
    MODULE_SYSTEM, MODULE_LAN, MODULE_DEVICES
)

# ---- CONFIG VIA ENV VARS (recommended) ----
PROTOCOL = os.getenv("CUDY_PROTOCOL", "https")
HOST = os.getenv("CUDY_HOST", "router.gdzi.es")
USERNAME = os.getenv("CUDY_USER", "admin")
PASSWORD = os.getenv("CUDY_PASS", "3zUo2Fk@")

if not PASSWORD:
    print("❌ Set CUDY_PASS env variable")
    sys.exit(1)


# ---- minimal fake hass ----
class FakeHass:
    async def async_add_executor_job(self, func, *args):
        return func(*args)


async def main():
    print("=== Cudy Router Smoke Test ===")
    print(f"Host: {PROTOCOL}://{HOST}")
    print(f"User: {USERNAME}")
    print("-----------------------------")

    hass = FakeHass()
    router = CudyRouter(
        hass=hass,
        protocol=PROTOCOL,
        host=HOST,
        username=USERNAME,
        password=PASSWORD,
    )

    # ---- AUTH ----
    print("🔐 Authenticating...")
    ok = router.authenticate()
    print(f"Auth result: {ok}")
    print(f"Auth value: {router.auth_cookie}")
    print(f"Auth cookie: {'SET' if router.auth_cookie else 'NOT SET'}")

    if not ok:
        print("❌ Authentication failed, aborting")
        return

    # ---- BASIC GETs ----
    def check(url, expect_json=False):
        print(f"\n➡️  GET {url}")
        data = router.get(url)
        if not data:
            print("❌ Empty response")
            return None
        if expect_json:
            try:
                parsed = json.loads(data)
                print("✅ JSON OK")
                return parsed
            except Exception as e:
                print(f"❌ JSON parse error: {e}")
                return None
        print(f"✅ HTML length: {len(data)}")
        return data

    check("admin/system/wizard")
    check("admin/network/mesh/status")
    check("admin/network/lan/status")
    check("admin/network/wan/status")
    check("admin/network/devices/status")
    check("admin/network/devices/devlist")

    # ---- FULL get_data() ----
    print("\n📦 Running get_data()")
    data = await router.get_data(hass, options={})

    print("\n=== Parsed modules ===")
    for key in [MODULE_SYSTEM, MODULE_LAN, MODULE_DEVICES]:
        value = data.get(key)
        if isinstance(value, dict):
            print(f"{key}: {len(value)} keys")
        elif isinstance(value, list):
            print(f"{key}: {len(value)} items")
        else:
            print(f"{key}: {type(value)}")

    print("\n🕒 Finished at", datetime.now().isoformat())


if __name__ == "__main__":
    asyncio.run(main())