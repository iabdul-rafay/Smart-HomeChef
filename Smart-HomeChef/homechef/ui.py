from typing import List, Dict, Any, Optional
import os

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTabWidget,
    QMessageBox,
    QDialog,
    QFormLayout,
    QSpinBox,
    QComboBox,
    QFileDialog,
    QCheckBox,
    QListView,
    QProgressBar,
    QApplication,
    QFrame,
)

from . import db
from .ai import suggest_recipes_from_ingredients, chatbot_reply


class HomeChefWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        db.init_db()
        self.setWindowTitle("HomeChef – AI-Powered Recipe Assistant")
        self.resize(1200, 780)
        self._build_ui()
        self._load_recipes()
        self._apply_theme(False)

    def _build_ui(self) -> None:
        root = QVBoxLayout()

        # Header with app name and theme toggle
        header = QHBoxLayout()
        title = QLabel("🍳 HomeChef")
        title.setStyleSheet("font-size: 20px; font-weight: 600; letter-spacing: 0.25px;")
        header.addWidget(title)
        header.addStretch(1)
        self.dark_mode_toggle = QCheckBox("Dark mode")
        self.dark_mode_toggle.setToolTip("Toggle light/dark theme")
        self.dark_mode_toggle.stateChanged.connect(lambda _: self._apply_theme(self.dark_mode_toggle.isChecked()))
        header.addWidget(self.dark_mode_toggle)
        root.addLayout(header)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        root.addWidget(line)

        # Top toolbar: search, filters, ingredients, AI suggest, favorites filter, add recipe
        search_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search recipes...")
        self.search_box.returnPressed.connect(self._load_recipes)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._load_recipes)

        self.diff_filter = QComboBox()
        self.diff_filter.addItems(["All", "Easy", "Medium", "Hard"])
        self.diff_filter.setToolTip("Filter by difficulty")
        self.diff_filter.currentIndexChanged.connect(self._load_recipes)

        self.time_filter = QSpinBox()
        self.time_filter.setRange(0, 600)
        self.time_filter.setSuffix(" min max")
        self.time_filter.setToolTip("Max cook time (0 = any)")
        self.time_filter.valueChanged.connect(self._load_recipes)

        self.ingredients_box = QLineEdit()
        self.ingredients_box.setPlaceholderText("Comma-separated ingredients you have (e.g., eggs, flour, milk)")
        suggest_btn = QPushButton("Suggest Recipes (AI)")
        suggest_btn.clicked.connect(self._ai_suggest)

        self.fav_only = QCheckBox("Favorites only")
        self.fav_only.stateChanged.connect(self._load_recipes)

        add_btn = QPushButton("＋ Add Recipe")
        add_btn.clicked.connect(self._open_add_recipe)

        search_row.addWidget(self.search_box)
        search_row.addWidget(search_btn)
        search_row.addWidget(self.diff_filter)
        search_row.addWidget(self.time_filter)
        search_row.addWidget(self.ingredients_box)
        search_row.addWidget(suggest_btn)
        search_row.addWidget(self.fav_only)
        search_row.addWidget(add_btn)
        root.addLayout(search_row)

        # Splitter: left recipes, right tabs for modules
        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)

        # Left: recipe list
        left = QWidget()
        left_layout = QVBoxLayout()
        self.recipe_list = QListWidget()
        self.recipe_list.setViewMode(QListView.IconMode)
        self.recipe_list.setIconSize(QSize(96, 96))
        self.recipe_list.setResizeMode(QListView.Adjust)
        self.recipe_list.setSpacing(8)
        self.recipe_list.itemSelectionChanged.connect(self._on_select_recipe)
        left_layout.addWidget(QLabel("Recipes"))
        left_layout.addWidget(self.recipe_list)
        left.setLayout(left_layout)

        # Right: tabs
        right_tabs = QTabWidget()
        right_tabs.setTabPosition(QTabWidget.West)

        # Suggestions tab
        suggest_tab = QWidget()
        suggest_layout = QVBoxLayout()
        self.suggest_results = QListWidget()
        self.suggest_results.itemClicked.connect(self._on_suggest_item_clicked)
        self.suggest_ideas = QTextEdit()
        self.suggest_ideas.setReadOnly(True)
        suggest_layout.addWidget(QLabel("Suggested Recipes"))
        suggest_layout.addWidget(self.suggest_results)
        suggest_layout.addWidget(QLabel("Creative Ideas / Substitutions"))
        suggest_layout.addWidget(self.suggest_ideas)
        suggest_tab.setLayout(suggest_layout)

        # Details tab
        details_tab = QWidget()
        details_layout = QVBoxLayout()
        self.title_label = QLabel("")
        self.meta_label = QLabel("")
        self.ingredients_text = QTextEdit()
        self.ingredients_text.setReadOnly(True)
        self.steps_text = QTextEdit()
        self.steps_text.setReadOnly(True)
        # Notes area
        self.notes_text = QTextEdit()
        self.notes_text.setPlaceholderText("Personal notes for this recipe...")
        save_notes_btn = QPushButton("Save Notes")
        save_notes_btn.clicked.connect(self._save_notes)
        fav_btn = QPushButton("Toggle Favorite")
        fav_btn.clicked.connect(self._toggle_favorite)
        add_missing_btn = QPushButton("Add Missing Ingredients to Grocery")
        add_missing_btn.clicked.connect(self._add_missing_to_grocery)

        details_layout.addWidget(self.title_label)
        details_layout.addWidget(self.meta_label)
        details_layout.addWidget(QLabel("Ingredients"))
        details_layout.addWidget(self.ingredients_text)
        details_layout.addWidget(QLabel("Steps"))
        details_layout.addWidget(self.steps_text)
        details_layout.addWidget(QLabel("Notes"))
        details_layout.addWidget(self.notes_text)
        details_layout.addWidget(save_notes_btn)
        details_layout.addWidget(add_missing_btn)
        details_layout.addWidget(fav_btn)
        details_tab.setLayout(details_layout)

        # Chat tab
        chat_tab = QWidget()
        chat_layout = QVBoxLayout()
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        chat_input_row = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask for cooking tips, substitutions, or guidance...")
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self._send_chat)
        chat_input_row.addWidget(self.chat_input)
        chat_input_row.addWidget(send_btn)
        chat_layout.addWidget(self.chat_history)
        chat_layout.addLayout(chat_input_row)
        chat_tab.setLayout(chat_layout)

        # Grocery tab
        grocery_tab = QWidget()
        grocery_layout = QVBoxLayout()
        self.grocery_list = QListWidget()
        self.grocery_list.itemChanged.connect(self._grocery_item_changed)
        self.grocery_input = QLineEdit()
        self.grocery_input.setPlaceholderText("Add grocery item...")
        gro_row = QHBoxLayout()
        gro_add = QPushButton("Add")
        gro_add.clicked.connect(self._grocery_add)
        gro_clear = QPushButton("Clear")
        gro_clear.clicked.connect(self._grocery_clear)
        gro_export = QPushButton("Export List")
        gro_export.clicked.connect(self._grocery_export)
        gro_row.addWidget(self.grocery_input)
        gro_row.addWidget(gro_add)
        gro_row.addWidget(gro_clear)
        gro_row.addWidget(gro_export)
        grocery_layout.addWidget(self.grocery_list)
        grocery_layout.addLayout(gro_row)
        grocery_tab.setLayout(grocery_layout)

        # Cooking Mode tab
        cooking_tab = QWidget()
        cooking_layout = QVBoxLayout()
        self.cook_step_label = QLabel("Select a recipe to start cooking mode.")
        self.cook_step_label.setWordWrap(True)
        self.cook_step_label.setStyleSheet("font-size: 18px;")
        self.cook_progress = QProgressBar()
        cook_row = QHBoxLayout()
        prev_btn = QPushButton("Previous Step")
        next_btn = QPushButton("Next Step")
        ask_ai_btn = QPushButton("Ask AI about this Step")
        prev_btn.clicked.connect(self._prev_step)
        next_btn.clicked.connect(self._next_step)
        ask_ai_btn.clicked.connect(self._ask_ai_about_step)
        cook_row.addWidget(prev_btn)
        cook_row.addWidget(next_btn)
        cook_row.addWidget(ask_ai_btn)
        cooking_layout.addWidget(self.cook_step_label)
        cooking_layout.addWidget(self.cook_progress)
        cooking_layout.addLayout(cook_row)
        cooking_tab.setLayout(cooking_layout)

        right_tabs.addTab(suggest_tab, "Suggestions")
        right_tabs.addTab(details_tab, "Recipe Details")
        right_tabs.addTab(chat_tab, "AI Assistant")
        right_tabs.addTab(grocery_tab, "Grocery List")
        right_tabs.addTab(cooking_tab, "Cooking Mode")

        splitter.addWidget(left)
        splitter.addWidget(right_tabs)
        splitter.setStretchFactor(0, 35)
        splitter.setStretchFactor(1, 65)
        root.addWidget(splitter)

        self.setLayout(root)
        self._load_grocery()
        self._enter_cooking_mode(None)

    # Data helpers
    def _load_recipes(self) -> None:
        self.recipe_list.clear()
        query = self.search_box.text().strip()
        # Base list
        if self.fav_only.isChecked():
            recipes = db.list_favorites()
            # Optionally re-filter by query on title/ingredients
            if query:
                q = query.lower()
                recipes = [
                    r for r in recipes
                    if q in (r.get("title", "").lower()) or q in (r.get("ingredients_text", "").lower())
                ]
        else:
            recipes = db.list_recipes(query if query else None)
        # Difficulty filter
        diff = self.diff_filter.currentText() if hasattr(self, 'diff_filter') else "All"
        if diff and diff != "All":
            recipes = [r for r in recipes if (r.get("difficulty") or "") == diff]
        # Time filter
        max_time = self.time_filter.value() if hasattr(self, 'time_filter') else 0
        if max_time and max_time > 0:
            recipes = [r for r in recipes if (r.get("cook_time") or 0) <= max_time]
        for r in recipes:
            title = r.get("title", "Untitled")
            item = QListWidgetItem(title)
            # thumbnail
            img = (r.get("image_path") or "").strip()
            if img and os.path.exists(img):
                icon = QIcon(QPixmap(img).scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                item.setIcon(icon)
            item.setToolTip(f"{title}\nTime: {r.get('cook_time') or '-'} min\nDifficulty: {r.get('difficulty') or '-'}")
            item.setData(Qt.UserRole, r)
            self.recipe_list.addItem(item)

    def _on_select_recipe(self) -> None:
        items = self.recipe_list.selectedItems()
        if not items:
            return
        data: Dict[str, Any] = items[0].data(Qt.UserRole)
        self._show_recipe(data)

    def _show_recipe(self, r: Dict[str, Any]) -> None:
        title = r.get("title", "")
        cook_time = r.get("cook_time")
        difficulty = r.get("difficulty")
        self.title_label.setText(f"<h2>{title}</h2>")
        meta = []
        if cook_time:
            meta.append(f"⏱️ {cook_time} min")
        if difficulty:
            meta.append(f"• {difficulty}")
        self.meta_label.setText(" ".join(meta))
        self.ingredients_text.setText(r.get("ingredients_text", ""))
        self.steps_text.setText(r.get("steps_text", ""))
        # Load notes
        rid = r.get("id")
        if isinstance(rid, int):
            self.notes_text.setText(db.get_recipe_notes(rid))
        # Prepare cooking mode
        self._enter_cooking_mode(r)

    def _toggle_favorite(self) -> None:
        items = self.recipe_list.selectedItems()
        if not items:
            return
        r: Dict[str, Any] = items[0].data(Qt.UserRole)
        rid = r.get("id")
        if not isinstance(rid, int):
            return
        current = r.get("is_favorite", 0) == 1
        db.set_favorite(rid, not current)
        # refresh list selection to update data record
        self._load_recipes()

    def _add_missing_to_grocery(self) -> None:
        items = self.recipe_list.selectedItems()
        if not items:
            QMessageBox.information(self, "Info", "Select a recipe first.")
            return
        r: Dict[str, Any] = items[0].data(Qt.UserRole)
        rid = r.get("id")
        if not isinstance(rid, int):
            return
        missing = db.add_missing_to_grocery(rid)
        if not missing:
            QMessageBox.information(self, "Grocery", "You have everything needed!")
        else:
            QMessageBox.information(self, "Grocery", f"Added missing items: {', '.join(missing)}")
        self._load_grocery()

    def _load_grocery(self) -> None:
        self.grocery_list.clear()
        for item in db.list_grocery():
            li = QListWidgetItem(item.get("name", ""))
            li.setData(Qt.UserRole, item)
            self.grocery_list.addItem(li)

    def _grocery_add(self) -> None:
        name = self.grocery_input.text().strip()
        if not name:
            return
        db.add_grocery_item(name)
        self.grocery_input.clear()
        self._load_grocery()

    def _grocery_clear(self) -> None:
        db.clear_grocery()
        self._load_grocery()

    def _grocery_export(self) -> None:
        text = db.export_grocery_text()
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Grocery", "Copied grocery list to clipboard.")

    def _grocery_item_changed(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.UserRole)
        if not isinstance(data, dict):
            return
        item_id = data.get("id")
        if not isinstance(item_id, int):
            return
        checked = item.checkState() == Qt.Checked
        db.set_grocery_checked(item_id, checked)

    def _ai_suggest(self) -> None:
        raw = self.ingredients_box.text().strip()
        ingredients = [s.strip() for s in raw.split(',') if s.strip()]
        local = db.list_recipes()
        result = suggest_recipes_from_ingredients(ingredients, local)
        matches: List[int] = result.get("matches", [])
        creative: List[str] = result.get("creative_suggestions", [])
        subs = result.get("substitutions", {})

        # Highlight matched recipes at the top
        if matches:
            self.search_box.setText("")
            self.recipe_list.clear()
            matched = [r for r in local if r.get("id") in matches]
            others = [r for r in local if r.get("id") not in matches]
            for r in matched + others:
                item = QListWidgetItem(r.get("title", "Untitled"))
                item.setData(Qt.UserRole, r)
                self.recipe_list.addItem(item)

        # Show AI summary in chat and list view
        summary_lines: List[str] = []
        if matches:
            summary_lines.append("Matched recipes: " + ", ".join([str(m) for m in matches]))
            # populate suggestions list with matched recipes
            self.suggest_results.clear()
            title_map = {r.get("id"): r.get("title", "") for r in local}
            for rid in matches:
                t = title_map.get(rid, f"Recipe {rid}")
                it = QListWidgetItem(t)
                it.setData(Qt.UserRole, {"id": rid})
                self.suggest_results.addItem(it)
        if creative:
            summary_lines.append("Ideas: " + ", ".join(creative))
            self.suggest_ideas.setPlainText("\n".join(creative))
        if subs:
            summary_lines.append("Substitutions:")
            for k, v in subs.items():
                summary_lines.append(f"- {k}: {v}")
        if summary_lines:
            self.chat_history.append("\n".join(summary_lines))

    def _on_suggest_item_clicked(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.UserRole)
        if not isinstance(data, dict):
            return
        rid = data.get("id")
        if not isinstance(rid, int):
            return
        r = db.get_recipe(rid)
        if r:
            self._show_recipe(r)

    def _send_chat(self) -> None:
        user_msg = self.chat_input.text().strip()
        if not user_msg:
            return
        # Attach current recipe context if selected
        context = None
        items = self.recipe_list.selectedItems()
        if items:
            context = items[0].data(Qt.UserRole)
        self._append_chat("user", user_msg)
        reply = chatbot_reply(user_msg, context=context)
        self._append_chat("assistant", reply)
        self.chat_input.clear()

    def _append_chat(self, role: str, text: str) -> None:
        if role == "user":
            html = f'<div style="text-align:right;color:#0b6bcb;"><b>You:</b> {text}</div>'
        else:
            html = f'<div style="text-align:left;color:#0a7b62;"><b>HomeChef:</b> {text}</div>'
        self.chat_history.append(html)

    def _enter_cooking_mode(self, recipe: Optional[Dict[str, Any]]) -> None:
        self._cook_steps: List[str] = []
        self._cook_index: int = 0
        if not recipe:
            self.cook_step_label.setText("Select a recipe to start cooking mode.")
            self.cook_progress.setRange(0, 1)
            self.cook_progress.setValue(0)
            return
        steps_raw = recipe.get("steps_text") or ""
        self._cook_steps = [s.strip() for s in steps_raw.splitlines() if s.strip()]
        self._cook_index = 0
        self._update_cooking_view()

    def _update_cooking_view(self) -> None:
        total = max(1, len(self._cook_steps))
        self.cook_progress.setRange(0, total)
        self.cook_progress.setValue(min(self._cook_index + 1, total))
        if self._cook_steps:
            step_txt = self._cook_steps[self._cook_index]
            self.cook_step_label.setText(step_txt)
        else:
            self.cook_step_label.setText("No steps.")

    def _prev_step(self) -> None:
        if not self._cook_steps:
            return
        self._cook_index = max(0, self._cook_index - 1)
        self._update_cooking_view()

    def _next_step(self) -> None:
        if not self._cook_steps:
            return
        self._cook_index = min(len(self._cook_steps) - 1, self._cook_index + 1)
        self._update_cooking_view()

    def _ask_ai_about_step(self) -> None:
        if not self._cook_steps:
            return
        msg = f"Question about step: {self._cook_steps[self._cook_index]}"
        self.chat_input.setText(msg)
        self._send_chat()

    def _save_notes(self) -> None:
        items = self.recipe_list.selectedItems()
        if not items:
            return
        r: Dict[str, Any] = items[0].data(Qt.UserRole)
        rid = r.get("id")
        if not isinstance(rid, int):
            return
        db.set_recipe_notes(rid, self.notes_text.toPlainText())
        QMessageBox.information(self, "Notes", "Notes saved.")

    def _apply_theme(self, dark: bool) -> None:
        app = QApplication.instance()
        if not app:
            return
        if not dark:
            # Light theme
            app.setStyleSheet(
                """
                QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
                QLineEdit, QTextEdit, QComboBox, QListWidget { background: #ffffff; }
                QPushButton { background: #0b6bcb; color: white; border: none; padding: 6px 10px; border-radius: 4px; }
                QPushButton:hover { background: #0a60b4; }
                QTabWidget::pane { border: 1px solid #e0e0e0; }
                QTabBar::tab { padding: 8px 12px; }
                QProgressBar { border: 1px solid #c0c0c0; border-radius: 3px; text-align: center; }
                QProgressBar::chunk { background-color: #0a7b62; }
                """
            )
        else:
            # Dark theme
            app.setStyleSheet(
                """
                QWidget { background: #202124; color: #e8eaed; font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
                QLineEdit, QTextEdit, QComboBox, QListWidget { background: #303134; color: #e8eaed; border: 1px solid #3c4043; }
                QPushButton { background: #1a73e8; color: #fff; border: none; padding: 6px 10px; border-radius: 4px; }
                QPushButton:hover { background: #1967d2; }
                QTabWidget::pane { border: 1px solid #3c4043; }
                QTabBar::tab { padding: 8px 12px; }
                QProgressBar { border: 1px solid #3c4043; border-radius: 3px; text-align: center; }
                QProgressBar::chunk { background-color: #34a853; }
                """
            )


class AddRecipeDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Recipe")
        self.title_edit = QLineEdit()
        self.ing_edit = QTextEdit()
        self.steps_edit = QTextEdit()
        self.time_spin = QSpinBox()
        self.time_spin.setRange(0, 1000)
        self.time_spin.setSuffix(" min")
        self.diff_combo = QComboBox()
        self.diff_combo.addItems(["", "Easy", "Medium", "Hard"])
        self.image_edit = QLineEdit()
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_image)

        form = QFormLayout()
        form.addRow("Title", self.title_edit)
        form.addRow("Ingredients (one per line)", self.ing_edit)
        form.addRow("Steps (one per line)", self.steps_edit)
        form.addRow("Cook Time", self.time_spin)
        form.addRow("Difficulty", self.diff_combo)
        img_row = QHBoxLayout()
        img_row.addWidget(self.image_edit)
        img_row.addWidget(browse)
        form.addRow("Image Path (optional)", img_row)

        btn_row = QHBoxLayout()
        ok = QPushButton("Save")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(ok)
        btn_row.addWidget(cancel)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(btn_row)
        self.setLayout(layout)

    def _browse_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.image_edit.setText(path)

    def values(self) -> Dict[str, Any]:
        return {
            "title": self.title_edit.text().strip(),
            "ingredients_text": self.ing_edit.toPlainText().strip(),
            "steps_text": self.steps_edit.toPlainText().strip(),
            "cook_time": int(self.time_spin.value()) if self.time_spin.value() > 0 else None,
            "difficulty": self.diff_combo.currentText().strip() or None,
            "image_path": self.image_edit.text().strip() or None,
        }

    def is_valid(self) -> bool:
        v = self.values()
        return bool(v["title"] and v["ingredients_text"] and v["steps_text"])


