import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from greenr.impact import Product, build_registry

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
CASES = {
    "ev": Product.EV_FINANCE,
    "green_home": Product.GREEN_HOME,
    "solar": Product.SOLAR_FINANCE,
    "paperless": Product.PAPERLESS_BANKING,
}


@pytest.fixture
def payload():
    def load(name):
        return json.loads((Path(__file__).parent / "fixtures" / f"{name}.json").read_text())
    return load


@pytest.fixture
def calculator():
    registry = build_registry(clock=lambda: NOW)
    return lambda name: registry[CASES[name]]
