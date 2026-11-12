# devolo Home Control Zentrale (MT2600): lokale API ohne Cloud

Die devolo Home Control Zentrale (Modell MT2600) lässt sich vollständig im eigenen Netz ansprechen, ohne die Hersteller-Cloud. Dieses Repository dokumentiert, wie das geht, was dabei funktioniert und wo die Grenzen liegen. Grundlage ist ein eigenes Gerät mit Firmware 8.91.1 (2021-06-29), Stand der Untersuchung: 12.11.2026.

## Die wichtigsten Ergebnisse

| Thema | Ergebnis |
| :--- | :--- |
| Lokale Steuerung | Anmeldung, Sitzung, JSON-RPC und Live-Ereignisse (WebSocket) funktionieren ohne Cloudkontakt. Gekoppelte Z-Wave-Geräte lassen sich lesen und schalten. |
| Zugangsdaten | Die Android-App sendet die lokalen Zugangsdaten per HTTP Basic Auth im Klartext an jedes Gerät, das im LAN ihre mDNS-Suche beantwortet. |
| Diagnoseschnittstelle | Port 22879 (DHCI) beantwortet Lesezugriffe auf Status und Firmwareversion ohne Anmeldung. |
| Schreibzugriff | Ein reversibler Schreibtest auf die Eigenschaft `description` war erfolgreich. |
| Neue Z-Wave-Geräte anlernen | Mit dem lokalen Benutzerzugang wurde kein Weg gefunden. |
| Backup und Restore | Diagnosearchive lassen sich erzeugen, aber nicht herunterladen. Ein Restore-Weg wurde nicht gefunden. |
| Betriebssystemzugang | Nicht nachgewiesen (kein SSH, kein Telnet, kein Root). |

Offene TCP-Ports: 80 (Portal, JSON-RPC, WebSocket), 8081 (nimmt Verbindungen an, setzt sie sofort zurück) und 22879 (DHCI).

## Inhalt

| Datei | Inhalt |
| :--- | :--- |
| [LOCAL-API-2026-11-12.md](LOCAL-API-2026-11-12.md) | Hauptdokument: Endpunkte, Login-Ablauf mit Codebeispiel, RPC-Methoden, Verwaltungsfunktionen, Grenzen |
| [dhci-client/READ-PROTOCOL-EVIDENCE.md](dhci-client/READ-PROTOCOL-EVIDENCE.md) | DHCI-Leseprotokoll, statisch aus der App devolo NetScanner ermittelt |
| [dhci-static/FINDINGS.md](dhci-static/FINDINGS.md) | Gegenprüfung des DHCI-Protokolls an der Firmware des dLAN 550 WiFi |
| [archive-research/](archive-research/) | Recherche zu Archivdownload und Restore (App-Analyse, ProSyst-Dokumentation) |
| `*-2026-11-1x.json`, [tcp-full-scan-2026-11-11.txt](tcp-full-scan-2026-11-11.txt) | Bereinigte Prüfprotokolle als Belege |
| [local_api_tools.py](local_api_tools.py) | Login-Helfer und lesender Konfigurationsexport |
| [description_roundtrip.py](description_roundtrip.py) | Schreibtest mit Journal und Wiederherstellung |
| [archive_download_probe.py](archive_download_probe.py) | Prüfung der Downloadwege für Diagnosearchive |

## Skripte verwenden

Die Skripte benötigen Python 3 und das Paket `requests`. Adresse und Zugangsdaten kommen aus Umgebungsvariablen:

```powershell
$env:MT2600_HOST    = '10.0.0.107'
$env:MT2600_USER    = '<mydevolo-User-UUID>'
$env:MT2600_PASSKEY = '<Local Passkey, 32 Hex-Zeichen>'
New-Item -ItemType Directory export-test
python local_api_tools.py export-test
```

Der Export enthält private Daten des eigenen Geräts. Ordner mit dem Präfix `export-` sind deshalb in `.gitignore` ausgeschlossen.

## Was nicht im Repository liegt

- **Eigene Kennungen:** Zugangsdaten, Kontoinhaber, E-Mail-Adresse, Seriennummer, MAC- und IPv6-Adressen sowie die Z-Wave Home-ID sind durch Platzhalter ersetzt.
- **Rohexport des Geräts:** Der vollständige Konfigurationsexport bleibt lokal.
- **Herstellerdateien:** Apps, Firmware, dekompilierter Code und gespeicherte Dokumentationsseiten sind nicht enthalten. Bezugsquellen und Prüfsummen stehen in den jeweiligen Befunddateien.

## Hinweis

Alle Prüfungen fanden am eigenen Gerät im eigenen Netz statt. Es besteht keine Verbindung zur devolo AG. Angaben gelten für die genannte Firmware; andere Versionen können sich anders verhalten.
