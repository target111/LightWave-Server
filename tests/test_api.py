"""API surface tests against the mock backend: the /effects endpoints,
the /leds state getter, and the shared preset store CRUD."""

import json

import pytest
from fastapi.testclient import TestClient

from lib.app import create_app
from lib.config import Settings


@pytest.fixture
def settings(tmp_path):
    # `backend` is populated via its LED_BACKEND validation alias.
    return Settings(  # pyright: ignore[reportCallIssue]
        LED_BACKEND="mock",  # pyright: ignore[reportCallIssue]
        led_count=30,
        presets_file=tmp_path / "presets.json",
    )


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c


# ---------- /effects ----------


def test_list_effects(client):
    effects = client.get("/effects").json()["effects"]
    assert len(effects) >= 12
    assert {"name", "description"} <= effects[0].keys()
    assert any(e["name"] == "CandyCane" for e in effects)


def test_effect_info(client):
    info = client.get("/effects/CandyCane").json()
    assert info["description"]
    assert any(a["name"] == "speed" for a in info["args"])

    assert client.get("/effects/Nonsense").status_code == 404


def test_start_running_stop(client):
    resp = client.post(
        "/effects/start",
        json={"effect_name": "CandyCane", "args": {"speed": 2.0}},
    )
    assert resp.status_code == 202
    assert resp.json() == {
        "status": "started",
        "effect": "CandyCane",
        "preset": None,
    }

    running = client.get("/effects/running").json()
    assert running["name"] == "CandyCane"
    assert running["preset"] is None

    assert client.post("/effects/stop").status_code == 202
    assert client.get("/effects/running").status_code == 404
    assert client.post("/effects/stop").status_code == 404


def test_start_unknown_effect(client):
    resp = client.post(
        "/effects/start", json={"effect_name": "Nonsense", "args": {}}
    )
    assert resp.status_code == 404


def test_start_bad_args_is_rejected(client):
    resp = client.post(
        "/effects/start",
        json={"effect_name": "CandyCane", "args": {"stripe_width": 0}},
    )
    assert resp.status_code == 503
    assert client.get("/effects/running").status_code == 404


# ---------- /leds ----------


def test_led_state_reflects_writes(client):
    state = client.get("/leds").json()
    assert state["count"] == 30
    assert len(state["pixels"]) == 30

    client.post("/leds/color/set", json={"color": "#ff0000"})
    state = client.get("/leds").json()
    assert state["pixels"][0] == [255, 0, 0]

    client.post("/leds/brightness", json={"brightness": 0.5})
    assert client.get("/leds").json()["brightness"] == 0.5

    client.post("/leds/color/clear")
    assert client.get("/leds").json()["pixels"][0] == [0, 0, 0]


# ---------- /presets ----------


def _save_cozy(client, **overrides):
    body = {
        "effect": "CandyCane",
        "args": {"speed": 2.0, "color1": [0, 128, 255]},
        "description": "blue candy cane",
    }
    body.update(overrides)
    return client.put("/presets/cozy", json=body)


def test_preset_crud_roundtrip(client, settings):
    assert client.get("/presets").json() == {"presets": []}

    resp = _save_cozy(client)
    assert resp.status_code == 200
    record = resp.json()
    assert record["name"] == "cozy"
    assert record["effect"] == "CandyCane"
    assert record["args"] == {"speed": 2.0, "color1": [0, 128, 255]}

    assert client.get("/presets/cozy").json() == record
    assert client.get("/presets").json()["presets"] == [record]

    # The store is one shared JSON file, written through atomically.
    on_disk = json.loads(settings.presets_file.read_text())
    assert on_disk["cozy"]["effect"] == "CandyCane"

    assert client.delete("/presets/cozy").status_code == 204
    assert client.get("/presets/cozy").status_code == 404
    assert client.delete("/presets/cozy").status_code == 404


def test_preset_validation(client):
    assert _save_cozy(client, effect="Nonsense").status_code == 422
    assert _save_cozy(client, args={"nonsense": 1}).status_code == 422
    assert _save_cozy(client, args={"stripe_width": 0}).status_code == 422

    # Presets must not shadow effect names, and names must stay
    # URL/CLI-friendly.
    body = {"effect": "CandyCane", "args": {}}
    assert client.put("/presets/CandyCane", json=body).status_code == 422
    assert client.put("/presets/bad name", json=body).status_code == 422

    assert client.get("/presets").json() == {"presets": []}


def test_presets_are_shared_across_restarts(client, settings):
    _save_cozy(client)

    with TestClient(create_app(settings)) as second:
        names = [p["name"] for p in second.get("/presets").json()["presets"]]
        assert names == ["cozy"]


def test_start_preset(client):
    _save_cozy(client)

    resp = client.post("/presets/cozy/start")
    assert resp.status_code == 202
    assert resp.json() == {
        "status": "started",
        "effect": "CandyCane",
        "preset": "cozy",
    }

    running = client.get("/effects/running").json()
    assert running["name"] == "CandyCane"
    assert running["preset"] == "cozy"

    # A plain effect start clears the preset attribution.
    client.post("/effects/start", json={"effect_name": "CandyCane"})
    assert client.get("/effects/running").json()["preset"] is None

    client.post("/effects/stop")


def test_start_missing_preset(client):
    assert client.post("/presets/cozy/start").status_code == 404
