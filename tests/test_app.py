import importlib
import sys
from pathlib import Path

import pytest

CONFIG_CONTENT = """[API]
OPENAI_API_KEY = test-key

[DATABASE]
SERVER = test-server
DATABASE = test-database
DRIVER = SQL Server
"""


@pytest.fixture(autouse=True)
def temporary_config():
    """Ensure a temporary config.ini exists so the app can import."""
    config_path = Path("config.ini")
    original_content = config_path.read_text() if config_path.exists() else None
    config_path.write_text(CONFIG_CONTENT)
    try:
        yield
    finally:
        if original_content is not None:
            config_path.write_text(original_content)
        else:
            config_path.unlink(missing_ok=True)


@pytest.fixture()
def app_module(monkeypatch):
    """Import the app module with a fake database to avoid real connections."""
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    if "app" in sys.modules:
        module = importlib.reload(sys.modules["app"])
    else:
        module = importlib.import_module("app")

    class FakeDB:
        def __init__(self):
            self.calls = []
            self.response = "No results found."

        def run(self, query):
            self.calls.append(query)
            if isinstance(self.response, Exception):
                raise self.response
            return self.response

    fake_db = FakeDB()
    monkeypatch.setattr(module, "db", fake_db)
    return module, fake_db


def test_empty_question_returns_prompt(app_module):
    app, _ = app_module

    response = app.ask_database("   ")

    assert response == "Please enter a question."


def test_query_generation_failure_returns_guidance(app_module, monkeypatch):
    app, fake_db = app_module
    monkeypatch.setattr(app, "generate_smart_sql", lambda question: "Error: test failure")

    response = app.ask_database("bad question")

    assert "Unable to generate query" in response
    assert "Being more specific" in response
    assert fake_db.calls == []


def test_no_results_response_includes_message_and_query(app_module, monkeypatch):
    app, fake_db = app_module
    generated_query = "SELECT * FROM dbo.fake_table"
    monkeypatch.setattr(app, "generate_smart_sql", lambda question: generated_query)
    fake_db.response = "No results found."

    response = app.ask_database("find nothing", show_details=True)

    assert "No data found matching your criteria." in response
    assert generated_query in response
