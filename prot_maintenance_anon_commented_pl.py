#!/usr/bin/env python3
# powyższa pierwsza linia wskazuje systemowi interpreter Python 3.
# ta linia otwiera albo zamyka wieloliniowy opis tekstowy.
"""
ta linia jest częścią składni Pythona i wspiera działanie sąsiednich linii.
Zanonimizowany orkiestrator utrzymania zależności i deployu.

ta linia jest częścią składni Pythona i wspiera działanie sąsiednich linii.
To jest wersja wewnętrznego skryptu utrzymaniowego przeznaczona do udostępnienia, z komentarzami.
ta linia jest częścią składni Pythona i wspiera działanie sąsiednich linii.
Celowo używa fikcyjnych danych SSH i ogólnych ścieżek.

Przepływ ogólny:
  1. Wczytaj konfigurację JSON opisującą projekty.
  2. Dla każdego włączonego projektu zainstaluj albo zaktualizuj zależności.
  3. Uruchom skonfigurowane testy.
  4. Uruchom skonfigurowane buildy.
  5. Opcjonalnie wykonaj deploy przez rsync po SSH.

Model bezpieczeństwa:
  - Domyślny tryb to dry-run, więc skrypt wypisuje komendy, ale ich nie wykonuje.
  - Realne wykonanie wymaga --execute.
  - Realny deploy dodatkowo wymaga --deploy oraz deploy=true w projekcie.

Oficjalna dokumentacja głównych elementów:
    - parsowanie CLI przez argparse: https://docs.python.org/3/library/argparse.html
    - dataclasses: https://docs.python.org/3/library/dataclasses.html
    - ścieżki pathlib: https://docs.python.org/3/library/pathlib.html
    - moduł json: https://docs.python.org/3/library/json.html
    - przechodzenie po katalogach przez os.walk: https://docs.python.org/3/library/os.html#os.walk
    - cytowanie powłoki przez shlex.quote: https://docs.python.org/3/library/shlex.html#shlex.quote
    - wykonywanie komend przez subprocess.run: https://docs.python.org/3/library/subprocess.html#subprocess.run
    - podpowiedzi typów Pythona: https://docs.python.org/3/library/typing.html
    - npm ci: https://docs.npmjs.com/cli/v10/commands/npm-ci
    - npm update: https://docs.npmjs.com/cli/v10/commands/npm-update
    - Composer install: https://getcomposer.org/doc/03-cli.md#install-i
    - Composer update: https://getcomposer.org/doc/03-cli.md#update-u
    - opcje rsync: https://download.samba.org/pub/rsync/rsync.1
    - klient OpenSSH: https://man.openbsd.org/ssh

Jak czytać:
  - Komentarze zaczynające się od "Dlaczego" wyjaśniają powód decyzji.
  - Komentarze zaczynające się od "Co" wyjaśniają bezpośredni efekt linii/bloku.
  - Komentarze zaczynające się od "Ryzyko" wskazują miejsca mogące zmienić pliki lub produkcję.
ta linia otwiera albo zamyka wieloliniowy opis tekstowy.
"""

# ta linia włącza nowsze zachowanie adnotacji typów, żeby typy były wygodniejsze.
from __future__ import annotations

# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# argparse parsuje flagi wiersza poleceń, takie jak --config, --execute i --deploy.
# ta linia importuje moduł argparse, czyli gotowe funkcje z biblioteki Pythona.
import argparse

# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# json czyta i zapisuje plik konfiguracyjny.
# ta linia importuje moduł json, czyli gotowe funkcje z biblioteki Pythona.
import json

# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# os.walk służy do skanowania workspace w poszukiwaniu manifestów pakietów.
# ta linia importuje moduł os, czyli gotowe funkcje z biblioteki Pythona.
import os

# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# shlex.quote bezpiecznie formatuje fragmenty powłoki do wyświetlania i komend SSH.
# ta linia importuje moduł shlex, czyli gotowe funkcje z biblioteki Pythona.
import shlex

# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# subprocess uruchamia zewnętrzne narzędzia: npm, composer, pytest, ssh i rsync.
# ta linia importuje moduł subprocess, czyli gotowe funkcje z biblioteki Pythona.
import subprocess

# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# sys daje dostęp do stderr i argv do raportowania błędów CLI.
# ta linia importuje moduł sys, czyli gotowe funkcje z biblioteki Pythona.
import sys

# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# dataclass ogranicza powtarzalny kod dla kontenera danych Project.
# ta linia importuje wybrane elementy z modułu, żeby można było używać ich krótszą nazwą.
from dataclasses import dataclass, field

# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# Path zapewnia bezpieczniejszą obsługę ścieżek niż zwykłe stringi.
# ta linia importuje wybrane elementy z modułu, żeby można było używać ich krótszą nazwą.
from pathlib import Path

# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# Any jest używane dla słowników JSON, których wartości mogą mieć różne typy.
# ta linia importuje wybrane elementy z modułu, żeby można było używać ich krótszą nazwą.
from typing import Any


# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# Fikcyjny host SSH użyty w anonimowym przykładzie. Zastąp go w prywatnej konfiguracji.
# ta linia definiuje domyślną wartość używaną, gdy config jej nie poda.
DEFAULT_HOST = "deploy.example.com"

# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# Fikcyjny port SSH użyty w anonimowym przykładzie. Zastąp go w prywatnej konfiguracji.
# ta linia definiuje domyślną wartość używaną, gdy config jej nie poda.
DEFAULT_PORT = 22

# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# Fikcyjny login SSH użyty w anonimowym przykładzie. Zastąp go w prywatnej konfiguracji.
# ta linia definiuje domyślną wartość używaną, gdy config jej nie poda.
DEFAULT_USER = "deploy_user"

# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# Nazwy katalogów pomijanych podczas wykrywania projektów w workspace.
# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# To są wygenerowane zależności, cache, narzędzia systemowe albo katalogi platform.
# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# których nie należy traktować jako niezależnych projektów do deployu.
# ta linia zaczyna zbiór nazw katalogów pomijanych podczas skanowania.
PRUNE_DIRS = {
    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
    ".cache",
    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
    ".git",
    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
    ".npm",
    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
    ".venv",
    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
    "Android",
    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
    "android",
    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
    "ios",
    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
    "node_modules",
    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
    "vendor",
    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
    "venv",
# ta linia zamyka albo otwiera strukturę danych lub wywołanie funkcji.
}


# ta linia mówi Pythonowi, żeby automatycznie stworzył konstruktor i obsługę pól klasy.
@dataclass
# ta linia zaczyna definicję klasy, czyli szablonu obiektu przechowującego dane projektu.
class Project:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Jeden lokalnie utrzymywany projekt lub pakiet.

        Atrybuty:
                name: Czytelny identyfikator używany w logach i filtrach --only.
                path: Lokalna ścieżka systemu plików do katalogu projektu.
                remote_path: Zdalny katalog deployu na serwerze.
                enabled: Jeśli false, projekt jest ignorowany przez runner.
                deploy: Jeśli true, projekt może zostać wysłany po podaniu --deploy.
                npm: True, gdy lokalnie istnieje package.json.
                composer: True, gdy lokalnie istnieje composer.json.
                python: True, gdy lokalnie istnieje requirements.txt albo pyproject.toml.
                build_commands: Komendy powłoki uruchamiane po testach, zwykle buildy assetów.
                test_commands: Komendy powłoki, które muszą przejść przed buildem/deployem.
                remote_commands: Komendy powłoki uruchamiane na serwerze po rsync.
                excludes: Dodatkowe wzorce wykluczeń rsync dla tego projektu.
    ta linia otwiera albo zamyka wieloliniowy opis tekstowy.
    """

    # Co: krótki stabilny identyfikator wypisywany w logach i akceptowany przez --only.
    #     name: str
    # Co: bezwzględny lub względny lokalny katalog zawierający projekt.
    #     path: Path
    # Co: katalog docelowy na zdalnym serwerze; None blokuje deploy.
    #     remote_path: str | None = None
    # Co: wyłączone projekty są pomijane przed uruchomieniem jakiejkolwiek komendy.
    #     enabled: bool = True
    # Co: drugi przełącznik bezpieczeństwa; samo --deploy bez tego nie wystarczy.
    #     deploy: bool = False
    # Co: flaga wykrytego package.json, używana do wyboru komend npm.
    #     npm: bool = False
    # Co: flaga wykrytego composer.json, używana do wyboru komend Composer.
    #     composer: bool = False
    # Co: flaga wykrytego manifestu Python, używana do wyboru komend pytest/pip.
    #     python: bool = False
    # Dlaczego: default_factory avoids sharing one mutable list between projects.
    #     build_commands: list[str] = field(default_factory=list)
    # Co: komendy, które muszą zwrócić kod 0 przed buildem/deployem.
    #     test_commands: list[str] = field(default_factory=list)
    # Co: komendy wykonywane przez SSH po rsync, np. migracje/cache.
    #     remote_commands: list[str] = field(default_factory=list)
    # Co: wzorce wykluczeń rsync specyficzne dla projektu.
    #     excludes: list[str] = field(default_factory=list)


# ta linia zaczyna funkcję load_json, czyli nazwany blok kodu do wielokrotnego użycia.
def load_json(path: Path) -> dict[str, Any]:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Wczytaj plik JSON i zwróć go jako słownik.

        path:
              Lokalizacja pliku konfiguracyjnego.
    ta linia otwiera albo zamyka wieloliniowy opis tekstowy.
    """

    # Co: otwórz plik jako tekst UTF-8, żeby działały nazwy ze znakami spoza ASCII.
    # ta linia otwiera zasób w bezpieczny sposób, tutaj najczęściej plik.
    with path.open("r", encoding="utf-8") as f:
            # Co: sparsuj JSON do słowników/list/stringów/liczb Pythona.
        # ta linia kończy funkcję i oddaje wynik do miejsca, które ją wywołało.
        return json.load(f)


