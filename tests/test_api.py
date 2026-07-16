"""API surface tests against the mock backend: the /api/effects
endpoints, the /api/leds and /api/state getters, and the shared preset
store CRUD."""

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


# ---------- /api/effects ----------


def test_list_effects(client):
    effects = client.get("/api/effects").json()["effects"]
    assert len(effects) >= 12
    assert {"name", "description"} <= effects[0].keys()
    assert any(e["name"] == "CandyCane" for e in effects)


def test_effect_info(client):
    info = client.get("/api/effects/CandyCane").json()
    assert info["description"]
    assert any(a["name"] == "speed" for a in info["args"])

    assert client.get("/api/effects/Nonsense").status_code == 404


def test_start_running_stop(client):
    resp = client.post(
        "/api/effects/CandyCane/start", json={"args": {"speed": 2.0}}
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "status": "started",
        "effect": "CandyCane",
        "preset": None,
    }

    running = client.get("/api/effects/running").json()["running"]
    assert running["name"] == "CandyCane"
    assert running["preset"] is None
    # start_time is timezone-aware UTC, not naive local time.
    assert running["start_time"].endswith(("Z", "+00:00"))

    resp = client.post("/api/effects/stop")
    assert resp.status_code == 200
    assert resp.json() == {"status": "stopped", "was_running": True}

    # Idle is a normal state: running is null and stop stays 200.
    assert client.get("/api/effects/running").json() == {"running": None}
    assert client.post("/api/effects/stop").json() == {
        "status": "stopped",
        "was_running": False,
    }


def test_start_without_body(client):
    # Args are optional; an empty POST starts the effect with defaults.
    assert client.post("/api/effects/CandyCane/start").status_code == 200
    client.post("/api/effects/stop")


def test_start_unknown_effect(client):
    resp = client.post("/api/effects/Nonsense/start", json={"args": {}})
    assert resp.status_code == 404


def test_start_bad_args_is_rejected(client):
    resp = client.post(
        "/api/effects/CandyCane/start", json={"args": {"stripe_width": 0}}
    )
    assert resp.status_code == 503
    assert client.get("/api/effects/running").json()["running"] is None


def test_enum_option_schema_and_validation(client):
    # A str option is advertised with its choices so the UI can render a
    # dropdown, and the value is validated on start.
    direction = next(
        a
        for a in client.get("/api/effects/CandyCane").json()["args"]
        if a["name"] == "direction"
    )
    assert direction["type"] == "enum"
    assert direction["choices"] == ["forward", "reverse"]

    ok = client.post(
        "/api/effects/CandyCane/start",
        json={"args": {"direction": "reverse"}},
    )
    assert ok.status_code == 200
    client.post("/api/effects/stop")

    bad = client.post(
        "/api/effects/CandyCane/start",
        json={"args": {"direction": "sideways"}},
    )
    assert bad.status_code == 503
    assert client.get("/api/effects/running").json()["running"] is None


def test_validation_errors_have_string_detail(client):
    # Malformed request bodies get the same {"detail": "<string>"} shape
    # as domain errors, so clients can always print detail as-is.
    resp = client.put("/api/leds/brightness", json={"brightness": 2.0})
    assert resp.status_code == 422
    assert isinstance(resp.json()["detail"], str)


# ---------- /api/leds ----------


def test_led_state_reflects_writes(client):
    state = client.get("/api/leds").json()
    assert state["count"] == 30
    assert len(state["pixels"]) == 30
    assert state["color"] is None

    assert (
        client.put("/api/leds/color", json={"color": "#ff0000"}).status_code
        == 204
    )
    state = client.get("/api/leds").json()
    assert state["pixels"][0] == [255, 0, 0]
    assert state["color"] == "#ff0000"

    client.put("/api/leds/brightness", json={"brightness": 0.5})
    assert client.get("/api/leds").json()["brightness"] == 0.5

    assert client.delete("/api/leds/color").status_code == 204
    state = client.get("/api/leds").json()
    assert state["pixels"][0] == [0, 0, 0]
    assert state["color"] is None


