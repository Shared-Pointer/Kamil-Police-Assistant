"""Pamięć przez previous_response_id: stan rozmowy trzyma OpenAI."""
from .asystent_baza import KamilBaza


class KamilChain(KamilBaza):
    """store=True. Klient pamięta tylko id ostatniej odpowiedzi.

    Uwaga: parametr instructions nie dziedziczy się przez previous_response_id,
    dlatego klasa bazowa przekazuje prompt systemowy w każdym wywołaniu.
    """

    TRYB = "chain"

    def __init__(self, klient=None, budzet=None):
        super().__init__(klient, budzet)
        self.ostatnie_id = None

    def _parametry_pamieci(self) -> dict:
        parametry = {"store": True}
        if self.ostatnie_id:
            parametry["previous_response_id"] = self.ostatnie_id
        return parametry

    def _start_tury(self, tekst: str):
        return [{"role": "user", "content": tekst}]

    def _po_odpowiedzi(self, odpowiedz) -> None:
        self.ostatnie_id = odpowiedz.id

    def _po_narzedziach(self, wyniki: list):
        return wyniki  # tylko nowe wyniki narzędzi, reszta jest po stronie OpenAI

    def _zapamietaj_stan(self):
        return self.ostatnie_id

    def _cofnij_tury(self, stan) -> None:
        self.ostatnie_id = stan

    def reset(self) -> None:
        self.ostatnie_id = None
        self.statystyki_tur = []