# ta linia zaczyna funkcję write_json, czyli nazwany blok kodu do wielokrotnego użycia.
def write_json(path: Path, data: dict[str, Any]) -> None:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Zapisz słownik jako czytelnie sformatowany JSON.

      ensure_ascii=False utrzymuje czytelność nazw projektów spoza ASCII.
    ta linia otwiera albo zamyka wieloliniowy opis tekstowy.
    """

    # Co: json.dumps serializuje dane Pythona z powrotem do JSON.
    # Dlaczego: indent=2 makes the config human-editable.
    # Dlaczego: ensure_ascii=False keeps readable Unicode instead of \uXXXX escapes.
    # ta linia zapisuje tekst do pliku na dysku.
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ta linia zaczyna funkcję run, czyli nazwany blok kodu do wielokrotnego użycia.
def run(cmd: list[str] | str, cwd: Path | None, dry_run: bool, timeout: int | None = None) -> int:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Wypisz i opcjonalnie wykonaj jedną komendę.

        cmd:
              Albo lista tokenów argv, albo tekstowa komenda powłoki.
              String jest używany tylko tam, gdzie celowo potrzebna jest składnia powłoki.
        cwd:
              Katalog roboczy. None oznacza bieżący katalog procesu.
        dry_run:
              Jeśli true, tylko wypisz komendę i zgłoś sukces.
        timeout:
              Maksymalny czas działania w sekundach. None oznacza brak jawnego timeoutu.

        Zwraca:
              Kod wyjścia procesu. 0 oznacza sukces dla komend Unix.
    ta linia otwiera albo zamyka wieloliniowy opis tekstowy.
    """

    # Co: komendy tekstowe potrzebują powłoki, bo mogą zawierać &&, potoki, zmienne środowiskowe itd.
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if isinstance(cmd, str):
            # Komendy tekstowe powłoki są wyświetlane bez zmian i uruchamiane z shell=True.
        # ta linia przygotowuje tekstową wersję komendy do wypisania w terminalu.
        printable = cmd
            # Ryzyko: shell=True executes shell syntax; only use trusted config commands.
        # ta linia ustala, czy komenda ma być uruchomiona przez powłokę systemową.
        shell = True
    # ta linia oznacza wariant awaryjny, gdy wcześniejszy warunek nie był spełniony.
    else:
            # Listy są bezpiecznie cytowane do wyświetlenia i uruchamiane bez shell=True.
            # Co: shlex.quote sprawia, że wypisane komendy są bezpieczne do kopiowania przy spacjach/znakach specjalnych.
        # ta linia przygotowuje tekstową wersję komendy do wypisania w terminalu.
        printable = " ".join(shlex.quote(x) for x in cmd)
            # Dlaczego: shell=False avoids shell interpretation for argv-style commands.
        # ta linia ustala, czy komenda ma być uruchomiona przez powłokę systemową.
        shell = False

    # Co: prefiks pokazuje katalog roboczy przed komendą.
    # ta linia przygotowuje prefiks z katalogiem roboczym do czytelnego logu.
    prefix = f"[{cwd}] " if cwd else ""
    # Co: zawsze wypisuj komendy, także podczas realnego wykonania, dla audytowalności.
    # ta linia wypisuje informację w terminalu dla osoby uruchamiającej skrypt.
    print(f"{prefix}$ {printable}")

    # Co: dry-run zatrzymuje się przed subprocess.run i udaje sukces.
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if dry_run:
        # ta linia kończy funkcję i oddaje wynik do miejsca, które ją wywołało.
        return 0

    # Co: subprocess.run czeka, aż komenda zakończy się albo minie timeout.
    # ta linia uruchamia zewnętrzną komendę i czeka na jej zakończenie.
    completed = subprocess.run(cmd, cwd=cwd, shell=shell, timeout=timeout)
    # Co: kod wywołujący używa returncode, żeby zdecydować, czy zgłosić błąd.
    # ta linia kończy funkcję i oddaje wynik do miejsca, które ją wywołało.
    return completed.returncode


# ta linia zaczyna funkcję detect_projects, czyli nazwany blok kodu do wielokrotnego użycia.
def detect_projects(root: Path) -> list[Project]:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Przeskanuj workspace i wykryj katalogi z manifestami zależności.

        root:
              Katalog główny workspace do przeskanowania.

        Reguły wykrywania:
              package.json -> projekt npm
              composer.json -> projekt Composer/PHP
              requirements.txt albo pyproject.toml -> projekt Python
    ta linia otwiera albo zamyka wieloliniowy opis tekstowy.
    """

    # Co: akumulator dla każdego katalogu wyglądającego jak projekt.
    # ta linia tworzy pustą listę z podpowiedzią typu dla czytelności kodu.
    projects: list[Project] = []

    # Co: os.walk zwraca każdy katalog, jego podkatalogi i nazwy plików.
    # ta linia zaczyna pętlę, czyli powtarzanie operacji dla kolejnych elementów.
    for dirpath, dirnames, filenames in os.walk(root):
            # Co: zamień tekstową ścieżkę z os.walk na obiekt pathlib.Path.
        # ta linia zamienia tekstową ścieżkę na obiekt Path i normalizuje ją.
        path = Path(dirpath)
            # Co: oblicz ścieżkę względem root, żeby nazwy projektów były stabilne i czytelne.
        # ta linia przypisuje wartość do zmiennej, czyli zapamiętuje wynik pod nazwą.
        rel = path.relative_to(root) if path != root else Path(".")

            # Jeśli bieżący katalog jest już w pomijanej ścieżce, zatrzymaj dalsze schodzenie.
            # dalej w głąb.
        # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
        if set(rel.parts) & PRUNE_DIRS:
            #             dirnames[:] = []
            # ta linia jest częścią składni Pythona i wspiera działanie sąsiednich linii.
            continue

            # Usuń pomijane katalogi potomne, zanim odwiedzi je os.walk.
        #         dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS]

            # Co: te booleany klasyfikują menedżery pakietów po plikach manifestu.
        # ta linia ustawia wartość True/False zależnie od tego, czy wykryto dany manifest.
        npm = "package.json" in filenames
        # ta linia ustawia wartość True/False zależnie od tego, czy wykryto dany manifest.
        composer = "composer.json" in filenames
        # ta linia ustawia wartość True/False zależnie od tego, czy wykryto dany manifest.
        python = "requirements.txt" in filenames or "pyproject.toml" in filenames

            # Co: tylko katalogi z co najmniej jednym znanym manifestem stają się projektami.
        # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
        if npm or composer or python:
                    # Co: utwórz obiekt Project i dopisz go do listy wynikowej.
            # ta linia dopisuje znaleziony projekt do listy projektów.
            projects.append(
                # ta linia jest częścią składni Pythona i wspiera działanie sąsiednich linii.
                Project(
                    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                    name=str(rel),
                    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                    path=path,
                    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                    npm=npm,
                    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                    composer=composer,
                    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                    python=python,
                # ta linia zamyka albo otwiera strukturę danych lub wywołanie funkcji.
                )
            # ta linia zamyka albo otwiera strukturę danych lub wywołanie funkcji.
            )

    # Co: zwróć wszystkie wykryte projekty do wywołującego.
    # ta linia kończy funkcję i oddaje wynik do miejsca, które ją wywołało.
    return projects


# ta linia zaczyna funkcję default_tests, czyli nazwany blok kodu do wielokrotnego użycia.
def default_tests(project: Project) -> list[str]:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Zwróć rozsądne domyślne komendy testów dla wykrytego projektu."""

    # Co: zacznij bez komend i dodaj tylko te pasujące do wykrytych narzędzi.
    # ta linia tworzy pustą listę z podpowiedzią typu dla czytelności kodu.
    commands: list[str] = []

    # Co: Projekty Composer często udostępniają skrypt "composer test".
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if project.composer:
        # ta linia dopisuje kolejną komendę do listy poleceń do wykonania.
        commands.append("composer test")
    # Co: --if-present zapobiega błędowi npm, gdy nie istnieje skrypt testowy.
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if project.npm:
        # ta linia dopisuje kolejną komendę do listy poleceń do wykonania.
        commands.append("npm test --if-present")
    # Co: pytest to popularny runner testów Python; config może to nadpisać.
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if project.python:
        # ta linia dopisuje kolejną komendę do listy poleceń do wykonania.
        commands.append("python3 -m pytest")

    # ta linia kończy funkcję i oddaje wynik do miejsca, które ją wywołało.
    return commands


