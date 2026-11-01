# Swiss News – Produktions-Runbook

Swiss News ist ein Kurzvideo-Newskanal (TikTok, Instagram Reels, YouTube Shorts) mit den wichtigsten Nachrichten **aus der
Schweiz**, auf Deutsch, zweimal täglich:

| Ausgabe | Datei | online | Inhalt |
| --- | --- | --- | --- |
| **Morgen** | `<YYYY-MM-DD>_01` | **06:30** Zürich | **Recap von gestern und der Nacht**: mehrere Meldungen – oder nur eine, wenn eine klar überragt |
| **Abend** | `<YYYY-MM-DD>_02` | **18:30** Zürich | **Das wichtigste Thema des Tages, genau erklärt** |

Ein geplanter Lauf produziert EINE Ausgabe komplett, ohne Rückfragen. Datum = heute in **Europe/Zurich**.

## 1. Setup (2 min)
```
cd <repo> && bash pipeline/setup.sh
```
Gibt es `stories/<name>.json` UND `videos/<name>.json` schon, ist die Ausgabe fertig: abbrechen.

## 2. Recherche
- Mehrere Websuchen: SRF News, NZZ, Tages-Anzeiger, watson, Blick, 20 Minuten, Keystone-SDA, RTS, RSI, admin.ch (Bundesrat), Polizeimeldungen.
- **Nur Schweiz:** Ereignisse in der Schweiz oder mit klarer Schweizer Betroffenheit (Bundesrat, Schweizer Firmen, Schweizer Sport).
- Jede Zahl und Aussage braucht **zwei seriöse Quellen** (oder eine offizielle Mitteilung). Unbestätigte Eilmeldungen: weglassen.
  Bei steigenden Zahlen „mindestens“. Nie raten. Artikel mit WebFetch öffnen für exakte Zahlen, Namen, Zeiten, Orte.
- Neutral, sachlich, nicht wertend. Keine Opfernamen, nichts Grafisches. Umstrittenes als umstritten kennzeichnen.
- Das Thema der letzten Ausgabe (neueste Datei in `stories/`) nicht einfach wiederholen – nur mit klarer neuer Entwicklung.

**Morgen (Recap):** Zeitraum gestern ca. 06:00 bis jetzt. Wähle **2–4 Meldungen** nach Relevanz (Politik, Wirtschaft,
Gesellschaft, Sport, Wetter/Unglücke). Gab es ein überragendes Ereignis (grosses Unglück, Abstimmungssonntag, Bundesratsentscheid
mit grosser Wirkung), mach nur dieses – dann wie ein Abendvideo, aber kürzer.
**Abend (Erklärstück):** Das eine wichtigste Thema des Tages. Erkläre: Was ist passiert? Warum? Wer ist betroffen? Wie geht es weiter?

## 3. Story-JSON schreiben → `stories/<name>.json`
```json
{
  "date": "2026-11-02", "edition": "morgen",          // morgen | abend
  "say": {"Fanti": "Fanti"},                           // optionale Umschreibungen für die Aussprache
  "scenes": [ … siehe unten … ],
  "title": "…",                                        // ≤ 90 Zeichen, sachlich
  "caption": "…",                                      // 2–4 Sätze auf Deutsch: was, warum wichtig, wie weiter
  "hashtags": ["schweiz", "news", "swissnews", "zürich", "polizei"]   // 5: schweiz, news, swissnews + 2 zum Thema
}
```
Intro („Swiss News am Morgen/Abend“) und Outro werden automatisch angefügt. Jede Szene hat `"vo"` = Sprechertext.

Szenentypen:
- `headline`: `"label"` (Rubrik: Politik · Wirtschaft · Gesellschaft · Sport · Wetter · Unglück · Justiz · Kultur), `"headline"` (max. 6 Wörter,
  Subjekt–Verb–Objekt, Präsens), `"source"` („Quelle: SRF, Kantonspolizei Bern“).
- `statement`: `"text"`: ein Satz oder Liste mit 2–3 Sätzen (je max. 12 Wörter) – erscheinen nacheinander mit den Sätzen des VO
  (also gleich viele Sätze im VO wie Texte). Roter Vollflächen-Frame. **Höchstens einer pro Video.**
