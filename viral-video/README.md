# DER DECODER – Investigativer KI-Avatar

| Datei | Inhalt |
|---|---|
| [dossier-2026-11-15.md](dossier-2026-11-15.md) | Weltlage nach Regionen mit Belegstufen, Muster, Hypothesen-Tests, Gematria-Tabelle, Quellen |
| [folge-01-wer-hat-den-schalter.md](folge-01-wer-hat-den-schalter.md) | Shenzhen + Starlink + FAA: Die Welt läuft über Schalter |
| [folge-02-der-preis-an-der-zapfsaeule.md](folge-02-der-preis-an-der-zapfsaeule.md) | Hormus → Ölpreis → Zinsen → Chile: Wer zahlt den Krieg? |
| [folge-03-jalta-2-0.md](folge-03-jalta-2-0.md) | Trump–Xi–Putin ohne Europa |
| [folge-04-freitag-der-13.md](folge-04-freitag-der-13.md) | FAA + Microsoft: Hypothese live geprüft |
| [folge-05-bin-ich-echt.md](folge-05-bin-ich-echt.md) | Deepfakes und die Regeln des Kanals |

**Veröffentlichungsplan:** F01 sofort → F04 (solange der FAA-Ausfall Thema ist) → F02 → F03 am 18.11., einen Tag vor Shenzhen → F05 als Profil-Folge. Danach: Folge zum Ergebnis von Shenzhen am 19./20.11.

**Grundregeln:** Belegstufe 🟢/🟡/🔴 aus dem Dossier übernehmen · 🔴 nur als „unbestätigt“ nennen · Video als KI-generiert kennzeichnen · Quellen in die Beschreibung.

## Video rendern (Folge 01)
```bash
pip install piper-tts pillow numpy   # ffmpeg muss installiert sein
curl -L -o voice.tgz https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-de-thorsten-low.tar.gz && tar xzf voice.tgz
cd render && PIPER_MODEL=../de-thorsten-low.onnx python3 build_folge01_v3.py ../folge-01-wer-hat-den-schalter.mp4 work
```
Stimme: Piper „Thorsten“ (neuronal, Deutsch, offline), Beat + Sound-FX prozedural erzeugt (`build_folge01_v3.py`). Moderator: eigene Figur in `render/host.py` (Lippensynchronisation über die Lautstärke, Blinzeln, gehobene Augenbraue bei Schlüsselwörtern).