# ta linia zaczyna funkcję default_builds, czyli nazwany blok kodu do wielokrotnego użycia.
def default_builds(project: Project) -> list[str]:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Zwróć rozsądne domyślne komendy buildu dla wykrytego projektu."""

    # ta linia tworzy pustą listę z podpowiedzią typu dla czytelności kodu.
    commands: list[str] = []

    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if project.npm:
        # ta linia dopisuje kolejną komendę do listy poleceń do wykonania.
        commands.append("npm run build --if-present")

    # ta linia kończy funkcję i oddaje wynik do miejsca, które ją wywołało.
    return commands


# ta linia zaczyna funkcję make_template, czyli nazwany blok kodu do wielokrotnego użycia.
def make_template(root: Path, output: Path) -> None:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Utwórz startowy config JSON z wykrytych projektów.

      Wszystkie projekty są domyślnie wyłączone. Zapobiega to przypadkowym masowym aktualizacjom
      albo deployom zaraz po wygenerowaniu pliku.
    ta linia otwiera albo zamyka wieloliniowy opis tekstowy.
    """

    # Co: najpierw wykryj projekty, potem zamień je na wpisy konfiguracji.
    # ta linia przypisuje wartość do zmiennej, czyli zapamiętuje wynik pod nazwą.
    projects = detect_projects(root)
    # Co: this dict mirrors the final JSON file structure.
    # ta linia przypisuje wartość do zmiennej, czyli zapamiętuje wynik pod nazwą.
    config = {
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        "ssh": {
            # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
            "host": DEFAULT_HOST,
            # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
            "port": DEFAULT_PORT,
            # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
            "user": DEFAULT_USER,
            # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
            "identity_file": "",
        # ta linia zamyka albo otwiera strukturę danych lub wywołanie funkcji.
        },
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        "projects": [
            # ta linia zamyka albo otwiera strukturę danych lub wywołanie funkcji.
            {
                # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                "name": p.name,
                # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                "path": str(p.path),
                # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                "enabled": False,
                # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                "deploy": False,
                # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                "remote_path": "/srv/apps/CHANGE_ME",
                # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                "test_commands": default_tests(p),
                # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                "build_commands": default_builds(p),
                # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                "remote_commands": [],
                # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                "excludes": [
                    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                    ".git",
                    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                    ".env",
                    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                    "node_modules",
                    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                    "storage/logs",
                    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                    "tests",
                    # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
                    "vendor",
                # ta linia zamyka albo otwiera strukturę danych lub wywołanie funkcji.
                ],
            # ta linia zamyka albo otwiera strukturę danych lub wywołanie funkcji.
            }
            # ta linia zaczyna pętlę, czyli powtarzanie operacji dla kolejnych elementów.
            for p in projects
        # ta linia zamyka albo otwiera strukturę danych lub wywołanie funkcji.
        ],
    # ta linia zamyka albo otwiera strukturę danych lub wywołanie funkcji.
    }

    # Co: zapisz wygenerowany szablon na dysku.
    # ta linia jest częścią składni Pythona i wspiera działanie sąsiednich linii.
    write_json(output, config)
    # Co: powiedz operatorowi, gdzie zapisano plik.
    # ta linia wypisuje informację w terminalu dla osoby uruchamiającej skrypt.
    print(f"Wrote template: {output}")
    # ta linia wypisuje informację w terminalu dla osoby uruchamiającej skrypt.
    print("All projects are disabled by default. Enable only projects that should be maintained.")


