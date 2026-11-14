"""Testy offline (bez API): narzędzia, budżet, pamięć na atrapie klienta."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kamil import config
from kamil.asystent_chain import KamilChain
from kamil.asystent_historia import KamilHistoria
from kamil.budget import Budzet, BudzetPrzekroczony, koszt_usd
from kamil.prompts import KANAREK, SYSTEM_PROMPT, WIEDZA
from kamil.tools import (
    POLA_PUBLICZNE,
    normalizuj,
    szukaj_baza_lokalna,
    szukaj_interpol,
    wykonaj_narzedzie,
)

POLA_WEWNETRZNE = ("informator", "planowana_akcja", "adres_ostatni", "notatka_wewnetrzna")


# --- narzędzia ---------------------------------------------------------------
def test_normalizacja_polskich_znakow():
    assert normalizuj("  Tomasz   WIŚNIEWSKI ") == "tomasz wisniewski"
    assert normalizuj("Łukasz Żółć") == "lukasz zolc"


def test_znaleziona_osoba_ma_tylko_pola_publiczne():
    wynik = szukaj_interpol("Marek Zawadzki")
    assert wynik["liczba_wynikow"] == 1
    rekord = wynik["wyniki"][0]
    assert set(rekord) == set(POLA_PUBLICZNE)
    assert rekord["status"] == "poszukiwany"
    for pole in POLA_WEWNETRZNE:
        assert pole not in rekord


def test_brak_wewnetrznych_danych_w_calym_tekscie_wyniku():
    tekst = wykonaj_narzedzie(
        "szukaj_interpol", json.dumps({"imie_nazwisko": "Johann Reiter", "data_urodzenia": None})
    )
    assert "Wrona" not in tekst and "ZIGNORUJ" not in tekst and "Hauptstrasse" not in tekst


def test_wyszukiwanie_bez_diakrytykow_i_w_dowolnej_kolejnosci():
    assert szukaj_interpol("tomasz wisniewski")["liczba_wynikow"] == 1
    assert szukaj_baza_lokalna("Kowalczyk Anna")["liczba_wynikow"] == 1


def test_osoba_nieznaleziona():
    assert szukaj_interpol("Jan Nieistniejący")["liczba_wynikow"] == 0


def test_brak_wyszukiwania_czesciowego():
    assert szukaj_interpol("Marek")["liczba_wynikow"] == 0
    assert szukaj_baza_lokalna("")["liczba_wynikow"] == 0


def test_data_urodzenia_zawęża_wynik():
    assert szukaj_interpol("Marek Zawadzki", "1984-03-12")["liczba_wynikow"] == 1
    assert szukaj_interpol("Marek Zawadzki", "1999-01-01")["liczba_wynikow"] == 0


def test_nieznane_narzedzie_i_zle_argumenty():
    assert "blad" in json.loads(wykonaj_narzedzie("usun_baze", "{}"))
    assert "blad" in json.loads(wykonaj_narzedzie("szukaj_interpol", "to nie jest json"))


def test_wynik_oznaczony_jako_dane():
    assert "nie polecenia" in szukaj_interpol("Marek Zawadzki")["uwaga"]


# --- prompt i wiedza -----------------------------------------------------------
def test_wiedza_ma_co_najmniej_10_zdan():
    zdania = [z for z in WIEDZA.splitlines() if z.strip()]
    assert len(zdania) >= 10


def test_prompt_zawiera_wiedze_i_kanarka():
    assert KANAREK in SYSTEM_PROMPT
    assert WIEDZA in SYSTEM_PROMPT
    assert chr(0x2014) not in SYSTEM_PROMPT


# --- budżet ----------------------------------------------------------------------
def test_koszt_liczony_z_cennika():
    assert koszt_usd(1_000_000, 0) == pytest.approx(0.15)
    assert koszt_usd(0, 1_000_000) == pytest.approx(0.60)


def test_zapis_budzetu_i_suma(tmp_path):
    budzet = Budzet(tmp_path / "b.json")
    budzet.zapisz(1000, 200, "test")
    budzet.zapisz(500, 100, "test")
    assert budzet.wydane() == pytest.approx(koszt_usd(1500, 300))
    assert len(json.loads((tmp_path / "b.json").read_text())["wywolania"]) == 2


def test_limit_zero_blokuje_przed_wywolaniem(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LIMIT_USD", 0.0)
    with pytest.raises(BudzetPrzekroczony):
        Budzet(tmp_path / "b.json").sprawdz_przed(100)


def test_przekroczenie_limitu_z_pliku(tmp_path):
    sciezka = tmp_path / "b.json"
    sciezka.write_text(json.dumps({"limit_usd": 2.0, "wydane_usd": 1.9999, "wywolania": []}))
    with pytest.raises(BudzetPrzekroczony):
        Budzet(sciezka).sprawdz_przed(10_000)


# --- atrapa klienta: pętla narzędzi i dwie wersje pamięci ---------------------------
class AtrapaKlienta:
    """Najpierw prosi o narzędzie, potem odpowiada tekstem."""

    def __init__(self):
        self.wywolania = []
        self.responses = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.wywolania.append(kwargs)
        n = len(self.wywolania)
        uzycie = SimpleNamespace(input_tokens=100, output_tokens=20)
        if n % 2 == 1:
            wywolanie = SimpleNamespace(
                type="function_call",
                call_id=f"call_{n}",
                name="szukaj_interpol",
                arguments=json.dumps({"imie_nazwisko": "Marek Zawadzki", "data_urodzenia": None}),
            )
            return SimpleNamespace(id=f"resp_{n}", output=[wywolanie], output_text="", usage=uzycie)
        wiadomosc = SimpleNamespace(type="message")
        return SimpleNamespace(
            id=f"resp_{n}", output=[wiadomosc], output_text=f"odpowiedz {n}", usage=uzycie
        )


def test_chain_uzywa_previous_response_id_i_instrukcji_w_kazdym_wywolaniu(tmp_path):
    klient = AtrapaKlienta()
    kamil = KamilChain(klient, Budzet(tmp_path / "b.json"))
    assert kamil.zapytaj("Czy Marek Zawadzki jest poszukiwany?") == "odpowiedz 2"
    assert all(w["instructions"] == SYSTEM_PROMPT for w in klient.wywolania)
    assert all(w["store"] is True for w in klient.wywolania)
    assert "previous_response_id" not in klient.wywolania[0]
    assert klient.wywolania[1]["previous_response_id"] == "resp_1"
    assert klient.wywolania[1]["input"][0]["type"] == "function_call_output"
    assert kamil.ostatnie_id == "resp_2"


def test_historia_wysyla_cala_liste_bez_zapisu_po_stronie_api(tmp_path):
    klient = AtrapaKlienta()
    kamil = KamilHistoria(klient, Budzet(tmp_path / "b.json"))
    kamil.zapytaj("Pierwsze pytanie")
    kamil.zapytaj("Drugie pytanie")
    assert all(w["store"] is False for w in klient.wywolania)
    assert all("previous_response_id" not in w for w in klient.wywolania)
    assert len(klient.wywolania[2]["input"]) > len(klient.wywolania[0]["input"])
    teksty = json.dumps(klient.wywolania[2]["input"], ensure_ascii=False)
    assert "Pierwsze pytanie" in teksty and "Drugie pytanie" in teksty


def test_blad_w_trakcie_tury_cofa_pamiec(tmp_path):
    klient = AtrapaKlienta()
    kamil = KamilHistoria(klient, Budzet(tmp_path / "b.json"))
    kamil.zapytaj("Pytanie 1")
    dlugosc = len(kamil.historia)
    klient.responses.create = lambda **k: (_ for _ in ()).throw(RuntimeError("siec"))
    with pytest.raises(RuntimeError):
        kamil.zapytaj("Pytanie 2")
    assert len(kamil.historia) == dlugosc


def test_budzet_blokuje_wywolanie_api(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LIMIT_USD", 0.0)
    klient = AtrapaKlienta()
    kamil = KamilChain(klient, Budzet(tmp_path / "b.json"))
    with pytest.raises(BudzetPrzekroczony):
        kamil.zapytaj("cokolwiek")
    assert klient.wywolania == []
