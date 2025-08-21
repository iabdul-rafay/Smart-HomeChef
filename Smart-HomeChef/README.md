# HomeChef – AI-Powered Desktop Recipe Assistant

An intelligent desktop app to help you discover meals from ingredients on hand, manage recipes and grocery lists, and get live AI cooking assistance.

## Features
- Recipe Management: local SQLite library with ingredients, steps, cook time, difficulty, favorites
- Smart Recipe Suggestions: enter ingredients to get matches, creative ideas, and substitutions (OpenAI GPT)
- AI Cooking Assistant: chat for step guidance, substitutions, and cooking questions
- Grocery List: auto-add missing ingredients for a selected recipe; add/clear items

## Tech Stack
- Python, PySide6 (Qt) for desktop UI
- SQLite for local data storage
- OpenAI-compatible SDK via OpenRouter (model: `meta-llama/llama-3.3-70b-instruct:free`)

## Setup
1) Create and activate a virtual environment (Windows PowerShell):
```bash
python -m venv .venv
. .venv/Scripts/activate
```
2) Install dependencies:
```bash
pip install -r requirements.txt
```
3) (Optional) Override the default OpenRouter API key (PowerShell):
```bash
$env:OPENROUTER_API_KEY = "sk-or-..."
```

## Run
```bash
python main.py
```

### Run (Streamlit UI)
```bash
streamlit run app.py
```

## Usage Tips
- Use the top bar to search recipes or enter comma-separated ingredients, then click "Suggest Recipes (AI)".
- Select a recipe to view details and steps. Click "Add Missing Ingredients to Grocery" to populate the list.
- Open the "AI Assistant" tab to ask cooking questions with recipe context.

## Project Structure
- `homechef/db.py`: SQLite schema and operations (recipes, pantry, grocery)
- `homechef/ai.py`: OpenAI GPT calls for suggestions and chatbot
- `homechef/ui.py`: PySide6 interface and module wiring
- `main.py`: App entry point

## Deliverables
- Executable can be produced with PyInstaller if needed, e.g.: `pyinstaller --onefile main.py`

## Notes
- Sample recipes are seeded on first run.
- The AI features require an active internet connection and a valid `OPENAI_API_KEY`.