# ta linia zaczyna funkcję project_from_config, czyli nazwany blok kodu do wielokrotnego użycia.
def project_from_config(item: dict[str, Any]) -> Project:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Zamień jeden wpis projektu JSON na obiekt Project.

        item:
              Jeden słownik z config["projects"].

      Funkcja ponownie wykrywa pliki manifestów z dysku, bo lokalny projekt
      mógł się zmienić od czasu wygenerowania configu.
    ta linia otwiera albo zamyka wieloliniowy opis tekstowy.
    """

    # Co: rozwiń ~ i znormalizuj segmenty względne do ścieżki bezwzględnej.
    # ta linia zamienia tekstową ścieżkę na obiekt Path i normalizuje ją.
    path = Path(item["path"]).expanduser().resolve()
    # Co: wypisz nazwy bezpośrednich plików potomnych, jeśli katalog istnieje; inaczej użyj pustego zbioru.
    # ta linia zbiera nazwy plików w katalogu projektu, żeby wykryć typ projektu.
    filenames = {p.name for p in path.iterdir()} if path.exists() and path.is_dir() else set()

    # Co: zbuduj obiekt Project używany przez pipeline.
    # ta linia kończy funkcję i oddaje wynik do miejsca, które ją wywołało.
    return Project(
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        name=item.get("name") or path.name,
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        path=path,
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        remote_path=item.get("remote_path"),
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        enabled=bool(item.get("enabled", True)),
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        deploy=bool(item.get("deploy", False)),
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        npm="package.json" in filenames,
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        composer="composer.json" in filenames,
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        python="requirements.txt" in filenames or "pyproject.toml" in filenames,
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        build_commands=list(item.get("build_commands", [])),
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        test_commands=list(item.get("test_commands", [])),
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        remote_commands=list(item.get("remote_commands", [])),
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        excludes=list(item.get("excludes", [])),
    # ta linia zamyka albo otwiera strukturę danych lub wywołanie funkcji.
    )


# ta linia zaczyna funkcję update_dependencies, czyli nazwany blok kodu do wielokrotnego użycia.
def update_dependencies(project: Project, dry_run: bool) -> None:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Zaktualizuj wersje zależności dla jednego projektu.

        To jest ryzykowny tryb. Może przepisać pliki lockfile:
          - composer update może zmienić composer.lock.
          - npm update może zmienić package-lock.json.
          - pip install -U aktualizuje zainstalowane pakiety Python w aktywnym środowisku.
    ta linia otwiera albo zamyka wieloliniowy opis tekstowy.
    """

    # Ryzyko: composer update may modify composer.lock and installed package versions.
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if project.composer:
        # ta linia uruchamia przygotowaną komendę i zapisuje jej kod zakończenia.
        rc = run(["composer", "update", "--no-interaction"], project.path, dry_run, timeout=1800)
        # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
        if rc != 0:
            # ta linia celowo zgłasza błąd, bo dalsze działanie byłoby niepoprawne.
            raise RuntimeError(f"{project.name}: composer update failed")

    # Ryzyko: npm update may modify package-lock.json.
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if project.npm:
            # Co: package-lock.json oznacza, że npm może aktualizować w ramach istniejących ograniczeń.
        # ta linia buduje ścieżkę do pliku lockfile npm.
        lock = project.path / "package-lock.json"
            # Co: without a lockfile, npm install creates/resolves dependency tree.
        # ta linia tworzy listę elementów komendy, która będzie później uruchomiona.
        cmd = ["npm", "update"] if lock.exists() else ["npm", "install"]
        # ta linia uruchamia przygotowaną komendę i zapisuje jej kod zakończenia.
        rc = run(cmd, project.path, dry_run, timeout=1800)
        # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
        if rc != 0:
            # ta linia celowo zgłasza błąd, bo dalsze działanie byłoby niepoprawne.
            raise RuntimeError(f"{project.name}: npm update/install failed")

    # Ryzyko: this updates the active Python environment, not a lockfile.
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if project.python:
            # Co: requirements.txt to klasyczny plik wejściowy pip.
        # ta linia buduje ścieżkę do pliku requirements.txt.
        req = project.path / "requirements.txt"
        # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
        if req.exists():
            # ta linia uruchamia przygotowaną komendę i zapisuje jej kod zakończenia.
            rc = run(["python3", "-m", "pip", "install", "-U", "-r", str(req)], project.path, dry_run, timeout=1800)
            # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
            if rc != 0:
                # ta linia celowo zgłasza błąd, bo dalsze działanie byłoby niepoprawne.
                raise RuntimeError(f"{project.name}: pip install failed")


# ta linia zaczyna funkcję install_locked, czyli nazwany blok kodu do wielokrotnego użycia.
def install_locked(project: Project, dry_run: bool) -> None:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Zainstaluj dokładne zablokowane wersje zależności dla jednego projektu.

      To jest bezpieczniejszy tryb używany, gdy nie podano --apply-updates.
      Przygotowuje zależności bez celowego podbijania wersji.
    ta linia otwiera albo zamyka wieloliniowy opis tekstowy.
    """

    # Co: uruchom instalację z lockfile tylko, gdy istnieje composer.lock.
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if project.composer and (project.path / "composer.lock").exists():
        # ta linia uruchamia przygotowaną komendę i zapisuje jej kod zakończenia.
        rc = run(["composer", "install", "--no-interaction", "--prefer-dist"], project.path, dry_run, timeout=1200)
        # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
        if rc != 0:
            # ta linia celowo zgłasza błąd, bo dalsze działanie byłoby niepoprawne.
            raise RuntimeError(f"{project.name}: composer install failed")

    # Co: npm ci wymaga package-lock.json i instaluje dokładne zablokowane wersje.
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if project.npm and (project.path / "package-lock.json").exists():
        # ta linia uruchamia przygotowaną komendę i zapisuje jej kod zakończenia.
        rc = run(["npm", "ci"], project.path, dry_run, timeout=1200)
        # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
        if rc != 0:
            # ta linia celowo zgłasza błąd, bo dalsze działanie byłoby niepoprawne.
            raise RuntimeError(f"{project.name}: npm ci failed")


# ta linia zaczyna funkcję run_commands, czyli nazwany blok kodu do wielokrotnego użycia.
def run_commands(project: Project, commands: list[str], dry_run: bool, label: str) -> None:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Uruchom komendy test/build specyficzne dla projektu.

        label:
              Czytelna nazwa fazy używana w komunikatach błędów, np. "tests".
    ta linia otwiera albo zamyka wieloliniowy opis tekstowy.
    """

    # Co: uruchom komendy w kolejności podanej w configu.
    # ta linia zaczyna pętlę, czyli powtarzanie operacji dla kolejnych elementów.
    for command in commands:
            # Co: komenda jest stringiem, więc składnia shell w configu jest dozwolona.
        # ta linia uruchamia przygotowaną komendę i zapisuje jej kod zakończenia.
        rc = run(command, project.path, dry_run, timeout=1800)
        # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
        if rc != 0:
            # ta linia celowo zgłasza błąd, bo dalsze działanie byłoby niepoprawne.
            raise RuntimeError(f"{project.name}: {label} failed: {command}")


