# Cloud LLM setup (Google AI Studio)

## 1) Create an API key

1. Go to https://aistudio.google.com/
2. Sign in with your Google account
3. Click **Get API Key** → **Create API key**
4. Copy the key

## 2) Configure environment variables

Set these values in your `.env`:

```env
LLM_PROVIDER=openai_compatible
LLM_API_KEY=your-google-api-key
LLM_API_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_MODEL=gemini-2.5-flash
```

## 3) Restart backend

Restart the backend service so the new environment variables are loaded.

## Alternatives

- **Groq**
  - `LLM_API_URL=https://api.groq.com/openai/v1`
  - `LLM_MODEL=llama-3.3-70b-versatile`
- **OpenRouter**
  - `LLM_API_URL=https://openrouter.ai/api/v1`
  - `LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free`
