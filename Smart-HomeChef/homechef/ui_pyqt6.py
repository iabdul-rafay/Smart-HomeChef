from typing import List, Dict, Any, Optional

import requests

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QStackedWidget,
    QScrollArea,
    QFrame,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QComboBox,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QMessageBox,
    QDialog,
    QFormLayout,
    QSpinBox,
)

from . import db


API_BASE_URL = "http://localhost:8000"


class HomeChefWindow(QMainWindow):
    """Dashboard-style PyQt6 UI for HomeChef with sidebar and stacked pages.

    Usage manual (quick):
    - Use the left sidebar to switch between sections: Recipe Management, Smart Recipe Suggestions,
      AI Cooking Assistant, Grocery List Management, Cooking Guide.
    - Top header has search, a quick cook-time filter, favorites toggle, and buttons to open
      suggestions or add a sample recipe.
    - If the API at http://localhost:8000 is unavailable, the UI falls back to the local database
      and shows a sample recipe as needed.
    """

    def __init__(self) -> None:
        super().__init__()
        db.init_db()
        self.setWindowTitle("HomeChef – AI-Powered Recipe Assistant")
        self.resize(1280, 860)
        self.setFont(QFont("Inter", 10))

        # Simple state
        self.selected_recipe: Optional[Dict[str, Any]] = None
        self._cook_steps: List[str] = []
        self._cook_index: int = 0

        # Build UI and theme
        self._build_ui()
        self._apply_qss_theme()

        # Initial data
        self._load_recipes_page()
        self._reload_grocery()

    # ---------- UI BUILD ----------
    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout()
        central.setLayout(root)
        self.setCentralWidget(central)

        # Sidebar
        self.sidebar = self._build_sidebar()
        root.addWidget(self.sidebar)

        # Main content
        content = QWidget()
        c_v = QVBoxLayout()
        content.setLayout(c_v)
        root.addWidget(content, 1)

        self.header = self._build_header()
        c_v.addWidget(self.header)

        self.pages = QStackedWidget()
        c_v.addWidget(self.pages, 1)

        footer = QLabel("© 2025 HomeChef")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setObjectName("Footer")
        c_v.addWidget(footer)

        # Pages
        self.page_recipes = self._build_recipes_page()
        self.page_suggest = self._build_suggestions_page()
        self.page_ai = self._build_ai_page()
        self.page_grocery = self._build_grocery_page()
        self.page_cook = self._build_cook_page()
        for p in [self.page_recipes, self.page_suggest, self.page_ai, self.page_grocery, self.page_cook]:
            self.pages.addWidget(p)

    def _build_sidebar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("Sidebar")
        v = QVBoxLayout()
        bar.setLayout(v)

        title = QLabel("🍲 HomeChef")
        title.setObjectName("SidebarTitle")
        v.addWidget(title)

        self.btn_nav_recipes = self._nav_button("🍳 Recipe Management", "recipes")
        self.btn_nav_suggest = self._nav_button("💡 Smart Recipe Suggestions", "suggest")
        self.btn_nav_ai = self._nav_button("🤖 AI Cooking Assistant", "ai")
        self.btn_nav_grocery = self._nav_button("🛒 Grocery List Management", "grocery")
        self.btn_nav_cook = self._nav_button("⏲️ Step-by-Step Cooking Guide", "cook")
        for b in [self.btn_nav_recipes, self.btn_nav_suggest, self.btn_nav_ai, self.btn_nav_grocery, self.btn_nav_cook]:
            v.addWidget(b)
        v.addStretch(1)
        return bar

    def _nav_button(self, text: str, key: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName(f"NavBtn-{key}")
        btn.setCheckable(True)
        btn.clicked.connect(lambda _: self._on_nav(key))
        return btn

    def _build_header(self) -> QWidget:
        h = QFrame()
        h.setObjectName("Header")
        row = QHBoxLayout()
        h.setLayout(row)

        logo = QLabel("🍲")
        logo.setObjectName("Logo")
        title = QLabel("HomeChef")
        title.setObjectName("Title")
        row.addWidget(logo)
        row.addWidget(title)
        row.addStretch(1)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search recipes…")
        self.search_box.returnPressed.connect(self._load_recipes_page)
        row.addWidget(self.search_box)

        self.time_filter = QComboBox()
        self.time_filter.addItems(["0 min", "15 min", "30 min", "45 min", "60 min"])
        self.time_filter.currentIndexChanged.connect(self._load_recipes_page)
        row.addWidget(self.time_filter)

        self.fav_only = QCheckBox("Favorites Only")
        self.fav_only.stateChanged.connect(self._load_recipes_page)
        row.addWidget(self.fav_only)

        btn_ai = QPushButton("Suggest Recipes (AI)")
        btn_ai.setObjectName("BtnSuggestAI")
        btn_ai.clicked.connect(lambda: self._on_nav("suggest"))
        row.addWidget(btn_ai)

        btn_add = QPushButton("Add Recipe")
        btn_add.setObjectName("BtnAdd")
        btn_add.clicked.connect(self._open_add_dialog)
        row.addWidget(btn_add)

        return h

    def _build_recipes_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout()
        page.setLayout(v)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.grid = QGridLayout()
        container.setLayout(self.grid)
        scroll.setWidget(container)
        v.addWidget(scroll, 1)

        return page

    def _build_suggestions_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout()
        page.setLayout(v)

        row = QHBoxLayout()
        self.ingredients_input = QLineEdit()
        self.ingredients_input.setPlaceholderText("Ingredients (comma-separated)")
        btn = QPushButton("Fetch Suggestions")
        btn.clicked.connect(self._fetch_suggestions)
        row.addWidget(self.ingredients_input)
        row.addWidget(btn)
        v.addLayout(row)

        self.suggest_list = QListWidget()
        self.suggest_ideas = QTextEdit()
        self.suggest_ideas.setReadOnly(True)
        v.addWidget(QLabel("Suggested Recipes"))
        v.addWidget(self.suggest_list)
        v.addWidget(QLabel("Creative Ideas / Substitutions"))
        v.addWidget(self.suggest_ideas)

        self.suggest_list.itemClicked.connect(self._on_suggest_clicked)
        return page

    def _build_ai_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout()
        page.setLayout(v)
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        row = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask for tips, substitutions, or guidance…")
        send = QPushButton("Send")
        send.clicked.connect(self._send_chat)
        row.addWidget(self.chat_input)
        row.addWidget(send)
        v.addWidget(self.chat_history, 1)
        v.addLayout(row)
        return page

    def _build_grocery_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout()
        page.setLayout(v)
        self.grocery_list = QListWidget()
        v.addWidget(self.grocery_list, 1)

        row = QHBoxLayout()
        self.grocery_input = QLineEdit()
        self.grocery_input.setPlaceholderText("Add grocery item…")
        btn_add = QPushButton("Add")
        btn_add.clicked.connect(self._grocery_add)
        btn_remove = QPushButton("Remove Selected")
        btn_remove.clicked.connect(self._grocery_remove_selected)
        btn_export = QPushButton("Export")
        btn_export.clicked.connect(self._grocery_export)
        btn_missing = QPushButton("Add Missing Ingredients")
        btn_missing.clicked.connect(self._add_missing_via_api)
        row.addWidget(self.grocery_input)
        row.addWidget(btn_add)
        row.addWidget(btn_remove)
        row.addWidget(btn_export)
        row.addStretch(1)
        row.addWidget(btn_missing)
        v.addLayout(row)
        return page

    def _build_cook_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout()
        page.setLayout(v)
        self.cook_step_label = QLabel("Select a recipe to start cooking mode.")
        self.cook_step_label.setWordWrap(True)
        self.cook_progress = QProgressBar()
        row = QHBoxLayout()
        prev = QPushButton("Previous Step")
        nextb = QPushButton("Next Step")
        ask = QPushButton("Ask AI about this Step")
        prev.clicked.connect(self._prev_step)
        nextb.clicked.connect(self._next_step)
        ask.clicked.connect(self._ask_ai_about_step)
        row.addWidget(prev)
        row.addWidget(nextb)
        row.addWidget(ask)
        v.addWidget(self.cook_step_label)
        v.addWidget(self.cook_progress)
        v.addLayout(row)
        return page

    # ---------- NAV ----------
    def _on_nav(self, key: str) -> None:
        mapping = {"recipes": 0, "suggest": 1, "ai": 2, "grocery": 3, "cook": 4}
        self.pages.setCurrentIndex(mapping.get(key, 0))
        if key == "recipes":
            self._load_recipes_page()
        elif key == "grocery":
            self._reload_grocery()

    # ---------- NETWORKING ----------
    def _get(self, path: str) -> Optional[Dict[str, Any]]:
        try:
            r = requests.get(f"{API_BASE_URL}{path}", timeout=6)
            if r.ok:
                return r.json()
        except Exception:
            return None
        return None

    def _post(self, path: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            r = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=10)
            if r.ok:
                return r.json()
        except Exception:
            return None
        return None

    # ---------- RECIPES PAGE ----------
    def _load_recipes_page(self) -> None:
        search = (self.search_box.text() or "").strip()
        max_time = self._selected_time()
        data = self._get(f"/recipes?search={search}&max_time={max_time}")
        if not data:
            # Fallback to local DB and a sample
            recipes = db.list_recipes(search if search else None)
            if max_time:
                recipes = [r for r in recipes if (r.get("cook_time") or 0) <= max_time]
            if not recipes:
                recipes = [{
                    "id": 1,
                    "name": "Pancakes",
                    "ingredients": "Flour, Eggs, Milk",
                    "cook_time": 20,
                    "difficulty": "Easy",
                    "image": "placeholder_image",
                }]
            data = {"recipes": recipes}

        recipes = data.get("recipes", []) if isinstance(data, dict) else []
        if self.fav_only.isChecked():
            recipes = [r for r in recipes if (r.get("is_favorite") == 1)]
        self._render_recipe_cards(recipes)

    def _selected_time(self) -> int:
        try:
            return int((self.time_filter.currentText() or "0").split()[0])
        except Exception:
            return 0

    def _render_recipe_cards(self, recipes: List[Dict[str, Any]]) -> None:
        # clear grid
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w is not None:
                w.setParent(None)

        cols = 3
        row = 0
        col = 0
        for r in recipes:
            card = self._recipe_card(r)
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _recipe_card(self, r: Dict[str, Any]) -> QWidget:
        card = QFrame()
        card.setObjectName("RecipeCard")
        v = QVBoxLayout()
        card.setLayout(v)
        title = QLabel(r.get("title") or r.get("name") or "Untitled")
        title.setObjectName("CardTitle")
        meta = QLabel(self._format_meta(r))
        meta.setObjectName("CardMeta")
        summ = QLabel((r.get("ingredients_text") or r.get("ingredients") or "").strip())
        summ.setWordWrap(True)
        v.addWidget(title)
        v.addWidget(meta)
        v.addWidget(summ)
        btn = QPushButton("View Details")
        btn.setObjectName("BtnView")
        btn.clicked.connect(lambda _: self._on_recipe_selected(r))
        v.addWidget(btn)
        return card

    def _format_meta(self, r: Dict[str, Any]) -> str:
        t = r.get("cook_time") or r.get("cook_time_min") or "-"
        if isinstance(t, int):
            t = f"{t} min"
        d = r.get("difficulty") or "-"
        return f"⏱ {t} • {d}"

    def _on_recipe_selected(self, r: Dict[str, Any]) -> None:
        self.selected_recipe = r
        steps_raw = r.get("steps_text") or r.get("steps") or ""
        self._cook_steps = [s.strip() for s in steps_raw.splitlines() if s.strip()]
        self._cook_index = 0
        self._update_cook_view()
        self._on_nav("cook")

    # ---------- SUGGESTIONS ----------
    def _fetch_suggestions(self) -> None:
        raw = (self.ingredients_input.text() or "").strip()
        ingredients = [s.strip() for s in raw.split(',') if s.strip()]
        data = self._post("/suggest", {"ingredients": ingredients})
        if not data:
            data = {
                "matches": [self.selected_recipe.get("id")] if self.selected_recipe else [],
                "creative_suggestions": ["Try savory crepes", "Make banana pancakes"],
                "substitutions": {"milk": "almond milk", "egg": "flax egg"},
            }
        self._apply_suggestions(data)

    def _apply_suggestions(self, data: Dict[str, Any]) -> None:
        self.suggest_list.clear()
        ideas = data.get("creative_suggestions") or []
        subs = data.get("substitutions") or {}
        matches = data.get("matches") or []
        id_to_title = {r.get("id"): r.get("title") for r in db.list_recipes()}
        for rid in matches:
            t = id_to_title.get(rid, f"Recipe {rid}")
            item = QListWidgetItem(t)
            item.setData(Qt.ItemDataRole.UserRole, rid)
            self.suggest_list.addItem(item)
        details: List[str] = []
        if ideas:
            details.append("Ideas: " + ", ".join(ideas))
        if subs:
            details.append("Substitutions:")
            for k, v in subs.items():
                details.append(f"- {k}: {v}")
        self.suggest_ideas.setPlainText("\n".join(details))

    def _on_suggest_clicked(self, item: QListWidgetItem) -> None:
        rid = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(rid, int):
            r = db.get_recipe(rid)
            if r:
                self._on_recipe_selected(r)

    # ---------- CHAT ----------
    def _send_chat(self) -> None:
        msg = (self.chat_input.text() or "").strip()
        if not msg:
            return
        self.chat_input.clear()
        self._append_chat("user", msg)
        payload = {"message": msg, "context": self.selected_recipe or {}}
        data = self._post("/chat", payload)
        text = data.get("reply") if data else "[Network unavailable] Tip: preheat your pan and taste as you go."
        self._append_chat("assistant", text)

    def _append_chat(self, role: str, text: str) -> None:
        color = "#3b82f6" if role == "user" else "#22c55e"
        who = "You" if role == "user" else "HomeChef"
        self.chat_history.append(f'<div style="margin:6px 0;color:{color};"><b>{who}:</b> {text}</div>')

    # ---------- GROCERY ----------
    def _add_missing_via_api(self) -> None:
        if not self.selected_recipe:
            QMessageBox.information(self, "Info", "Select a recipe on the Recipes page first.")
            return
        rid = self.selected_recipe.get("id")
        data = self._get(f"/grocery_list/{rid}") if isinstance(rid, int) else None
        if not data and isinstance(rid, int):
            missing = db.add_missing_to_grocery(rid)
            if not missing:
                QMessageBox.information(self, "Grocery", "You have everything needed!")
            else:
                QMessageBox.information(self, "Grocery", f"Added missing items: {', '.join(missing)}")
        self._reload_grocery()

    def _reload_grocery(self) -> None:
        self.grocery_list.clear()
        for it in db.list_grocery():
            self.grocery_list.addItem(it.get("name", ""))

    def _grocery_add(self) -> None:
        name = (self.grocery_input.text() or "").strip()
        if not name:
            return
        db.add_grocery_item(name)
        self.grocery_input.clear()
        self._reload_grocery()

    def _grocery_remove_selected(self) -> None:
        # Placeholder: full remove requires IDs wiring in the list.
        QMessageBox.information(self, "Info", "Remove via DB or extend implementation to include IDs.")

    def _grocery_export(self) -> None:
        text = db.export_grocery_text()
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Grocery", "Copied grocery list to clipboard.")

    # ---------- COOKING ----------
    def _update_cook_view(self) -> None:
        total = max(1, len(self._cook_steps))
        self.cook_progress.setRange(0, total)
        self.cook_progress.setValue(min(self._cook_index + 1, total))
        self.cook_step_label.setText(self._cook_steps[self._cook_index] if self._cook_steps else "No steps.")

    def _prev_step(self) -> None:
        if not self._cook_steps:
            return
        self._cook_index = max(0, self._cook_index - 1)
        self._update_cook_view()

    def _next_step(self) -> None:
        if not self._cook_steps:
            return
        self._cook_index = min(len(self._cook_steps) - 1, self._cook_index + 1)
        self._update_cook_view()

    def _ask_ai_about_step(self) -> None:
        if not self._cook_steps:
            return
        msg = f"Question about step: {self._cook_steps[self._cook_index]}"
        self._append_chat("user", msg)
        self._send_chat()

    # ---------- SAMPLE / ADD ----------
    def _open_add_dialog(self) -> None:
        dlg = AddRecipeDialog(self)
        res = dlg.exec()
        if res != QDialog.DialogCode.Accepted:
            return
        values = dlg.values()
        if not values.get("title") or not values.get("ingredients_text"):
            QMessageBox.warning(self, "Missing", "Please provide a name and ingredients.")
            return
        try:
            db.add_recipe(
                title=values["title"],
                ingredients_text=values["ingredients_text"],
                steps_text="",
                cook_time=values.get("cook_time"),
                difficulty=None,
                image_path=None,
            )
            QMessageBox.information(self, "Success", "Recipe added.")
            self._load_recipes_page()
            self._on_nav("recipes")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add recipe: {e}")

    # ---------- THEME & RESPONSIVE ----------
    def _apply_qss_theme(self) -> None:
        qss = """
        QWidget { background-color: #1f2937; color: #e5e7eb; font-family: 'Inter','Segoe UI',Arial,sans-serif; }
        #Footer { padding: 8px 0; color: #9ca3af; }

        /* Sidebar */
        #Sidebar { background-color: #111827; border-right: 1px solid #0b1220; min-width: 230px; }
        #SidebarTitle { color: #fff; font-size: 18px; font-weight: 600; padding: 16px 12px; }
        QPushButton[objectName="NavBtn-recipes"] { background-color: qlineargradient(spread:pad,x1:0,y1:0,x2:1,y2:1, stop:0 #3b82f6, stop:1 #1d4ed8); color: #fff; border-radius: 10px; padding: 10px 14px; margin: 6px 12px; }
        QPushButton[objectName="NavBtn-suggest"] { background-color: qlineargradient(spread:pad,x1:0,y1:0,x2:1,y2:1, stop:0 #22c55e, stop:1 #15803d); color: #fff; border-radius: 10px; padding: 10px 14px; margin: 6px 12px; }
        QPushButton[objectName="NavBtn-ai"] { background-color: qlineargradient(spread:pad,x1:0,y1:0,x2:1,y2:1, stop:0 #f59e0b, stop:1 #b45309); color: #111827; border-radius: 10px; padding: 10px 14px; margin: 6px 12px; }
        QPushButton[objectName="NavBtn-grocery"] { background-color: qlineargradient(spread:pad,x1:0,y1:0,x2:1,y2:1, stop:0 #ef4444, stop:1 #991b1b); color: #fff; border-radius: 10px; padding: 10px 14px; margin: 6px 12px; }
        QPushButton[objectName="NavBtn-cook"] { background-color: qlineargradient(spread:pad,x1:0,y1:0,x2:1,y2:1, stop:0 #a855f7, stop:1 #6b21a8); color: #fff; border-radius: 10px; padding: 10px 14px; margin: 6px 12px; }

        /* Header */
        #Header { background: #111827; border-bottom: 1px solid #0b1220; padding: 10px; }
        #Logo { font-size: 20px; }
        #Title { font-size: 18px; font-weight: 600; color: #e5e7eb; }
        QLineEdit { background-color: #111827; border: 1px solid #374151; padding: 8px 10px; border-radius: 8px; color: #e5e7eb; }
        QComboBox { background-color: #111827; border: 1px solid #374151; padding: 8px 10px; border-radius: 8px; color: #e5e7eb; }
        QCheckBox { padding: 0 6px; }
        QPushButton#BtnSuggestAI { background-color: #2563eb; color: #fff; padding: 8px 12px; border-radius: 8px; }
        QPushButton#BtnAdd { background-color: #059669; color: #fff; padding: 8px 12px; border-radius: 8px; }

        /* Cards */
        #RecipeCard { background-color: #0f172a; border: 1px solid #1f2937; border-radius: 12px; padding: 12px; }
        #RecipeCard:hover { border-color: #3b82f6; }
        #CardTitle { font-size: 14px; font-weight: 600; color: #e5e7eb; }
        #CardMeta { color: #9ca3af; }
        #BtnView { background-color: #3b82f6; color: white; border-radius: 8px; padding: 6px 10px; }

        QProgressBar { border: 1px solid #374151; border-radius: 6px; text-align: center; }
        QProgressBar::chunk { background-color: #22c55e; }
        """
        self.setStyleSheet(qss)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        width = self.size().width()
        self.sidebar.setMaximumWidth(70 if width < 900 else 230)


class AddRecipeDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Recipe")
        self.setModal(True)

        self.title_edit = QLineEdit()
        self.time_spin = QSpinBox()
        self.time_spin.setRange(0, 1000)
        self.time_spin.setSuffix(" min")
        self.ing_edit = QTextEdit()
        self.ing_edit.setPlaceholderText("One ingredient per line")

        form = QFormLayout()
        form.addRow("Name", self.title_edit)
        form.addRow("Cook Time", self.time_spin)
        form.addRow("Ingredients", self.ing_edit)

        btns = QHBoxLayout()
        ok = QPushButton("Save")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)

        root = QVBoxLayout()
        root.addLayout(form)
        root.addLayout(btns)
        self.setLayout(root)

    def values(self) -> Dict[str, Any]:
        title = (self.title_edit.text() or "").strip()
        cook_time = int(self.time_spin.value()) if self.time_spin.value() > 0 else None
        ingredients_text = (self.ing_edit.toPlainText() or "").strip()
        return {"title": title, "cook_time": cook_time, "ingredients_text": ingredients_text}


