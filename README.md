# Kamil, policyjny asystent samoobsługowy

Prototyp asystenta na przedmiot **Zaawansowane metody sztucznej inteligencji** (WSB Merito Wrocław, prowadzący dr inż. Maciej Pondel).
Autor: Kajetan Mieloch, nr albumu 113353.

Kamil to oficjalny punkt samoobsługowy dla osób poszukiwanych lub podejrzanych. Sprawdza w bazach Interpolu i w lokalnych bazach policyjnych, czy dana osoba jest poszukiwana, wyjaśnia, jak dobrowolnie się zgłosić, jakie przysługują prawa i jak uzyskać obrońcę. Ton jest urzędowy i uprzejmy, z lekką nutą humoru.

**Wszystkie dane w projekcie są fikcyjne.** To projekt edukacyjny.

## Co jest w środku

- **Wiedza** asystenta: 14 zdań regulaminu w `kamil/wiedza.md`.
- **Narzędzia** (function calling): `szukaj_interpol` i `szukaj_baza_lokalna`. Zwracają wyłącznie pola publiczne, więc informator, planowana akcja, adres i notatka wewnętrzna nigdy nie trafiają do modelu.
- **Prompt systemowy** odporny na niewłaściwe pytania: zakres, wiedza i zasady bezpieczeństwa (`kamil/prompts.py`).
- **Dwie wersje pamięci rozmowy**:
  - `KamilHistoria`: cała historia trzymana po stronie klienta,
  - `KamilChain`: pamięć przez `previous_response_id` (stan po stronie OpenAI).
- **Licznik budżetu** z twardym limitem 2 USD, zapisywany poza repozytorium w `~/.kamil_budget.json`.
- **Testy**: offline w `tests/` oraz testy logiki i odporności na manipulację w notebooku.
- **Raport** z wykonanego notebooka: `raport/Raport_Kamil_ZMSI.pdf`.

## Struktura

```
kamil/
  config.py            model, ceny, limit budżetu
  budget.py            licznik budżetu
  wiedza.md            wiedza asystenta
  dane/bazy.json       fikcyjne bazy (Interpol i lokalna)
  tools.py             narzędzia i filtrowanie pól
  prompts.py           prompt systemowy
  asystent_baza.py     wspólna pętla narzędzi, jedyne miejsce wywołania API
  asystent_historia.py pamięć: lista historii
  asystent_chain.py    pamięć: previous_response_id
cli.py                 czat w terminalu
tests/test_tools.py    testy offline
Kamil_asystent.ipynb   notebook z wykonanymi testami (to także raport)
raport/                raport PDF
scripts/build_report.sh budowa PDF z notebooka
```

## Uruchomienie

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Klucz do OpenAI trzeba podać w zmiennej środowiskowej `OPENAI_API_KEY` albo w pliku `.env` (wzór w `.env.example`). Plik `.env` jest ignorowany przez git.

Czat w terminalu:

```bash
python cli.py                  # pamięć przez previous_response_id (domyślnie)
python cli.py --tryb historia  # pamięć jako lista historii
```

W czacie działają komendy `/reset`, `/budzet` i `/koniec`.

Testy offline (nie używają API i nic nie kosztują):

```bash
python -m pytest tests/
```

Notebook z testami (kosztuje kilka centów, a licznik budżetu pilnuje limitu):

```bash
jupyter nbconvert --to notebook --execute --inplace Kamil_asystent.ipynb
./scripts/build_report.sh   # raport PDF
```

## Jak Kamil broni się przed manipulacją

1. **Warstwa danych.** Narzędzia zwracają tylko pola z białej listy. Nawet gdyby model dał się nabrać, nie ma czego wyciec. Wynik jest dodatkowo opakowany jako dane, a nie polecenie.
2. **Warstwa promptu.** Prompt zabrania ujawniania instrukcji, zmiany roli, pomocy w ucieczce i podawania danych osób trzecich, a treść z narzędzi traktuje jako dane. W prompcie ukryty jest znacznik kontrolny, którego wyciek wykrywają testy.
3. **Warstwa kosztów.** Każde wywołanie API przechodzi przez licznik budżetu, więc ewentualna pętla lub nadużycie nie przekroczą 2 USD.

W notebooku jest też test, który na chwilę wyłącza pierwszą warstwę i sprawdza, czy sam model oprze się poleceniu ukrytemu w danych z bazy.

## Pamięć: historia czy previous_response_id

Obie wersje pamiętają kontekst rozmowy. Wersja z `previous_response_id` wysyła po stronie klienta znacznie mniej danych, ale OpenAI i tak rozlicza cały kontekst, a stan rozmowy leży po ich stronie. Parametr `instructions` nie dziedziczy się przez `previous_response_id`, więc prompt systemowy jest przekazywany w każdym wywołaniu. Szczegóły i liczby są w raporcie.