- `number`: `"number"` (≤ 5 Zeichen: 2, 150, 4,2, 1,2 Mio.), `"unit"` (Festnahmen, %, Mio. CHF), `"text"` (Erklärung, max. 12 Wörter), `"label"`, `"source"`.
- `place`: `"place"` (Ortsname), `"lat"`, `"lon"` (echte Koordinaten nachschlagen), `"line"` („Kanton Wallis · Aufsichtsbeschwerde“), `"label"`, `"source"`.
- `photo`: `"image"`: `"File:….jpg"` von Wikimedia Commons, `"text"` (1 Satz, max. 3 Zeilen), `"label"`, optional `"position": "50% 30%"` (Bildausschnitt).
  Bildnachweis wird automatisch aus Commons übernommen. Bilder suchen:
  `python3 pipeline/images.py search "Langstrasse Zürich"` → Liste + `build/img-search/sheet.jpg` mit Nummern (mit Read ansehen).
  Wikimedia drosselt Anfragen: höchstens ~4 Suchen pro Lauf; bei „429“ 60 s warten und einmal wiederholen, sonst ohne Foto weiter.
  **Regeln:** nur Treffer mit „OK“ (freie Lizenz). Orte, Gebäude, Landschaften, Fahrzeuge, Symbolbilder – **keine Fotos, auf denen
  Personen das Motiv sind**, keine Agenturfotos, keine Screenshots, nichts Grafisches. Das Bild muss zum Inhalt passen
  (z. B. Bundeshaus bei Bundesratsentscheid, Ort des Geschehens). Kein passendes freies Bild → Karte oder Zahl nehmen.
- `recap` (nur Morgen, als erste Szene): `"title"` („Das Wichtigste seit gestern“), `"items"`: 2–4 × `{"label": "Zürich", "text": "Krawalle nach Demos"}`
  (text max. 6 Wörter), `"vo"`: ein Einleitungssatz + **genau ein Satz pro Meldung**.

Lange Komposita mit `|` als Trennvorschlag schreiben („Zwangs|verwaltung“).

**Aufbau Morgen (Recap, 45–70 s, VO 110–170 Wörter):**
`recap` → pro Meldung 1 Szene (`headline`, `place`, `number` oder `photo`), Label dabei mit Nummer: `"label": "1 · Zürich"`.
Bei nur einer Meldung: `headline` + 2–3 Szenen.
**Aufbau Abend (Erklärstück, 60–80 s, VO 160–200 Wörter):**
`headline` → 4–6 Szenen, z. B. `photo` → `place` → `number` → `statement` → `photo`/`number` („Wie geht es weiter?“).
Mindestens ein `photo`, wenn ein passendes freies Bild existiert.

Schreibregeln: Schweizer Rechtschreibung (immer „ss“, nie „ß“). Zahlen im Bild mit Komma und schmalem Abstand (12 000, 4,2 %).
Keine Ausrufezeichen, keine Emojis, keine wertenden Adjektive, keine Anrede im Bild (im VO „du“ ok). Aussagen zuordnen („…, sagt die Polizei“).
VO: kurze Sätze, Zahlen als Wörter ausschreiben („hundertfünfzig“, „neunzehn“), Jahreszahlen als Ziffern. Kein Frame länger als 16 s.
Aussprache prüfen: `python3 pipeline/tts.py check Name1 Name2` – wenn falsch, Umschreibung in `"say"`.

## 4. Layout prüfen
```
python3 pipeline/make_video.py stories/<name>.json --stills
```
Jede ERROR/WARNING-Zeile beheben. Dann **`build/<name>/sheet.jpg` ansehen** (Read): Text nicht abgeschnitten, keine
Überlappung, Foto passend und gut zugeschnitten, Karte zeigt den richtigen Ort. JSON anpassen und wiederholen.

## 5. Rendern und veröffentlichen
```
python3 pipeline/publish.py stories/<name>.json
```
Rendert das MP4 (~3–5 min), lädt es hoch und plant es über die GitHub Action in Buffer für 06:30 bzw. 18:30 (Zürich) auf
TikTok, Instagram und YouTube.
- Ist es schon später als 15 Minuten vor dem Termin: `--now` anhängen (sofort veröffentlichen).
- `RESULT: OK` → fertig. Abschluss mit 2 Zeilen (Thema + Termin).
- `RESULT: FAILED` / `UNKNOWN` oder ein nicht lösbarer Fehler → einmal wiederholen; klappt es nicht, Push-Mitteilung an den
  Nutzer (PushNotification) auf Deutsch: was fehlschlug und dass die Ausgabe fehlt. Damit den Lauf beenden.

Nie etwas anderes posten, nie Posts löschen, nie Workflows oder Secrets in einem geplanten Lauf ändern.
