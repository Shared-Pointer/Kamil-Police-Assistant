"""Wersja bazowa pamięci: cała historia rozmowy trzymana po stronie klienta."""
from .asystent_baza import KamilBaza


class KamilHistoria(KamilBaza):
    """store=False. Przy każdej turze wysyłamy całą listę historii."""

    TRYB = "historia"

    def __init__(self, klient=None, budzet=None):
        super().__init__(klient, budzet)
        self.historia = []

    def _parametry_pamieci(self) -> dict:
        return {"store": False}

    def _start_tury(self, tekst: str):
        self.historia.append({"role": "user", "content": tekst})
        return list(self.historia)

    def _po_odpowiedzi(self, odpowiedz) -> None:
        for element in odpowiedz.output:
            if element.type == "message":
                self.historia.append({"role": "assistant", "content": odpowiedz.output_text})
            elif element.type == "function_call":
                self.historia.append(
                    {
                        "type": "function_call",
                        "call_id": element.call_id,
                        "name": element.name,
                        "arguments": element.arguments,
                    }
                )

    def _po_narzedziach(self, wyniki: list):
        self.historia.extend(wyniki)
        return list(self.historia)

    def _zapamietaj_stan(self):
        return len(self.historia)

    def _cofnij_tury(self, stan) -> None:
        del self.historia[stan:]

    def reset(self) -> None:
        self.historia = []
        self.statystyki_tur = []
