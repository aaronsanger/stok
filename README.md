# `[STOK]` Feature Slice (No-Docker Workstation + Django Handoff)

This repository contains the standalone `[STOK]` per-category stock checking slice (`[STOK] {2-digit Wil}{4-digit Depo} {Kategori}` or `[STOK] {Kategori}`, sorted from largest to lowest stock).
It requires **zero Docker** and only 1 Python package (`vertica-python`).

---

## 1. Folder Structure

```text
.
├── stok_service.py                # Pure Python [STOK] engine (vertica-python + offline fallback)
├── run_local_server.py            # No-Docker workstation server (127.0.0.1:8080) & CLI runner
├── start_workstation.bat          # Double-click Windows launcher (No Docker)
├── requirements.txt               # Only vertica-python>=1.3.8
├── .env.example                   # Vertica connection config (copy to .env on workstation/server)
├── django_integration/
│   ├── views.py                   # Ready-to-use Django views (stok_workbench_view, api_stok_view)
│   └── urls.py                    # Ready-to-use Django urlpatterns
├── templates/
│   └── stok_workbench.html        # Pure HTML template (works in Django & standalone server)
├── static/
│   ├── stok_workbench.css         # Stylesheet
│   └── stok_workbench.js          # Vanilla JS frontend (calls /api/stok/)
├── sql/
│   └── StockChecking.sql          # Vertica query parameterized with {{KEY}}, sorted DESC
└── data/
    └── StockChecking_cache.json   # Offline dummy dataset for local testing
```

---

## 2. Running on Your Workstation (Without Docker)

1. Install `vertica-python`:
   ```powershell
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your office Vertica credentials (`DB_ENGINE=vertica`, `VERTICA_HOST`, `VERTICA_USER`, `VERTICA_PASSWORD`). Leave `DB_ENGINE=sqlite_mock` when testing offline.
3. Double-click `start_workstation.bat` (or run `python run_local_server.py`) and open **http://127.0.0.1:8080**, or run from CMD:
   ```powershell
   python run_local_server.py --cmd "[STOK] 219602 WAFER FLAT"
   python run_local_server.py --cmd "[STOK] WAFER STICK"
   ```

---

## 3. How to Sync `[STOK]` Into a Django System

### Option A: Call `StokEngine` Inside an Existing Django WhatsApp Bot Handler
```python
from stok_service import StokEngine

stok_engine = StokEngine()

# When incoming WhatsApp message starts with "[STOK]":
result = stok_engine.run_stok_command(incoming_message)
wa_reply_text = result["reply_message"]  # Sorted largest to lowest, ready to send to WhatsApp
```

### Option B: Mount the Included Django Views & HTML/CSS/JS Tester
In Django `urls.py`:
```python
from django.urls import include, path

urlpatterns = [
    # ... existing urls ...
    path("stok/", include("django_integration.urls")),
]
```
This exposes:
- `GET  /stok/` -> HTML + CSS + JS `[STOK]` tester
- `GET  /stok/api/stok/?q=[STOK] 219602 WAFER FLAT` -> JSON + formatted WhatsApp reply
- `POST /stok/api/stok/` -> `{"command": "[STOK] WAFER STICK"}`
