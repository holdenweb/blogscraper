from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_text():
    def read(name: str) -> str:
        return (FIXTURES / name).read_text()

    return read


@pytest.fixture
def test_db():
    """A scratch database for DB-backed tests; dropped afterwards.

    Pure-function tests must not request this fixture, so the bulk of the
    suite runs without a mongod.
    """
    import mongoengine

    conn = mongoengine.connect("blogscraper_test", uuidRepresentation="standard")
    yield conn["blogscraper_test"]
    conn.drop_database("blogscraper_test")
    mongoengine.disconnect()
