import argparse
import asyncio
import os
import statistics
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import asyncpg
import httpx
from jose import jwt

# Ensure `app` package is importable when script is run from any cwd.
sys.path.append(str(Path(__file__).resolve().parents[1]))

@dataclass
class RequestResult:
    ok: bool
    status_code: int
    elapsed_ms: float


def _db_url() -> str:
    raw = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


async def ensure_tenant_and_profile(conn: asyncpg.Connection, subdomain: str) -> uuid.UUID:
    tenant_row = await conn.fetchrow(
        """
        INSERT INTO tenants (subdomain, name, is_active)
        VALUES ($1, $2, true)
        ON CONFLICT (subdomain)
        DO UPDATE SET is_active = true
        RETURNING id
        """,
        subdomain,
        f"Load Test {subdomain}",
    )
    tenant_id = tenant_row["id"]

    await conn.execute(
        """
        INSERT INTO barber_profiles (tenant_id, slot_duration_minutes, work_start_time, work_end_time, weekly_closed_days)
        VALUES ($1, 30, '09:00:00', '19:00:00', '{}'::integer[])
        ON CONFLICT (tenant_id) DO NOTHING
        """,
        tenant_id,
    )
    return tenant_id


async def ensure_users(conn: asyncpg.Connection, tenant_id: uuid.UUID, count: int, phone_prefix: str) -> list[uuid.UUID]:
    rows = await conn.fetch(
        """
        SELECT id
        FROM users
        WHERE tenant_id = $1 AND phone LIKE $2
        ORDER BY created_at ASC
        LIMIT $3
        """,
        tenant_id,
        f"{phone_prefix}%",
        count,
    )
    user_ids = [r["id"] for r in rows]

    missing = count - len(user_ids)
    if missing <= 0:
        return user_ids

    for i in range(len(user_ids), count):
        phone = f"{phone_prefix}{i:06d}"
        row = await conn.fetchrow(
            """
            INSERT INTO users (tenant_id, phone, first_name, last_name)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            tenant_id,
            phone,
            "Load",
            f"User{i}",
        )
        user_ids.append(row["id"])

    return user_ids


async def hit_endpoints(
    base_url: str,
    host_header: str,
    user_id: uuid.UUID,
    loops: int,
    mode: str,
    timeout: float,
    secret_key: str,
) -> list[RequestResult]:
    token = jwt.encode(
        {
            "sub": str(user_id),
            "role": "user",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=240),
        },
        secret_key,
        algorithm="HS256",
    )
    today = datetime.now().date().isoformat()
    cookies = {"user_session": token}
    headers = {"Host": host_header}

    out: list[RequestResult] = []
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers, cookies=cookies) as client:
        for _ in range(loops):
            if mode in ("mixed", "bookings"):
                start = time.perf_counter()
                try:
                    res = await client.get("/api/v1/bookings/my")
                    out.append(RequestResult(res.status_code < 400, res.status_code, (time.perf_counter() - start) * 1000))
                except Exception:
                    out.append(RequestResult(False, 0, (time.perf_counter() - start) * 1000))

            if mode in ("mixed", "slots"):
                start = time.perf_counter()
                try:
                    res = await client.get(f"/api/v1/slots?date={today}")
                    out.append(RequestResult(res.status_code < 400, res.status_code, (time.perf_counter() - start) * 1000))
                except Exception:
                    out.append(RequestResult(False, 0, (time.perf_counter() - start) * 1000))

    return out


async def run_load(args: argparse.Namespace) -> None:
    conn = await asyncpg.connect(_db_url())
    try:
        tenant_id = await ensure_tenant_and_profile(conn, args.subdomain)
        user_ids = await ensure_users(conn, tenant_id, args.users, args.phone_prefix)
    finally:
        await conn.close()

    host_header = f"{args.subdomain}.localhost:8000"

    sem = asyncio.Semaphore(args.concurrency)
    all_results: list[RequestResult] = []

    async def worker(uid: uuid.UUID) -> None:
        async with sem:
            results = await hit_endpoints(
                base_url=args.base_url,
                host_header=host_header,
                user_id=uid,
                loops=args.loops,
                mode=args.mode,
                timeout=args.timeout,
                secret_key=args.secret_key,
            )
            all_results.extend(results)

    wall_start = time.perf_counter()
    await asyncio.gather(*(worker(uid) for uid in user_ids))
    wall_elapsed = time.perf_counter() - wall_start

    summarize(all_results, wall_elapsed)


def summarize(results: Iterable[RequestResult], wall_seconds: float) -> None:
    results = list(results)
    if not results:
        print("No requests executed.")
        return

    total = len(results)
    ok = sum(1 for r in results if r.ok)
    fail = total - ok
    latencies = [r.elapsed_ms for r in results]
    status_counts: dict[int, int] = {}
    for r in results:
        status_counts[r.status_code] = status_counts.get(r.status_code, 0) + 1

    lat_sorted = sorted(latencies)
    p95_idx = max(0, int(len(lat_sorted) * 0.95) - 1)
    p99_idx = max(0, int(len(lat_sorted) * 0.99) - 1)

    print("\n=== Load Test Summary ===")
    print(f"Total requests: {total}")
    print(f"Success: {ok}")
    print(f"Failed: {fail}")
    print(f"Wall time: {wall_seconds:.2f}s")
    print(f"Throughput: {total / wall_seconds:.2f} req/s")
    print(f"Latency avg: {statistics.mean(latencies):.2f} ms")
    print(f"Latency p95: {lat_sorted[p95_idx]:.2f} ms")
    print(f"Latency p99: {lat_sorted[p99_idx]:.2f} ms")
    print("Status codes:")
    for code, count in sorted(status_counts.items(), key=lambda x: x[0]):
        print(f"  {code}: {count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple local load test for customer endpoints")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--subdomain", default="loadtest", help="Tenant subdomain for Host header")
    parser.add_argument("--users", type=int, default=100, help="Number of simulated users")
    parser.add_argument("--loops", type=int, default=10, help="Requests loop count per user")
    parser.add_argument("--concurrency", type=int, default=100, help="Max concurrent workers")
    parser.add_argument("--mode", choices=["mixed", "slots", "bookings"], default="mixed")
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout seconds")
    parser.add_argument("--phone-prefix", default="+90555000", help="Phone prefix for generated users")
    parser.add_argument(
        "--secret-key",
        default=os.getenv("SECRET_KEY", "dev_secret_key_min_32_chars_placeholder"),
        help="JWT secret key used by backend",
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run_load(parse_args()))
