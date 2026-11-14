"""Ustawienia asystenta: model, ceny, limit budżetu."""
from pathlib import Path

MODEL = "gpt-4o-mini"

# Ceny w USD za 1 milion tokenów (gpt-4o-mini).
CENA_WEJSCIE_1M = 0.15
CENA_WYJSCIE_1M = 0.60

# Twardy limit wydatków na cały projekt.
LIMIT_USD = 2.0
BUDGET_PATH = Path.home() / ".kamil_budget.json"

MAX_OUTPUT_TOKENS = 500
MAX_RUND_NARZEDZI = 4  # zabezpieczenie przed zapętleniem wywołań narzędzi
