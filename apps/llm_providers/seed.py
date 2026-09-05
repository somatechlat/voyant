"""LLM Providers — Seed data with common providers and models.

Run: docker exec voyant_api python apps/llm_providers/seed.py
"""

from __future__ import annotations

PROVIDERS = [
    {
        "name": "Groq",
        "slug": "groq",
        "description": "Ultra-fast LLM inference. OpenAI-compatible API.",
        "api_base_url": "https://api.groq.com/openai/v1",
        "supports_chat": True,
        "supports_streaming": True,
        "supports_json_mode": True,
        "supports_function_calling": True,
        "supports_vision": False,
        "is_system": True,
        "models": [
            {
                "name": "openai/gpt-oss-120b",
                "display_name": "GPT-OSS 120B",
                "description": "Open-source GPT model, 120B parameters. Fast inference on Groq.",
                "context_window": 131072,
                "max_output_tokens": 32768,
                "supports_json_mode": True,
                "supports_function_calling": True,
                "supports_reasoning": True,
                "input_price": 0.0,
                "output_price": 0.0,
                "is_default": True,
            },
            {
                "name": "openai/gpt-oss-20b",
                "display_name": "GPT-OSS 20B",
                "description": "Open-source GPT model, 20B parameters. Fastest inference.",
                "context_window": 131072,
                "max_output_tokens": 32768,
                "supports_json_mode": True,
                "supports_function_calling": True,
                "supports_reasoning": True,
                "input_price": 0.0,
                "output_price": 0.0,
            },
            {
                "name": "llama-3.3-70b-versatile",
                "display_name": "Llama 3.3 70B Versatile",
                "description": "Meta's Llama 3.3 70B. Best general-purpose model on Groq.",
                "context_window": 131072,
                "max_output_tokens": 32768,
                "supports_json_mode": True,
                "supports_function_calling": True,
                "input_price": 0.59,
                "output_price": 0.79,
            },
            {
                "name": "llama-3.1-8b-instant",
                "display_name": "Llama 3.1 8B Instant",
                "description": "Meta's Llama 3.1 8B. Ultra-fast, low cost.",
                "context_window": 131072,
                "max_output_tokens": 8192,
                "supports_json_mode": True,
                "input_price": 0.05,
                "output_price": 0.08,
            },
            {
                "name": "mixtral-8x7b-32768",
                "display_name": "Mixtral 8x7B",
                "description": "Mistral's mixture-of-experts model.",
                "context_window": 32768,
                "max_output_tokens": 32768,
                "supports_json_mode": True,
                "supports_function_calling": True,
                "input_price": 0.24,
                "output_price": 0.24,
            },
        ],
    },
    {
        "name": "OpenAI",
        "slug": "openai",
        "description": "OpenAI API. Industry standard.",
        "api_base_url": "https://api.openai.com/v1",
        "supports_chat": True,
        "supports_streaming": True,
        "supports_json_mode": True,
        "supports_function_calling": True,
        "supports_vision": True,
        "is_system": True,
        "models": [
            {
                "name": "gpt-4o",
                "display_name": "GPT-4o",
                "description": "OpenAI's flagship multimodal model.",
                "context_window": 128000,
                "max_output_tokens": 16384,
                "supports_vision": True,
                "supports_json_mode": True,
                "supports_function_calling": True,
                "input_price": 2.50,
                "output_price": 10.00,
                "is_default": True,
            },
            {
                "name": "gpt-4o-mini",
                "display_name": "GPT-4o Mini",
                "description": "Fast, cheap GPT-4o variant.",
                "context_window": 128000,
                "max_output_tokens": 16384,
                "supports_vision": True,
                "supports_json_mode": True,
                "supports_function_calling": True,
                "input_price": 0.15,
                "output_price": 0.60,
            },
            {
                "name": "o3-mini",
                "display_name": "o3-mini",
                "description": "OpenAI's reasoning model.",
                "context_window": 200000,
                "max_output_tokens": 100000,
                "supports_json_mode": True,
                "supports_function_calling": True,
                "supports_reasoning": True,
                "input_price": 1.10,
                "output_price": 4.40,
            },
        ],
    },
    {
        "name": "Anthropic",
        "slug": "anthropic",
        "description": "Anthropic Claude API.",
        "api_base_url": "https://api.anthropic.com/v1",
        "supports_chat": True,
        "supports_streaming": True,
        "supports_json_mode": False,
        "supports_function_calling": True,
        "supports_vision": True,
        "is_system": True,
        "models": [
            {
                "name": "claude-sonnet-4-20250514",
                "display_name": "Claude Sonnet 4",
                "description": "Anthropic's latest Sonnet model. Best balance of speed and intelligence.",
                "context_window": 200000,
                "max_output_tokens": 16384,
                "supports_vision": True,
                "supports_function_calling": True,
                "input_price": 3.00,
                "output_price": 15.00,
                "is_default": True,
            },
            {
                "name": "claude-3-5-haiku-20241022",
                "display_name": "Claude 3.5 Haiku",
                "description": "Anthropic's fastest model. Low cost.",
                "context_window": 200000,
                "max_output_tokens": 8192,
                "supports_vision": True,
                "supports_function_calling": True,
                "input_price": 0.80,
                "output_price": 4.00,
            },
        ],
    },
    {
        "name": "MiMo (Xiaomi)",
        "slug": "mimo",
        "description": "Xiaomi MiMo models. OpenAI-compatible API.",
        "api_base_url": "https://api.mimo.xiaomi.com/v1",
        "api_key": "tp-skzqqovjqtqhr1iase36kroqhwxmh1nwr5ifx6iykp1q902v",
        "supports_chat": True,
        "supports_streaming": True,
        "supports_json_mode": False,
        "supports_function_calling": False,
        "supports_vision": False,
        "is_system": True,
        "models": [
            {
                "name": "MiMo-7B-RL",
                "display_name": "MiMo 7B RL",
                "description": "Xiaomi MiMo 7B Reinforcement Learning model. Reasoning-focused.",
                "context_window": 131072,
                "max_output_tokens": 32768,
                "supports_reasoning": True,
                "input_price": 0.0,
                "output_price": 0.0,
                "is_default": True,
            },
        ],
    },
    {
        "name": "Google",
        "slug": "google",
        "description": "Google Gemini API.",
        "api_base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "supports_chat": True,
        "supports_streaming": True,
        "supports_json_mode": True,
        "supports_function_calling": True,
        "supports_vision": True,
        "is_system": True,
        "models": [
            {
                "name": "gemini-2.5-flash",
                "display_name": "Gemini 2.5 Flash",
                "description": "Google's fast multimodal model.",
                "context_window": 1048576,
                "max_output_tokens": 65536,
                "supports_vision": True,
                "supports_json_mode": True,
                "supports_function_calling": True,
                "supports_reasoning": True,
                "input_price": 0.15,
                "output_price": 0.60,
                "is_default": True,
            },
            {
                "name": "gemini-2.5-pro",
                "display_name": "Gemini 2.5 Pro",
                "description": "Google's most capable model.",
                "context_window": 1048576,
                "max_output_tokens": 65536,
                "supports_vision": True,
                "supports_json_mode": True,
                "supports_function_calling": True,
                "supports_reasoning": True,
                "input_price": 1.25,
                "output_price": 10.00,
            },
        ],
    },
    {
        "name": "Mistral",
        "slug": "mistral",
        "description": "Mistral AI API.",
        "api_base_url": "https://api.mistral.ai/v1",
        "supports_chat": True,
        "supports_streaming": True,
        "supports_json_mode": True,
        "supports_function_calling": True,
        "supports_vision": False,
        "is_system": True,
        "models": [
            {
                "name": "mistral-large-latest",
                "display_name": "Mistral Large",
                "description": "Mistral's flagship model.",
                "context_window": 128000,
                "max_output_tokens": 32768,
                "supports_json_mode": True,
                "supports_function_calling": True,
                "input_price": 2.00,
                "output_price": 6.00,
                "is_default": True,
            },
            {
                "name": "mistral-small-latest",
                "display_name": "Mistral Small",
                "description": "Mistral's fast, cheap model.",
                "context_window": 32000,
                "max_output_tokens": 32768,
                "supports_json_mode": True,
                "supports_function_calling": True,
                "input_price": 0.10,
                "output_price": 0.30,
            },
        ],
    },
    {
        "name": "DeepSeek",
        "slug": "deepseek",
        "description": "DeepSeek API. Strong reasoning models.",
        "api_base_url": "https://api.deepseek.com/v1",
        "supports_chat": True,
        "supports_streaming": True,
        "supports_json_mode": True,
        "supports_function_calling": True,
        "supports_vision": False,
        "is_system": True,
        "models": [
            {
                "name": "deepseek-chat",
                "display_name": "DeepSeek V3",
                "description": "DeepSeek V3 general-purpose model.",
                "context_window": 65536,
                "max_output_tokens": 8192,
                "supports_json_mode": True,
                "supports_function_calling": True,
                "input_price": 0.14,
                "output_price": 0.28,
                "is_default": True,
            },
            {
                "name": "deepseek-reasoner",
                "display_name": "DeepSeek R1",
                "description": "DeepSeek R1 reasoning model.",
                "context_window": 65536,
                "max_output_tokens": 8192,
                "supports_reasoning": True,
                "input_price": 0.55,
                "output_price": 2.19,
            },
        ],
    },
]