# ta linia zaczyna funkcję ssh_base, czyli nazwany blok kodu do wielokrotnego użycia.
def ssh_base(ssh: dict[str, Any]) -> list[str]:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Zbuduj wspólny prefiks komendy SSH z config["ssh"]."""

    # Co: lista argv zaczyna się od programu ssh.
    # ta linia tworzy listę elementów komendy, która będzie później uruchomiona.
    cmd = [
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        "ssh",
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        "-p",
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        str(ssh.get("port", DEFAULT_PORT)),
    # ta linia zamyka albo otwiera strukturę danych lub wywołanie funkcji.
    ]

    # Co: opcjonalna ścieżka do klucza prywatnego z configu.
    # ta linia pobiera opcjonalną ścieżkę do prywatnego klucza SSH.
    identity = ssh.get("identity_file")
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if identity:
        # ta linia dopisuje kilka elementów do listy komendy.
        cmd.extend(["-i", str(Path(identity).expanduser())])

    # Co: dopisz cel SSH w formacie user@host.
    # ta linia dopisuje jeden element na końcu listy komendy.
    cmd.append(f"{ssh.get('user', DEFAULT_USER)}@{ssh.get('host', DEFAULT_HOST)}")
    # Co: zwróć wielorazowy prefiks komendy, jeszcze nieuruchomiony.
    # ta linia kończy funkcję i oddaje wynik do miejsca, które ją wywołało.
    return cmd


# ta linia zaczyna funkcję deploy_project, czyli nazwany blok kodu do wielokrotnego użycia.
def deploy_project(project: Project, ssh: dict[str, Any], dry_run: bool) -> None:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Wyślij jeden projekt przez rsync i uruchom opcjonalne komendy zdalne.

      Upload używa --delete, więc pliki usunięte lokalnie są też usuwane zdalnie.
      To jest przydatne dla czystych deployów, ale sprawia, że dokładność remote_path
      jest krytyczna.
    ta linia otwiera albo zamyka wieloliniowy opis tekstowy.
    """

    # Co: deploy nie może ruszyć bez katalogu docelowego.
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if not project.remote_path:
        # ta linia celowo zgłasza błąd, bo dalsze działanie byłoby niepoprawne.
        raise RuntimeError(f"{project.name}: remote_path is required for deploy")

    # Co: podstawowe wykluczenia rsync chronią lokalne/runtime pliki przed uploadem.
    # Ryzyko: excluding .env prevents overwriting production secrets.
    # ta linia zaczyna listę wykluczeń dla rsync.
    excludes = [
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        "--exclude",
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        ".git",
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        "--exclude",
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        "node_modules",
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        "--exclude",
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        ".env",
    # ta linia zamyka albo otwiera strukturę danych lub wywołanie funkcji.
    ]

    # Co: dopisz reguły wykluczeń specyficzne dla projektu z konfiguracji.
    # ta linia zaczyna pętlę, czyli powtarzanie operacji dla kolejnych elementów.
    for item in project.excludes:
            # Co: rsync oczekuje każdego wykluczenia jako dwóch tokenów argv: --exclude WZORZEC.
        # ta linia rozszerza listę wzorców, których rsync nie ma wysyłać na serwer.
        excludes.extend(["--exclude", item])

    # Co: rsync dostaje transport SSH jako jeden string po -e.
    # ta linia buduje fragment komendy SSH używany przez rsync.
    ssh_cmd = f"ssh -p {int(ssh.get('port', DEFAULT_PORT))}"
    # Co: opcjonalna ścieżka do klucza prywatnego z configu.
    # ta linia pobiera opcjonalną ścieżkę do prywatnego klucza SSH.
    identity = ssh.get("identity_file")
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if identity:
        # ta linia przypisuje wartość do zmiennej, czyli zapamiętuje wynik pod nazwą.
        ssh_cmd += f" -i {shlex.quote(str(Path(identity).expanduser()))}"

    # Co: zbuduj zdalny cel rsync w formacie user@host:/path/.
    # Dlaczego: rstrip avoids accidental double slash before the final /.
    # ta linia składa adres zdalny w formacie użytkownik@host:ścieżka.
    remote = f"{ssh.get('user', DEFAULT_USER)}@{ssh.get('host', DEFAULT_HOST)}:{project.remote_path.rstrip('/')}/"
    # Co: zbuduj listę argv dla rsync.
    # ta linia zaczyna budowanie komendy rsync odpowiedzialnej za wysyłkę plików.
    rsync_cmd = [
            # Co: nazwa programu wykonywalnego.
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        "rsync",
            # Co: -a zachowuje metadane rekurencyjnie, a -z kompresuje transfer.
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        "-az",
            # Ryzyko: --delete removes remote files missing locally. Use only with verified remote_path.
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        "--delete",
            # Co: rozwiń listę excludes bezpośrednio do argv rsync.
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        *excludes,
            # Co: -e mówi rsync, której zdalnej powłoki użyć.
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        "-e",
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        ssh_cmd,
            # Co: trailing slash means copy directory contents, not the directory itself.
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        f"{str(project.path).rstrip('/')}/",
            # Co: zdalny cel złożony powyżej.
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        remote,
    # ta linia zamyka albo otwiera strukturę danych lub wywołanie funkcji.
    ]

    # Co: upload files unless dry-run is active.
    # ta linia uruchamia przygotowaną komendę i zapisuje jej kod zakończenia.
    rc = run(rsync_cmd, None, dry_run, timeout=1800)
    # Co: niezerowy kod wyjścia rsync zatrzymuje ten projekt.
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if rc != 0:
        # ta linia celowo zgłasza błąd, bo dalsze działanie byłoby niepoprawne.
        raise RuntimeError(f"{project.name}: rsync failed")

    # Co: uruchom komendy po deployu na serwerze w skonfigurowanej kolejności.
    # ta linia zaczyna pętlę, czyli powtarzanie operacji dla kolejnych elementów.
    for command in project.remote_commands:
            # Co: najpierw przejdź do katalogu deployu, potem uruchom skonfigurowaną komendę.
        # ta linia tworzy komendę, która najpierw przejdzie do katalogu na serwerze.
        remote_command = f"cd {shlex.quote(project.remote_path)} && {command}"
            # Co: *ssh_base expands the SSH argv prefix into this command list.
        # ta linia uruchamia przygotowaną komendę i zapisuje jej kod zakończenia.
        rc = run([*ssh_base(ssh), remote_command], None, dry_run, timeout=1200)
        # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
        if rc != 0:
            # ta linia celowo zgłasza błąd, bo dalsze działanie byłoby niepoprawne.
            raise RuntimeError(f"{project.name}: remote command failed: {command}")


