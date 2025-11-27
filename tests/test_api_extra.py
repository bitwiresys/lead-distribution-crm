from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_list_operators_empty_returns_empty_list(client: TestClient) -> None:
    response = client.get("/operators/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_operator_duplicate_name_returns_400(client: TestClient) -> None:
    payload = {"name": "duplicate", "load_limit": 10, "is_active": True}

    first = client.post("/operators/", json=payload)
    assert first.status_code == 201

    second = client.post("/operators/", json=payload)
    assert second.status_code == 400


def test_update_operator_success_and_not_found(client: TestClient) -> None:
    create_response = client.post(
        "/operators/",
        json={"name": "to-update", "load_limit": 5, "is_active": True},
    )
    assert create_response.status_code == 201
    operator_id = create_response.json()["id"]

    update_response = client.patch(
        f"/operators/{operator_id}",
        json={"load_limit": 15, "is_active": False},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["load_limit"] == 15
    assert updated["is_active"] is False

    not_found = client.patch(
        "/operators/9999",
        json={"load_limit": 1},
    )
    assert not_found.status_code == 404


def test_list_sources_empty_returns_empty_list(client: TestClient) -> None:
    response = client.get("/sources/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_source_duplicate_name_returns_400(client: TestClient) -> None:
    payload = {"name": "dup-source"}

    first = client.post("/sources/", json=payload)
    assert first.status_code == 201

    second = client.post("/sources/", json=payload)
    assert second.status_code == 400


def test_set_source_weights_empty_payload_returns_400(client: TestClient) -> None:
    source_response = client.post("/sources/", json={"name": "no-weights"})
    assert source_response.status_code == 201
    source_id = source_response.json()["id"]

    response = client.post(f"/sources/{source_id}/weights", json=[])
    assert response.status_code == 400


def test_get_source_weights_not_found_returns_404(client: TestClient) -> None:
    response = client.get("/sources/9999/weights")
    assert response.status_code == 404


def test_list_contacts_returns_contacts(client: TestClient) -> None:
    operator_response = client.post(
        "/operators/",
        json={"name": "op-list-contacts", "load_limit": 100, "is_active": True},
    )
    assert operator_response.status_code == 201
    operator_id = operator_response.json()["id"]

    source_response = client.post("/sources/", json={"name": "bot-list-contacts"})
    assert source_response.status_code == 201
    source_id = source_response.json()["id"]

    weights_response = client.post(
        f"/sources/{source_id}/weights",
        json=[{"operator_id": operator_id, "weight": 10}],
    )
    assert weights_response.status_code == 200
    assert len(weights_response.json()) == 1

    create_contact_response = client.post(
        "/contacts",
        json={
            "external_lead_id": "lead-for-list",
            "source_id": source_id,
            "message": None,
        },
    )
    assert create_contact_response.status_code == 201

    contacts_response = client.get("/contacts")
    assert contacts_response.status_code == 200
    contacts = contacts_response.json()
    assert len(contacts) == 1


def test_register_contact_translates_service_value_error_to_404(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_response = client.post("/sources/", json={"name": "err-source"})
    assert source_response.status_code == 201
    source_id = source_response.json()["id"]

    from app import api as api_package  # noqa: F401  # ensured for import side effects

    def fake_create_contact_for_lead(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise ValueError("forced error for test")

    monkeypatch.setattr("app.api.contacts.create_contact_for_lead", fake_create_contact_for_lead)

    response = client.post(
        "/contacts",
        json={
            "external_lead_id": "lead-error",
            "source_id": source_id,
            "message": None,
        },
    )
    assert response.status_code == 404
