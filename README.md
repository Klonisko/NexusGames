# NexusGames — szybki poradnik uruchomienia (dla nie‑IT)

Krótko: krok po kroku jak uruchomić aplikację na nowym komputerze z Windows. Instrukcja zakłada, że pracujesz lokalnie i chcesz uruchomić projekt z folderu NexusGames.

Wymagania w skrócie
- Windows, dostęp do konta z prawami instalacji
- Python 3.8+ (zalecane 3.9–3.11)
- Serwer MySQL lub MariaDB (możesz użyć XAMPP)
- Pliki projektu w folderze (mian.py, db_schema.sql, img/, requirements.txt, .env_example)

1) Pobranie i przygotowanie plików
- Skompresuj/przenieś cały folder NexusGames na komputer uczelni lub skopiuj go na pulpit.
- Upewnij się, że w folderze są: mian.py, db_schema.sql, img/ oraz requirements.txt (jeśli nie ma, wygeneruj lokalnie przed przeniesieniem).

2) Zainstaluj Pythona
- Pobierz i zainstaluj Python ze strony https://python.org (zaznacz "Add Python to PATH" podczas instalacji).
- Sprawdź w PowerShell:
```powershell
python --version
```

3) Zainstaluj serwer MySQL / MariaDB
- Najprościej: zainstaluj XAMPP lub MySQL Community Server oraz MySQL Workbench.
- Uruchom serwer MySQL (panel XAMPP lub usługę MySQL).

4) Zaimportuj schemat bazy danych
- Utwórz bazę danych `nexus_games` w Workbench lub CLI:
  - MySQL Workbench: File → Run SQL Script → wybierz db_schema.sql i uruchom.
  - Albo w PowerShell / CMD (w katalogu z plikiem):
```powershell
mysql -u root -p
# wprowadź hasło, następnie w konsoli mysql:
CREATE DATABASE IF NOT EXISTS nexus_games;
USE nexus_games;
SOURCE C:/Users/<TwojUser>/Desktop/NexusGames/db_schema.sql;
EXIT;
```
- Jeśli masz plik eksportu (dump), zaimportuj go:
```powershell
mysql -u root -p nexus_games < "C:\Users\<TwojUser>\Desktop\NexusGames\nexus_games_backup.sql"
```

5) Przygotuj plik .env (konfiguracja połączenia)
- Skopiuj `.env_example` lub utwórz `.env` w folderze projektu z zawartością:
```text
DB_HOST=localhost
DB_USER=root
DB_PASS=
DB_NAME=nexus_games
```
- Jeśli MySQL ma hasło dla root, wpisz je w DB_PASS.

6) (Opcjonalne) Stwórz virtualenv i zainstaluj zależności
- W PowerShell, w katalogu projektu:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate
python -m pip install --upgrade pip
# jeśli masz requirements.txt:
python -m pip install -r requirements.txt
# jeśli nie, zainstaluj potrzebne pakiety:
python -m pip install bcrypt python-dotenv customtkinter pillow mysql-connector-python
```

7) Uruchom aplikację
- Będąc w folderze projektu i aktywowanym venv (jeśli używasz):
```powershell
python mian.py
```
- Aplikacja otworzy okno GUI.

8) Podstawowe testy (co pokazać na prezentacji)
- Zarejestruj nowego użytkownika.
- Zaloguj się.
- Dodaj grę do koszyka, usuń, dodaj ponownie.
- Sfinalizuj zakup (Portfel).
- Sprawdź w Workbench, że pojawiły się wpisy w tabelach: koszyk / licencje / zamowienia / uzytkownicy.

9) Najczęstsze problemy i rozwiązania
- ModuleNotFoundError: bcrypt / dotenv → zainstaluj:
```powershell
python -m pip install bcrypt python-dotenv
```
- MySQL Workbench pokazuje komunikat o małych literach (lower_case_table_names) — to normalne na Windows, używaj nazw tabel małymi literami (kod już do tego dopasowany).
- Błąd połączenia do DB → sprawdź wartości w `.env` i czy serwer MySQL działa.
- Jeśli logowanie zwraca "Invalid salt" lub podobne — możliwe stare hasła w bazie; kod zawiera fallback rehash (przy pierwszym logowaniu plaintext zostanie zrehashowane). Najbezpieczniej: zrób backup DB przed większymi zmianami.

10) Przygotowanie do prezentacji (szybkie)
- Spakuj cały folder NexusGames + nexus_games_backup.sql + .env_example + README.md.
- Na komputerze uczelni:
  - Zainstaluj Python + MySQL (albo uruchom z exe, jeśli przygotujesz).
  - Zaimportuj dump i utwórz `.env`.
  - Zainstaluj wymagania: python -m pip install -r requirements.txt
  - Uruchom: python mian.py

