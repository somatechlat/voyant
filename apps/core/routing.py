"""
WebSocket URL routing for Voyant real-time subscriptions.

Endpoints:
    /ws/ontology — Ontology change notifications
    /ws/jobs     — Job status updates
    /ws/agents   — Agent events
    /ws/scraper  — Scraper events
"""

from django.urls import re_path

from apps.core.consumers import VoyantConsumer

websocket_urlpatterns = [
    re_path(r"ws/ontology/$", VoyantConsumer.as_asgi()),  # type: ignore[reportCallIssue, reportArgumentType]
    re_path(r"ws/jobs/$", VoyantConsumer.as_asgi()),  # type: ignore[reportCallIssue, reportArgumentType]
    re_path(r"ws/agents/$", VoyantConsumer.as_asgi()),  # type: ignore[reportCallIssue, reportArgumentType]
    re_path(r"ws/scraper/$", VoyantConsumer.as_asgi()),  # type: ignore[reportCallIssue, reportArgumentType]
]
