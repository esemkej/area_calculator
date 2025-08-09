from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QLabel,
    QHBoxLayout, QVBoxLayout, QSlider, QCheckBox, QFileDialog, QScrollArea,
    QShortcut, QSizePolicy, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QTimer, QSettings, QStandardPaths, QEvent
from PyQt5.QtGui import QPixmap, QKeySequence, QImage
from os import path
import sys, numpy as np, cv2

class SoilErosionUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Area Calculator")
        self.setGeometry(100, 100, 1280, 720)

        # Variables
        self.settings = QSettings("esemkej", "Area Calculator")
        self.qimage = None
        self.picked_color = None
        self.tool_mode = None
        self.debug = True
        self.sensitivity = 100
        self.anchors = []
        self.temp_mouse_pos = None
        self.first_plot_point = True
        self.point_distance = 10  # Distance from which a click counts as an anchor click
        self.hovered_anchor_index = None
        self.strict_sensitivity = 5
        self.polygon_closed = False

        # Repaint throttles
        self.repaint_timer = QTimer(self)
        self.repaint_timer.setSingleShot(True)
        self.repaint_timer.timeout.connect(self.update_final_image)

        # Live preview throttle for manual patch dialog
        self.manual_preview_timer = QTimer(self)
        self.manual_preview_timer.setSingleShot(True)
        self.manual_preview_timer.timeout.connect(self.update_final_image)

        # Persistent UI vars
        self.line_width = int(self.settings.value("var/line_width", 2))
        self.preview_line_width = int(self.settings.value("var/preview_line_width", 1))
        self.anchor_radius = int(self.settings.value("var/anchor_radius", 4))

        app = QApplication.instance()
        self.text_size = int(self.settings.value("ui/text_size", app.font().pointSize() or 8))

        # Manual patches
        self.manual_patches = []
        self.manual_pick_radius = 10
        self.manual_preview = None

        # Font size init
        f = app.font()
        f.setPointSize(self.text_size)
        app.setFont(f)

        # === CENTRAL WIDGET ===
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # === TOP BAR ===
        top_bar = QHBoxLayout()
        self.load_button = QPushButton("Open Image")
        self.toggle_checkbox = QCheckBox("Show Highlighted Layer")
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setMinimum(0)
        self.sensitivity_slider.setMaximum(255)
        self.sensitivity_slider.setValue(self.sensitivity)
        self.sensitivity_label = QLabel(f"Sensitivity: {self.sensitivity}")

        top_bar.addWidget(self.load_button)
        top_bar.addWidget(self.toggle_checkbox)
        top_bar.addWidget(self.sensitivity_label)
        top_bar.addWidget(self.sensitivity_slider)

        # === MAIN BODY ===
        body_layout = QHBoxLayout()

        # Left tool panel
        tool_panel = QVBoxLayout()
        self.pick_color_button = QPushButton("Pick a color")
        self.plot_line_button = QPushButton("Plot a line")
        self.delete_line_button = QPushButton("Delete line")
        self.manual_mode_button = QPushButton("Manual mode")
        self.calculate_area_button = QPushButton("Calculate area")
        self.pick_color_button.setCheckable(True)
        self.plot_line_button.setCheckable(True)
        self.manual_mode_button.setCheckable(True)

        self.strict_checkbox = QCheckBox("Strict mode")
        self.strict_slider = QSlider(Qt.Horizontal)
        self.strict_slider.setMinimum(0)
        self.strict_slider.setMaximum(10)
        self.strict_slider.setValue(self.strict_sensitivity)
        self.strict_slider.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.strict_label = QLabel(f"Sensitivity: {self.strict_sensitivity}")

        self.line_checkbox = QCheckBox("Line")
        self.manual_checkbox = QCheckBox("Manual layer")

        self.line_width_label = QLabel(f"Line width: {self.line_width}")
        self.line_width_slider = QSlider(Qt.Horizontal)
        self.line_width_slider.setMinimum(1)
        self.line_width_slider.setMaximum(10)
        self.line_width_slider.setValue(self.line_width)
        self.line_width_slider.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

        self.preview_line_width_label = QLabel(f"Preview line width: {self.preview_line_width}")
        self.preview_line_width_slider = QSlider(Qt.Horizontal)
        self.preview_line_width_slider.setMinimum(1)
        self.preview_line_width_slider.setMaximum(10)
        self.preview_line_width_slider.setValue(self.preview_line_width)
        self.preview_line_width_slider.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

        self.anchor_radius_label = QLabel(f"Anchor radius: {self.anchor_radius}")
        self.anchor_radius_slider = QSlider(Qt.Horizontal)
        self.anchor_radius_slider.setMinimum(1)
        self.anchor_radius_slider.setMaximum(20)
        self.anchor_radius_slider.setValue(self.anchor_radius)
        self.anchor_radius_slider.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

        self.text_size_label = QLabel(f"Text size: {self.text_size}")
        self.text_size_slider = QSlider(Qt.Horizontal)
        self.text_size_slider.setMinimum(6)
        self.text_size_slider.setMaximum(24)
        self.text_size_slider.setValue(self.text_size)
        self.text_size_slider.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

        tool_panel.addWidget(self.pick_color_button)
        tool_panel.addWidget(self.plot_line_button)
        tool_panel.addWidget(self.delete_line_button)
        tool_panel.addWidget(self.manual_mode_button)
        tool_panel.addWidget(self.calculate_area_button)
        tool_panel.addWidget(self.strict_checkbox)
        tool_panel.addWidget(self.strict_slider)
        tool_panel.addWidget(self.strict_label)
        tool_panel.addWidget(self.line_checkbox)
        tool_panel.addWidget(self.manual_checkbox)
        tool_panel.addWidget(self.line_width_label)
        tool_panel.addWidget(self.line_width_slider)
        tool_panel.addWidget(self.preview_line_width_label)
        tool_panel.addWidget(self.preview_line_width_slider)
        tool_panel.addWidget(self.anchor_radius_label)
        tool_panel.addWidget(self.anchor_radius_slider)
        tool_panel.addWidget(self.text_size_label)
        tool_panel.addWidget(self.text_size_slider)
        self.delete_line_button.hide()
        self.strict_slider.hide()
        self.strict_label.hide()
        self.line_checkbox.hide()
        tool_panel.addStretch()

        tool_widget = QWidget()
        tool_widget.setLayout(tool_panel)

        # Image display
        self.image_label = ClickableLabel("Image will appear here")
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.mouse_moved_callback = self.mouse_moved
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.image_label)

        body_layout.addWidget(tool_widget)
        body_layout.addWidget(self.scroll_area)

        # === Assemble Layouts ===
        main_layout.addLayout(top_bar)
        main_layout.addLayout(body_layout)

        # Binds
        self.load_button.clicked.connect(self.load_image)
        self.toggle_checkbox.stateChanged.connect(self.request_repaint)
        self.sensitivity_slider.valueChanged.connect(self.update_sensitivity)
        self.pick_color_button.toggled.connect(self.pick_color)
        self.plot_line_button.toggled.connect(self.plot_line)
        self.delete_line_button.clicked.connect(self.delete_line)
        self.manual_mode_button.toggled.connect(self.manual_mode)
        self.calculate_area_button.clicked.connect(self.analyze_field)
        self.strict_checkbox.stateChanged.connect(self.strict_mode)
        self.strict_slider.valueChanged.connect(self.update_strict)
        self.line_checkbox.stateChanged.connect(self.request_repaint)
        self.manual_checkbox.stateChanged.connect(self.request_repaint)
        self.line_width_slider.valueChanged.connect(self.update_line_width)
        self.preview_line_width_slider.valueChanged.connect(self.update_preview_line_width)
        self.anchor_radius_slider.valueChanged.connect(self.update_anchor_radius)
        self.text_size_slider.sliderReleased.connect(self.update_global_font)
        self.text_size_slider.valueChanged.connect(self.update_text_size_label)

        shortcut_open = QShortcut(QKeySequence("Ctrl+O"), self)
        shortcut_open.activated.connect(self.load_image)

    # ---------- Logic ----------
    def request_repaint(self, *args, **kwargs):
        if not self.repaint_timer.isActive():
            self.repaint_timer.start(16)

    def load_image(self):
        if self.debug:
            file_path = path.join(path.dirname(__file__), "debug_image.png")
            if not path.exists(file_path):
                print("[DEBUG] debug_image.png not found")
                return
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
            )
        if file_path:
            pixmap = QPixmap(file_path)
            self.qimage = pixmap.toImage()
            self.base_rgba = self.qimage_to_array(self.qimage)
            vw = self.scroll_area.viewport().width()
            vh = self.scroll_area.viewport().height()
            self.image_label.setPixmap(
                pixmap.scaled(vw, vh, Qt.KeepAspectRatio, Qt.FastTransformation)
            )
            print(f"Loaded: {file_path}")
            self.request_repaint()

    def update_sensitivity(self, value):
        self.sensitivity = value
        self.sensitivity_label.setText(f"Sensitivity: {value}")
        if self.toggle_checkbox.isChecked():
            self.request_repaint()

    def qimage_to_array(self, qimage):
        qimg = qimage.convertToFormat(QImage.Format_RGBA8888)
        w, h = qimg.width(), qimg.height()
        ptr = qimg.bits()
        ptr.setsize(qimg.byteCount())
        arr = np.array(ptr, dtype=np.uint8).reshape((h, w, 4))
        return arr  # RGBA

    def get_color_mask(self, image_arr, target_color, tolerance):
        if image_arr.shape[2] == 4:
            image_arr = image_arr[:, :, :3]  # drop alpha
        r, g, b = target_color
        diff = np.abs(image_arr - np.array([r, g, b]))
        distance = np.sum(diff, axis=2)
        return distance <= tolerance

    def create_highlight_overlay(self, mask, highlight_color=(255, 0, 0)):
        h, w = mask.shape
        overlay = np.zeros((h, w, 4), dtype=np.uint8)
        overlay[mask] = [*highlight_color, 150]
        return overlay

    def merge_overlay_with_image(self, base_rgba, overlay_rgba):
        if base_rgba.shape[2] == 3:  # just in case
            base_rgba = np.dstack((base_rgba, np.full(base_rgba.shape[:2], 255, dtype=np.uint8)))
        zeroa = overlay_rgba[:, :, 3] == 0
        overlay_rgba[zeroa] = [0, 0, 0, 0]
        base = base_rgba.astype(np.float32)
        over = overlay_rgba.astype(np.float32)
        a = (over[:, :, 3:4] / 255.0)
        out = base * (1.0 - a) + over * a
        return out.astype(np.uint8)

    def arr_to_qpixmap(self, arr):
        h, w, _ = arr.shape
        image = QImage(arr.data, w, h, QImage.Format_RGBA8888)
        return QPixmap.fromImage(image.copy())

    def map_click_to_image_coords(self, pos):
        label_w, label_h = self.image_label.width(), self.image_label.height()
        img_w, img_h = self.qimage.width(), self.qimage.height()
        scale = min(label_w / img_w, label_h / img_h)
        disp_w, disp_h = img_w * scale, img_h * scale
        offset_x = (label_w - disp_w) / 2
        offset_y = (label_h - disp_h) / 2
        x = int((pos.x() - offset_x) / scale)
        y = int((pos.y() - offset_y) / scale)
        if 0 <= x < img_w and 0 <= y < img_h:
            return x, y
        return None

    def update_final_image(self):
        if not self.qimage:
            return

        base_arr = getattr(self, "base_rgba", self.qimage_to_array(self.qimage))
        h, w = base_arr.shape[:2]

        # --- AUTO HIGHLIGHT (global) ---
        if self.toggle_checkbox.isChecked() and self.picked_color:
            auto_mask = self.get_color_mask(base_arr, self.picked_color, self.sensitivity)
            if self.strict_checkbox.isChecked():
                level = int(round(getattr(self, "strict_sensitivity", self.strict_slider.value())))
                auto_mask = self.apply_strict_filter(auto_mask, level)
            highlight_overlay = self.create_highlight_overlay(auto_mask)  # red
        else:
            highlight_overlay = np.zeros((h, w, 4), dtype=np.uint8)

        # --- MANUAL PATCHES (blue, optional visibility) ---
        manual_mask = np.zeros((h, w), dtype=bool)
        if self.manual_checkbox.isChecked():
            manual_mask = self.recompute_manual_mask()
        manual_overlay = self.create_highlight_overlay(manual_mask, highlight_color=(0, 0, 255))

        # Combine auto + manual without alpha bleed
        combined_overlay = highlight_overlay.copy()
        manual_alpha = manual_overlay[:, :, 3] > 0
        if manual_alpha.any():
            combined_overlay[manual_alpha, 3] = np.maximum(
                combined_overlay[manual_alpha, 3],
                manual_overlay[manual_alpha, 3]
            )
            a_m = (manual_overlay[manual_alpha, 3:4] / 255.0).astype(np.float32)
            combined_overlay[manual_alpha, :3] = (
                combined_overlay[manual_alpha, :3] * (1.0 - a_m) +
                manual_overlay[manual_alpha, :3] * a_m
            ).astype(np.uint8)

        # --- LINE OVERLAY (anchors, preview) ---
        if self.line_checkbox.isChecked() and self.anchors:
            line_overlay = np.zeros((h, w, 4), dtype=np.uint8)
            lw = getattr(self, "line_width", 2)
            for i in range(1, len(self.anchors)):
                cv2.line(line_overlay, self.anchors[i - 1], self.anchors[i], (0, 255, 0, 255), lw)
            if getattr(self, "temp_mouse_pos", None):
                plw = getattr(self, "preview_line_width", 1)
                cv2.line(line_overlay, self.anchors[-1], self.temp_mouse_pos, (255, 255, 0, 255), plw)
            ar = getattr(self, "anchor_radius", 4)
            for i, (x, y) in enumerate(self.anchors):
                color = (255, 255, 0, 255) if i == self.hovered_anchor_index else (0, 255, 0, 255)
                cv2.circle(line_overlay, (x, y), int(ar), color, -1)
        else:
            line_overlay = np.zeros((h, w, 4), dtype=np.uint8)

        # Merge lines on top
        line_mask = line_overlay[:, :, 3] > 0
        if line_mask.any():
            combined_overlay[line_mask, 3] = np.maximum(
                combined_overlay[line_mask, 3],
                line_overlay[line_mask, 3]
            )
            a_line = (line_overlay[line_mask, 3:4] / 255.0).astype(np.float32)
            combined_overlay[line_mask, :3] = (
                combined_overlay[line_mask, :3] * (1.0 - a_line) +
                line_overlay[line_mask, :3] * a_line
            ).astype(np.uint8)

        # --- COMPOSITE OVER BASE ---
        final = self.merge_overlay_with_image(base_arr, combined_overlay)
        pixmap = self.arr_to_qpixmap(final)
        vw = self.scroll_area.viewport().width()
        vh = self.scroll_area.viewport().height()
        self.image_label.setPixmap(
            pixmap.scaled(vw, vh, Qt.KeepAspectRatio, Qt.FastTransformation)
        )

    def pick_color(self, checked):
        if checked:
            self.tool_mode = "color"
            self.plot_line_button.setChecked(False)
            self.manual_mode_button.setChecked(False)
            print("Click on a color you want to highlight")
        elif not checked and not self.plot_line_button.isChecked() and not self.manual_mode_button.isChecked():
            self.tool_mode = None

    def plot_line(self, checked):
        if checked:
            self.tool_mode = "plot"
            self.pick_color_button.setChecked(False)
            self.manual_mode_button.setChecked(False)
            print("Click anywhere to start plotting a line")
        elif not checked and not self.pick_color_button.isChecked() and not self.manual_mode_button.isChecked():
            self.tool_mode = None
            if not self.polygon_closed:
                self.delete_line()

    def delete_line(self):
        if self.anchors:
            self.anchors = []
            self.line_checkbox.hide()
            self.delete_line_button.hide()
            self.plot_line_button.setChecked(False)
            self.request_repaint()
            if self.polygon_closed:
                print("Line deleted")
            else:
                print("Line deleted - polygon not closed")
        else:
            print("No line drawn")

    def create_field_mask(self, shape):
        mask = np.zeros((shape[0], shape[1]), dtype=np.uint8)
        if len(self.anchors) >= 3:
            pts = np.array([self.anchors], dtype=np.int32)
            cv2.fillPoly(mask, pts, 255)
        return mask

    def apply_field_mask(self, base_arr, field_mask):
        if base_arr.shape[2] == 4:
            base_rgba = base_arr.copy()
        else:
            base_rgba = np.dstack((base_arr, np.full(base_arr.shape[:2], 255, dtype=np.uint8)))
        base_rgba[field_mask == 0] = [0, 0, 0, 0]
        return base_rgba

    def crop_to_field(self, img_with_alpha, field_mask):
        coords = cv2.findNonZero(field_mask)
        x, y, w, h = cv2.boundingRect(coords)
        return img_with_alpha[y:y+h, x:x+w], field_mask[y:y+h, x:x+w]

    def calculate_pixel_percentage(self, cropped_img, highlight_mask):
        field_pixels = np.count_nonzero(cropped_img[:, :, 3])
        colored_pixels = np.count_nonzero(highlight_mask[:, :, 3])
        percent = (colored_pixels / field_pixels) * 100 if field_pixels else 0
        return percent

    def analyze_field(self):
        if not self.qimage or len(self.anchors) < 3 or not self.polygon_closed:
            print("Image not loaded or polygon not defined/closed")
            return

        base_arr = self.base_rgba
        field_mask = self.create_field_mask(base_arr.shape[:2])
        field_only = self.apply_field_mask(base_arr, field_mask)
        cropped_img, _ = self.crop_to_field(field_only, field_mask)

        if self.picked_color:
            auto_mask = self.get_color_mask(cropped_img[:, :, :3], self.picked_color, self.sensitivity)
            if self.strict_checkbox.isChecked():
                auto_mask = self.apply_strict_filter(auto_mask, self.strict_slider.value())

            # manual mask, cropped to bbox — include only if manual layer is visible
            full_manual = self.recompute_manual_mask().astype(np.uint8) * 255 if self.manual_checkbox.isChecked() else np.zeros(base_arr.shape[:2], dtype=np.uint8)
            coords = cv2.findNonZero(field_mask)
            x, y, w, h = cv2.boundingRect(coords)
            manual_cropped = full_manual[y:y+h, x:x+w] > 0

            final_mask = np.logical_or(auto_mask, manual_cropped)
            highlight_overlay = self.create_highlight_overlay(final_mask)
            percent = self.calculate_pixel_percentage(cropped_img, highlight_overlay)
            print(f"Highlighted area: {percent:.2f}%")
        else:
            print("No color selected — can't compute highlight %")

    def strict_mode(self, checked):
        if checked:
            self.strict_slider.show()
            self.strict_label.show()
        else:
            self.strict_slider.hide()
            self.strict_label.hide()
        self.request_repaint()

    def update_strict(self, value):
        self.strict_sensitivity = value
        self.strict_label.setText(f"Sensitivity: {value}")
        if self.strict_checkbox.isChecked():
            self.request_repaint()

    def apply_strict_filter(self, mask: np.ndarray, level: int) -> np.ndarray:
        m = (mask.astype(np.uint8) > 0).astype(np.uint8)
        k = max(1, int(2 * level + 1))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        opened = cv2.morphologyEx(m, cv2.MORPH_OPEN, kernel)
        min_frac = 0.001 + 0.004 * ((level - 1) / 9.0)
        min_size = int(opened.size * min_frac)
        num, labels, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
        keep = np.zeros_like(opened, dtype=np.uint8)
        for i in range(1, num):
            if stats[i, cv2.CC_STAT_AREA] >= min_size:
                keep[labels == i] = 1
        return keep.astype(bool)

    def manual_mode(self, checked):
        if checked:
            self.tool_mode = "manual"
            self.pick_color_button.setChecked(False)
            self.plot_line_button.setChecked(False)
            print("Click on specific patches to add them manually")
        elif not checked and not self.pick_color_button.isChecked() and not self.plot_line_button.isChecked():
            self.tool_mode = None

    def update_line_width(self, value):
        self.line_width = value
        self.line_width_label.setText(f"Line width: {value}")
        self.settings.setValue("var/line_width", value)
        if (self.plot_line_button.isChecked() or self.anchors):
            self.request_repaint()

    def update_preview_line_width(self, value):
        self.preview_line_width = value
        self.preview_line_width_label.setText(f"Preview line width: {value}")
        self.settings.setValue("var/preview_line_width", value)
        if (self.plot_line_button.isChecked() or self.anchors):
            self.request_repaint()

    def update_anchor_radius(self, value):
        self.anchor_radius = value
        self.anchor_radius_label.setText(f"Anchor radius: {value}")
        self.settings.setValue("var/anchor_radius", value)
        if (self.plot_line_button.isChecked() or self.anchors):
            self.request_repaint()

    def update_global_font(self):
        app = QApplication.instance()
        f = app.font()
        f.setPointSize(self.text_size_slider.value())
        app.setFont(f)
        self.settings.setValue("ui/text_size", self.text_size_slider.value())
        self.request_repaint()

    def update_text_size_label(self, value):
        self.text_size = value
        self.text_size_label.setText(f"Text size: {value}")

    def recompute_manual_mask(self):
        h, w = self.base_rgba.shape[:2]
        acc = np.zeros((h, w), dtype=bool)
        for p in self.manual_patches:
            acc = np.logical_or(acc, p["mask"])
        if self.manual_preview is not None:
            acc = np.logical_or(acc, self.manual_preview["mask"])
        return acc

    def make_patch_mask(self, center, radius, sensitivity, strict_sensitivity):
        h, w = self.base_rgba.shape[:2]
        roi = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(roi, center, int(radius), 1, -1)

        y = np.clip(center[1], 0, h-1)
        x = np.clip(center[0], 0, w-1)
        target_rgb = tuple(int(v) for v in self.base_rgba[y, x, :3])

        color_mask = self.get_color_mask(self.base_rgba, target_rgb, int(sensitivity))
        color_mask &= roi.astype(bool)

        if strict_sensitivity and strict_sensitivity > 0:
            color_mask = self.apply_strict_filter(color_mask, int(strict_sensitivity))
        return color_mask

    def add_manual_patch(self, center):
        dlg = QDialog(self)
        dlg.setWindowTitle("Manual patch")
        lay = QVBoxLayout(dlg)

        def mk(label_text, mn, mx, val):
            lab = QLabel(f"{label_text}: {val}")
            s = QSlider(Qt.Horizontal)
            s.setMinimum(mn); s.setMaximum(mx); s.setValue(val)
            s.valueChanged.connect(lambda v, L=lab, T=label_text: L.setText(f"{T}: {v}"))
            lay.addWidget(lab); lay.addWidget(s)
            return s, lab

        # defaults
        s_radius, _ = mk("Radius", 5, 200, 30)
        s_sens,   _ = mk("Sensitivity", 0, 255, self.sensitivity)
        s_strict, _ = mk("Strict", 0, 10, 0)

        # initialize preview
        self.update_manual_preview(center, s_radius.value(), s_sens.value(), s_strict.value())

        # live update preview on slider changes
        s_radius.valueChanged.connect(lambda v: self.update_manual_preview(center, v, s_sens.value(), s_strict.value()))
        s_sens.valueChanged.connect(  lambda v: self.update_manual_preview(center, s_radius.value(), v, s_strict.value()))
        s_strict.valueChanged.connect(lambda v: self.update_manual_preview(center, s_radius.value(), s_sens.value(), v))

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dlg)
        lay.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)

        if dlg.exec_() == QDialog.Accepted:
            p = self.manual_preview
            if p is not None:
                self.manual_patches.append(p)
                added = int(np.count_nonzero(p["mask"]))
                print(f"[Manual] Patch added at {p['center']} | radius={p['radius']}, sens={p['sensitivity']}, strict={p['strict']} | pixels={added}")
            self.manual_preview = None
            self.request_repaint()
        else:
            self.manual_preview = None
            self.request_repaint()

    def remove_manual_patch_near(self, pos):
        if not self.manual_patches:
            return False
        x, y = pos
        for i in range(len(self.manual_patches)-1, -1, -1):
            cx, cy = self.manual_patches[i]["center"]
            if np.hypot(x - cx, y - cy) < max(self.manual_pick_radius, self.manual_patches[i]["radius"] * 0.5):
                self.manual_patches.pop(i)
                self.request_repaint()
                return True
        return False

    def update_manual_preview(self, center, radius, sensitivity, strict):
        mask = self.make_patch_mask(center, radius, sensitivity, strict)
        self.manual_preview = {
            "center": center,
            "radius": radius,
            "sensitivity": sensitivity,
            "strict": strict,
            "mask": mask
        }
        if not self.manual_preview_timer.isActive():
            self.manual_preview_timer.start(16)

    # ---------- UX ----------
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_L:
            self.toggle_checkbox.toggle()

    def mousePressEvent(self, event):
        if self.tool_mode == "color":
            if event.button() == Qt.LeftButton and self.qimage:
                pos = self.image_label.mapFromGlobal(event.globalPos())
                label_w, label_h = self.image_label.width(), self.image_label.height()
                img_w, img_h = self.qimage.width(), self.qimage.height()
                scale = min(label_w / img_w, label_h / img_h)
                disp_w, disp_h = img_w * scale, img_h * scale
                offset_x = (label_w - disp_w) / 2
                offset_y = (label_h - disp_h) / 2
                x = int((pos.x() - offset_x) / scale)
                y = int((pos.y() - offset_y) / scale)
                if 0 <= x < img_w and 0 <= y < img_h:
                    color = self.qimage.pixelColor(x, y)
                    r, g, b = color.red(), color.green(), color.blue()
                    hexv = f"#{r:02x}{g:02x}{b:02x}"
                    print(f"Picked color:\nRGB: ({r}, {g}, {b})\nHEX: {hexv}")
                    self.picked_color = (r, g, b)
                    self.request_repaint()
                    print(f"Clicked: ({x}, {y}) in label — Image size: {self.qimage.width()} x {self.qimage.height()}")
                    self.toggle_checkbox.setChecked(True)
                    self.pick_color_button.setChecked(False)
                else:
                    print("Click was outside the image")

        elif self.tool_mode == "plot":
            if self.first_plot_point:
                self.delete_line_button.show()
                self.line_checkbox.show()
                self.line_checkbox.setChecked(True)
            if event.button() == Qt.LeftButton:
                pos = self.image_label.mapFromGlobal(event.globalPos())
                mapped = self.map_click_to_image_coords(pos)
                if mapped:
                    x, y = mapped
                    if self.anchors:
                        first_x, first_y = self.anchors[0]
                        dist = np.hypot(x - first_x, y - first_y)
                        if dist < self.point_distance:
                            self.anchors.append((first_x, first_y))
                            self.temp_mouse_pos = None
                            self.request_repaint()
                            self.plot_line_button.setChecked(False)
                            self.polygon_closed = True
                            print("Polygon closed")
                    self.anchors.append((x, y))
                    if not self.polygon_closed:
                        print(f"Added anchor at: ({x}, {y})")
                    self.request_repaint()
            elif event.button() == Qt.RightButton:
                pos = self.image_label.mapFromGlobal(event.globalPos())
                mapped = self.map_click_to_image_coords(pos)
                if mapped:
                    x, y = mapped
                    for i, (ax, ay) in enumerate(self.anchors):
                        dist = np.hypot(x - ax, y - ay)
                        if dist < self.point_distance:
                            removed = self.anchors.pop(i)
                            self.request_repaint()
                            print(f"Removed anchor at: {removed}")
                            return

        elif self.tool_mode == "manual":
            pos = self.image_label.mapFromGlobal(event.globalPos())
            mapped = self.map_click_to_image_coords(pos)
            if not mapped:
                return
            x, y = mapped
            if event.button() == Qt.LeftButton:
                self.add_manual_patch((x, y))
            elif event.button() == Qt.RightButton:
                removed = self.remove_manual_patch_near((x, y))
                if removed:
                    print(f"Removed manual patch near: {(x, y)}")

    def mouseMoveEvent(self, event):
        if self.tool_mode == "plot" and self.anchors:
            pos = self.image_label.mapFromGlobal(event.globalPos())
            mapped = self.map_click_to_image_coords(pos)
            if mapped:
                self.temp_mouse_pos = mapped
                self.hovered_anchor_index = None
                x, y = mapped
                for i, (ax, ay) in enumerate(self.anchors):
                    dist = np.hypot(x - ax, y - ay)
                    if dist < self.point_distance:
                        self.hovered_anchor_index = i
                        break
                self.request_repaint()

    def mouse_moved(self, event):
        if self.tool_mode == "plot" and self.anchors:
            pos = self.image_label.mapFromGlobal(event.globalPos())
            mapped = self.map_click_to_image_coords(pos)
            if mapped:
                self.temp_mouse_pos = mapped
                self.hovered_anchor_index = None
                x, y = mapped
                for i, (ax, ay) in enumerate(self.anchors):
                    dist = np.hypot(x - ax, y - ay)
                    if dist < self.point_distance:
                        self.hovered_anchor_index = i
                        break
                self.request_repaint()

    def resizeEvent(self, event):
        self.request_repaint()
        super().resizeEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            self.request_repaint()
        super().changeEvent(event)

class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.mouse_moved_callback = None

    def mouseMoveEvent(self, event):
        if self.mouse_moved_callback:
            self.mouse_moved_callback(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SoilErosionUI()
    window.show()
    sys.exit(app.exec_())