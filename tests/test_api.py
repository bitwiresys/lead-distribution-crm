from __future__ import annotations

from fastapi.testclient import TestClient


def test_full_flow_creates_contact_and_lead(client: TestClient) -> None:
    operator_response = client.post(
        "/operators/",
        json={"name": "op-api", "load_limit": 100, "is_active": True},
    )
    assert operator_response.status_code == 201
    operator_id = operator_response.json()["id"]

    source_response = client.post("/sources/", json={"name": "api-bot"})
    assert source_response.status_code == 201
    source_id = source_response.json()["id"]

    weights_response = client.post(
        f"/sources/{source_id}/weights",
        json=[{"operator_id": operator_id, "weight": 10}],
    )
    assert weights_response.status_code == 200
    assert len(weights_response.json()) == 1

    contact_response = client.post(
        "/contacts",
        json={
            "external_lead_id": "lead-api-1",
            "source_id": source_id,
            "message": "Hello from API test",
        },
    )
    assert contact_response.status_code == 201
    contact_body = contact_response.json()
    assert contact_body["lead_id"] is not None
    assert contact_body["operator_id"] == operator_id
    assert contact_body["source_id"] == source_id

    operators_list = client.get("/operators/")
    assert operators_list.status_code == 200
    operators = operators_list.json()
    assert operators
    assert operators[0]["active_contacts"] >= 1

    leads_response = client.get("/leads")
    assert leads_response.status_code == 200
    leads = leads_response.json()
    assert len(leads) == 1
    assert len(leads[0]["contacts"]) == 1

    stats_response = client.get("/stats/distribution")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats
    assert stats[0]["contacts_count"] == 1


def test_register_contact_returns_404_for_unknown_source(client: TestClient) -> None:
    contact_response = client.post(
        "/contacts",
        json={
            "external_lead_id": "non-existing-source-lead",
            "source_id": 9999,
            "message": None,
        },
    )
    assert contact_response.status_code == 404


def test_setting_weights_fails_for_unknown_operator(client: TestClient) -> None:
    source_response = client.post("/sources/", json={"name": "bad-weights-source"})
    assert source_response.status_code == 201
    source_id = source_response.json()["id"]

    weights_response = client.post(
        f"/sources/{source_id}/weights",
        json=[{"operator_id": 9999, "weight": 10}],
    )
    assert weights_response.status_code == 400