# ta linia zaczyna funkcję execute, czyli nazwany blok kodu do wielokrotnego użycia.
def execute(config_path: Path, apply_updates: bool, deploy: bool, dry_run: bool, only: set[str]) -> int:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Uruchom pipeline utrzymaniowy dla wszystkich wybranych projektów.

        Pipeline dla każdego projektu:
      ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
      1. zainstaluj zablokowane zależności albo zaktualizuj zależności,
      ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
      2. uruchom testy,
      ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
      3. uruchom buildy,
          4. opcjonalnie wykonaj deploy.

        Zwraca:
              0, gdy wszystkie wybrane projekty przejdą; 1, gdy co najmniej jeden nie przejdzie.
    ta linia otwiera albo zamyka wieloliniowy opis tekstowy.
    """

    # Co: wczytaj z dysku config JSON utrzymywany przez operatora.
    # ta linia wczytuje konfigurację JSON z pliku.
    config = load_json(config_path)
    # Co: Ustawienia SSH są opcjonalne; braki uzupełniają wartości domyślne.
    # ta linia pobiera ustawienia SSH z konfiguracji albo pusty słownik.
    ssh = config.get("ssh", {})
    # Co: zamień surowe słowniki JSON projektów na obiekty Project.
    # ta linia tworzy listę projektów za pomocą składni list comprehension.
    projects = [project_from_config(item) for item in config.get("projects", [])]
    # Co: zostaw tylko włączone projekty i opcjonalnie tylko nazwy wskazane przez --only.
    # ta linia tworzy listę projektów za pomocą składni list comprehension.
    projects = [p for p in projects if p.enabled and (not only or p.name in only)]

    # Co: pusty wybór nie jest błędem; po prostu nie ma nic do zrobienia.
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if not projects:
        # ta linia wypisuje informację w terminalu dla osoby uruchamiającej skrypt.
        print("No enabled projects matched.")
        # ta linia kończy funkcję i oddaje wynik do miejsca, które ją wywołało.
        return 0

    # Co: zbieraj błędy zamiast przerywać cały batch przy pierwszym błędzie.
    # ta linia tworzy pustą listę z podpowiedzią typu dla czytelności kodu.
    failures: list[str] = []

    # Co: przetwarzaj projekty jeden po drugim.
    # ta linia zaczyna pętlę, czyli powtarzanie operacji dla kolejnych elementów.
    for project in projects:
            # Co: visible section marker in terminal output.
        # ta linia wypisuje informację w terminalu dla osoby uruchamiającej skrypt.
        print(f"\n=== {project.name} ===")

            # Dlaczego: per-project try/except lets later projects continue after one failure.
        # ta linia zaczyna blok, w którym mogą wystąpić błędy przechwytywane niżej.
        try:
                    # Co: przerwij wcześnie, jeśli config wskazuje brakujący lokalny katalog.
            # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
            if not project.path.exists():
                # ta linia celowo zgłasza błąd, bo dalsze działanie byłoby niepoprawne.
                raise RuntimeError(f"path does not exist: {project.path}")

                    # Co: wybierz między ryzykownym trybem aktualizacji a bezpieczniejszą instalacją z lockfile.
            # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
            if apply_updates:
                # ta linia jest częścią składni Pythona i wspiera działanie sąsiednich linii.
                update_dependencies(project, dry_run)
            # ta linia oznacza wariant awaryjny, gdy wcześniejszy warunek nie był spełniony.
            else:
                # ta linia jest częścią składni Pythona i wspiera działanie sąsiednich linii.
                install_locked(project, dry_run)

                    # Co: testy muszą przejść przed buildami.
            # ta linia jest częścią składni Pythona i wspiera działanie sąsiednich linii.
            run_commands(project, project.test_commands, dry_run, "tests")
                    # Co: buildy muszą przejść przed deployem.
            # ta linia jest częścią składni Pythona i wspiera działanie sąsiednich linii.
            run_commands(project, project.build_commands, dry_run, "build")

                    # Co: deploy wymaga jednocześnie globalnego --deploy i deploy=true w projekcie.
            # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
            if deploy and project.deploy:
                # ta linia jest częścią składni Pythona i wspiera działanie sąsiednich linii.
                deploy_project(project, ssh, dry_run)
            # ta linia sprawdza kolejny warunek, jeśli poprzednie warunki nie pasowały.
            elif deploy:
                            # Co: wyjaśnij, dlaczego upload nie nastąpił dla tego projektu.
                # ta linia wypisuje informację w terminalu dla osoby uruchamiającej skrypt.
                print("Deploy skipped: project.deploy=false")

            # Co: każdy wyjątek w tym projekcie jest zapisany jako porażka.
        # ta linia obsługuje błąd, żeby cały skrypt nie kończył się natychmiast.
        except Exception as exc:
                    # Co: zachowaj nazwę projektu razem z komunikatem wyjątku.
            # ta linia zapisuje opis błędu, żeby pokazać go w podsumowaniu.
            failures.append(f"{project.name}: {exc}")
                    # Co: stderr oddziela błędy od normalnych logów komend.
            # ta linia wypisuje informację w terminalu dla osoby uruchamiającej skrypt.
            print(f"ERROR: {exc}", file=sys.stderr)

    # Co: końcowe podsumowanie ułatwia skanowanie długiego wyniku batcha.
    # ta linia wypisuje informację w terminalu dla osoby uruchamiającej skrypt.
    print("\n=== Summary ===")
    # ta linia wypisuje informację w terminalu dla osoby uruchamiającej skrypt.
    print(f"Projects: {len(projects)}")
    # ta linia wypisuje informację w terminalu dla osoby uruchamiającej skrypt.
    print(f"Failures: {len(failures)}")

    # Co: wypisz każdy błąd w osobnej linii dla łatwego kopiowania.
    # ta linia zaczyna pętlę, czyli powtarzanie operacji dla kolejnych elementów.
    for failure in failures:
        # ta linia wypisuje informację w terminalu dla osoby uruchamiającej skrypt.
        print(f"- {failure}")

    # Co: niezerowy kod wyjścia pozwala automatyzacji/CI wykryć porażkę.
    # ta linia kończy funkcję i oddaje wynik do miejsca, które ją wywołało.
    return 1 if failures else 0


# ta linia zaczyna funkcję main, czyli nazwany blok kodu do wielokrotnego użycia.
def main() -> int:
    # ta linia zaczyna wieloliniowy opis działania pliku albo funkcji.
    """Punkt wejścia CLI.

      Parsuje argumenty, tworzy szablon na żądanie, a w przeciwnym razie uruchamia
      pipeline utrzymaniowy.
    ta linia otwiera albo zamyka wieloliniowy opis tekstowy.
    """

    # Co: utwórz parser wiersza poleceń i główny tekst pomocy.
    # ta linia tworzy parser argumentów, czyli mechanizm rozumienia opcji CLI.
    parser = argparse.ArgumentParser(description="Update, test, build and deploy configured projects.")
    # Co: --root jest używany tylko podczas generowania szablonu konfiguracji.
    # ta linia dodaje jedną opcję wiersza poleceń, której można użyć przy uruchamianiu skryptu.
    parser.add_argument("--root", default="/workspace", help="Workspace root for template generation.")
    # Co: --config wskazuje plik JSON kontrolujący projekty i SSH.
    # ta linia dodaje jedną opcję wiersza poleceń, której można użyć przy uruchamianiu skryptu.
    parser.add_argument("--config", default="./maintenance.config.json", help="Config file path.")
    # Co: store_true oznacza, że flaga staje się True, gdy jest podana.
    # ta linia dodaje jedną opcję wiersza poleceń, której można użyć przy uruchamianiu skryptu.
    parser.add_argument("--init-config", action="store_true", help="Create a disabled template config and exit.")
    # ta linia dodaje jedną opcję wiersza poleceń, której można użyć przy uruchamianiu skryptu.
    parser.add_argument("--apply-updates", action="store_true", help="Run package update commands instead of locked installs.")
    # ta linia dodaje jedną opcję wiersza poleceń, której można użyć przy uruchamianiu skryptu.
    parser.add_argument("--deploy", action="store_true", help="Deploy projects with deploy=true via rsync/SSH.")
    # ta linia dodaje jedną opcję wiersza poleceń, której można użyć przy uruchamianiu skryptu.
    parser.add_argument("--execute", action="store_true", help="Actually run commands. Without this, dry-run is used.")
    # ta linia dodaje jedną opcję wiersza poleceń, której można użyć przy uruchamianiu skryptu.
    parser.add_argument("--only", action="append", default=[], help="Run only a named project. Can be repeated.")
    # Co: sparsuj sys.argv według definicji powyżej.
    # ta linia czyta argumenty przekazane w terminalu i zapisuje je w obiekcie args.
    args = parser.parse_args()

    # Co: znormalizuj --root do bezwzględnego pathlib.Path.
    # ta linia zamienia tekstową ścieżkę na obiekt Path i normalizuje ją.
    root = Path(args.root).expanduser().resolve()
    # Co: znormalizuj --config do bezwzględnego pathlib.Path.
    # ta linia zamienia tekstową ścieżkę na obiekt Path i normalizuje ją.
    config_path = Path(args.config).expanduser().resolve()

    # Co: generowanie szablonu to osobny tryb, który kończy się natychmiast.
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if args.init_config:
        # ta linia jest częścią składni Pythona i wspiera działanie sąsiednich linii.
        make_template(root, config_path)
        # ta linia kończy funkcję i oddaje wynik do miejsca, które ją wywołało.
        return 0

    # Co: normalne uruchomienie wymaga istniejącego pliku config.
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if not config_path.exists():
        # ta linia wypisuje informację w terminalu dla osoby uruchamiającej skrypt.
        print(f"Config not found: {config_path}", file=sys.stderr)
        # ta linia wypisuje informację w terminalu dla osoby uruchamiającej skrypt.
        print(f"Create one with: {sys.argv[0]} --init-config", file=sys.stderr)
        # ta linia kończy funkcję i oddaje wynik do miejsca, które ją wywołało.
        return 2

    # Co: brak --execute oznacza tryb dry-run. To główne domyślne zabezpieczenie.
    # ta linia ustala, czy skrypt ma tylko pokazywać komendy, czy naprawdę je wykonywać.
    dry_run = not args.execute

    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if dry_run:
        # ta linia wypisuje informację w terminalu dla osoby uruchamiającej skrypt.
        print("DRY RUN: pass --execute to run commands.")
    # ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
    if args.deploy and dry_run:
        # ta linia wypisuje informację w terminalu dla osoby uruchamiającej skrypt.
        print("Deploy is also dry-run. Nothing will be uploaded.")

    # Co: przekaż sparsowane wartości CLI do funkcji orkiestrującej.
    # ta linia kończy funkcję i oddaje wynik do miejsca, które ją wywołało.
    return execute(
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        config_path=config_path,
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        apply_updates=args.apply_updates,
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        deploy=args.deploy,
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        dry_run=dry_run,
        # ta linia jest elementem większej listy, słownika albo wieloliniowego tekstu.
        only=set(args.only),
    # ta linia zamyka albo otwiera strukturę danych lub wywołanie funkcji.
    )


# ta linia jest komentarzem dla człowieka; Python ją ignoruje podczas wykonywania.
# Co: this block runs only when the file is executed as a script, not imported.
# ta linia sprawdza warunek; kod pod spodem wykona się tylko, jeśli warunek jest prawdziwy.
if __name__ == "__main__":
    # Co: SystemExit używa kodu zwrotu main() jako statusu procesu.
    # ta linia celowo zgłasza błąd, bo dalsze działanie byłoby niepoprawne.
    raise SystemExit(main())
