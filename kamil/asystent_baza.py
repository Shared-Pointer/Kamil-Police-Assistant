"""Wspólna logika asystenta: wywołanie API przez jedną funkcję i pętla narzędzi."""
import json

from . import config
from .budget import Budzet
from .prompts import SYSTEM_PROMPT
from .tools import NARZEDZIA, wykonaj_narzedzie

ODPOWIEDZ_AWARYJNA = (
    "Przepraszam, nie udało się dokończyć sprawdzania. "
    "Proszę zadzwonić na numer 800 100 200 (numer fikcyjny)."
)


def _oszacuj_tokeny(tekst: str) -> int:
    # Zachowawczo: ok. 3 znaki na token dla języka polskiego.
    return len(tekst) // 3 + 1


class KamilBaza:
    TRYB = "baza"

    def __init__(self, klient=None, budzet=None):
        if klient is None:
            from openai import OpenAI

            klient = OpenAI()
        self.klient = klient
        self.budzet = budzet or Budzet()
        self.statystyki_tur = []  # lista słowników: tokeny wejścia/wyjścia na turę
        self._ostatnie_wejscie = 0
        self._ostatnie_znaki = 0

    # Metody do nadpisania w klasach potomnych.
    def _parametry_pamieci(self) -> dict:
        raise NotImplementedError

    def _po_odpowiedzi(self, odpowiedz) -> None:
        raise NotImplementedError

    def _start_tury(self, tekst: str):
        raise NotImplementedError

    def _po_narzedziach(self, wyniki: list):
        raise NotImplementedError

    def _cofnij_tury(self, stan) -> None:
        raise NotImplementedError

    def _zapamietaj_stan(self):
        raise NotImplementedError

    def reset(self) -> None:
        raise NotImplementedError

    def _wywolaj(self, wejscie):
        """Jedyne miejsce, w którym wołamy API. Tu działa kontrola budżetu."""
        parametry = self._parametry_pamieci()
        szacunek = (
            _oszacuj_tokeny(json.dumps(wejscie, ensure_ascii=False, default=str))
            + _oszacuj_tokeny(SYSTEM_PROMPT)
            + self._ostatnie_wejscie
        )
        self.budzet.sprawdz_przed(szacunek)
        self._ostatnie_znaki = len(json.dumps(wejscie, ensure_ascii=False, default=str))
        odpowiedz = self.klient.responses.create(
            model=config.MODEL,
            instructions=SYSTEM_PROMPT,  # instrukcje nie dziedziczą się przez previous_response_id
            input=wejscie,
            tools=NARZEDZIA,
            max_output_tokens=config.MAX_OUTPUT_TOKENS,
            **parametry,
        )
        uzycie = odpowiedz.usage
        self.budzet.zapisz(uzycie.input_tokens, uzycie.output_tokens, self.TRYB)
        self._ostatnie_wejscie = uzycie.input_tokens
        return odpowiedz

    def zapytaj(self, tekst: str) -> str:
        stan = self._zapamietaj_stan()
        tura = {"tryb": self.TRYB, "input_tokens": 0, "output_tokens": 0, "wywolania": 0, "znaki_wyslane": 0}
        try:
            wejscie = self._start_tury(tekst)
            for _ in range(config.MAX_RUND_NARZEDZI + 1):
                odpowiedz = self._wywolaj(wejscie)
                tura["input_tokens"] += odpowiedz.usage.input_tokens
                tura["output_tokens"] += odpowiedz.usage.output_tokens
                tura["wywolania"] += 1
                tura["znaki_wyslane"] += self._ostatnie_znaki
                self._po_odpowiedzi(odpowiedz)
                wywolania = [o for o in odpowiedz.output if o.type == "function_call"]
                if not wywolania:
                    self.statystyki_tur.append(tura)
                    return odpowiedz.output_text
                wyniki = [
                    {
                        "type": "function_call_output",
                        "call_id": w.call_id,
                        "output": wykonaj_narzedzie(w.name, w.arguments),
                    }
                    for w in wywolania
                ]
                wejscie = self._po_narzedziach(wyniki)
        except Exception:
            self._cofnij_tury(stan)  # nie zostawiamy w pamięci połowy tury
            raise
        self._cofnij_tury(stan)
        return ODPOWIEDZ_AWARYJNA
