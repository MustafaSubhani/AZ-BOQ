"""Paths and environment. Every path the engine touches is defined here."""
import os
from pathlib import Path

ROOT = Path(os.environ.get("AZBOQ_ROOT", Path(__file__).resolve().parents[2]))
DATA_DIR = Path(os.environ.get("AZBOQ_DATA", ROOT / "data"))
PACKAGE_DIR = DATA_DIR / "Hadrut DEPO"
BILL_PATH = DATA_DIR / "BOQ-Hadrut.xlsx"
BILL_PDF_PATH = DATA_DIR / "BOQ-Hadrut.pdf"

CACHE_DIR = Path(os.environ.get("AZBOQ_CACHE", ROOT / "cache"))
DXF_DIR = CACHE_DIR / "dxf"
LIBREDWG_DIR = CACHE_DIR / "libredwg"
TILES_DIR = CACHE_DIR / "tiles"
EXPORT_DIR = CACHE_DIR / "exports"
DB_PATH = CACHE_DIR / "azboq.sqlite"
TRANSLATIONS_DB = CACHE_DIR / "translations.sqlite"
RUN_LOG_DIR = CACHE_DIR / "runs"

BACKEND_DIR = Path(__file__).resolve().parents[1]
RULES_DIR = BACKEND_DIR / "demo_rules"
LEGACY_FONT_DIR = Path(__file__).resolve().parent / "text" / "legacy_fonts"
GLOSSARY_PATH = Path(__file__).resolve().parent / "text" / "glossary.az-en.yaml"

TOOLS_DIR = ROOT / "tools"
ODA_EXE = Path(os.environ.get("AZBOQ_ODA", TOOLS_DIR / "oda" / "ODAFileConverter.exe"))
LIBREDWG_TOOL = TOOLS_DIR / "libredwg" / "count.mjs"
FONT_DIR = TOOLS_DIR / "fonts"

OPENAI_TRANSLATION_MODEL = os.environ.get("OPENAI_TRANSLATION_MODEL", "gpt-5.6-sol")
OPENAI_VISION_MODEL = os.environ.get("OPENAI_VISION_MODEL", OPENAI_TRANSLATION_MODEL)


def ensure_dirs():
    for d in (CACHE_DIR, DXF_DIR, LIBREDWG_DIR, TILES_DIR, EXPORT_DIR, RUN_LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)
