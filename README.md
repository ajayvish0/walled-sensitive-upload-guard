# Sensitive Upload Guard

A standalone desktop DLP application for **ChatGPT** (https://chatgpt.com) and **Perplexity** (https://www.perplexity.ai).

It opens your installed Google Chrome under its control and, before anything leaves the browser, inspects
text prompts and file uploads for the marker **`WALLED_SENSITIVE`**. If the marker is found, a **native desktop dialog**
asks you to **Continue** or **Cancel**. It also changes the text colour of every AI response on both sites.

**Demo video:** https://drive.google.com/file/d/1MOSOWlhnq39DuXhY6_SFX97CbE3wIm8l/view?usp=sharing
(ChatGPT and Perplexity: clean prompt, marker prompt with Cancel and Continue, text / PDF / image files, response colour.)

There is **no browser extension, plugin or add-on**: the app is a Python program that drives Chrome with Playwright.
See [ARCHITECTURE.md](ARCHITECTURE.md) for the design.

## Requirements

- Python 3.11 or newer (developed and tested on 3.13)
- Google Chrome installed
- Windows, macOS or Linux (Linux: `sudo apt install python3-tk`)

## Setup

```bash
git clone https://github.com/ajayvish0/walled-sensitive-upload-guard.git
cd walled-sensitive-upload-guard
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1      macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
python scripts/make_fixtures.py     # optional: regenerates tests/fixtures
```

`playwright install` is **not** needed; the installed Chrome is used.

## Run

```bash
python -m walled_guard        # or: walled-guard
```

1. Click **Start protected browser**. Chrome opens with ChatGPT and Perplexity in two tabs.
2. Sign in once on each site. The profile is kept in `~/.walled-guard/chrome-profile`, so you stay signed in.
   Prefer **email login**; Google sign-in is often refused in automation-controlled Chrome.
3. Use the sites normally. Test with the files in `tests/fixtures/`.
4. **Stop** or closing the window closes Chrome. Closing Chrome yourself also returns the app to *Stopped*.

## Usage

| You do | Result |
|---|---|
| Send a prompt without the marker | Sent immediately, no dialog |
| Send a prompt containing `WALLED_SENSITIVE` (Enter or Send button) | Native dialog: says *text prompt*, shows a preview and length, **Continue** / **Cancel** |
| Attach, drag-drop or paste a text / PDF / image file containing the marker | Native dialog **before** the file reaches the site: says *file*, shows its name, type and size |
| **Continue** | The original prompt or file proceeds untouched |
| **Cancel** | Blocked. The prompt stays in the box and the file is not attached; edit or retry normally |
| Read an AI answer | Response text is orange (`#FF7A00`) on both sites, also while streaming |

In the dialog, Esc and the close button mean Cancel, and Enter does nothing, so a stray keypress cannot approve a send.

Test files for a manual run are in `tests/fixtures/` (`sensitive.txt`, `sensitive.pdf`, `sensitive_scanned.pdf`, `sensitive.png`, `sensitive.jpg` and clean counterparts).

## Detection

- Prompts, text files and PDF text layers: exact, case-sensitive `WALLED_SENSITIVE`.
- Scanned PDFs and images: OCR (RapidOCR) with a tolerant match (case, separators, `I/1/l/|/!` look-alikes).
- Supported formats: text-like files (txt, md, csv, json, log, xml, yaml, ...), PDF (text layer and OCR of scanned/image pages), images (png, jpg, webp, gif, bmp, tiff).
- The file type is decided from magic bytes first, then the extension, so a renamed file is still inspected.

## Policy

- Marker found but the dialog cannot be shown: **block** (fail-closed).
- Inspection error, unreadable file or file over 30 MB: **allow and log** (fail-open), so the sites keep working.
- Logs (`~/.walled-guard/guard.log`) contain metadata only, never prompt or file content.

## Tests

```bash
pytest -q
```

Unit tests cover detection, decoding, OCR, PDF, the inspector, dialog and bridge. Browser tests run the real page script in
headless Chrome against a local fake chat page (no network, no login). The dialog is bypassed in tests with
`WALLED_DIALOG_AUTO=continue|cancel`.

## Architecture

```mermaid
flowchart LR
    GUI[gui.py<br/>Tk control window] -->|start / stop| ENG[engine.py<br/>worker thread]
    ENG -->|launch_persistent_context| CH[(Chrome)]
    ENG --> BR[browser.py<br/>install_guard]
    BR -->|add_init_script| JS[inject/*.js<br/>sites, style, guard]
    JS -->|__wg_inspect_prompt<br/>__wg_inspect_file| BR
    BR --> BRG[bridge.py]
    BRG --> INS[inspector.py]
    INS --> DET[detector.py]
    INS --> EXT[extractors<br/>text / pdf / image OCR]
    BRG -->|flagged| DLG[dialog.py<br/>separate Tk process]
    CH --- JS
```

How a prompt is intercepted and enforced:

```mermaid
sequenceDiagram
    participant U as User
    participant G as guard.js (capture phase)
    participant B as bridge.py
    participant D as dialog.py (process)
    participant S as Site code
    U->>G: Enter / click Send
    G->>G: preventDefault + stopImmediatePropagation
    G->>B: __wg_inspect_prompt({site, text})
    alt no marker
        B-->>G: allow
    else marker found
        B->>D: confirm("prompt", preview)
        D-->>B: Continue (exit 0) or Cancel (exit 1)
        B-->>G: allow or block
    end
    alt allow
        G->>S: re-fire the original action once
    else block
        G->>U: text stays in the box
    end
```

Files follow the same path (`__wg_inspect_file`, one dialog per flagged file). Details: [ARCHITECTURE.md](ARCHITECTURE.md).

## Project layout

```
src/walled_guard/
  config.py  logging_setup.py   constants, logging
  detector.py                   marker matching (exact and OCR-tolerant)
  extractors/                   text decoding, image OCR, PDF text + OCR
  inspector.py                  one entry point: inspect_prompt / inspect_file
  dialog.py                     native Tk confirmation dialog (separate process)
  bridge.py                     handlers called from the page, decision flow
  inject/                       sites.js (selectors), style.js (colour), guard.js (interception)
  script_builder.py  browser.py builds the page script, wires Playwright bindings
  engine.py                     launches Chrome in a worker thread
  gui.py  __main__.py           desktop control window and entry point
scripts/make_fixtures.py        generates tests/fixtures
tests/                          unit tests, browser tests, fake chat page
```

## Known limitations

- Editing an already-sent message, voice input, and site-side connectors or cloud-drive pickers are not intercepted.
- Unreadable files and files over 30 MB are not inspected and are allowed (a log entry is written).
- OCR can miss very small or stylised text.
- Site markup changes over time. If a site stops being detected, update the selectors in `src/walled_guard/inject/sites.js`
  (run `__wgDebug()` in the page console to see what is found).
- Google sign-in may be refused in the automation-controlled Chrome; use email login.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Install Google Chrome" | Install Google Chrome; the app launches it through Playwright |
| Verification loop or Google login refused | Use email login |
| `__wgDebug()` shows `false` / `0` | The site changed its markup; update `sites.js` |
| First image or scanned PDF check is slow | The OCR engine loads on first use; later checks are fast |
| Chrome shows "unsupported command-line flag" | Harmless; the app starts Chrome through Playwright. Close the bar with its X |
| ChatGPT shows "Verify you are human" | Cloudflare's check for automated browsers. Tick it once and wait; it can take up to a minute |
| Dialog does not appear | Check `~/.walled-guard/guard.log`; if it cannot be shown the action is blocked |