def seed():
    """Seed LLM providers and models into the database."""
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")
    import django
    django.setup()

    from apps.llm_providers.models import ActiveLLMConfig, LLMModel, LLMProvider

    created_providers = 0
    created_models = 0

    for p_data in PROVIDERS:
        models_data = p_data.pop("models", [])

        provider, created = LLMProvider.objects.update_or_create(
            slug=p_data["slug"],
            defaults=p_data,
        )
        if created:
            created_providers += 1

        for m_data in models_data:
            _, created = LLMModel.objects.update_or_create(
                provider=provider,
                name=m_data["name"],
                defaults=m_data,
            )
            if created:
                created_models += 1

    # Set default active config for intent engine (Groq + GPT-OSS 120B)
    groq = LLMProvider.objects.filter(slug="groq").first()
    gpt_oss = LLMModel.objects.filter(provider=groq, name="openai/gpt-oss-120b").first() if groq else None

    if groq and gpt_oss:
        ActiveLLMConfig.objects.update_or_create(
            purpose="intent",
            defaults={
                "provider": groq,
                "model": gpt_oss,
                "temperature": 0.1,
                "max_tokens": 4096,
                "timeout_seconds": 30,
            },
        )

    total_providers = LLMProvider.objects.count()
    total_models = LLMModel.objects.count()
    print(f"Seeded: {created_providers} providers, {created_models} models")
    print(f"Total:  {total_providers} providers, {total_models} models")


if __name__ == "__main__":
    seed()
