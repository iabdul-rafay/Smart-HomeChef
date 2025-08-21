from typing import List, Dict, Any, Optional
import os

from openai import OpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
DEFAULT_OPENROUTER_API_KEY = "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"


def get_openai_client(api_key: Optional[str] = None) -> OpenAI:
    """Create an OpenAI-compatible client pointed at OpenRouter."""
    key = api_key or os.getenv("OPENROUTER_API_KEY") or DEFAULT_OPENROUTER_API_KEY
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=key)


def suggest_recipes_from_ingredients(
    ingredients: List[str],
    local_recipes: List[Dict[str, Any]],
    model: str = OPENROUTER_MODEL,
    client: Optional[OpenAI] = None,
) -> Dict[str, Any]:
    """Ask GPT to match and suggest recipes.

    Returns a dict with keys:
    - matches: list of recipe ids that best match
    - creative_suggestions: list of textual recipe ideas
    - substitutions: mapping of ingredient -> alternatives
    """
    if client is None:
        client = get_openai_client()

    titles = [r.get("title", "") for r in local_recipes]
    prompt = (
        "You are an assistant helping users cook from what they have.\n"
        "Given the following available ingredients and the local recipe titles,\n"
        "1) choose top 3 matching titles (if any) by name;\n"
        "2) propose up to 3 creative recipe ideas if matches are weak;\n"
        "3) provide simple substitutions for common missing ingredients.\n"
        "Return strict JSON with keys: matches (titles), creative_suggestions, substitutions (object)."
    )

    user = {
        "ingredients": ingredients,
        "local_recipe_titles": titles,
    }

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": str(user)},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content or "{}"
    try:
        import json

        data = json.loads(content)
    except Exception:
        data = {"matches": [], "creative_suggestions": [], "substitutions": {}}

    # Map matched titles to ids
    title_to_id = {r.get("title", ""): r.get("id") for r in local_recipes}
    match_ids: List[int] = []
    for t in data.get("matches", []) or []:
        rid = title_to_id.get(t)
        if isinstance(rid, int):
            match_ids.append(rid)

    return {
        "matches": match_ids,
        "creative_suggestions": data.get("creative_suggestions", []) or [],
        "substitutions": data.get("substitutions", {}) or {},
    }


def chatbot_reply(
    message: str,
    context: Optional[Dict[str, Any]] = None,
    model: str = OPENROUTER_MODEL,
    client: Optional[OpenAI] = None,
) -> str:
    if client is None:
        client = get_openai_client()
    system = (
        "You are HomeChef, a friendly culinary assistant. Provide precise, safe,"
        " step-by-step guidance. Offer substitutions when helpful and avoid unsafe advice."
    )
    messages = [{"role": "system", "content": system}]
    if context:
        messages.append({"role": "system", "content": f"Context: {context}"})
    messages.append({"role": "user", "content": message})
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.5,
        )
        return completion.choices[0].message.content or ""
    except Exception as e:
        return f"[AI error] {e}"


