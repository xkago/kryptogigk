# Zad2: analiza i łamanie szyfru monoalfabetycznego

Narzędzie `analysis.py` przygotowuje zestawienie częstości znaków dla ALFA26 i ALFA37, pozwala ręcznie podawać znane podstawienia oraz zawiera eksperymentalny solver oparty na n-gramach. Dołączony pakiet `kryptolib/` pochodzi z dostarczonego archiwum Zad1 (`zad_1/genai`) i obsługuje przygotowanie tekstu w obu trybach.

## Uruchomienie

Z katalogu `zad2/gpt_6_luna`:

```sh
python3 analysis.py ścieżka/do/szyfrogramu.txt --mode ALFA26
python3 analysis.py ścieżka/do/szyfrogramu.txt --mode ALFA37
