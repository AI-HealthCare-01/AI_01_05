import asyncio
from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest
import pytest_asyncio
from _pytest.fixtures import FixtureRequest
from tortoise import generate_config
from tortoise.contrib.test import finalizer, initializer

from app.db.databases import TORTOISE_APP_MODELS

TEST_DB_TZ = "Asia/Seoul"


def get_test_db_config() -> dict:
    tortoise_config = generate_config(
        db_url="sqlite://:memory:",
        app_modules={"models": TORTOISE_APP_MODELS},
        connection_label="models",
        testing=True,
    )
    tortoise_config["timezone"] = TEST_DB_TZ
    return tortoise_config


@pytest.fixture(scope="session", autouse=True)
def initialize(request: FixtureRequest) -> Generator[None, None]:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        with patch("tortoise.contrib.test.getDBConfig", Mock(return_value=get_test_db_config())):
            initializer(modules=TORTOISE_APP_MODELS)
        yield
        finalizer()
    finally:
        loop.close()


@pytest_asyncio.fixture(autouse=True, scope="session")  # type: ignore[type-var]
def event_loop() -> None:
    pass
