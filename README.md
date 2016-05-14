# Einführung

Das Python-Skript "Save.TV Movie Mailer" sucht in den Save.TV Aufnahmen zum einen:
* nach Filmen mit einem IMDB-Rating >= 7.0 und 
* nach Suchbegriffen (z. B. hinterlegte Film-Titel, Darsteller oder Themen wie zukünftige Reiseziele). 

Die Treffer werden anschaulich per Email versand, sodass der Empfänger über interessante neue Filme auf Save.TV informiert bleibt.

Die Suchbegriffe werden als reguläre Ausdrücke in einer Datei hinterlegt (ein Suchbegriff pro Zeile).

Das Skript ist mehrbenutzerfähig, sodass benutzerindividuelle Suchbegriffe angegeben werden können und ensprechend die Ergebnisse an unterschiedliche Email-Adressen versand werden.

Das Skript basiert auf Funktionen des von Save.TV veröffentlichten Kodi-Plugins (siehe http://cdn.save.tv/downloads/kodi/plugin.video.savetv-0.7.zip).

# Vorbereitung und Konfiguration

1. Kopieren der Dateien des Skripts in ein eigenes Verzeichnis, z. B.:
   ```
    mkdir /home/pi/save-tv-mailer; cp /folder/of/unzipped/files /home/pi/save-tv-mailer/
   ```
2. Erstellen eines Verzeichnisses für die benutzerindividuellen SQLite-Datenbanken, z. B: 
   ```
    mkdir /home/pi/save-tv-mailer/raspispass
   ```
3. Hinterlegung der Save-TV-Zugangsdaten in der Datei "savetv.py":
   ```
    username = ''
    password = ''
   ```
4. Hinterlegung der Mail-Zugangsdaten in der Datei "savetv-movie-mailer.py":
   ```
        [...]

        # Mail configuration
        from_address = ['RaspiVDR', 'savetv@domain.com']
        recipient = ['Raspispass', 'raspispass@domain.com']
        subject = "[RaspVDR] Neue Film-Treffer in Save.TV"
        smtpserver = 'smtp.domain.com'
        smtp_username = "savetv@domain.com"
        smtp_password = "mail-password"
   ```
5. Erstellung der Movie-Liste mit regulären Ausdrücken. Eine kurze Beschreibung mit Beispielen wie folgt:
   ```
    WICHTIG: Keine Leerzeichen, da dann ALLE Einträge erfasst werden.
    REGEXP-BEFEHL: ^  = Zeilenanfang
    REGEXP-BEFEHL: .  = Ein beliebiges Zeichen
    REGEXP-BEFEHL: \s = Leerzeichen/Tab und Satz-Zeichen
    REGEXP-BEFEHL: .* = Ein beliebiges Zeichen - Aber beliebig oft -> *
    REGEXP-BEFEHL: $  = Ende des Titels
    REGEXP-BEFEHL: \. = Tatsächlicher Punkt
    REGEXP-BEFEHL: (?=Terminator)(?=^((?!S.C.C.).)*$) => Ein Schlüsselbegriff (Terminator) soll enthalten sein, aber nicht in Kominbation mit einem anderen Schlüsselbegriff (S.C.C.)
    ====== Darsteller
    Norton
    Deniro
    Pacino
    Damon
    ====== Filme
    Sherlock.*Holmes
    Blade.*Runner
    James.*Bond
    Cumberbatch
    Di.*Caprio
   ```
# Aufruf
```
    Usage: python savetv-movie-mailer.py --recipient-mail-addr=<test@example.com> --recipient-name=<username> --savetv-movie-list=<movie-liste.txt>
```
## Parameter
```
--recipient-mail-addr=<recipient@domain.com>
  The mail address of the recipient is specified.

--recipient-name=<username>
  This parameter specifies the local directory where the search result databases are stored for each user

--savetv-movie-list=<filename-of-movie-list.txt>
  This parameter specifies the filename that contains the regular expressions (by each line) for the movie matches
```
## Beispielhafte Ausgaben beim Aufruf des Skripts von der Konsole
```
    [-] Connect to SaveTV server:
        [*] Access Token:   [...]
        [*] Session Expire: 1463230528.45
        [*] Refresh Token:  [...]
    [*] Authentication succeeded
    [*] Using pysqlite version 2.6.0
    [*] Using SQLite version 3.7.13
    [*] Using pysqlite version 2.6.0
    [*] Using SQLite version 3.7.13
    [*] Connected to SQLite database raspispass/savetvRecordings.db
    [*] Created new SQLite database raspispass/savetvRecordings.db
    [*] Using pysqlite version 2.6.0
    [*] Using SQLite version 3.7.13
    [*] Connected to SQLite database raspispass/epgEventsMatched.db
    [*] Created new SQLite database raspispass/epgEventsMatched.db
    [-] Fetch SaveTV recordings:
    ------------------------------------------------------------------------
    [-] TotalCound: 1778
    [-] Limit:      5000
    [-] Offset:     0
    ------------------------------------------------------------------------
        [*] Das Wunder von Merching (IMDB: 5.9)
        [*] Lena Lorenz - Spurlos verschwunden (IMDB: )
        [*] John Woo's Blackjack (IMDB: )
        [*] Der Teufel trägt Prada (IMDB: )
        [*] Coyote Ugly (IMDB: 5.6)
        [*] Werner - Volles Rooäää!!! (IMDB: 5.1)
        [...]
        [*] Aristocats (IMDB: 7.1)
        [*] Zweimal lebenslänglich (IMDB: 6.6)
        [*] Ticket nach Telluride - Drei Freundinnen in Amerika (IMDB: )
        [*] Xxy (IMDB: 7.2)
    [*] Searching for regular expression in recordings database: Sherlock.*Holmes
    [*] Searching for regular expression in recordings database: Blade.*Runner
    [*] Searching for regular expression in recordings database: James.*Bond
    [*] Searching for regular expression in recordings database: Cumberbatch
    [*] Searching for regular expression in recordings database: Di.*Caprio
    [*] IMDB Match(es) found! (4)
    [*] Added movie for IMDB rating: Marianne
    [*] IMDB Match(es) found! (4)
    [*] Added movie for IMDB rating: Marianne
    [*] Added movie for IMDB rating: Mammon - Per Anhalter durch das Geldsystem
    [*] Added movie for IMDB rating: Xxy
    [*] Added movie for IMDB rating: Aristocats
    [*] No backup file yet exists ... creating one
    [---------------
    [-] Title:       Aristocats
    [-] Description: Paris im Jahr 1910: Die etwas exzentrische und schwerreiche Madame Adelaide Bonfamille bestimmt ihre geliebten Katzen als Erben und sorgt damit für eine Enttäuschung bei ihrem treuen Butler Edgar, der sich selbst gute Chance auf den Nachlass seiner Herrin ausgerechnet hatte. Edgar ist so wütend, dass er die reichen Erben kurzerhand weit außerhalb der Stadt aussetzt, um sie ein für allemal loszuwerden. Er ahnt ja nicht, dass die Katzen sich der Herausforderung stellen und sich schon bald auf den beschwerlichen Weg zurück nach Paris machen ...Disney-Klassiker aus dem Jahr 1970!
    [---------------
    [-] Title:       Insomnia - Schlaflos
    [-] Description: In einem der besten Psychothriller der letzten Jahre glänzt Al Pacino als schlafloser Cop, der in dem Mordfall an einer 17-jährigen ermittelt. Diese Tat hat die Bewohner einer Kleinstadt nördlich des Polarkreises aufgeschreckt. Doch schon bald haben der erfahrene Will Donner und sein Kollege Hap eine heiße Spur in dem Ort, an dem die Sonne niemals untergeht. Doch der verdächtige Autor Walter Finch – brillant: Robin Williams – kann entkommen. Plötzlich fallen wie aus dem Nichts Schüsse, und Hap wird tödlich getroffen. Damit hat ein psychologisch ausgefeiltes Katz-und-Maus-Spiel begonnen, in dessen Verlauf der schlaflose Donner an seinem Verstand zweifelt. Pacino und Williams liefern sich ein Psycho-Duell, das den Zuschauern den Atem raubt.
    [...]
    Successfully sent email
    [*] Disconnected from DB
    [*] Disconnected from DB
```

# Beispielhafte Mail mit den Suchergebnissen:

![Beispielhafte Mail mit den Suchergebnissen](https://github.com/raspispass/savetv-movie-mailer/blob/master/savetv-movie-mailer-example-mail.png "Beispielhafte Mail mit den Suchergebnissen")

# Integration mit Dropbox

Damit die Movie-Liste komfortabel vom Desktop-Rechner aus bearbeitet werden kann, ist eine Synchronisierung der Datei über den Dienst Dropbox möglich. Hierfür kann folgendes Bash-Skript auf dem Server verwendet werden, welches in regelmäßigen Abständen die Movie-Liste aus der Dropbox herunterlädt. Hinterlegt werden muss der individuelle Download-Link:
```
    #!/bin/bash
    wget https://www.dropbox.com/sh/[...]/[...]?dl=1 -O dropbox_tmp.zip;unzip -o dropbox_tmp.zip;rm dropbox_tmp.zip; dos2unix savetv-movie-liste-from-dropbox.txt
```

