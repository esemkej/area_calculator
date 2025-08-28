from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QLabel,
    QHBoxLayout, QVBoxLayout, QSlider, QCheckBox, QFileDialog, QScrollArea,
    QShortcut, QSizePolicy, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QTimer, QSettings, QEvent
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
        self.debug = False
        self.sensitivity = 100
        self.anchors = []
        self.temp_mouse_pos = None
        self.first_plot_point = True
        self.point_distance = 10  # Distance from which a click counts as an anchor click
        self.hovered_anchor_index = None
        self.strict_sensitivity = 5
        self.polygon_closed = False
        self.delay = 3000
        self.transient_sensitivity = 100
        self.transient_strict = 5
        self.transient_color = None
        self.non_resizable_labels = [] # Labels inside of the area calculation layout that don't answer to global font size changes unless manually updated
        self.cache = {
            "highlight_mask": None,
            "highlight_overlay": None,
            "manual_mask": None,
            "manual_overlay": None,
            "transient_mask": None,
            "transient_overlay": None,
            "line_overlay": None
        }
        self.dirty = {
            "highlight": True,
            "manual": True,
            "transient": True,
            "lines": True
        }

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
        self.quick_settings = self.settings.value("ui/quick_settings", True, type=bool)

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

        # Info timer
        self.timer = QTimer()
        self.timer.setSingleShot(True)

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
        self.pick_transient_color_button = QPushButton("Pick transient color")
        self.plot_line_button = QPushButton("Plot a line")
        self.delete_line_button = QPushButton("Delete line")
        self.manual_mode_button = QPushButton("Manual mode")
        self.calculate_area_button = QPushButton("Calculate area")
        self.settings_button = QPushButton("Settings")
        self.pick_color_button.setCheckable(True)
        self.pick_transient_color_button.setCheckable(True)
        self.plot_line_button.setCheckable(True)
        self.manual_mode_button.setCheckable(True)

        # Color display
        self.color_parent = QWidget()
        self.color_parent.setLayout(QHBoxLayout())
        self.color_parent.layout().setContentsMargins(0, 0, 0, 0)
        self.color_layout_0 = QWidget()
        self.color_layout_0.setStyleSheet("background-color: #000000;")
        self.color_layout_0.setLayout(QHBoxLayout())
        self.color_layout_0.layout().setContentsMargins(1, 1, 1, 1)
        self.color_layout_1 = QWidget()
        self.color_layout_1.setStyleSheet("background-color: #ffffff;")
        self.color_layout_1.setLayout(QHBoxLayout())
        self.color_layout_1.layout().setContentsMargins(1, 1, 1, 1)
        self.color_container = QWidget()
        self.color_container.setFixedSize(int(self.text_size * 2), int(self.text_size * 2))
        self.color_layout_1.layout().addWidget(self.color_container)
        self.color_layout_0.layout().addWidget(self.color_layout_1)
        self.color_parent.layout().addWidget(self.color_layout_0, alignment=Qt.AlignHCenter)
        self.color_label = QLabel()

        self.strict_checkbox = QCheckBox("Strict mode")
        self.strict_slider = QSlider(Qt.Horizontal)
        self.strict_slider.setMinimum(0)
        self.strict_slider.setMaximum(10)
        self.strict_slider.setValue(self.strict_sensitivity)
        self.strict_slider.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.strict_label = QLabel(f"Sensitivity: {self.strict_sensitivity}")

        # Transient
        self.line_checkbox = QCheckBox("Line")
        self.manual_checkbox = QCheckBox("Manual layer")
        self.transient_checkbox = QCheckBox("Transient layer")

        # Transient color display
        self.transient_color_parent = QWidget()
        self.transient_color_parent.setLayout(QHBoxLayout())
        self.transient_color_parent.layout().setContentsMargins(0, 0, 0, 0)
        self.transient_color_layout_0 = QWidget()
        self.transient_color_layout_0.setStyleSheet("background-color: #000000;")
        self.transient_color_layout_0.setLayout(QHBoxLayout())
        self.transient_color_layout_0.layout().setContentsMargins(1, 1, 1, 1)
        self.transient_color_layout_1 = QWidget()
        self.transient_color_layout_1.setStyleSheet("background-color: #ffffff;")
        self.transient_color_layout_1.setLayout(QHBoxLayout())
        self.transient_color_layout_1.layout().setContentsMargins(1, 1, 1, 1)
        self.transient_color_container = QWidget()
        self.transient_color_container.setFixedSize(int(self.text_size * 2), int(self.text_size * 2))
        self.transient_color_layout_1.layout().addWidget(self.transient_color_container)
        self.transient_color_layout_0.layout().addWidget(self.transient_color_layout_1)
        self.transient_color_parent.layout().addWidget(self.transient_color_layout_0, alignment=Qt.AlignHCenter)
        self.transient_color_label = QLabel()

        # Transient controls
        self.transient_label = QLabel(f"Sensitivity: {self.transient_sensitivity}")
        self.transient_slider = QSlider(Qt.Horizontal)
        self.transient_slider.setMinimum(1)
        self.transient_slider.setMaximum(255)
        self.transient_slider.setValue(self.transient_sensitivity)
        self.transient_slider.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.transient_strict_label = QLabel(f"Strict sensitivity: {self.transient_strict}")
        self.transient_strict_slider = QSlider(Qt.Horizontal)
        self.transient_strict_slider.setMinimum(0)
        self.transient_strict_slider.setMaximum(10)
        self.transient_strict_slider.setValue(self.transient_strict)
        self.transient_strict_slider.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.compare_checkbox = QCheckBox("Comparison image")

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

        # Area panel
        self.area_main_layout = QWidget()
        self.area_main_layout.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.area_main_layout.setStyleSheet("background:#000000;")
        self.area_main_layout.setLayout(QHBoxLayout())
        self.area_main_layout.layout().setContentsMargins(0, 0, 0, 0)
        self.area_main_layout.layout().setSpacing(0)

        # left_texts_layout (column)
        left_texts_layout = QVBoxLayout()
        left_texts_layout.setContentsMargins(0, 0, 0, 0)
        left_texts_layout.setSpacing(0)
        self.area_main_layout.layout().addLayout(left_texts_layout, 1)

        # --- left_highlight_layout ---
        left_highlight_wrapper = QWidget()
        left_highlight_wrapper.setLayout(QHBoxLayout())
        left_highlight_wrapper.layout().setContentsMargins(2, 2, 1, 1)  # margins outside white cell
        left_highlight_wrapper.layout().setSpacing(0)

        left_highlight_layout = QWidget()
        left_highlight_layout.setStyleSheet("background:#FFFFFF;")
        left_highlight_layout.setLayout(QHBoxLayout())
        left_highlight_layout.layout().setContentsMargins(8, 8, 8, 8)   # padding
        left_highlight_layout.layout().setSpacing(0)

        highlight_label = QLabel("Highlight area:")
        left_highlight_layout.layout().addWidget(highlight_label)
        self.non_resizable_labels.append(highlight_label)

        left_highlight_wrapper.layout().addWidget(left_highlight_layout)
        left_texts_layout.addWidget(left_highlight_wrapper)

        # --- left_manual_layout ---
        left_manual_wrapper = QWidget()
        left_manual_wrapper.setLayout(QHBoxLayout())
        left_manual_wrapper.layout().setContentsMargins(2, 1, 1, 1)
        left_manual_wrapper.layout().setSpacing(0)

        left_manual_layout = QWidget()
        left_manual_layout.setStyleSheet("background:#FFFFFF;")
        left_manual_layout.setLayout(QHBoxLayout())
        left_manual_layout.layout().setContentsMargins(8, 8, 8, 8)
        left_manual_layout.layout().setSpacing(0)

        manual_label = QLabel("Manual area:")
        left_manual_layout.layout().addWidget(manual_label)
        self.non_resizable_labels.append(manual_label)

        left_manual_wrapper.layout().addWidget(left_manual_layout)
        left_texts_layout.addWidget(left_manual_wrapper)

        # --- left_transcient_layout ---
        left_transcient_wrapper = QWidget()
        left_transcient_wrapper.setLayout(QHBoxLayout())
        left_transcient_wrapper.layout().setContentsMargins(2, 1, 1, 1)
        left_transcient_wrapper.layout().setSpacing(0)

        left_transcient_layout = QWidget()
        left_transcient_layout.setStyleSheet("background:#FFFFFF;")
        left_transcient_layout.setLayout(QHBoxLayout())
        left_transcient_layout.layout().setContentsMargins(8, 8, 8, 8)
        left_transcient_layout.layout().setSpacing(0)

        transcient_label = QLabel("Transcient area:")
        left_transcient_layout.layout().addWidget(transcient_label)
        self.non_resizable_labels.append(transcient_label)

        left_transcient_wrapper.layout().addWidget(left_transcient_layout)
        left_texts_layout.addWidget(left_transcient_wrapper)

        # --- left_combined_layout ---
        left_combined_wrapper = QWidget()
        left_combined_wrapper.setLayout(QHBoxLayout())
        left_combined_wrapper.layout().setContentsMargins(2, 1, 1, 2)
        left_combined_wrapper.layout().setSpacing(0)

        left_combined_layout = QWidget()
        left_combined_layout.setStyleSheet("background:#FFFFFF;")
        left_combined_layout.setLayout(QHBoxLayout())
        left_combined_layout.layout().setContentsMargins(8, 8, 8, 8)
        left_combined_layout.layout().setSpacing(0)

        combined_area_label = QLabel("Combined area:")
        left_combined_layout.layout().addWidget(combined_area_label)
        self.non_resizable_labels.append(combined_area_label)

        left_combined_wrapper.layout().addWidget(left_combined_layout)
        left_texts_layout.addWidget(left_combined_wrapper)

        # right_texts_layout (column)
        right_texts_layout = QVBoxLayout()
        right_texts_layout.setContentsMargins(0, 0, 0, 0)
        right_texts_layout.setSpacing(0)
        self.area_main_layout.layout().addLayout(right_texts_layout, 1)

        # --- right_highlight_layout ---
        right_highlight_wrapper = QWidget()
        right_highlight_wrapper.setLayout(QHBoxLayout())
        right_highlight_wrapper.layout().setContentsMargins(1, 2, 2, 1)
        right_highlight_wrapper.layout().setSpacing(0)

        right_highlight_layout = QWidget()
        right_highlight_layout.setStyleSheet("background:#FFFFFF;")
        right_highlight_layout.setLayout(QHBoxLayout())
        right_highlight_layout.layout().setContentsMargins(8, 8, 8, 8)
        right_highlight_layout.layout().setSpacing(0)

        self.highlight_perc = QLabel("None")
        right_highlight_layout.layout().addWidget(self.highlight_perc)
        self.non_resizable_labels.append(self.highlight_perc)

        right_highlight_wrapper.layout().addWidget(right_highlight_layout)
        right_texts_layout.addWidget(right_highlight_wrapper)

        # --- right_manual_layout ---
        right_manual_wrapper = QWidget()
        right_manual_wrapper.setLayout(QHBoxLayout())
        right_manual_wrapper.layout().setContentsMargins(1, 1, 2, 1)
        right_manual_wrapper.layout().setSpacing(0)

        right_manual_layout = QWidget()
        right_manual_layout.setStyleSheet("background:#FFFFFF;")
        right_manual_layout.setLayout(QHBoxLayout())
        right_manual_layout.layout().setContentsMargins(8, 8, 8, 8)
        right_manual_layout.layout().setSpacing(0)

        self.manual_perc = QLabel("None")
        right_manual_layout.layout().addWidget(self.manual_perc)
        self.non_resizable_labels.append(self.manual_perc)

        right_manual_wrapper.layout().addWidget(right_manual_layout)
        right_texts_layout.addWidget(right_manual_wrapper)

        # --- right_transcient_layout ---
        right_transcient_wrapper = QWidget()
        right_transcient_wrapper.setLayout(QHBoxLayout())
        right_transcient_wrapper.layout().setContentsMargins(1, 1, 2, 1)
        right_transcient_wrapper.layout().setSpacing(0)

        right_transcient_layout = QWidget()
        right_transcient_layout.setStyleSheet("background:#FFFFFF;")
        right_transcient_layout.setLayout(QHBoxLayout())
        right_transcient_layout.layout().setContentsMargins(8, 8, 8, 8)
        right_transcient_layout.layout().setSpacing(0)

        self.transcient_perc = QLabel("None")
        right_transcient_layout.layout().addWidget(self.transcient_perc)
        self.non_resizable_labels.append(self.transcient_perc)

        right_transcient_wrapper.layout().addWidget(right_transcient_layout)
        right_texts_layout.addWidget(right_transcient_wrapper)

        # --- right_combined_layout ---
        right_combined_wrapper = QWidget()
        right_combined_wrapper.setLayout(QHBoxLayout())
        right_combined_wrapper.layout().setContentsMargins(1, 1, 2, 2)
        right_combined_wrapper.layout().setSpacing(0)

        right_combined_layout = QWidget()
        right_combined_layout.setStyleSheet("background:#FFFFFF;")
        right_combined_layout.setLayout(QHBoxLayout())
        right_combined_layout.layout().setContentsMargins(8, 8, 8, 8)
        right_combined_layout.layout().setSpacing(0)

        self.combined_perc = QLabel("None")
        right_combined_layout.layout().addWidget(self.combined_perc)
        self.non_resizable_labels.append(self.combined_perc)

        right_combined_wrapper.layout().addWidget(right_combined_layout)
        right_texts_layout.addWidget(right_combined_wrapper)

        tool_panel.addWidget(self.pick_color_button)
        tool_panel.addWidget(self.color_parent)
        tool_panel.addWidget(self.color_label)
        tool_panel.addWidget(self.pick_transient_color_button)
        tool_panel.addWidget(self.plot_line_button)
        tool_panel.addWidget(self.delete_line_button)
        tool_panel.addWidget(self.manual_mode_button)
        tool_panel.addWidget(self.calculate_area_button)
        tool_panel.addWidget(self.settings_button)
        tool_panel.addWidget(self.strict_checkbox)
        tool_panel.addWidget(self.strict_label)
        tool_panel.addWidget(self.strict_slider)
        tool_panel.addWidget(self.line_checkbox)
        tool_panel.addWidget(self.manual_checkbox)
        tool_panel.addWidget(self.transient_checkbox)
        tool_panel.addWidget(self.transient_color_parent)
        tool_panel.addWidget(self.transient_color_label)
        tool_panel.addWidget(self.transient_label)
        tool_panel.addWidget(self.transient_slider)
        tool_panel.addWidget(self.transient_strict_label)
        tool_panel.addWidget(self.transient_strict_slider)
        tool_panel.addWidget(self.compare_checkbox)
        tool_panel.addWidget(self.line_width_label)
        tool_panel.addWidget(self.line_width_slider)
        tool_panel.addWidget(self.preview_line_width_label)
        tool_panel.addWidget(self.preview_line_width_slider)
        tool_panel.addWidget(self.anchor_radius_label)
        tool_panel.addWidget(self.anchor_radius_slider)
        tool_panel.addWidget(self.text_size_label)
        tool_panel.addWidget(self.text_size_slider)
        tool_panel.addWidget(self.area_main_layout)

        self.color_parent.hide()
        self.color_label.hide()
        self.delete_line_button.hide()
        self.strict_label.hide()
        self.strict_slider.hide()
        self.transient_color_parent.hide()
        self.transient_color_label.hide()
        self.transient_label.hide()
        self.transient_slider.hide()
        self.transient_strict_label.hide()
        self.transient_strict_slider.hide()
        self.line_checkbox.hide()
        if not self.quick_settings:
            self.line_width_label.hide()
            self.line_width_slider.hide()
            self.preview_line_width_label.hide()
            self.preview_line_width_slider.hide()
            self.anchor_radius_label.hide()
            self.anchor_radius_slider.hide()
            self.text_size_label.hide()
            self.text_size_slider.hide()
        tool_panel.addStretch()

        tool_widget = QWidget()
        tool_widget.setLayout(tool_panel)

        # Image display
        self.image_label = ClickableLabel("Image will appear here")
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.mouse_moved_callback = self.mouse_moved
        self.compare_image_label = QLabel("Comparison image will appear here")
        self.compare_image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.compare_image_label.setAlignment(Qt.AlignCenter)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scroll_area.setWidget(self.image_label)
        self.compare_scroll_area = QScrollArea()
        self.compare_scroll_area.setWidgetResizable(True)
        self.compare_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.compare_scroll_area.setWidget(self.compare_image_label)

        # Info display
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        self.info_label = QLabel()
        info_layout.addWidget(self.info_label, alignment=Qt.AlignHCenter)

        right_scroll_layout = QHBoxLayout()
        right_scroll_layout.setContentsMargins(0, 0, 0, 0)
        right_scroll_layout.addWidget(self.scroll_area, 1)
        right_scroll_layout.addWidget(self.compare_scroll_area, 1)

        right_body_layout = QVBoxLayout()
        right_body_layout.setContentsMargins(0, 0, 0, 0)
        right_body_layout.addLayout(right_scroll_layout)
        right_body_layout.addLayout(info_layout)

        body_layout.addWidget(tool_widget)
        body_layout.addLayout(right_body_layout)
        self.compare_scroll_area.hide()

        # === Assemble Layouts ===
        main_layout.addLayout(top_bar)
        main_layout.addLayout(body_layout)

        # Binds
        self.load_button.clicked.connect(self.load_image)
        self.toggle_checkbox.stateChanged.connect(self.toggle_highlight_layer)
        self.sensitivity_slider.valueChanged.connect(self.update_sensitivity)
        self.pick_color_button.toggled.connect(self.pick_color)
        self.pick_transient_color_button.toggled.connect(self.pick_transient_color)
        self.plot_line_button.toggled.connect(self.plot_line)
        self.delete_line_button.clicked.connect(self.delete_line)
        self.manual_mode_button.toggled.connect(self.manual_mode)
        self.calculate_area_button.clicked.connect(self.analyze_field)
        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.strict_checkbox.stateChanged.connect(self.strict_mode)
        self.strict_slider.valueChanged.connect(self.update_strict)
        self.line_checkbox.stateChanged.connect(self.toggle_line_layer)
        self.manual_checkbox.stateChanged.connect(self.toggle_manual_layer)
        self.transient_checkbox.stateChanged.connect(self.toggle_transient)
        self.transient_slider.valueChanged.connect(self.update_transient_sensitivity)
        self.transient_strict_slider.valueChanged.connect(self.update_transient_strict)
        self.compare_checkbox.stateChanged.connect(self.compare_image)
        self.line_width_slider.valueChanged.connect(self.update_line_width)
        self.preview_line_width_slider.valueChanged.connect(self.update_preview_line_width)
        self.anchor_radius_slider.valueChanged.connect(self.update_anchor_radius)
        self.text_size_slider.sliderReleased.connect(self.update_global_font)
        self.text_size_slider.valueChanged.connect(self.update_text_size_label)
        self.timer.timeout.connect(self.remove_hint)

        shortcut_open = QShortcut(QKeySequence("Ctrl+O"), self)
        shortcut_open.activated.connect(self.load_image)

    # ---------- Logic ----------
    def request_repaint(self):
        if not self.repaint_timer.isActive():
            self.repaint_timer.start(16)

    def load_image(self):
        if self.debug:
            file_path = path.join(path.dirname(__file__), "debug_image.png")
            if not path.exists(file_path):
                self.path_label.setText("[DEBUG] debug_image.png not found")
                return
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
            )
        if file_path:
            self.pixmap = QPixmap(file_path)
            self.qimage = self.pixmap.toImage()
            self.base_rgba = self.qimage_to_array(self.qimage)
            self.invalidate_all()
            vw = self.scroll_area.viewport().width()
            vh = self.scroll_area.viewport().height()
            self.image_label.setPixmap(
                self.pixmap.scaled(vw, vh, Qt.KeepAspectRatio, Qt.FastTransformation)
            )
            self.compare_image_label.setPixmap(
                self.pixmap.scaled(vw, vh, Qt.KeepAspectRatio, Qt.FastTransformation)
            )
            self.hint(f"Loaded: {file_path}", True)
            self.request_repaint()

    def update_sensitivity(self, value):
        self.sensitivity = value
        self.sensitivity_label.setText(f"Sensitivity: {value}")
        self.invalidate("highlight")
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

    def create_highlight_overlay(self, mask, highlight_color=(204, 199, 34)):
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

        # --- HIGHLIGHT ---
        if self.dirty["highlight"]:
            hm, hov = self.build_highlight(base_arr)
            self.cache["highlight_mask"] = hm
            self.cache["highlight_overlay"] = hov
            self.dirty["highlight"] = False
            # downstream dependencies
            self.dirty["transient"] = True
            self.dirty["manual"] = True

        # --- TRANSIENT (exclude highlight) ---
        if self.dirty["transient"]:
            tm, tov = self.build_transient(base_arr, forbid_mask=self.cache["highlight_mask"])
            self.cache["transient_mask"] = tm
            self.cache["transient_overlay"] = tov
            self.dirty["transient"] = False
            # manual depends on highlight+transient
            self.dirty["manual"] = True

        # --- MANUAL (exclude highlight | transient) ---
        if self.dirty["manual"]:
            # build a combined forbid mask (higher-priority union)
            forbid = None
            if self.cache["highlight_mask"] is not None:
                forbid = self.cache["highlight_mask"].copy()
            if self.cache["transient_mask"] is not None:
                forbid = self.cache["transient_mask"] if forbid is None else np.logical_or(forbid, self.cache["transient_mask"])

            mm, mov = self.build_manual(base_arr, forbid_mask=forbid)
            self.cache["manual_mask"] = mm
            self.cache["manual_overlay"] = mov
            self.dirty["manual"] = False

        # --- LINES ---
        if self.dirty["lines"]:
            lov = self.build_lines((h, w))
            self.cache["line_overlay"] = lov
            self.dirty["lines"] = False

        # --- COMBINE OVERLAYS ---
        combined_overlay = np.zeros((h, w, 4), dtype=np.uint8)

        def _blend_on_top(dst, src):
            mask = src[:, :, 3] > 0
            if not mask.any():
                return dst
            dst_alpha = dst[mask, 3]
            src_alpha = src[mask, 3]
            dst[mask, 3] = np.maximum(dst_alpha, src_alpha)
            a = (src_alpha.astype(np.float32) / 255.0)[:, None]
            dst[mask, :3] = (dst[mask, :3].astype(np.float32) * (1.0 - a) +
                            src[mask, :3].astype(np.float32) * a).astype(np.uint8)
            return dst

        combined_overlay = _blend_on_top(combined_overlay, self.cache["highlight_overlay"])
        combined_overlay = _blend_on_top(combined_overlay, self.cache["transient_overlay"])
        combined_overlay = _blend_on_top(combined_overlay, self.cache["manual_overlay"])
        combined_overlay = _blend_on_top(combined_overlay, self.cache["line_overlay"])

        # --- COMPOSITE OVER BASE ---
        final = self.merge_overlay_with_image(base_arr, combined_overlay)
        pixmap = self.arr_to_qpixmap(final)
        vw = self.scroll_area.viewport().width()
        vh = self.scroll_area.viewport().height()
        self.image_label.setPixmap(
            pixmap.scaled(vw, vh, Qt.KeepAspectRatio, Qt.FastTransformation)
        )
        if self.compare_checkbox.isChecked():
            self.compare_image_label.setPixmap(
                self.pixmap.scaled(vw, vh, Qt.KeepAspectRatio, Qt.FastTransformation)
            )

    def pick_color(self, checked):
        if checked:
            self.tool_mode = "color"
            self.plot_line_button.setChecked(False)
            self.manual_mode_button.setChecked(False)
            self.hint("Click on a color you want to highlight", True)
        elif not checked and not self.plot_line_button.isChecked() and not self.manual_mode_button.isChecked():
            self.tool_mode = None

    def plot_line(self, checked):
        if checked:
            self.tool_mode = "plot"
            self.pick_color_button.setChecked(False)
            self.manual_mode_button.setChecked(False)
            self.hint("Click anywhere to start plotting a line", True)
        elif not checked and not self.pick_color_button.isChecked() and not self.manual_mode_button.isChecked():
            self.tool_mode = None
            if not self.polygon_closed:
                self.delete_line()

    def delete_line(self):
        if self.anchors:
            self.anchors = []
            self.temp_mouse_pos = None
            self.hovered_anchor_index = None
            self.polygon_closed = False
            self.first_plot_point = True
            self.line_checkbox.hide()
            self.delete_line_button.hide()
            self.plot_line_button.setChecked(False)
            self.invalidate("lines")
            self.request_repaint()
            if self.polygon_closed:
                self.hint("Line deleted", True)
            else:
                self.hint("Line deleted - polygon not closed", True)
        else:
            self.hint("No line drawn", True)

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
        # must have an image and a closed polygon
        if not self.qimage or len(self.anchors) < 3 or not self.polygon_closed:
            self.hint("Image not loaded or polygon not defined/closed", True)
            return

        base_arr = self.base_rgba

        # --- build field mask and crop to its bbox ---
        field_mask_u8 = self.create_field_mask(base_arr.shape[:2])  # 0/255
        coords = cv2.findNonZero(field_mask_u8)
        if coords is None:
            self.hint("Polygon mask is empty", True)
            return

        x, y, w, h = cv2.boundingRect(coords)
        field_roi = field_mask_u8[y:y+h, x:x+w] > 0

        # Field-only image (for denominator via alpha>0 in percentage)
        field_only_rgba = self.apply_field_mask(base_arr, field_mask_u8)
        cropped_img = field_only_rgba[y:y+h, x:x+w]

        # ---------- HIGHLIGHT (raw) ----------
        highlight_full = None
        if self.toggle_checkbox.isChecked() and self.picked_color is not None:
            highlight_full = self.get_color_mask(base_arr[:, :, :3], self.picked_color, int(self.sensitivity))
            if self.strict_checkbox.isChecked():
                highlight_full = self.apply_strict_filter(highlight_full, int(self.strict_sensitivity))
            high_cropped = highlight_full[y:y+h, x:x+w] & field_roi
            p_high = self.calculate_pixel_percentage(cropped_img, self.create_highlight_overlay(high_cropped))
            self.highlight_perc.setText(f"{p_high:.2f}%")
        else:
            high_cropped = np.zeros((h, w), dtype=bool)
            self.highlight_perc.setText("None")

        # ---------- TRANSIENT (raw -> disjoint by removing highlight) ----------
        trans_full = None
        if self.transient_checkbox.isChecked() and (self.transient_color is not None):
            trans_full = self.get_color_mask(base_arr[:, :, :3], self.transient_color, int(self.transient_sensitivity))
            if int(self.transient_strict) > 0:
                trans_full = self.apply_strict_filter(trans_full, int(self.transient_strict))
            if highlight_full is not None:
                trans_full = trans_full & (~highlight_full)  # disjoint from highlight
            trans_cropped = trans_full[y:y+h, x:x+w] & field_roi
            p_trans = self.calculate_pixel_percentage(cropped_img, self.create_highlight_overlay(trans_cropped, highlight_color=(186, 113, 0)))
            self.transcient_perc.setText(f"{p_trans:.2f}%")
        else:
            trans_cropped = np.zeros((h, w), dtype=bool)
            self.transcient_perc.setText("None")

        # ---------- MANUAL (raw -> disjoint by removing highlight|transient) ----------
        man_cropped = np.zeros((h, w), dtype=bool)
        if self.manual_checkbox.isChecked():
            manual_full = self.recompute_manual_mask()
            forbid = None
            if highlight_full is not None:
                forbid = highlight_full.copy()
            if trans_full is not None:
                forbid = trans_full if forbid is None else np.logical_or(forbid, trans_full)
            if forbid is not None:
                manual_full = manual_full & (~forbid)  # disjoint from higher-priority classes
            man_cropped = manual_full[y:y+h, x:x+w] & field_roi
            p_manual = self.calculate_pixel_percentage(cropped_img, self.create_highlight_overlay(man_cropped, highlight_color=(0, 0, 255)))
            self.manual_perc.setText(f"{p_manual:.2f}%")
        else:
            self.manual_perc.setText("None")

        # ---------- COMBINED (union of disjoint classes) ----------
        combined_cropped = high_cropped | trans_cropped | man_cropped
        p_combined = self.calculate_pixel_percentage(cropped_img, self.create_highlight_overlay(combined_cropped))
        self.combined_perc.setText(f"{p_combined:.2f}%")

    def strict_mode(self, checked):
        if checked:
            self.strict_slider.show()
            self.strict_label.show()
        else:
            self.strict_slider.hide()
            self.strict_label.hide()
        self.invalidate("highlight")
        self.request_repaint()

    def update_strict(self, value):
        self.strict_sensitivity = value
        if value == 0:
            self.strict_label.setText("Sensitivity: Off")
        else:
            self.strict_label.setText(f"Sensitivity: {value}")
        self.invalidate("highlight")
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
            self.manual_checkbox.setChecked(True)
            self.hint("Click on specific patches to add them manually", False)
        elif not checked and not self.pick_color_button.isChecked() and not self.plot_line_button.isChecked():
            self.tool_mode = None
            self.remove_hint()
            if not self.manual_patches:
                self.manual_checkbox.setChecked(False)

    def update_line_width(self, value):
        print("update")
        self.line_width = value
        self.line_width_label.setText(f"Line width: {value}")
        self.settings.setValue("var/line_width", value)
        if (self.plot_line_button.isChecked() or self.anchors):
            self.invalidate("lines")
            self.request_repaint()

    def update_preview_line_width(self, value):
        self.preview_line_width = value
        self.preview_line_width_label.setText(f"Preview line width: {value}")
        self.settings.setValue("var/preview_line_width", value)
        if (self.plot_line_button.isChecked() or self.anchors):
            self.invalidate("lines")
            self.request_repaint()

    def update_anchor_radius(self, value):
        self.anchor_radius = value
        self.anchor_radius_label.setText(f"Anchor radius: {value}")
        self.settings.setValue("var/anchor_radius", value)
        if (self.plot_line_button.isChecked() or self.anchors):
            self.invalidate("lines")
            self.request_repaint()

    def update_global_font(self):
        app = QApplication.instance()
        f = app.font()
        f.setPointSize(self.text_size_slider.value())
        app.setFont(f)

        for i in self.non_resizable_labels:
            i.setFont(f)

        self.settings.setValue("ui/text_size", self.text_size_slider.value())
        self.color_container.setFixedSize(int(self.text_size * 2), int(self.text_size * 2))
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
        s_strict, _ = mk("Strict sensitivity", 0, 10, 0)

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
                self.hint(f"[Manual] Patch added at {p['center']} | Radius: {p['radius']}, Sensitivity: {p['sensitivity']}, Strict sensitivity: {p['strict']} | Pixels: {added}", True)
            self.manual_preview = None
            self.invalidate("manual")
            self.request_repaint()
        else:
            self.manual_preview = None
            self.invalidate("manual")
            self.request_repaint()

    def remove_manual_patch_near(self, pos):
        if not self.manual_patches:
            return False
        x, y = pos
        for i in range(len(self.manual_patches)-1, -1, -1):
            cx, cy = self.manual_patches[i]["center"]
            if np.hypot(x - cx, y - cy) < max(self.manual_pick_radius, self.manual_patches[i]["radius"] * 0.5):
                self.manual_patches.pop(i)
                self.invalidate("manual")
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
        self.invalidate("manual")
        if not self.manual_preview_timer.isActive():
            self.manual_preview_timer.start(16)

    def compare_image(self, checked):
        if checked:
            self.compare_scroll_area.show()
            self.request_repaint()
        else:
            self.compare_scroll_area.hide()
            self.request_repaint()

    def hint(self, text, timed):
        self.info_label.show()
        self.info_label.setText(text)
        if timed:
            if self.timer.isActive():
                self.timer.stop()
            self.timer.start(self.delay)

    def remove_hint(self):
        self.info_label.setText("")

    def update_transient_sensitivity(self, value):
        self.transient_sensitivity = value
        self.transient_label.setText(f"Sensitivity: {value}")
        self.invalidate("transient", "manual")
        self.request_repaint()

    def update_transient_strict(self, value):
        self.transient_strict = value
        if value == 0:
            self.transient_strict_label.setText("Strict sensitivity: Off")
        else:
            self.transient_strict_label.setText(f"Strict sensitivity: {value}")
        self.invalidate("transient", "manual")
        self.request_repaint()

    def pick_transient_color(self, checked):
        if checked:
            self.tool_mode = "transient_color"
            self.pick_color_button.setChecked(False)
            self.plot_line_button.setChecked(False)
            self.manual_mode_button.setChecked(False)
            self.hint("Click on a color for the transient layer", False)
        elif not checked and not self.plot_line_button.isChecked() and not self.manual_mode_button.isChecked():
            self.tool_mode = None

    def toggle_transient(self, checked):
        if checked:
            if self.transient_color:
                self.transient_color_parent.show()
                self.transient_color_label.show()
            self.transient_label.show()
            self.transient_slider.show()
            self.transient_strict_label.show()
            self.transient_strict_slider.show()
        else:
            self.transient_color_parent.hide()
            self.transient_color_label.hide()
            self.transient_label.hide()
            self.transient_slider.hide()
            self.transient_strict_label.hide()
            self.transient_strict_slider.hide()
        self.invalidate("transient", "manual")
        self.request_repaint()

    def build_transient_overlay(self, base_arr):
        if self.transient_color is None:
            h, w = base_arr.shape[:2]
            return np.zeros((h, w, 4), dtype=np.uint8)

        tol = int(getattr(self, "transient_sensitivity", 100))
        mask = self.get_color_mask(base_arr, self.transient_color, tol)

        if self.strict_checkbox.isChecked():
            level = int(round(getattr(self, "transient_strict", self.transient_strict)))
            mask = self.apply_strict_filter(mask, level)
        
        return self.create_highlight_overlay(mask, highlight_color=(186, 113, 0))

    def invalidate(self, *layers):
        for k in layers:
            self.dirty[k] = True
    
    def invalidate_all(self):
        for k in self.dirty:
            self.dirty[k] = True

    def build_highlight(self, base_arr):
        """Returns (mask, overlay) for the main highlight layer."""
        h, w = base_arr.shape[:2]
        if not (self.toggle_checkbox.isChecked() and self.picked_color):
            return np.zeros((h, w), dtype=bool), np.zeros((h, w, 4), dtype=np.uint8)

        mask = self.get_color_mask(base_arr, self.picked_color, int(self.sensitivity))
        if self.strict_checkbox.isChecked():
            level = int(self.strict_sensitivity)
            mask = self.apply_strict_filter(mask, level)
        overlay = self.create_highlight_overlay(mask)  # gold default
        return mask, overlay

    def build_manual(self, base_arr, forbid_mask=None):
        """Returns (mask, overlay) for manual layer (only if checkbox is on).
        If forbid_mask is provided, manual excludes those pixels (disjoint)."""
        h, w = base_arr.shape[:2]
        if not self.manual_checkbox.isChecked():
            return np.zeros((h, w), dtype=bool), np.zeros((h, w, 4), dtype=np.uint8)

        mask = self.recompute_manual_mask()

        # EXCLUDE higher-priority classes (highlight and/or transient) if provided
        if forbid_mask is not None:
            mask = np.logical_and(mask, np.logical_not(forbid_mask))

        overlay = self.create_highlight_overlay(mask, highlight_color=(0, 0, 255))
        return mask, overlay

    def build_transient(self, base_arr, forbid_mask=None):
        """
        Second highlight layer (orange). Excludes any pixels already in forbid_mask (highlight),
        so it never overlaps visually.
        """
        h, w = base_arr.shape[:2]
        if not (self.transient_checkbox.isChecked() and self.transient_color is not None):
            return np.zeros((h, w), dtype=bool), np.zeros((h, w, 4), dtype=np.uint8)

        tol = int(self.transient_sensitivity)
        tmask = self.get_color_mask(base_arr, self.transient_color, tol)

        # independent strict for transient
        level = int(self.transient_strict)
        if level > 0:
            tmask = self.apply_strict_filter(tmask, level)

        # EXCLUDE highlight pixels if present
        if forbid_mask is not None:
            tmask = np.logical_and(tmask, np.logical_not(forbid_mask))

        overlay = self.create_highlight_overlay(tmask, highlight_color=(186, 113, 0))  # #ba7100
        return tmask, overlay

    def build_lines(self, shape_hw):
        """Returns overlay for lines/anchors if enabled."""
        h, w = shape_hw
        if not (self.line_checkbox.isChecked() and self.anchors):
            return np.zeros((h, w, 4), dtype=np.uint8)

        line_overlay = np.zeros((h, w, 4), dtype=np.uint8)
        lw = int(self.line_width)
        for i in range(1, len(self.anchors)):
            cv2.line(line_overlay, self.anchors[i - 1], self.anchors[i], (0, 255, 0, 255), lw)
        if getattr(self, "temp_mouse_pos", None):
            plw = int(self.preview_line_width)
            cv2.line(line_overlay, self.anchors[-1], self.temp_mouse_pos, (255, 255, 0, 255), plw)
        ar = int(self.anchor_radius)
        for i, (x, y) in enumerate(self.anchors):
            color = (255, 255, 0, 255) if i == self.hovered_anchor_index else (0, 255, 0, 255)
            cv2.circle(line_overlay, (x, y), ar, color, -1)
        return line_overlay

    def toggle_line_layer(self, _):
        self.invalidate("lines")
        self.request_repaint()

    def toggle_manual_layer(self, _):
        self.invalidate("manual")
        self.request_repaint()

    def toggle_highlight_layer(self, _):
        self.invalidate("highlight", "transient", "manual")
        self.request_repaint()

    def open_settings_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Settings")
        layout = QVBoxLayout(dlg)

        s_line_width_label = QLabel(f"Line width: {self.line_width}")
        line_width_slider = QSlider(Qt.Horizontal)
        line_width_slider.setMinimum(1)
        line_width_slider.setMaximum(10)
        line_width_slider.setValue(self.line_width)
        line_width_slider.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

        s_preview_line_width_label = QLabel(f"Preview line width: {self.preview_line_width}")
        preview_line_width_slider = QSlider(Qt.Horizontal)
        preview_line_width_slider.setMinimum(1)
        preview_line_width_slider.setMaximum(10)
        preview_line_width_slider.setValue(self.preview_line_width)
        preview_line_width_slider.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

        s_anchor_radius_label = QLabel(f"Anchor radius: {self.anchor_radius}")
        anchor_radius_slider = QSlider(Qt.Horizontal)
        anchor_radius_slider.setMinimum(1)
        anchor_radius_slider.setMaximum(20)
        anchor_radius_slider.setValue(self.anchor_radius)
        anchor_radius_slider.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

        s_text_size_label = QLabel(f"Text size: {self.text_size}")
        text_size_slider = QSlider(Qt.Horizontal)
        text_size_slider.setMinimum(6)
        text_size_slider.setMaximum(24)
        text_size_slider.setValue(self.text_size)
        text_size_slider.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

        quick_settings_checkbox = QCheckBox("Show settings in tool panel")
        quick_settings_checkbox.setChecked(self.quick_settings)

        layout.addWidget(s_line_width_label)
        layout.addWidget(line_width_slider)
        layout.addWidget(s_preview_line_width_label)
        layout.addWidget(preview_line_width_slider)
        layout.addWidget(s_anchor_radius_label)
        layout.addWidget(anchor_radius_slider)
        layout.addWidget(s_text_size_label)
        layout.addWidget(text_size_slider)
        layout.addWidget(quick_settings_checkbox)

        line_width_slider.valueChanged.connect(
            lambda v: s_line_width_label.setText(f"Line width: {v}")
        )
        preview_line_width_slider.valueChanged.connect(
            lambda v: s_preview_line_width_label.setText(f"Preview line width: {v}")
        )
        anchor_radius_slider.valueChanged.connect(
            lambda v: s_anchor_radius_label.setText(f"Anchor radius: {v}")
        )
        text_size_slider.valueChanged.connect(
            lambda v: s_text_size_label.setText(f"Text size: {v}")
        )

        # Button box
        btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Apply | QDialogButtonBox.Cancel, parent=dlg
        )
        layout.addWidget(btns)

        apply_button = btns.button(QDialogButtonBox.Apply)
        if apply_button:
            def _on_apply():
                self.line_width_slider.setValue(line_width_slider.value())
                self.preview_line_width_slider.setValue(preview_line_width_slider.value())
                self.anchor_radius_slider.setValue(anchor_radius_slider.value())
                self.text_size_slider.setValue(text_size_slider.value())
                self.update_global_font()
                if quick_settings_checkbox.isChecked():
                    self.quick_settings = True
                    self.settings.setValue("ui/quick_settings", True)
                    self.line_width_label.show()
                    self.line_width_slider.show()
                    self.preview_line_width_label.show()
                    self.preview_line_width_slider.show()
                    self.anchor_radius_label.show()
                    self.anchor_radius_slider.show()
                    self.text_size_label.show()
                    self.text_size_slider.show()
                else:
                    self.quick_settings = False
                    self.settings.setValue("ui/quick_settings", False)
                    self.line_width_label.hide()
                    self.line_width_slider.hide()
                    self.preview_line_width_label.hide()
                    self.preview_line_width_slider.hide()
                    self.anchor_radius_label.hide()
                    self.anchor_radius_slider.hide()
                    self.text_size_label.hide()
                    self.text_size_slider.hide()

            apply_button.clicked.connect(_on_apply)

        # OK (call hook, then close)
        def _on_ok():
            self.line_width_slider.setValue(line_width_slider.value())
            self.preview_line_width_slider.setValue(preview_line_width_slider.value())
            self.anchor_radius_slider.setValue(anchor_radius_slider.value())
            self.text_size_slider.setValue(text_size_slider.value())
            self.update_global_font()
            if quick_settings_checkbox.isChecked():
                self.quick_settings = True
                self.settings.setValue("ui/quick_settings", True)
                self.line_width_label.show()
                self.line_width_slider.show()
                self.preview_line_width_label.show()
                self.preview_line_width_slider.show()
                self.anchor_radius_label.show()
                self.anchor_radius_slider.show()
                self.text_size_label.show()
                self.text_size_slider.show()
            else:
                self.quick_settings = False
                self.settings.setValue("ui/quick_settings", False)
                self.line_width_label.hide()
                self.line_width_slider.hide()
                self.preview_line_width_label.hide()
                self.preview_line_width_slider.hide()
                self.anchor_radius_label.hide()
                self.anchor_radius_slider.hide()
                self.text_size_label.hide()
                self.text_size_slider.hide()
            dlg.accept()

        btns.accepted.connect(_on_ok)

        # Cancel (call hook, then close)
        def _on_cancel():
            dlg.reject()

        btns.rejected.connect(_on_cancel)

        dlg.exec_()
        return None

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
                    self.color_container.setStyleSheet(f"background-color: {hexv};")
                    self.color_label.setText(f"RGB: ({r}, {g}, {b})\nHEX: {hexv}")
                    self.color_parent.show()
                    self.color_label.show()
                    self.picked_color = (r, g, b)
                    self.invalidate("highlight", "transient")
                    self.request_repaint()
                    self.toggle_checkbox.setChecked(True)
                    self.pick_color_button.setChecked(False)
                    self.remove_hint()
                else:
                    self.hint("Click was outside the image", True)
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
                            self.invalidate("lines")
                            self.temp_mouse_pos = None
                            self.request_repaint()
                            self.polygon_closed = True
                            self.plot_line_button.setChecked(False)
                            self.hint("Polygon closed", True)
                    was_empty = not self.anchors
                    self.anchors.append((x, y))
                    self.invalidate("lines")
                    if was_empty:
                        self.first_plot_point = False
                    if not self.polygon_closed:
                        self.hint(f"Added anchor at: ({x}, {y})", True)
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
                            self.invalidate("lines")
                            self.request_repaint()
                            self.hint(f"Removed anchor at: {removed}", True)
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
                    self.hint(f"Removed manual patch near: {(x, y)}", True)
        elif self.tool_mode == "transient_color":
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
                    self.transient_color = (color.red(), color.green(), color.blue())
                    hexv = f"#{color.red():02x}{color.green():02x}{color.blue():02x}"
                    self.transient_color_container.setStyleSheet(f"background-color: {hexv};")
                    self.transient_color_label.setText(f"Transient color:\nRGB: {self.transient_color}\nHEX: {hexv}")
                    self.transient_color_parent.show()
                    self.transient_color_label.show()
                    self.invalidate("transient", "manual")
                    self.request_repaint()
                    self.transient_checkbox.setChecked(True)
                    self.pick_transient_color_button.setChecked(False)
                    self.remove_hint()

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
                self.invalidate("lines")
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
                self.invalidate("lines")
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