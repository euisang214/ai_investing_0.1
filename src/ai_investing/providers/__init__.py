"""Provider package.

Supported providers:
  - fake: Deterministic test provider (no API key needed)
  - openai: OpenAI GPT models via langchain-openai
  - anthropic: Anthropic Claude models via langchain-anthropic
  - google: Google Gemini models via langchain-google-genai
  - groq: Groq-hosted models via langchain-groq
  - openai_compatible: Any OpenAI-compatible endpoint (Together, Fireworks, Ollama, vLLM, etc.)
"""
