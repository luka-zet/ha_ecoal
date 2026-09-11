# Integracja eCoal dla Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/example/ha-ecoal?style=flat-square)](https://github.com/example/ha-ecoal/releases)

Niestandardowa integracja (*custom integration*) dla **Home Assistant** umożliwiająca lokalny odczyt i zapis parametrów pracy sterownika kotła **eCoal** (np. eCoal v2.x / v3.x) przez lokalny protokół HTTP (Basic Auth) i endpoint XML.

---

## 1. Opis działania i lista encji

Integracja komunikuje się bezpośrednio ze sterownikiem eCoal w sieci lokalnej, odpytując endpoint `http://{host}/getregister.cgi`. Wszystkie dane pobierane są **jednym zapytaniem HTTP** co **15 sekund**, po czym aktualizują skojarzone encje w ramach jednego urządzenia.

Wszystkie encje (poza wirtualnymi, opisanymi w sekcji [5](#5-encje-wirtualne--automatyzacje-zima-lato-i-krzywa-grzania)) należą do jednego urządzenia **„Sterownik eCoal"** w Home Assistant.

### 1.1 Sensory (`sensor`)

| Identyfikator (`tid`) | Nazwa encji | Klasa (`device_class`) | Jednostka |
|---|---|---|---|
| `tkot_value` | Temperatura kotła | `temperature` | °C |
| `tcwu_value` | Temperatura CWU | `temperature` | °C |
| `tpow_value` | Temperatura powrotu | `temperature` | °C |
| `tsp_value` | Temperatura spalin | `temperature` | °C |
| `t1_value` | Temperatura za zaworem 4D | `temperature` | °C |
| `fuel_level` | Poziom paliwa | — | % |
| `ob1_zaw4d_pos` | Pozycja zaworu 4D | — | % |
| `next_fuel_time` | Następny zasyp | `timestamp` | Data i czas (UTC) |
| `tryb_auto_mode` | Aktualny tryb pracy kotła | — | Tekst opisowy: `Ręczny` / `Automatyczny` / `Alarmowy` (read-only) |

### 1.2 Sensory binarne (`binary_sensor`)

Wszystkie sensory binarne posiadają klasę `running` (`Włączony / Wyłączony`):

| Identyfikator (`tid`) | Nazwa encji | Stan ON (`True`) | Stan OFF (`False`) |
|---|---|---|---|
| `out_pomp1` | Pompa CO | Wartość > 0 | Wartość == 0 (lub `None` przy braku danych) |
| `out_cwu` | Pompa CWU | Wartość > 0 | Wartość == 0 (lub `None` przy braku danych) |
| `out_dm` | Dmuchawa | Wartość > 0 | Wartość == 0 (lub `None` przy braku danych) |

> **Obsługa wartości niepoprawnych w sensorach binarnych:**
> Jeżeli sterownik zwróci błąd lub nie dostarczy danego rejestru, stan encji przyjmuje `None` (stan *Niedostępny* / *Nieznany*), co jest zgodne z idiomami Home Assistant i zapobiega fałszywym odczytom w automatyzacjach.

### 1.3 Encje z możliwością zapisu (`number` / `select`)

Integracja pozwala na modyfikację następujących parametrów — każda z tych encji jednocześnie **odczytuje** aktualną wartość ze sterownika i **zapisuje** zmianę po edycji z poziomu UI:

| Identyfikator (`tid`) | Nazwa encji | Typ encji | Klasa | Zakres / Opcje |
|---|---|---|---|---|
| `ob1_zaw4d_tzad` | Temperatura 4D zadana | `number` | `temperature` | 20–80 °C (krok 1) |
| `kot_tzad` | Temperatura kotła zadana | `number` | `temperature` | 40–80 °C (krok 1) |
| `cwu_tzad` | Temperatura CWU zadana | `number` | `temperature` | 20–60 °C (krok 1) |
| `zima_lato` | Tryb zima/lato | `select` | — | `Zima`, `Lato`, `Auto zima/lato` |
| `tryb_auto` | Tryb pracy kotła (sterowanie) | `select` | — | `Ręczny`, `Automatyczny` (zapis do sterownika) |

> **Uwaga:** encje `kot_tzad` i `cwu_tzad` pojawiają się w Home Assistant jako encje `number` (nie jako sensory) — w tabeli sensorów ich nie ma, ponieważ są pełnoprawnymi encjami modyfikowalnymi.

---

## 2. Wymagania

- Home Assistant Core w wersji **2024.1.0** lub nowszej (Python 3.12+ / 3.13+).
- Sterownik kotła eCoal podłączony do tej samej sieci lokalnej (LAN) co instancja Home Assistant.
- Aktywne uwierzytelnianie HTTP Basic Auth (login i hasło do panelu sterownika).

---

## 3. Instalacja ręczna

1. Pobierz kod źródłowy integracji.
2. Skopiuj katalog `custom_components/ecoal/` do folderu konfiguracyjnego Home Assistanta:
   ```text
   /config/custom_components/ecoal/
   ```
3. Zrestartuj Home Assistant.

---

## 4. Instalacja przez HACS (Custom Repository)

1. Upewnij się, że masz zainstalowany [HACS](https://hacs.xyz/).
2. W HACS przejdź do zakładki **Integrations** → menu w prawym górnym rogu (3 kropki) → **Custom repositories** (*Niestandardowe repozytoria*).
3. Wklej URL swojego repozytorium, wybierz kategorię **Integration** i kliknij **Add** (*Dodaj*).
4. Odszukaj **eCoal**, kliknij **Download** (*Pobierz*).
5. Zrestartuj Home Assistant.

---

## 5. Encje wirtualne – automatyzacje Zima/Lato i Krzywa grzania

Integracja udostępnia **dwie wbudowane automatyzacje**, które działają w tle i nie wymagają tworzenia automatyzacji HA. Obie opierają się na **wirtualnych encjach** (switche + encje number), których stan jest zapisywany lokalnie w HA i odtwarzany po restarcie.

### 5.1 Konfiguracja zewnętrznego czujnika temperatury

Obie automatyzacje korzystają z tego samego, zewnętrznego czujnika temperatury (np. czujnik pogodowy). Wskaż go w opcjach integracji:

1. **Ustawienia** → **Urządzenia oraz usługi** → kafelek **eCoal** → **Konfiguruj**.
2. Z listy **Czujnik temperatury zewnętrznej** wybierz encję termometru (`device_class: temperature`).
3. Zatwierdź — od tego momentu obie poniższe funkcjonalności są aktywne, ale domyślnie **wyłączone** (switche w pozycji OFF).

### 5.2 Automatyczny tryb Zima / Lato

Włączenie automatycznego przełączania trybu na sterowniku w zależności od temperatury zewnętrznej.

Powiązane encje wirtualne (na urządzeniu **Sterownik eCoal**):

| Encja | Typ | Domyślnie | Opis |
|---|---|---|---|
| `switch.<id>_auto_zima_lato` | `switch` | OFF | Włącznik automatycznego trybu Zima/Lato |
| `number.<id>_threshold_lato` | `number` | 15.0 °C | Próg przejścia w **Lato** (temp. zewnętrzna ≥ tej wartości) |
| `number.<id>_threshold_zima` | `number` | 10.0 °C | Próg przejścia w **Zimę** (temp. zewnętrzna ≤ tej wartości) |

**Logika:** gdy switch jest ON, integracja przy każdej zmianie czujnika sprawdza temperaturę:
- `temp ≥ próg_lato` → wysyła do sterownika tryb `1` (Lato),
- `temp ≤ próg_zima` → wysyła tryb `0` (Zima),
- w pozostałych przypadkach (strefa histerezy między progami) — nie robi nic.

Komenda jest wysyłana **wyłącznie wtedy, gdy tryb faktycznie wymaga zmiany** (brak niepotrzebnego ruchu HTTP).

> **Wskazówka:** zaleca się ustawienie `próg_lato` nieco powyżej `próg_zima` (minimum różnicy np. 1 °C) — w ten sposób automatyzacja nie oscyluje między trybami.

### 5.3 Krzywa grzania (sterowanie zaworem 4D)

Włączenie automatycznego sterowania **temperaturą zadaną zaworu 4D** (`ob1_zaw4d_tzad`) w zależności od temperatury zewnętrznej, wg liniowej krzywej grzania.

Powiązane encje wirtualne:

| Encja | Typ | Domyślnie | Opis |
|---|---|---|---|
| `switch.<id>_heating_curve` | `switch` | OFF | Włącznik automatycznej krzywej grzania |
| `number.<id>_heating_curve_temp_min` | `number` | 50 °C | Temp. zaworu 4D dla temperatury zewnętrznej **-10 °C** |
| `number.<id>_heating_curve_temp_max` | `number` | 30 °C | Temp. zaworu 4D dla temperatury zewnętrznej **+10 °C** |

**Logika:** gdy switch jest ON, integracja oblicza temperaturę zadaną zaworu liniowo między dwoma zdefiniowanymi punktami (przy -10 °C → `temp_min`, przy +10 °C → `temp_max`). Wynik jest zaokrąglany do liczby całkowitej i przycinany do zakresu **20–80 °C**. Nowa wartość jest wysyłana do sterownika wyłącznie wtedy, gdy różni się od aktualnie ustawionej.

Krzywa NIE zmienia temperatury kotła — steruje wyłącznie zaworem mieszającym 4D.

---

## 6. Konfiguracja przez Interfejs Użytkownika (UI)

Integracja jest w pełni konfigurowalna z poziomu UI:

1. W Home Assistant przejdź do: **Ustawienia** → **Urządzenia oraz usługi** → **Dodaj integrację**.
2. Wyszukaj **eCoal**.
3. Wypełnij formularz konfiguracyjny:
   - **Host / Adres IP**: np. `192.168.1.50` (bez `http://` i bez ścieżek).
   - **Użytkownik**: nazwa użytkownika HTTP Basic Auth (np. `admin` lub zdefiniowany w sterowniku).
   - **Hasło**: hasło dostępowe do sterownika.
4. Kliknij **Zatwierdź**. Integracja przetestuje połączenie ze sterownikiem i utworzy urządzenie ze wszystkimi encjami.

---

## 7. Cykl odświeżania danych

Odświeżanie danych odbywa się automatycznie co **15 sekund** przy użyciu wzorca `DataUpdateCoordinator`. Wszystkie rejestry są pobierane w **pojedynczym zapytaniu HTTP**, co minimalizuje obciążenie mikrokontrolera w sterowniku kotła.

---

## 8. Serwisy

Integracja udostępnia dwa dodatkowe serwisy wywoływane z poziomu automatyzacji HA lub skryptów:

| Serwis | Pola | Opis |
|---|---|---|
| `ecoal.add_fuel` | `fuel: float` (1–500 kg) | Dodaje określoną ilość paliwa do zasobnika (rejestr `add_fuel`) |
| `ecoal.set_time_to_empty` | `time_to_empty: float` (0–10000) | Ustawia czas do wypalenia paliwa w zasobniku (rejestr `time_to_empty`) |

Definicje i walidacja pól znajdują się w pliku `custom_components/ecoal/services.yaml`.

---

## 9. Diagnostyka i logowanie (Debug)

W przypadku problemów z komunikacją włącz szczegółowe logi w pliku `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.ecoal: debug
```

Pomocny jest też skrypt `diagnose.py` w katalogu głównym repozytorium, który weryfikuje poprawność importów i parsera XML bez konieczności uruchamiania HA.

---

## 10. Bezpieczeństwo w sieci lokalnej

> [!WARNING]
> Sterownik eCoal komunikuje się za pośrednictwem nieszyfrowanego protokołu HTTP z uwierzytelnianiem HTTP Basic Auth. Używaj integracji **wyłącznie w zaufanej, zabezpieczonej sieci lokalnej (LAN / VLAN)**. Nigdy nie wystawiaj portu sterownika bezpośrednio do publicznego Internetu bez tunelu VPN lub reverse proxy.

---

## 11. Znane ograniczenia i założenia

- **Zapis:** Integracja pozwala na zapis następujących parametrów: temperatura zadana 4D, temperatura zadana kotła, temperatura zadana CWU, tryb Zima/Lato oraz tryb pracy kotła (`tryb_auto`). Pozostałe parametry (np. czas do wypalenia, dodane paliwo) są dostępne wyłącznie jako **serwisy** (sekcja [8](#8-serwisy)) lub tylko do odczytu.
- **Tryb pracy kotła:** eksponowany jest jako **dwie osobne encje**, ponieważ sterownik udostępnia dwa różne rejestry:
  - `select.<entry_id>_tryb_auto` — zapisuje wartość do rejestru `tryb_auto` (`0` Ręczny / `1` Automatyczny). Rejestr jest tylko do zapisu.
  - `sensor.<entry_id>_tryb_auto_mode` — odczytuje wartość rejestru `tryb_auto_state` (`0` Ręczny / `1` Automatyczny / `2` Alarmowy). Rejestr jest tylko do odczytu. Stan `Alarmowy` pojawia się automatycznie, gdy sterownik zgłasza błąd.
- **Rejestr `out_zaw4d`:** jest pobierany przez koordynatora, ale aktualnie nie jest eksponowany jako żadna encja — służy do celów diagnostycznych i planowanego rozszerzenia w przyszłych wersjach.
- **Pomijanie nieświeżych rejestrów:** Rejestry bez atrybutu `v` (np. oznaczone jako `status="outdated_data"`) są automatycznie pomijane przez parser i nie nadpisują poprzednich poprawnych wartości błędnymi danymi.
- **Częstotliwość odświeżania:** 15 s — wartość dobrana kompromisowo między aktualnością danych a obciążeniem sterownika. Nie jest konfigurowalna.