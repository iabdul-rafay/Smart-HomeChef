import os
import sqlite3
from typing import List, Optional, Dict, Any


DB_PATH = os.path.join(os.getcwd(), "homechef.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            ingredients_text TEXT NOT NULL,
            steps_text TEXT NOT NULL,
            cook_time INTEGER,
            difficulty TEXT,
            image_path TEXT,
            is_favorite INTEGER DEFAULT 0
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pantry_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS grocery_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            is_checked INTEGER DEFAULT 0
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS recipe_notes (
            recipe_id INTEGER PRIMARY KEY,
            notes_text TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    insert_sample_recipes_if_empty()


def insert_sample_recipes_if_empty() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM recipes")
    count = cur.fetchone()[0]
    if count and count > 0:
        conn.close()
        return

    samples = [
        {
            "title": "Simple Crepes",
            "ingredients_text": (
                "1 cup flour\n2 eggs\n1/2 cup milk\n1/2 cup water\nPinch of salt\n1 tbsp butter"
            ),
            "steps_text": (
                "1) Whisk flour and eggs.\n"
                "2) Gradually add milk and water while whisking.\n"
                "3) Add salt and melted butter; whisk until smooth.\n"
                "4) Heat a lightly oiled pan, pour batter, cook each side 1-2 minutes."
            ),
            "cook_time": 20,
            "difficulty": "Easy",
            "image_path": "",
        },
        {
            "title": "Pasta Aglio e Olio",
            "ingredients_text": (
                "200g spaghetti\n3 cloves garlic\n4 tbsp olive oil\nRed pepper flakes\nSalt\nParsley"
            ),
            "steps_text": (
                "1) Cook spaghetti until al dente.\n"
                "2) Gently cook sliced garlic in olive oil; add pepper flakes.\n"
                "3) Toss pasta with oil, season with salt, finish with parsley."
            ),
            "cook_time": 15,
            "difficulty": "Easy",
            "image_path": "",
        },
        {
            "title": "Veggie Omelette",
            "ingredients_text": (
                "3 eggs\n1/4 cup milk\n1/4 cup diced bell pepper\n1/4 cup diced onion\nSalt\nPepper\nOlive oil"
            ),
            "steps_text": (
                "1) Whisk eggs with milk, salt, pepper.\n"
                "2) Sauté peppers and onions in oil.\n"
                "3) Pour eggs, cook until set; fold and serve."
            ),
            "cook_time": 10,
            "difficulty": "Easy",
            "image_path": "",
        },
    ]
    for s in samples:
        cur.execute(
            """
            INSERT INTO recipes (title, ingredients_text, steps_text, cook_time, difficulty, image_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                s["title"],
                s["ingredients_text"],
                s["steps_text"],
                s["cook_time"],
                s["difficulty"],
                s["image_path"],
            ),
        )
    conn.commit()
    conn.close()


def list_recipes(search: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    if search:
        like = f"%{search.lower()}%"
        cur.execute(
            """
            SELECT * FROM recipes
            WHERE LOWER(title) LIKE ? OR LOWER(ingredients_text) LIKE ?
            ORDER BY title ASC
            """,
            (like, like),
        )
    else:
        cur.execute("SELECT * FROM recipes ORDER BY title ASC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_recipe(
    title: str,
    ingredients_text: str,
    steps_text: str,
    cook_time: Optional[int] = None,
    difficulty: Optional[str] = None,
    image_path: Optional[str] = None,
) -> int:
    """Insert a new recipe and return its id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO recipes (title, ingredients_text, steps_text, cook_time, difficulty, image_path)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            title.strip(),
            ingredients_text.strip(),
            steps_text.strip(),
            cook_time if cook_time is not None else None,
            (difficulty or None),
            (image_path or None),
        ),
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return int(rid)


def get_recipe(recipe_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def set_favorite(recipe_id: int, is_favorite: bool) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE recipes SET is_favorite = ? WHERE id = ?",
        (1 if is_favorite else 0, recipe_id),
    )
    conn.commit()
    conn.close()


def list_favorites() -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM recipes WHERE is_favorite = 1 ORDER BY title ASC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_pantry() -> List[str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM pantry_items ORDER BY name ASC")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows


def add_pantry_item(name: str) -> None:
    if not name:
        return
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO pantry_items (name) VALUES (?)", (name.strip().lower(),))
        conn.commit()
    finally:
        conn.close()


def remove_pantry_item(name: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM pantry_items WHERE name = ?", (name.strip().lower(),))
    conn.commit()
    conn.close()


def list_grocery() -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, is_checked FROM grocery_items ORDER BY name ASC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_grocery_item(name: str) -> None:
    if not name:
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO grocery_items (name, is_checked) VALUES (?, 0)", (name.strip().lower(),))
    conn.commit()
    conn.close()


def remove_grocery_item(item_id: int) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM grocery_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def clear_grocery() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM grocery_items")
    conn.commit()
    conn.close()


def set_grocery_checked(item_id: int, checked: bool) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE grocery_items SET is_checked = ? WHERE id = ?",
        (1 if checked else 0, item_id),
    )
    conn.commit()
    conn.close()


def export_grocery_text() -> str:
    items = list_grocery()
    lines = [
        f"[{'x' if it.get('is_checked') else ' '}] {it.get('name','')}" for it in items
    ]
    return "\n".join(lines)


def get_recipe_notes(recipe_id: int) -> str:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT notes_text FROM recipe_notes WHERE recipe_id = ?", (recipe_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else ""


def set_recipe_notes(recipe_id: int, notes_text: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO recipe_notes (recipe_id, notes_text) VALUES (?, ?)\n"
        "ON CONFLICT(recipe_id) DO UPDATE SET notes_text = excluded.notes_text",
        (recipe_id, notes_text),
    )
    conn.commit()
    conn.close()


def _normalize_ingredient(line: str) -> str:
    s = line.strip().lower()
    # very simple normalization: remove punctuation commonly used and numbers
    for ch in [',', '.', ';', ':', '(', ')']:
        s = s.replace(ch, ' ')
    return ' '.join([tok for tok in s.split() if not tok.isdigit()])


def compute_missing_ingredients(recipe_id: int) -> List[str]:
    recipe = get_recipe(recipe_id)
    if not recipe:
        return []
    pantry = set(list_pantry())
    ingredients_lines = [l for l in (recipe.get("ingredients_text") or "").splitlines() if l.strip()]
    missing: List[str] = []
    for line in ingredients_lines:
        item = _normalize_ingredient(line)
        # take last token as key ingredient heuristic
        key = item.split()[-1] if item.split() else item
        if key and key not in pantry:
            missing.append(key)
    # unique preserve order
    seen = set()
    uniq: List[str] = []
    for m in missing:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    return uniq


def add_missing_to_grocery(recipe_id: int) -> List[str]:
    missing = compute_missing_ingredients(recipe_id)
    for m in missing:
        add_grocery_item(m)
    return missing


