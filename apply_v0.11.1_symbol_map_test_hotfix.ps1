$ErrorActionPreference = "Stop"

if (-not (Test-Path "pyproject.toml")) {
    throw "Run this script from the crypto-composite-market-data repository root."
}
if (-not (Test-Path "tests\test_symbol_map_edge_cases.py")) {
    throw "Expected tests\test_symbol_map_edge_cases.py is missing."
}

$patch = @'
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return
        raise SystemExit(f"PATCH_CONTEXT_MISSING path={path} old={old!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")

replace_once(
    "tests/test_symbol_map_edge_cases.py",
    '        resolve_symbol("BTC-USDT", "coinbase", "spot_usdt")\n',
    '        resolve_symbol("BTC-USDT", "unknownvenue", "spot_usdt")\n',
)

print("v0.11.1 symbol-map test hotfix applied")
'@

$patch | py -