def _validate_and_insert(values: Dict[str, Any]) -> int:
    return db.add_recipe(
        title=values["title"],
        ingredients_text=values["ingredients_text"],
        steps_text=values["steps_text"],
        cook_time=values.get("cook_time"),
        difficulty=values.get("difficulty"),
        image_path=values.get("image_path"),
    )


def _find_item_by_id(widget: QListWidget, rid: int) -> QListWidgetItem | None:
    for i in range(widget.count()):
        it = widget.item(i)
        data = it.data(Qt.UserRole)
        if isinstance(data, dict) and data.get("id") == rid:
            return it
    return None


def _select_item(widget: QListWidget, item: QListWidgetItem) -> None:
    widget.setCurrentItem(item)


def _warn(parent: QWidget, text: str) -> None:
    QMessageBox.warning(parent, "Warning", text)


def _info(parent: QWidget, text: str) -> None:
    QMessageBox.information(parent, "Info", text)


def _error(parent: QWidget, text: str) -> None:
    QMessageBox.critical(parent, "Error", text)


def _success(parent: QWidget, text: str) -> None:
    QMessageBox.information(parent, "Success", text)


def _scroll_to_top(widget: QListWidget) -> None:
    if widget.count() > 0:
        widget.scrollToItem(widget.item(0))


def _scroll_to_item(widget: QListWidget, item: QListWidgetItem) -> None:
    widget.scrollToItem(item)


def _refresh_list_and_select(widget: QListWidget, load_fn, rid: int) -> None:
    load_fn()
    it = _find_item_by_id(widget, rid)
    if it is not None:
        _select_item(widget, it)
        _scroll_to_item(widget, it)


def _is_ok(result: int) -> bool:
    return result == QDialog.Accepted


def _not_ok(result: int) -> bool:
    return not _is_ok(result)


def _open_add_recipe(self: HomeChefWidget) -> None:
    dlg = AddRecipeDialog(self)
    res = dlg.exec()
    if _not_ok(res):
        return
    if not dlg.is_valid():
        _warn(self, "Please fill Title, Ingredients, and Steps.")
        return
    try:
        values = dlg.values()
        rid = _validate_and_insert(values)
        _success(self, "Recipe added.")
        _refresh_list_and_select(self.recipe_list, self._load_recipes, rid)
    except Exception as e:
        _error(self, f"Failed to add recipe: {e}")

# bind as method
HomeChefWidget._open_add_recipe = _open_add_recipe


