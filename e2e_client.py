from __future__ import annotations

import sys
import time
from typing import Any

import httpx

BASE_URL = "http://127.0.0.1:8000"


def log(message: str) -> None:
    print(f"[E2E] {message}")


def assert_status(response: httpx.Response, expected_status: int) -> None:
    if response.status_code != expected_status:
        raise RuntimeError(
            f"Unexpected status {response.status_code} for {response.request.method} "
            f"{response.request.url}: {response.text}",
        )


def wait_for_service(client: httpx.Client, *, timeout_seconds: int = 30) -> None:
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            response = client.get("/docs")
            if response.status_code == 200:
                log("Service is up (docs endpoint reachable)")
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise TimeoutError("Service did not become ready within timeout")


def main() -> int:
    log("Starting end-to-end scenario")
    with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
        wait_for_service(client)

        # 1. Список операторов (ожидаем пустой на чистой БД)
        log("Listing operators (expected empty list)")
        response = client.get("/operators/")
        assert_status(response, 200)
        operators: list[dict[str, Any]] = response.json()

        # допускаем повторный запуск e2e, поэтому не требуем строго []

        # 2. Создаём операторов
        log("Creating operators")
        operator_payloads = [
            {"name": "alice", "load_limit": 3, "is_active": True},
            {"name": "bob", "load_limit": 5, "is_active": True},
        ]
        created_operators: list[dict[str, Any]] = []
        for payload in operator_payloads:
            response = client.post("/operators/", json=payload)
            if response.status_code == 400 and "already exists" in response.text:
                # оператор уже есть, получим список и найдём его там
                list_response = client.get("/operators/")
                assert_status(list_response, 200)
                existing = [
                    item
                    for item in list_response.json()
                    if item["name"] == payload["name"]
                ]
                if not existing:
                    raise RuntimeError("Operator exists check failed")
                created_operators.append(existing[0])
            else:
                assert_status(response, 201)
                created_operators.append(response.json())

        log(f"Operators in scenario: {[op['name'] for op in created_operators]}")

        # 3. Создаём источники
        log("Creating sources")
        source_payloads = [
            {"name": "telegram-bot"},
            {"name": "whatsapp-bot"},
        ]
        created_sources: list[dict[str, Any]] = []
        for payload in source_payloads:
            response = client.post("/sources/", json=payload)
            if response.status_code == 400 and "already exists" in response.text:
                list_response = client.get("/sources/")
                assert_status(list_response, 200)
                existing = [
                    item
                    for item in list_response.json()
                    if item["name"] == payload["name"]
                ]
                if not existing:
                    raise RuntimeError("Source exists check failed")
                created_sources.append(existing[0])
            else:
                assert_status(response, 201)
                created_sources.append(response.json())

        log(f"Sources in scenario: {[src['name'] for src in created_sources]}")

        alice_id = created_operators[0]["id"]
        bob_id = created_operators[1]["id"]
        source_a_id = created_sources[0]["id"]
        source_b_id = created_sources[1]["id"]

        # 4. Настраиваем веса операторов для источников
        log("Setting operator weights for sources")
        response = client.post(
            f"/sources/{source_a_id}/weights",
            json=[
                {"operator_id": alice_id, "weight": 10},
                {"operator_id": bob_id, "weight": 30},
            ],
        )
        assert_status(response, 200)

        response = client.post(
            f"/sources/{source_b_id}/weights",
            json=[
                {"operator_id": alice_id, "weight": 20},
                {"operator_id": bob_id, "weight": 20},
            ],
        )
        assert_status(response, 200)

        # 5. Регистрируем несколько обращений из разных источников
        log("Registering contacts for several leads and sources")
        contacts_payloads = [
            {"external_lead_id": "lead-1", "source_id": source_a_id, "message": "Hi from A"},
            {"external_lead_id": "lead-1", "source_id": source_b_id, "message": "Hi from B"},
            {"external_lead_id": "lead-2", "source_id": source_a_id, "message": "Second lead"},
            {"external_lead_id": "lead-3", "source_id": source_b_id, "message": None},
        ]
        for payload in contacts_payloads:
            response = client.post("/contacts", json=payload)
            assert_status(response, 201)

        # 6. Обновляем параметры оператора
        log("Updating operator state (load_limit and activity)")
        response = client.patch(
            f"/operators/{alice_id}",
            json={"load_limit": 10, "is_active": True},
        )
        assert_status(response, 200)

        # 7. Читаем все основные представления
        log("Fetching operators list with active load")
        response = client.get("/operators/")
        assert_status(response, 200)
        operators_after = response.json()
        if not operators_after:
            raise RuntimeError("Expected at least one operator in list")

        log("Fetching sources list")
        response = client.get("/sources/")
        assert_status(response, 200)

        log("Fetching weights for each source")
        for source_id in (source_a_id, source_b_id):
            weights_response = client.get(f"/sources/{source_id}/weights")
            assert_status(weights_response, 200)

        log("Fetching contacts list")
        response = client.get("/contacts")
        assert_status(response, 200)
        contacts = response.json()
        if not contacts:
            raise RuntimeError("Expected at least one contact in list")

        log("Fetching leads with contacts")
        response = client.get("/leads")
        assert_status(response, 200)
        leads = response.json()
        if not leads:
            raise RuntimeError("Expected at least one lead in list")

        log("Fetching distribution stats")
        response = client.get("/stats/distribution")
        assert_status(response, 200)
        stats = response.json()
        if not stats:
            raise RuntimeError("Expected at least one distribution stat entry")

        log("End-to-end scenario finished successfully")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        log(f"Scenario failed: {exc}")
        raise SystemExit(1)