def test_color_guarded_while_effect_runs(client):
    client.post("/api/effects/CandyCane/start")
    assert (
        client.put("/api/leds/color", json={"color": "#ff0000"}).status_code
        == 409
    )
    assert client.delete("/api/leds/color").status_code == 409
    client.post("/api/effects/stop")


def test_brightness_survives_effect_start(client):
    # Starting an effect must not reset user-set brightness.
    client.put("/api/leds/brightness", json={"brightness": 0.3})
    client.post("/api/effects/CandyCane/start")
    assert client.get("/api/leds").json()["brightness"] == 0.3
    client.post("/api/effects/stop")


# ---------- /api/state ----------


def test_state_summary(client):
    state = client.get("/api/state").json()
    assert state == {
        "running": None,
        "count": 30,
        "brightness": 1.0,
        "color": None,
        "lit": False,
    }

    client.put("/api/leds/color", json={"color": "#00ff00"})
    state = client.get("/api/state").json()
    assert state["color"] == "#00ff00"
    assert state["lit"] is True
    assert "pixels" not in state

    client.post("/api/effects/CandyCane/start")
    state = client.get("/api/state").json()
    assert state["running"]["name"] == "CandyCane"
    # An effect paints over the solid color, so it is no longer reported.
    assert state["color"] is None
    client.post("/api/effects/stop")


# ---------- /api/presets ----------


def _save_cozy(client, **overrides):
    body = {
        "effect": "CandyCane",
        "args": {"speed": 2.0, "color1": [0, 128, 255]},
        "description": "blue candy cane",
    }
    body.update(overrides)
    return client.put("/api/presets/cozy", json=body)


def test_preset_crud_roundtrip(client, settings):
    assert client.get("/api/presets").json() == {"presets": []}

    resp = _save_cozy(client)
    assert resp.status_code == 200
    record = resp.json()
    assert record["name"] == "cozy"
    assert record["effect"] == "CandyCane"
    assert record["args"] == {"speed": 2.0, "color1": [0, 128, 255]}

    assert client.get("/api/presets/cozy").json() == record
    assert client.get("/api/presets").json()["presets"] == [record]

    # The store is one shared JSON file, written through atomically.
    on_disk = json.loads(settings.presets_file.read_text())
    assert on_disk["cozy"]["effect"] == "CandyCane"

    assert client.delete("/api/presets/cozy").status_code == 204
    assert client.get("/api/presets/cozy").status_code == 404
    assert client.delete("/api/presets/cozy").status_code == 404


def test_preset_validation(client):
    assert _save_cozy(client, effect="Nonsense").status_code == 422
    assert _save_cozy(client, args={"nonsense": 1}).status_code == 422
    assert _save_cozy(client, args={"stripe_width": 0}).status_code == 422
    assert (
        _save_cozy(client, args={"direction": "sideways"}).status_code == 422
    )

    # Presets must not shadow effect names, and names must stay
    # URL/CLI-friendly.
    body = {"effect": "CandyCane", "args": {}}
    assert client.put("/api/presets/CandyCane", json=body).status_code == 422
    assert client.put("/api/presets/bad name", json=body).status_code == 422

    assert client.get("/api/presets").json() == {"presets": []}


def test_presets_are_shared_across_restarts(client, settings):
    _save_cozy(client)

    with TestClient(create_app(settings)) as second:
        names = [
            p["name"] for p in second.get("/api/presets").json()["presets"]
        ]
        assert names == ["cozy"]


def test_start_preset(client):
    _save_cozy(client)

    resp = client.post("/api/presets/cozy/start")
    assert resp.status_code == 200
    assert resp.json() == {
        "status": "started",
        "effect": "CandyCane",
        "preset": "cozy",
    }

    running = client.get("/api/effects/running").json()["running"]
    assert running["name"] == "CandyCane"
    assert running["preset"] == "cozy"

    # A plain effect start clears the preset attribution.
    client.post("/api/effects/CandyCane/start")
    assert (
        client.get("/api/effects/running").json()["running"]["preset"] is None
    )

    client.post("/api/effects/stop")


def test_start_missing_preset(client):
    assert client.post("/api/presets/cozy/start").status_code == 404
