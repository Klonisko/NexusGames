import customtkinter
import bcrypt
import mysql.connector
from tkinter import messagebox
from PIL import Image
import os
from dotenv import load_dotenv
import re
import logging
from logging.handlers import RotatingFileHandler
load_dotenv()

EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

baza = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASS", ""),
    database=os.getenv("DB_NAME", "nexus_games")
)
kursor = baza.cursor(buffered=True)

# --- nowa tabela na koszyki (jeśli nie istnieje) ---
kursor.execute("""
CREATE TABLE IF NOT EXISTS Koszyki (
    id_koszyka INT AUTO_INCREMENT PRIMARY KEY,
    id_uzytkownika INT NOT NULL,
    id_gry INT NOT NULL,
    UNIQUE KEY unik (id_uzytkownika, id_gry)
)
""")
baza.commit()

okno = customtkinter.CTk()
okno.geometry("1200x800")
okno.title("Nexus Games")
customtkinter.set_appearance_mode("dark")

zalogowany_id = None
rola_zalogowanego = None
koszyk = []

ramka_logowania = customtkinter.CTkFrame(okno, fg_color="transparent")
ramka_boczna = customtkinter.CTkFrame(okno, width=250, corner_radius=0, fg_color="#171a21")
ramka_zawartosci = customtkinter.CTkScrollableFrame(okno, corner_radius=0, fg_color="#1b2838")

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('app.log', maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def zaladuj_okladke(id_gry, szerokosc, wysokosc):
    # próbuj kilku rozszerzeń (.jpg, .png, .jpeg), fallback do default.png/.jpg
    possible = [f"img/{id_gry}.jpg", f"img/{id_gry}.png", f"img/{id_gry}.jpeg", "img/default.png", "img/default.jpg"]
    # kolory tła używane w UI — jeśli logo jest w bocznym panelu, użyj koloru tego panelu
    default_bg = "#171a21"  # boczne ramki używają #171a21 / zawartość #1b2838
    for sciezka in possible:
        if os.path.exists(sciezka):
            try:
                obraz = Image.open(sciezka).convert("RGBA")
                # jeśli obraz ma przezroczystość, wklej go na tło w kolorze default_bg
                if obraz.mode == "RGBA":
                    bg = Image.new("RGB", obraz.size, default_bg)
                    alpha = obraz.split()[3]  # kanał alfa
                    bg.paste(obraz, mask=alpha)
                    final = bg
                else:
                    final = obraz.convert("RGB")
                # skalowanie zachowujące proporcje: dopasuj obraz do boxu (szerokosc x wysokosc)
                orig_w, orig_h = final.size
                if orig_w == 0 or orig_h == 0:
                    return None
                ratio = min(szerokosc / orig_w, wysokosc / orig_h)
                new_w = max(1, int(orig_w * ratio))
                new_h = max(1, int(orig_h * ratio))
                final = final.resize((new_w, new_h), Image.LANCZOS)
                return customtkinter.CTkImage(light_image=final, dark_image=final, size=(new_w, new_h))
            except Exception:
                logging.exception(f"Błąd ładowania obrazu: {sciezka}")
                return None
    return None

def wyczysc_zawartosc():
    for widget in ramka_zawartosci.winfo_children():
        widget.destroy()

def buduj_menu_boczne():
    for widget in ramka_boczna.winfo_children():
        widget.destroy()
    # logo = customtkinter.CTkLabel(ramka_boczna, text="NEXUS", font=("Arial", 36, "bold"), text_color="#66c0f4")
    # logo.pack(pady=(40, 5))
    # użyj obrazka img/logo zamiast tekstu; zwiększona wysokość, zachowana proporcja
    logo_img = zaladuj_okladke('logo', 160, 120)
    if logo_img:
        logo = customtkinter.CTkLabel(ramka_boczna, text="", image=logo_img)
    else:
        logo = customtkinter.CTkLabel(ramka_boczna, text="NEXUS", font=("Arial", 36, "bold"), text_color="#66c0f4")
    logo.pack(pady=(40, 5))
    podtytul = customtkinter.CTkLabel(ramka_boczna, text="STORE", font=("Arial", 16, "bold"), text_color="#c7d5e0")
    podtytul.pack(pady=(0, 40))
    kursor.execute("SELECT saldo_portfela, nick FROM Uzytkownicy WHERE id_uzytkownika=%s", (zalogowany_id,))
    dane_usera = kursor.fetchone()
    portfel = customtkinter.CTkLabel(ramka_boczna, text=f"Witaj, {dane_usera[1]}\nPortfel: {dane_usera[0]} zł", font=("Arial", 14), text_color="#8f98a0")
    portfel.pack(pady=(0, 30))
    customtkinter.CTkButton(ramka_boczna, text="Sklep", font=("Arial", 16), fg_color="transparent", hover_color="#2a475e", anchor="w", command=pokaz_sklep).pack(fill="x", padx=20, pady=5)
    customtkinter.CTkButton(ramka_boczna, text="Biblioteka", font=("Arial", 16), fg_color="transparent", hover_color="#2a475e", anchor="w", command=pokaz_biblioteke).pack(fill="x", padx=20, pady=5)
    customtkinter.CTkButton(ramka_boczna, text=f"Koszyk ({len(koszyk)})", font=("Arial", 16), fg_color="transparent", hover_color="#2a475e", anchor="w", command=pokaz_koszyk).pack(fill="x", padx=20, pady=5)
    if rola_zalogowanego == 'admin':
        customtkinter.CTkButton(ramka_boczna, text="Panel Admina", font=("Arial", 16), text_color="#a3c83f", fg_color="transparent", hover_color="#2a475e", anchor="w", command=pokaz_admina).pack(fill="x", padx=20, pady=5)
    customtkinter.CTkButton(ramka_boczna, text="Wyloguj", font=("Arial", 16), text_color="#ff5959", fg_color="transparent", hover_color="#2a475e", anchor="w", command=wyloguj).pack(side="bottom", fill="x", padx=20, pady=40)

def wyloguj():
    global zalogowany_id, rola_zalogowanego, koszyk
    zalogowany_id = None
    rola_zalogowanego = None
    koszyk.clear()
    ramka_boczna.pack_forget()
    ramka_zawartosci.pack_forget()
    ramka_logowania.pack(expand=True)

def zaloguj():
    global zalogowany_id, rola_zalogowanego
    email = wejscie_email.get().strip()
    haslo = wejscie_haslo.get()
    if not email or not haslo:
        messagebox.showerror("Błąd", "Podaj e-mail i hasło.")
        return

    kursor.execute("SELECT id_uzytkownika, rola, haslo_hash FROM Uzytkownicy WHERE email=%s", (email,))
    row = kursor.fetchone()
    if not row:
        messagebox.showerror("Błąd", "Błędne dane logowania.")
        return

    uid, rola, stored = row
    ok = False

    # normalizuj typ przechowywanego hasła
    if stored is None:
        stored_str = ""
    elif isinstance(stored, bytes):
        stored_str = stored.decode('utf-8', errors='ignore')
    else:
        stored_str = str(stored)

    try:
        # jeśli wygląda jak hash bcrypt ($2a$ / $2b$ / $2y$) - sprawdzamy bcrypt
        if stored_str.startswith("$2"):
            ok = bcrypt.checkpw(haslo.encode('utf-8'), stored_str.encode('utf-8'))
        else:
            # fallback: porównanie plaintext (stare hasła) i rehash do bcrypt
            if haslo == stored_str:
                ok = True
                try:
                    new_hash = bcrypt.hashpw(haslo.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    kursor.execute("UPDATE Uzytkownicy SET haslo_hash=%s WHERE id_uzytkownika=%s", (new_hash, uid))
                    baza.commit()
                except Exception:
                    # ignoruj błąd aktualizacji hasła, ale pozwól na zalogowanie
                    pass
    except Exception:
        ok = False

    if ok:
        zalogowany_id = uid
        rola_zalogowanego = rola
        zaladuj_koszyk_z_bazy(zalogowany_id)
        ramka_logowania.pack_forget()
        ramka_boczna.pack(side="left", fill="y")
        ramka_zawartosci.pack(side="right", fill="both", expand=True)
        buduj_menu_boczne()
        pokaz_sklep()
    else:
        messagebox.showerror("Błąd", "Błędne dane logowania.")

def pokaz_sklep():
    wyczysc_zawartosc()
    naglowek = customtkinter.CTkLabel(ramka_zawartosci, text="WYRÓŻNIONE I POLECANE", font=("Arial", 24, "bold"), text_color="#ffffff")
    naglowek.grid(row=0, column=0, columnspan=3, pady=30, padx=40, sticky="w")
    kursor.execute("SELECT id_gry, tytul, cena FROM gry")
    gry = kursor.fetchall()
    kolumna = 0
    rzad = 1
    for gra in gry:
        id_gry, tytul, cena = gra
        kafelek = customtkinter.CTkFrame(ramka_zawartosci, fg_color="#202d39", corner_radius=10)
        kafelek.grid(row=rzad, column=kolumna, padx=20, pady=20, sticky="nsew")
        grafika = zaladuj_okladke(id_gry, 240, 120)
        if grafika:
            etykieta_okladki = customtkinter.CTkLabel(kafelek, text="", image=grafika)
            etykieta_okladki.pack(pady=(10, 0), padx=10)
        etykieta_tytul = customtkinter.CTkLabel(kafelek, text=tytul, font=("Arial", 16, "bold"), text_color="#c7d5e0")
        etykieta_tytul.pack(pady=(15, 5), padx=10)
        etykieta_cena = customtkinter.CTkLabel(kafelek, text=f"{cena} zł", font=("Arial", 14), text_color="#a3c83f")
        etykieta_cena.pack(pady=(0, 15))
        przycisk_szczegoly = customtkinter.CTkButton(kafelek, text="Zobacz stronę gry", fg_color="#2a475e", hover_color="#66c0f4", command=lambda g=id_gry: pokaz_gre(g))
        przycisk_szczegoly.pack(pady=(0, 15), padx=20)
        kolumna += 1
        if kolumna > 2:
            kolumna = 0
            rzad += 1

def pokaz_gre(id_gry):
    wyczysc_zawartosc()
    kursor.execute("SELECT tytul, opis, cena, wymagania FROM gry WHERE id_gry=%s", (id_gry,))
    gra = kursor.fetchone()
    if not gra: return
    grafika = zaladuj_okladke(id_gry, 600, 300)
    if grafika:
        etykieta_okladki = customtkinter.CTkLabel(ramka_zawartosci, text="", image=grafika)
        etykieta_okladki.pack(pady=30)
    tytul_gry = customtkinter.CTkLabel(ramka_zawartosci, text=gra[0], font=("Arial", 36, "bold"), text_color="#ffffff")
    tytul_gry.pack(pady=10)
    opis_gry = customtkinter.CTkLabel(ramka_zawartosci, text=gra[1], font=("Arial", 16), text_color="#acb2b8", wraplength=800, justify="center")
    opis_gry.pack(pady=20, padx=50)
    cena_gry = customtkinter.CTkLabel(ramka_zawartosci, text=f"{gra[2]} zł", font=("Arial", 24, "bold"), text_color="#a3c83f")
    cena_gry.pack(pady=10)
    customtkinter.CTkButton(ramka_zawartosci, text="Dodaj do koszyka", width=300, height=50, font=("Arial", 18, "bold"), fg_color="#5c7e10", hover_color="#76a114", command=lambda: dodaj_do_koszyka(id_gry, gra[0], gra[2])).pack(pady=20)

def dodaj_do_koszyka(id_gry, tytul, cena):
    if not zalogowany_id:
        messagebox.showerror("Błąd", "Musisz być zalogowany, żeby dodać do koszyka.")
        return
    kursor.execute("SELECT id_licencji FROM Licencje WHERE id_uzytkownika=%s AND id_gry=%s", (zalogowany_id, id_gry))
    if kursor.fetchone():
        messagebox.showinfo("Biblioteka", "Posiadasz już ten produkt na swoim koncie.")
        return
    # dodaj do tabeli Koszyki (unikat zapewnia, że nie dublujemy)
    try:
        kursor.execute("INSERT INTO Koszyki (id_uzytkownika, id_gry) VALUES (%s, %s)", (zalogowany_id, id_gry))
        baza.commit()
    except Exception:
        pass
    # lokalna lista (UI)
    for element in koszyk:
        if element['id'] == id_gry:
            return
    koszyk.append({'id': id_gry, 'tytul': tytul, 'cena': cena})
    buduj_menu_boczne()
    messagebox.showinfo("Koszyk", "Gra została poprawnie dodana do twojego koszyka.")

def pokaz_koszyk():
    wyczysc_zawartosc()
    naglowek = customtkinter.CTkLabel(ramka_zawartosci, text="TWÓJ KOSZYK", font=("Arial", 28, "bold"), text_color="#ffffff")
    naglowek.pack(pady=40)
    if not koszyk:
        customtkinter.CTkLabel(ramka_zawartosci, text="Koszyk świezi pustkami.", font=("Arial", 18), text_color="#8f98a0").pack(pady=50)
        return
    suma = 0.0
    for element in koszyk:
        suma += float(element['cena'])
        kafelek = customtkinter.CTkFrame(ramka_zawartosci, fg_color="#202d39")
        kafelek.pack(fill="x", padx=100, pady=5)
        customtkinter.CTkLabel(kafelek, text=element['tytul'], font=("Arial", 18, "bold"), text_color="#c7d5e0").pack(side="left", padx=30, pady=25)
        customtkinter.CTkLabel(kafelek, text=f"{element['cena']} zł", font=("Arial", 18), text_color="#a3c83f").pack(side="right", padx=30)
        # przycisk usuń
        customtkinter.CTkButton(kafelek, text="Usuń", fg_color="#7b2a2a", hover_color="#a33a3a", width=100, command=lambda g=element['id']: usun_z_koszyka(g)).pack(side="right", padx=(0,10))
    customtkinter.CTkLabel(ramka_zawartosci, text=f"Razem do zapłaty: {suma:.2f} zł", font=("Arial", 24, "bold"), text_color="#ffffff").pack(pady=40)
    customtkinter.CTkButton(ramka_zawartosci, text="Sfinalizuj transakcję z portfela", width=300, height=50, font=("Arial", 18), command=lambda: zaplac(suma)).pack()

def zaplac(suma):
    kursor.execute("SELECT saldo_portfela FROM Uzytkownicy WHERE id_uzytkownika=%s", (zalogowany_id,))
    saldo = kursor.fetchone()[0]
    if saldo < suma:
        messagebox.showerror("Brak środków", "Twoje saldo jest niewystarczające na te zakupy.")
        return
    try:
        nowe_saldo = float(saldo) - suma
        kursor.execute("UPDATE uzytkownicy SET saldo_portfela=%s WHERE id_uzytkownika=%s", (nowe_saldo, zalogowany_id))
        kursor.execute("INSERT INTO Zamowienia (id_uzytkownika, kwota_laczna, metoda_platnosci, status) VALUES (%s, %s, 'Portfel', 'Zakończone')", (zalogowany_id, suma))
        for element in koszyk:
            kursor.execute("INSERT INTO Licencje (id_uzytkownika, id_gry) VALUES (%s, %s)", (zalogowany_id, element['id']))
        # usuń wpisy z tabeli Koszyki dla użytkownika
        kursor.execute("DELETE FROM Koszyki WHERE id_uzytkownika=%s", (zalogowany_id,))
        baza.commit()
        koszyk.clear()
        buduj_menu_boczne()
        pokaz_biblioteke()
        messagebox.showinfo("Sukces", "Transakcja udana. Gry są gotowe do pobrania.")
    except Exception as e:
        logging.exception("Krytyczny błąd systemu płatności:")
        messagebox.showerror("Błąd", "Wystąpił błąd podczas realizacji płatności. Sprawdź app.log.")

def pokaz_biblioteke():
    wyczysc_zawartosc()
    naglowek = customtkinter.CTkLabel(ramka_zawartosci, text="TWOJA KOLEKCJA", font=("Arial", 28, "bold"), text_color="#ffffff")
    naglowek.pack(pady=40)
    kursor.execute("SELECT g.tytul FROM Licencje l JOIN gry g ON l.id_gry = g.id_gry WHERE l.id_uzytkownika=%s", (zalogowany_id,))
    licencje = kursor.fetchall()
    for lic in licencje:
        kafelek = customtkinter.CTkFrame(ramka_zawartosci, fg_color="#202d39")
        kafelek.pack(fill="x", padx=100, pady=5)
        customtkinter.CTkLabel(kafelek, text=lic[0], font=("Arial", 18, "bold"), text_color="#c7d5e0").pack(side="left", padx=30, pady=25)
        customtkinter.CTkButton(kafelek, text="Zainstaluj", fg_color="#2a475e", hover_color="#66c0f4").pack(side="right", padx=30)

def pokaz_admina():
    wyczysc_zawartosc()
    customtkinter.CTkLabel(ramka_zawartosci, text="DODAJ NOWY PRODUKT", font=("Arial", 28, "bold"), text_color="#ffffff").pack(pady=40)
    global wpis_tytul, wpis_opis, wpis_cena
    wpis_tytul = customtkinter.CTkEntry(ramka_zawartosci, placeholder_text="Pełny tytuł", width=500, height=45)
    wpis_tytul.pack(pady=10)
    wpis_opis = customtkinter.CTkEntry(ramka_zawartosci, placeholder_text="Zarys fabuły", width=500, height=45)
    wpis_opis.pack(pady=10)
    wpis_cena = customtkinter.CTkEntry(ramka_zawartosci, placeholder_text="Cena", width=500, height=45)
    wpis_cena.pack(pady=10)
    customtkinter.CTkButton(ramka_zawartosci, text="Opublikuj w sklepie", width=300, height=50, command=zapisz_gre).pack(pady=40)

def zapisz_gre():
    try:
        kursor.execute("INSERT INTO gry (tytul, opis, cena) VALUES (%s, %s, %s)", (wpis_tytul.get(), wpis_opis.get(), float(wpis_cena.get())))
        baza.commit()
        pokaz_sklep()
    except ValueError:
        messagebox.showerror("Błąd", "Sprawdź poprawność wpisanej ceny.")

def usun_gre(id_gry):
    try:
        kursor.execute("DELETE FROM gry WHERE id_gry=%s", (id_gry,))
        baza.commit()
        pokaz_sklep()
    except Exception as e:
        messagebox.showerror("Błąd", "Nie można usunąć gry.")
        logging.exception("usun_gre error:")

def edytuj_gre(id_gry):
    # prosty dialog edycji — zaimplementuj UI analogicznie do dodawania
    pass

ramka_logowania.pack(expand=True)
customtkinter.CTkLabel(ramka_logowania, text="LOGOWANIE DO NEXUS", font=("Arial", 28, "bold"), text_color="#ffffff").pack(pady=30, padx=50)
wejscie_email = customtkinter.CTkEntry(ramka_logowania, placeholder_text="Adres e-mail", width=350, height=45)
wejscie_email.pack(pady=10)
wejscie_haslo = customtkinter.CTkEntry(ramka_logowania, placeholder_text="Hasło", show="*", width=350, height=45)
wejscie_haslo.pack(pady=10)
customtkinter.CTkButton(ramka_logowania, text="Zaloguj", width=350, height=45, fg_color="#2a475e", hover_color="#66c0f4", command=zaloguj).pack(pady=10)

# przycisk otwierający okno rejestracji
customtkinter.CTkButton(ramka_logowania, text="Zarejestruj", width=350, height=45, fg_color="#2a475e", hover_color="#66c0f4", command=lambda: otworz_rejestracje()).pack(pady=5)

def otworz_rejestracje():
    top = customtkinter.CTkToplevel(okno)
    top.title("Rejestracja")
    top.geometry("420x380")
    top.grab_set()

    customtkinter.CTkLabel(top, text="UTWÓRZ KONTO", font=("Arial", 20, "bold")).pack(pady=(20,10))
    entry_nick = customtkinter.CTkEntry(top, placeholder_text="Nick", width=360, height=40)
    entry_nick.pack(pady=6)
    entry_email_reg = customtkinter.CTkEntry(top, placeholder_text="Adres e-mail", width=360, height=40)
    entry_email_reg.pack(pady=6)
    entry_haslo_reg = customtkinter.CTkEntry(top, placeholder_text="Hasło", show="*", width=360, height=40)
    entry_haslo_reg.pack(pady=6)
    entry_haslo2_reg = customtkinter.CTkEntry(top, placeholder_text="Powtórz hasło", show="*", width=360, height=40)
    entry_haslo2_reg.pack(pady=6)

    def zarejestruj():
        nick = entry_nick.get().strip()
        email = entry_email_reg.get().strip()
        h1 = entry_haslo_reg.get()
        h2 = entry_haslo2_reg.get()

        if not nick or not email or not h1:
            messagebox.showerror("Błąd", "Wypełnij wszystkie pola.")
            return
        if not EMAIL_RE.match(email):
            messagebox.showerror("Błąd", "Niepoprawny format e-mail.")
            return
        if h1 != h2:
            messagebox.showerror("Błąd", "Hasła nie są zgodne.")
            return

        # sprawdź czy email już istnieje
        kursor.execute("SELECT 1 FROM Uzytkownicy WHERE email=%s", (email,))
        if kursor.fetchone():
            messagebox.showerror("Błąd", "Konto z tym adresem e-mail już istnieje.")
            return

        try:
            # zgodnie z istniejącym schematem przechowujemy hasło w kolumnie haslo_hash (bez hashowania, tak jak w reszcie aplikacji)
            hashed = bcrypt.hashpw(h1.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            kursor.execute(
                "INSERT INTO Uzytkownicy (nick, email, haslo_hash, saldo_portfela, rola) VALUES (%s, %s, %s, %s, %s)",
                (nick, email, hashed, 0, 'user')
            )
            baza.commit()
            messagebox.showinfo("Sukces", "Konto utworzone. Możesz się zalogować.")
            top.destroy()
        except Exception as e:
            messagebox.showerror("Błąd", "Nie udało się utworzyć konta.")
            logging.exception("Rejestracja error:")

    customtkinter.CTkButton(top, text="Utwórz konto", width=300, height=40, fg_color="#5c7e10", hover_color="#76a114", command=zarejestruj).pack(pady=(12,6))
    customtkinter.CTkButton(top, text="Anuluj", width=300, height=36, fg_color="#2a475e", hover_color="#66c0f4", command=top.destroy).pack()

def zaladuj_koszyk_z_bazy(uzytkownik_id):
    koszyk.clear()
    if not uzytkownik_id:
        return
    try:
        kursor.execute("""
            SELECT k.id_gry, g.tytul, g.cena
            FROM Koszyki k
            JOIN gry g ON k.id_gry = g.id_gry
            WHERE k.id_uzytkownika=%s
        """, (uzytkownik_id,))
        for id_gry, tytul, cena in kursor.fetchall():
            koszyk.append({'id': id_gry, 'tytul': tytul, 'cena': cena})
    except Exception as e:
        logging.exception("Błąd wczytywania koszyka z bazy:")

def usun_z_koszyka(id_gry):
    if not zalogowany_id:
        return
    try:
        kursor.execute("DELETE FROM Koszyki WHERE id_uzytkownika=%s AND id_gry=%s", (zalogowany_id, id_gry))
        baza.commit()
    except Exception as e:
        logging.exception("Błąd usuwania z koszyka:")
    # usuń lokalnie i odśwież UI
    for i, el in enumerate(koszyk):
        if el['id'] == id_gry:
            koszyk.pop(i)
            break
    buduj_menu_boczne()
    pokaz_koszyk()

if __name__ == "__main__":
    # uruchomienie GUI — konieczne, żeby okno się pokazało
    okno.mainloop()