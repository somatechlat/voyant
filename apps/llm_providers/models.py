"""
LLM Provider Management — Django ORM Models.

Allows admins to configure any OpenAI-compatible LLM provider
through the admin UI. Pre-seeded with common providers.
"""

from __future__ import annotations

import uuid

from django.db import models


class LLMProvider(models.Model):
    """An LLM provider configuration (Groq, OpenAI, Anthropic, MiMo, etc.)."""

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text="Provider name (e.g. 'Groq', 'MiMo')")
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-safe identifier (e.g. 'groq', 'mimo')")
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True)

    # Connection
    api_base_url = models.CharField(max_length=500, help_text="OpenAI-compatible API base URL")
    api_key = models.CharField(max_length=500, blank=True, help_text="API key (encrypted in Vault)")
    api_key_vault_path = models.CharField(max_length=255, blank=True, help_text="Vault path for API key")

    # Capabilities
    supports_chat = models.BooleanField(default=True)
    supports_streaming = models.BooleanField(default=True)
    supports_json_mode = models.BooleanField(default=False)
    supports_function_calling = models.BooleanField(default=False)
    supports_vision = models.BooleanField(default=False)
    supports_embeddings = models.BooleanField(default=False)

    # Config
    default_headers = models.JSONField(default=dict, blank=True, help_text='Extra headers: {"X-Custom": "value"}')
    rate_limit_rpm = models.IntegerField(default=0, help_text="Requests per minute (0 = unlimited)")
    timeout_seconds = models.IntegerField(default=30)

    is_system = models.BooleanField(default=False, help_text="System providers cannot be deleted")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "llm_provider"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"Provider({self.name} [{self.status}])"


class LLMModel(models.Model):
    """A specific model available from an LLM provider."""

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(LLMProvider, on_delete=models.CASCADE, related_name="models")
    name = models.CharField(max_length=200, help_text="Model ID (e.g. 'openai/gpt-oss-120b')")
    display_name = models.CharField(max_length=200, blank=True, help_text="Human-readable name")
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True)

    # Capabilities
    context_window = models.IntegerField(default=4096, help_text="Max context tokens")
    max_output_tokens = models.IntegerField(default=4096, help_text="Max completion tokens")
    supports_vision = models.BooleanField(default=False)
    supports_function_calling = models.BooleanField(default=False)
    supports_json_mode = models.BooleanField(default=False)
    supports_reasoning = models.BooleanField(default=False, help_text="Supports reasoning/chain-of-thought")

    # Pricing (per 1M tokens)
    input_price = models.FloatField(default=0.0, help_text="Price per 1M input tokens ($)")
    output_price = models.FloatField(default=0.0, help_text="Price per 1M output tokens ($)")

    # Usage
    is_default = models.BooleanField(default=False, help_text="Default model for this provider")
    use_count = models.PositiveIntegerField(default=0)
    avg_latency_ms = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "llm_model"
        ordering = ["provider", "name"]
        unique_together = [("provider", "name")]

    def __str__(self) -> str:
        return f"{self.provider.name}/{self.name}"


class ActiveLLMConfig(models.Model):
    """Singleton model storing which provider+model is currently active for each purpose."""

    PURPOSE_INTENT = "intent"
    PURPOSE_ANALYSIS = "analysis"
    PURPOSE_SCRAPER = "scraper"
    PURPOSE_GENERAL = "general"
    PURPOSE_CHOICES = [
        (PURPOSE_INTENT, "Intent Engine"),
        (PURPOSE_ANALYSIS, "Data Analysis"),
        (PURPOSE_SCRAPER, "Scraper AI"),
        (PURPOSE_GENERAL, "General"),
    ]

    purpose = models.CharField(max_length=50, choices=PURPOSE_CHOICES, primary_key=True)
    provider = models.ForeignKey(LLMProvider, on_delete=models.SET_NULL, null=True)
    model = models.ForeignKey(LLMModel, on_delete=models.SET_NULL, null=True)
    temperature = models.FloatField(default=0.1)
    max_tokens = models.IntegerField(default=4096)
    timeout_seconds = models.IntegerField(default=30)

    class Meta:
        db_table = "llm_active_config"

    def __str__(self) -> str:
        return f"{self.purpose}: {self.provider}/{self.model}"
