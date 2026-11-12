"""Tests for SQLite-persisted Fraud Hold / Exception reviews and Multi-Project package ingestion."""
import io
import zipfile

import pytest

from azboq import config
from azboq.operations import build_operations
from azboq.projects import delete_project, ingest_uploaded_project, list_projects
from azboq.reviews import add_review, supersede


def test_fraud_hold_and_exception_persist_and_clear(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "fraud_test.sqlite")
    ops0 = build_operations()
    alerts = ops0["fraud_alerts"]
    assert len(alerts) >= 5
    first_id = alerts[0]["id"]
    total_exp = ops0["summary"]["total_exposure_azn"]
    assert ops0["summary"]["holds_count"] == 0

    # Enforce payment hold
    rid = add_review("fraud", first_id, "hold", {"exposure_azn": alerts[0]["exposure_azn"]},
                     "Freeze payment pending Forma-2 re-check", "G. Feyzullayev")
    ops1 = build_operations()
    held = next(a for a in ops1["fraud_alerts"] if a["id"] == first_id)
    assert held["decision"]["action"] == "hold"
    assert held["decision"]["author"] == "G. Feyzullayev"
    assert ops1["summary"]["holds_count"] == 1
    assert ops1["summary"]["held_exposure_azn"] == pytest.approx(alerts[0]["exposure_azn"])

    # Switch to exception -> reduces active exposure
    rid2 = add_review("fraud", first_id, "exception", {}, "Approved by signed VO-02", "G. Feyzullayev")
    ops2 = build_operations()
    exc = next(a for a in ops2["fraud_alerts"] if a["id"] == first_id)
    assert exc["decision"]["action"] == "exception"
    assert ops2["summary"]["active_exposure_azn"] == pytest.approx(total_exp - alerts[0]["exposure_azn"])

    # Clear decision -> restores full exposure
    supersede(rid2, "G. Feyzullayev", "Restored to open review")
    ops3 = build_operations()
    cleared = next(a for a in ops3["fraud_alerts"] if a["id"] == first_id)
    assert cleared["decision"] is None
    assert ops3["summary"]["active_exposure_azn"] == pytest.approx(total_exp)


def test_project_package_upload_classifies_dwg_zip_and_junk(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "proj_test.sqlite")
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")

    # Build a small zip containing a mock DWG header and a .bak junk file
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as zf:
        zf.writestr("01-plan.dwg", b"AC1027" + b"\x00" * 64)
        zf.writestr("01-plan.bak", b"junk")
        zf.writestr("plot.log", b"plot log")

    created = ingest_uploaded_project(
        name="Füzuli Fire Station",
        order_code="9540",
        location="Füzuli",
        client="FHN",
        uploaded_files=[("package.zip", zbuf.getvalue())],
    )
    assert created["name"] == "Füzuli Fire Station"
    assert created["summary"]["dwg_count"] == 1
    assert created["summary"]["ignored_count"] == 2

    all_projs = list_projects()
    assert any(p["id"] == "hadrut-9335" for p in all_projs)
    assert any(p["id"] == created["id"] for p in all_projs)

    with pytest.raises(ValueError):
        delete_project("hadrut-9335")

    assert delete_project(created["id"]) is True
    assert not any(p["id"] == created["id"] for p in list_projects())


def test_project_zip_skips_paths_that_leave_the_package(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "proj_escape.sqlite")
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")

    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as zf:
        zf.writestr("../outside.txt", b"nope")
        zf.writestr("sheets/ok.pdf", b"%PDF-1.4\n")

    created = ingest_uploaded_project(
        name="Escape",
        order_code="1",
        location="Baku",
        client="FHN",
        uploaded_files=[("package.zip", zbuf.getvalue())],
    )
    names = [f["name"] for f in created["summary"]["files"]]
    assert "package/sheets/ok.pdf" in names
    assert all("outside" not in name for name in names)
    assert not (tmp_path / "outside.txt").exists()
    assert created["summary"]["pdf_count"] == 1

    with pytest.raises(ValueError):
        delete_project("../secret")
