from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPen
from PyQt6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from redcord.services.art_service import ART_TYPES, CANVAS_PRESETS, ArtSaveRequest, ArtService
from redcord.storage.sqlite_store import SQLiteStore


class BoCLiteCanvas(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ArtCanvas")
        self.setMinimumSize(540, 380)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image = QImage(1280, 800, QImage.Format.Format_RGB32)
        self.image.fill(QColor("#ffffff"))
        self.tool = "brush"
        self.color = QColor("#111111")
        self.brush_width = 6
        self.show_grid = True
        self._history: list[QImage] = []
        self._drawing = False
        self._last_pos = QPoint()
        self._start_pos = QPoint()
        self._preview_pos = QPoint()

    def set_tool(self, tool: str) -> None:
        self.tool = tool

    def set_color(self, color: QColor) -> None:
        if color.isValid():
            self.color = color

    def set_brush_width(self, width: int) -> None:
        self.brush_width = max(1, int(width))

    def set_canvas_size(self, width: int, height: int) -> None:
        self._push_history()
        self.image = QImage(max(64, int(width)), max(64, int(height)), QImage.Format.Format_RGB32)
        self.image.fill(QColor("#ffffff"))
        self.update()
        self.changed.emit()

    def clear_canvas(self) -> None:
        self._push_history()
        self.image.fill(QColor("#ffffff"))
        self.update()
        self.changed.emit()

    def toggle_grid(self) -> bool:
        self.show_grid = not self.show_grid
        self.update()
        return self.show_grid

    def undo(self) -> None:
        if not self._history:
            return
        self.image = self._history.pop()
        self.update()
        self.changed.emit()

    def load_image(self, path: str | Path) -> bool:
        image = QImage(str(path))
        if image.isNull():
            return False
        self._push_history()
        self.image = image.convertToFormat(QImage.Format.Format_RGB32)
        self.update()
        self.changed.emit()
        return True

    def paintEvent(self, _event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#101010"))
        target = self._target_rect()
        painter.fillRect(target, QColor("#ffffff"))
        painter.drawImage(target, self.image)
        if self.show_grid:
            self._draw_grid(painter, target)
        if self._drawing and self.tool in {"line", "rect", "ellipse"}:
            pen = QPen(self.color, self.brush_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            preview = QRect(self._to_widget_pos(self._start_pos), self._to_widget_pos(self._preview_pos)).normalized()
            if self.tool == "line":
                painter.drawLine(self._to_widget_pos(self._start_pos), self._to_widget_pos(self._preview_pos))
            elif self.tool == "rect":
                painter.drawRect(preview)
            else:
                painter.drawEllipse(preview)

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = self._to_image_pos(event.position().toPoint())
        if pos is None:
            return
        self._push_history()
        if self.tool == "fill":
            self.image.fill(self.color)
            self.update()
            self.changed.emit()
            return
        self._drawing = True
        self._last_pos = pos
        self._start_pos = pos
        self._preview_pos = pos
        if self.tool in {"brush", "eraser"}:
            self._draw_line(pos, pos)

    def mouseMoveEvent(self, event) -> None:  # noqa: ANN001
        if not self._drawing:
            return
        pos = self._to_image_pos(event.position().toPoint())
        if pos is None:
            return
        self._preview_pos = pos
        if self.tool in {"brush", "eraser"}:
            self._draw_line(self._last_pos, pos)
            self._last_pos = pos
            self.changed.emit()
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
        if event.button() != Qt.MouseButton.LeftButton or not self._drawing:
            return
        pos = self._to_image_pos(event.position().toPoint()) or self._preview_pos
        if self.tool in {"line", "rect", "ellipse"}:
            self._draw_shape(self._start_pos, pos)
        self._drawing = False
        self.update()
        self.changed.emit()

    def _push_history(self) -> None:
        self._history.append(self.image.copy())
        if len(self._history) > 30:
            self._history.pop(0)

    def _draw_line(self, start: QPoint, end: QPoint) -> None:
        painter = QPainter(self.image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#ffffff") if self.tool == "eraser" else self.color
        painter.setPen(QPen(color, self.brush_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawLine(start, end)
        painter.end()

    def _draw_shape(self, start: QPoint, end: QPoint) -> None:
        painter = QPainter(self.image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self.color, self.brush_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        rect = QRect(start, end).normalized()
        if self.tool == "line":
            painter.drawLine(start, end)
        elif self.tool == "rect":
            painter.drawRect(rect)
        elif self.tool == "ellipse":
            painter.drawEllipse(rect)
        painter.end()

    def _draw_grid(self, painter: QPainter, target: QRect) -> None:
        if target.isNull():
            return
        painter.save()
        painter.setPen(QPen(QColor(185, 54, 73, 115), 1, Qt.PenStyle.DashLine))
        for fraction in (1 / 3, 2 / 3):
            x = target.left() + int(target.width() * fraction)
            y = target.top() + int(target.height() * fraction)
            painter.drawLine(x, target.top(), x, target.bottom())
            painter.drawLine(target.left(), y, target.right(), y)
        painter.restore()

    def _target_rect(self) -> QRect:
        margin = 18
        available = self.rect().adjusted(margin, margin, -margin, -margin)
        if available.width() <= 0 or available.height() <= 0:
            return QRect()
        scale = min(available.width() / self.image.width(), available.height() / self.image.height())
        width = int(self.image.width() * scale)
        height = int(self.image.height() * scale)
        x = available.x() + (available.width() - width) // 2
        y = available.y() + (available.height() - height) // 2
        return QRect(x, y, width, height)

    def _to_image_pos(self, pos: QPoint) -> QPoint | None:
        target = self._target_rect()
        if not target.contains(pos) or target.width() <= 0 or target.height() <= 0:
            return None
        x = int((pos.x() - target.x()) * self.image.width() / target.width())
        y = int((pos.y() - target.y()) * self.image.height() / target.height())
        return QPoint(max(0, min(self.image.width() - 1, x)), max(0, min(self.image.height() - 1, y)))

    def _to_widget_pos(self, pos: QPoint) -> QPoint:
        target = self._target_rect()
        x = target.x() + int(pos.x() * target.width() / self.image.width())
        y = target.y() + int(pos.y() * target.height() / self.image.height())
        return QPoint(x, y)


class ArtStudioTab(QWidget):
    def __init__(
        self,
        store: SQLiteStore,
        get_project_id: Callable[[], str | None],
        set_status: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.store = store
        self.service = ArtService(store)
        self.get_project_id = get_project_id
        self.set_status = set_status
        self.current_asset_id: str | None = None
        self._loading = False
        self._dirty = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        left = QFrame()
        left.setObjectName("Panel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)

        title = QLabel("Арты и обложки")
        title.setObjectName("TitleLabel")
        left_layout.addWidget(title)
        self.type_filter = QComboBox()
        self.type_filter.addItem("Все разделы", "")
        for key, label in ART_TYPES:
            self.type_filter.addItem(label, key)
        self.type_filter.currentIndexChanged.connect(self.reload_assets)
        left_layout.addWidget(self.type_filter)

        self.asset_list = QListWidget()
        self.asset_list.setObjectName("CompactList")
        self.asset_list.currentItemChanged.connect(self.on_asset_selected)
        left_layout.addWidget(self.asset_list, 1)

        buttons = QGridLayout()
        self.new_btn = QPushButton("Новый")
        self.save_btn = QPushButton("Сохранить")
        self.delete_btn = QPushButton("Удалить")
        self.export_btn = QPushButton("Экспорт PNG")
        for index, button in enumerate([self.new_btn, self.save_btn, self.delete_btn, self.export_btn]):
            buttons.addWidget(button, index // 2, index % 2)
        left_layout.addLayout(buttons)

        meta = QFrame()
        meta.setObjectName("Panel")
        meta_layout = QVBoxLayout(meta)
        meta_layout.setContentsMargins(8, 8, 8, 8)
        meta_layout.setSpacing(6)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Название арта")
        self.art_type_combo = QComboBox()
        for key, label in ART_TYPES:
            self.art_type_combo.addItem(label, key)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(118)
        self.notes_edit.setPlaceholderText("Референсы, стиль, идея обложки, палитра.")
        meta_layout.addWidget(QLabel("Название"))
        meta_layout.addWidget(self.title_edit)
        meta_layout.addWidget(QLabel("Раздел"))
        meta_layout.addWidget(self.art_type_combo)
        meta_layout.addWidget(QLabel("Заметки"))
        meta_layout.addWidget(self.notes_edit)
        left_layout.addWidget(meta)

        center = QFrame()
        center.setObjectName("Panel")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(8, 8, 8, 8)
        center_layout.setSpacing(6)

        tools = QHBoxLayout()
        self.tool_buttons: dict[str, QPushButton] = {}
        for tool, label in [
            ("brush", "Кисть"),
            ("eraser", "Ластик"),
            ("fill", "Заливка"),
            ("line", "Линия"),
            ("rect", "Рамка"),
            ("ellipse", "Эллипс"),
        ]:
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, value=tool: self.set_tool(value))
            self.tool_buttons[tool] = button
            tools.addWidget(button)
        self.tool_buttons["brush"].setChecked(True)
        self.color_btn = QPushButton("Цвет")
        self.color_btn.clicked.connect(self.pick_color)
        tools.addWidget(self.color_btn)
        tools.addWidget(QLabel("Размер"))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(1, 64)
        self.size_slider.setValue(6)
        self.size_slider.setMaximumWidth(130)
        self.size_slider.valueChanged.connect(self.set_brush_width)
        tools.addWidget(self.size_slider)
        self.grid_btn = QPushButton("Сетка")
        self.grid_btn.setCheckable(True)
        self.grid_btn.setChecked(True)
        self.grid_btn.clicked.connect(self.toggle_grid)
        self.undo_btn = QPushButton("Undo")
        self.clear_btn = QPushButton("Очистить")
        self.import_image_btn = QPushButton("Импорт")
        self.undo_btn.clicked.connect(self.undo)
        self.clear_btn.clicked.connect(self.clear_canvas)
        self.import_image_btn.clicked.connect(self.import_image)
        for button in [self.grid_btn, self.undo_btn, self.clear_btn, self.import_image_btn]:
            tools.addWidget(button)
        tools.addStretch(1)
        center_layout.addLayout(tools)

        presets = QHBoxLayout()
        presets.addWidget(QLabel("Холст"))
        self.preset_combo = QComboBox()
        for key, label, width, height in CANVAS_PRESETS:
            self.preset_combo.addItem(f"{label} ({width}x{height})", (width, height, key))
        self.apply_preset_btn = QPushButton("Применить размер")
        self.apply_preset_btn.clicked.connect(self.apply_canvas_preset)
        presets.addWidget(self.preset_combo)
        presets.addWidget(self.apply_preset_btn)
        presets.addStretch(1)
        self.canvas_info = QLabel("1280x800")
        self.canvas_info.setObjectName("MutedLabel")
        presets.addWidget(self.canvas_info)
        center_layout.addLayout(presets)

        self.canvas = BoCLiteCanvas()
        self.canvas.changed.connect(self.mark_dirty)
        center_layout.addWidget(self.canvas, 1)

        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.setSizes([315, 980])

        self.new_btn.clicked.connect(self.new_art)
        self.save_btn.clicked.connect(self.save_art)
        self.delete_btn.clicked.connect(self.delete_art)
        self.export_btn.clicked.connect(self.export_art)
        self.title_edit.textChanged.connect(self.mark_dirty)
        self.notes_edit.textChanged.connect(self.mark_dirty)
        self.art_type_combo.currentIndexChanged.connect(self.mark_dirty)
        self._sync_color_button()

    def reload_assets(self) -> None:
        current_project = self.get_project_id()
        self.asset_list.blockSignals(True)
        self.asset_list.clear()
        if current_project:
            art_type = str(self.type_filter.currentData() or "")
            for asset in self.store.list_art_assets(current_project, art_type or None):
                label = dict(ART_TYPES).get(asset.art_type, asset.art_type)
                item = QListWidgetItem(f"{asset.title} [{label}]")
                item.setData(256, asset.id)
                self.asset_list.addItem(item)
        self.asset_list.blockSignals(False)

    def on_asset_selected(self, current: QListWidgetItem | None = None, _previous: QListWidgetItem | None = None) -> None:
        item = current or self.asset_list.currentItem()
        if not item:
            return
        asset = self.store.get_art_asset(str(item.data(256)))
        if not asset:
            return
        self._loading = True
        self.current_asset_id = asset.id
        self.title_edit.setText(asset.title)
        self._set_combo_value(self.art_type_combo, asset.art_type)
        self.notes_edit.setPlainText(asset.notes)
        if asset.file_path and Path(asset.file_path).exists():
            self.canvas.load_image(asset.file_path)
            self._update_canvas_info()
        self._loading = False
        self._dirty = False

    def new_art(self) -> None:
        self.current_asset_id = None
        self.title_edit.setText("Новый арт")
        self.notes_edit.clear()
        self._set_combo_value(self.art_type_combo, "concept_art")
        self.apply_canvas_preset()
        self._dirty = False
        self.set_status("BoC Lite: новый холст")

    def save_art(self) -> None:
        project_id = self.get_project_id()
        if not project_id:
            QMessageBox.information(self, "BoC Lite", "Сначала выберите или создайте проект.")
            return
        try:
            asset = self.service.save_asset(
                ArtSaveRequest(
                    project_id=project_id,
                    title=self.title_edit.text(),
                    art_type=str(self.art_type_combo.currentData() or "concept_art"),
                    notes=self.notes_edit.toPlainText(),
                    image=self.canvas.image,
                    asset_id=self.current_asset_id,
                )
            )
        except OSError as exc:
            QMessageBox.warning(self, "BoC Lite", str(exc))
            return
        self.current_asset_id = asset.id
        self._dirty = False
        self.reload_assets()
        self._select_asset(asset.id)
        self.set_status(f"BoC Lite: сохранено {asset.title}")

    def delete_art(self) -> None:
        if not self.current_asset_id:
            return
        if QMessageBox.question(self, "BoC Lite", "Удалить выбранный арт из списка? PNG-файл останется в data/art_assets.") != QMessageBox.StandardButton.Yes:
            return
        self.store.delete_art_asset(self.current_asset_id)
        self.current_asset_id = None
        self.reload_assets()
        self.new_art()

    def export_art(self) -> None:
        default_name = self.service.unique_export_name(self.title_edit.text())
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт PNG", str(Path.home() / f"{default_name}.png"), "PNG (*.png)")
        if not path:
            return
        try:
            target = self.service.export_png(self.canvas.image, path)
        except OSError as exc:
            QMessageBox.warning(self, "BoC Lite", str(exc))
            return
        self.set_status(f"BoC Lite: PNG экспортирован {target}")

    def import_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Импорт изображения", str(Path.home()), "Images (*.png *.jpg *.jpeg *.bmp)")
        if path and not self.canvas.load_image(path):
            QMessageBox.warning(self, "BoC Lite", "Не удалось открыть изображение.")
        self._update_canvas_info()

    def set_tool(self, tool: str) -> None:
        self.canvas.set_tool(tool)
        for key, button in self.tool_buttons.items():
            button.setChecked(key == tool)
        self.set_status(f"BoC Lite: {self.tool_buttons[tool].text()}")

    def pick_color(self) -> None:
        color = QColorDialog.getColor(self.canvas.color, self, "Цвет кисти")
        if color.isValid():
            self.canvas.set_color(color)
            self._sync_color_button()

    def set_brush_width(self, width: int) -> None:
        self.canvas.set_brush_width(width)

    def apply_canvas_preset(self) -> None:
        width, height, key = self.preset_combo.currentData()
        self.canvas.set_canvas_size(int(width), int(height))
        if key in {"book_cover", "comic_cover", "manga_cover"}:
            self._set_combo_value(self.art_type_combo, key)
        self._update_canvas_info()
        self.set_status(f"BoC Lite: холст {width}x{height}")

    def toggle_grid(self) -> None:
        visible = self.canvas.toggle_grid()
        self.grid_btn.setChecked(visible)
        self.set_status("BoC Lite: сетка включена" if visible else "BoC Lite: сетка выключена")

    def clear_canvas(self) -> None:
        self.canvas.clear_canvas()
        self.set_status("BoC Lite: холст очищен")

    def undo(self) -> None:
        self.canvas.undo()
        self._update_canvas_info()
        self.set_status("BoC Lite: undo")

    def mark_dirty(self, *_args: object) -> None:
        if not self._loading:
            self._dirty = True
            self._update_canvas_info()

    def _update_canvas_info(self) -> None:
        self.canvas_info.setText(f"{self.canvas.image.width()}x{self.canvas.image.height()}")

    def _sync_color_button(self) -> None:
        self.color_btn.setStyleSheet(f"background: {self.canvas.color.name()}; color: #ffffff;")

    def _select_asset(self, asset_id: str) -> None:
        for row in range(self.asset_list.count()):
            if self.asset_list.item(row).data(256) == asset_id:
                self.asset_list.setCurrentRow(row)
                return

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return
