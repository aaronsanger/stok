"""
Django views for the [STOK] feature.
Drop into your friend's Django app and wire in urls.py (see django_integration/urls.py).
"""

from __future__ import annotations

import json
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from stok_service import StokEngine

engine = StokEngine()


def stok_workbench_view(request: HttpRequest):
    """Render the [STOK] HTML + CSS + JS tester in Django."""
    return render(request, "stok_workbench.html")


@csrf_exempt
def api_stok_view(request: HttpRequest) -> JsonResponse:
    """
    GET  /api/stok/?q=[STOK] 219602 WAFER FLAT
    POST /api/stok/ {"command": "[STOK] WAFER STICK"}
    """
    if request.method == "POST":
        try:
            body = json.loads(request.body.decode("utf-8") or "{}")
        except Exception:
            body = {}
        cmd = str(body.get("command") or body.get("message") or body.get("q") or "[STOK] 219602 WAFER FLAT")
    else:
        cmd = str(request.GET.get("q") or request.GET.get("command") or "[STOK] 219602 WAFER FLAT")
    return JsonResponse(engine.run_stok_command(cmd))
