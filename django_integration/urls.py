"""
Django URL configuration for [STOK].
Include in your friend's Django project urls.py:
    path("stok/", include("django_integration.urls")),
"""

from django.urls import path
from . import views

urlpatterns = [
    path("", views.stok_workbench_view, name="stok_workbench"),
    path("api/stok/", views.api_stok_view, name="api_stok"),
]
