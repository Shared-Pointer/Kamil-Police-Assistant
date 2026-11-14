"""Czat z Kamilem w terminalu: python cli.py [--tryb historia|chain]"""
import argparse

from dotenv import load_dotenv

from kamil.asystent_chain import KamilChain
from kamil.asystent_historia import KamilHistoria
from kamil.budget import Budzet, BudzetPrzekroczony

POMOC = "Komendy: /reset (nowa rozmowa), /budzet (stan limitu), /koniec (wyjście)."


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Kamil, policyjny asystent samoobsługowy")
    parser.add_argument("--tryb", choices=["historia", "chain"], default="chain")
    argumenty = parser.parse_args()

    kamil = KamilChain() if argumenty.tryb == "chain" else KamilHistoria()
    print(f"Kamil, Centrum Obsługi Osób Poszukiwanych (tryb pamięci: {argumenty.tryb}).")
    print("Projekt edukacyjny, wszystkie dane są fikcyjne.")
    print(POMOC)
    while True:
        try:
            tekst = input("\nTy: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not tekst:
            continue
        if tekst == "/koniec":
            break
        if tekst == "/reset":
            kamil.reset()
            print("Rozmowa wyczyszczona.")
            continue
        if tekst == "/budzet":
            print(Budzet().podsumowanie())
            continue
        try:
            print(f"\nKamil: {kamil.zapytaj(tekst)}")
        except BudzetPrzekroczony as blad:
            print(f"\n[Budżet] {blad}")
            break
        except Exception as blad:  # błąd sieci, klucza itp. nie zamyka czatu
            print(f"\n[Błąd] {type(blad).__name__}: {blad}")


if __name__ == "__main__":
    main()
