import asyncio
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.main import create_app
from app.settings import get_settings


@pytest.mark.asyncio
async def test_healthcheck(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    index_root = tmp_path / "index"
    db_path = tmp_path / "db.sqlite"

    monkeypatch.setenv("BITHARBOR_SERVER__DATA_ROOT", str(data_root))
    monkeypatch.setenv("BITHARBOR_ANN__INDEX_DIRECTORY", str(index_root))
    monkeypatch.setenv("BITHARBOR_ANN__VECTORS_PATH", str(index_root / "vectors.fp32"))
    monkeypatch.setenv("BITHARBOR_DB__URL", f"sqlite+aiosqlite:///{db_path}")

    get_settings.cache_clear()

    app = create_app()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

