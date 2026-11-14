"""Licznik budżetu zapisany w pliku poza repozytorium.

Każde wywołanie API przechodzi przez Budzet.sprawdz_przed() i Budzet.zapisz().
Kod nigdy nie zeruje licznika.
"""
import json
import os
import tempfile
import time

from . import config


class BudzetPrzekroczony(RuntimeError):
    """Rzucany, gdy kolejne wywołanie mogłoby przekroczyć limit."""


def koszt_usd(tokeny_we: int, tokeny_wy: int) -> float:
    return (
        tokeny_we * config.CENA_WEJSCIE_1M + tokeny_wy * config.CENA_WYJSCIE_1M
    ) / 1_000_000


class Budzet:
    def __init__(self, sciezka=None):
        self.sciezka = sciezka or config.BUDGET_PATH

    def _wczytaj(self) -> dict:
        if not os.path.exists(self.sciezka):
            return {"limit_usd": config.LIMIT_USD, "wydane_usd": 0.0, "wywolania": []}
        with open(self.sciezka, encoding="utf-8") as f:
            return json.load(f)

    def _zapisz_plik(self, dane: dict) -> None:
        katalog = os.path.dirname(self.sciezka) or "."
        fd, tmp = tempfile.mkstemp(dir=katalog, prefix=".kamil_budget_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dane, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.sciezka)

    def wydane(self) -> float:
        return float(self._wczytaj()["wydane_usd"])

    def limit(self) -> float:
        # Limit bierzemy z konfiguracji, jeśli jest niższy niż w pliku.
        return min(float(self._wczytaj()["limit_usd"]), config.LIMIT_USD)

    def pozostalo(self) -> float:
        return self.limit() - self.wydane()

    def sprawdz_przed(self, szacowane_tokeny_wejscia: int) -> None:
        szacunek = koszt_usd(szacowane_tokeny_wejscia, config.MAX_OUTPUT_TOKENS)
        if self.wydane() + szacunek > self.limit():
            raise BudzetPrzekroczony(
                f"Limit {self.limit():.2f} USD zostałby przekroczony "
                f"(wydane {self.wydane():.4f} USD, szacunek {szacunek:.4f} USD)."
            )

    def zapisz(self, tokeny_we: int, tokeny_wy: int, tryb: str) -> float:
        dane = self._wczytaj()
        koszt = koszt_usd(tokeny_we, tokeny_wy)
        dane["wydane_usd"] = round(float(dane["wydane_usd"]) + koszt, 8)
        dane["wywolania"].append(
            {
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "model": config.MODEL,
                "in": tokeny_we,
                "out": tokeny_wy,
                "koszt": round(koszt, 8),
                "tryb": tryb,
            }
        )
        self._zapisz_plik(dane)
        return koszt

    def podsumowanie(self) -> str:
        d = self._wczytaj()
        return (
            f"Wydane: {d['wydane_usd']:.4f} USD z limitu {d['limit_usd']:.2f} USD "
            f"({len(d['wywolania'])} wywołań)."
        )
