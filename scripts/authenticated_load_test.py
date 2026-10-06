"""Run a small authenticated load test against an isolated backend instance.

The script creates one disposable Supabase Auth user with the service-role
client, obtains a JWT through the application's login endpoint, creates one
memoir through the public API, and reuses that JWT for read-only requests.
"""

import argparse
import concurrent.futures
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter
from dotenv import load_dotenv
from supabase import Client, create_client
load_dotenv()

def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} must be set in the environment")
    return value


def request_json(
    base_url: str,
    path: str,
    method: str = "GET",
    token: str | None = None,
    payload: dict | None = None,
) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/")),
        data=body,
        headers=headers,
        method=method,
    )
    
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response_body = response.read().decode("utf-8")
            return response.status, json.loads(response_body) if response_body else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"\nFASTAPI REJECTED THE REQUEST TO {path}")
        print(f"Details: {error_body}\n")
        raise

def create_confirmed_user(admin: Client, email: str, password: str) -> str:
    response = admin.auth.admin.create_user(
        {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"full_name": "Authenticated Load Test User"},
        }
    )
    user = getattr(response, "user", None)
    if not user or not user.id:
        raise RuntimeError("Supabase Admin did not return the created user")

    # The application expects a matching profile row before it creates a memoir.
    admin.table("user_account").upsert(
        {
            "id": str(user.id),
            "email": email,
            "full_name": "Authenticated Load Test User",
            "auth_provider_uid": str(user.id),
        },
        on_conflict="id",
    ).execute()
    return str(user.id)


def login(base_url: str, email: str, password: str) -> str:
    status, response = request_json(
        base_url,
        "/api/auth/login",
        method="POST",
        payload={"email": email, "password": password},
    )
    token = response.get("access_token")
    if status != 200 or not token:
        raise RuntimeError(f"Application login failed with HTTP {status}: {response}")
    return token


def create_memoir(base_url: str, token: str) -> str:
    status, response = request_json(
        base_url,
        "/api/memoirs/",
        method="POST",
        token=token,
        payload={
            "subject_name": "Authenticated Load Test Subject",
            "subject_is_living": True,
            "description": "Disposable fixture created by authenticated_load_test.py",
            "visibility": "invited_only",
            "comment_policy": "invited_only",
            "relationship": "other",
        },
    )
    memoir_id = response.get("data", {}).get("id")
    if status != 201 or not memoir_id:
        raise RuntimeError(f"Memoir fixture creation failed with HTTP {status}: {response}")
    return str(memoir_id)


def delete_fixture(admin: Client, user_id: str, memoir_id: str) -> None:
    admin.table("memoir_participant").delete().eq("memoir_id", memoir_id).execute()
    admin.table("memoir").delete().eq("id", memoir_id).execute()
    admin.auth.admin.delete_user(user_id)


def run_load(base_url: str, token: str, memoir_id: str, workers: int, duration: float) -> Counter:
    endpoints = [
        f"/api/memoirs/{memoir_id}",
        f"/api/memories/feed/{memoir_id}",
        f"/api/search/?{urllib.parse.urlencode({'memoir_id': memoir_id, 'q': 'load'})}",
    ]
    results: Counter = Counter()
    stop_at = time.perf_counter() + duration
    lock = threading.Lock()

    def hit(endpoint: str) -> None:
        try:
            status, _ = request_json(base_url, endpoint, token=token)
            result = f"HTTP {status}"
        except urllib.error.HTTPError as error:
            result = f"HTTP {error.code}"
        except Exception as error:
            result = type(error).__name__
        with lock:
            results[result] += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        while time.perf_counter() < stop_at:
            futures = [pool.submit(hit, endpoint) for endpoint in endpoints for _ in range(workers)]
            for future in futures:
                future.result()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--duration", type=float, default=10)
    parser.add_argument("--keep-fixture", action="store_true")
    args = parser.parse_args()

    if args.workers < 1 or args.duration <= 0:
        raise SystemExit("--workers must be positive and --duration must be greater than zero")

    supabase_url = required_env("SUPABASE_URL")
    service_role_key = required_env("SUPABASE_SERVICE_ROLE_KEY")
    admin = create_client(supabase_url, service_role_key)

    email = f"load-test-{uuid.uuid4().hex[:12]}@example.com"
    password = secrets.token_urlsafe(18)
    user_id = create_confirmed_user(admin, email, password)
    memoir_id = ""
    try:
        token = login(args.base_url, email, password)
        memoir_id = create_memoir(args.base_url, token)
        started = time.perf_counter()
        results = run_load(args.base_url, token, memoir_id, args.workers, args.duration)
        elapsed = time.perf_counter() - started
        total = sum(results.values())
        print(json.dumps({
            "user_id": user_id,
            "memoir_id": memoir_id,
            "duration_seconds": round(elapsed, 3),
            "workers": args.workers,
            "requests": total,
            "requests_per_second": round(total / elapsed, 2),
            "results": dict(results),
        }, indent=2))
    finally:
        if args.keep_fixture:
            print(f"Fixture retained: memoir_id={memoir_id}, user_id={user_id}")
        elif memoir_id:
            delete_fixture(admin, user_id, memoir_id)
        else:
            admin.auth.admin.delete_user(user_id)


if __name__ == "__main__":
    main()