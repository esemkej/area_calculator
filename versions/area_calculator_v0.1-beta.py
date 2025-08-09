from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QLabel,
    QHBoxLayout, QVBoxLayout, QSlider, QCheckBox, QFileDialog, QScrollArea, QShortcut
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QKeySequence, QImage
from os import path
import sys, numpy as np, cv2

class SoilErosionUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Area Calculator")
        self.setGeometry(100, 100, 1280, 720)

        # Variables
        self.qimage = None
        self.picked_color = None
        self.tool_mode = None
        self.debug = False
        self.sensitivity = 100
        self.anchors = []
        self.temp_mouse_pos = None
        self.first_plot_point = True
        self.point_distance = 10 # Distance from which a click counts as an anchor click
        self.hovered_anchor_index = None

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
        self.sensitivity_slider.setValue(100)
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
        self.calculate_area_button = QPushButton("Calculate area")
        self.pick_color_button.setCheckable(True)
        self.plot_line_button.setCheckable(True)
        self.line_checkbox = QCheckBox("Line")
        tool_panel.addWidget(self.pick_color_button)
        tool_panel.addWidget(self.plot_line_button)
        tool_panel.addWidget(self.delete_line_button)
        tool_panel.addWidget(self.calculate_area_button)
        tool_panel.addWidget(self.line_checkbox)
        self.delete_line_button.hide()
        self.line_checkbox.hide()
        tool_panel.addStretch()

        tool_widget = QWidget()
        tool_widget.setLayout(tool_panel)

        # Image display (placeholder label)
        self.image_label = ClickableLabel("Image will appear here")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.mouse_moved_callback = self.mouse_moved
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.image_label)

        body_layout.addWidget(tool_widget)
        body_layout.addWidget(scroll_area)

        # === Assemble Layouts ===
        main_layout.addLayout(top_bar)
        main_layout.addLayout(body_layout)

        # Binds
        self.load_button.clicked.connect(self.load_image)
        self.toggle_checkbox.stateChanged.connect(self.update_final_image)
        self.sensitivity_slider.valueChanged.connect(self.update_sensitivity)
        self.pick_color_button.toggled.connect(self.pick_color)
        self.plot_line_button.toggled.connect(self.plot_line)
        self.delete_line_button.clicked.connect(self.delete_line)
        self.calculate_area_button.clicked.connect(self.analyze_field)
        self.line_checkbox.stateChanged.connect(self.update_final_image)

        shortcut_open = QShortcut(QKeySequence("Ctrl+O"), self)
        shortcut_open.activated.connect(self.load_image)
    
    # Logic
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
            self.image_label.setPixmap(pixmap.scaled(
                self.image_label.width(),
                self.image_label.height(),
                Qt.KeepAspectRatio
            ))
            print(f"Loaded: {file_path}")
            self.update_final_image()

    def update_sensitivity(self, value):
        self.sensitivity = value
        self.sensitivity_label.setText(f"Sensitivity: {value}")
        if self.toggle_checkbox.isChecked():
            self.update_final_image()

    def qimage_to_array(self, qimage):
        width, height, ptr = qimage.width(), qimage.height(), qimage.bits()
        ptr.setsize(qimage.byteCount())
        arr = np.array(ptr).reshape((height, width, 4))
        return arr[:, :, :3].copy()

    def get_color_mask(self, image_arr, target_color, tolerance):
        r, g, b = target_color
        diff = np.abs(image_arr - np.array([r, g, b]))
        distance = np.sum(diff, axis=2)
        return distance <= tolerance

    def create_highlight_overlay(self, mask, highlight_color=(255, 0, 0)):
        h, w = mask.shape
        overlay = np.zeros((h, w, 4), dtype=np.uint8)
        overlay[mask] = [*highlight_color, 150]
        return overlay

    def merge_overlay_with_image(self, base, overlay):
        base_rgba = np.dstack((base, np.full(base.shape[:2], 255, dtype=np.uint8))).astype(np.float32)
        overlay = overlay.astype(np.float32)

        alpha = overlay[:, :, 3:4] / 255.0
        blended = base_rgba * (1 - alpha) + overlay * alpha
        return blended.astype(np.uint8)

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
        
        base_arr = self.qimage_to_array(self.qimage)

        # Highlight overlay
        highlight_overlay = None
        if self.toggle_checkbox.isChecked() and self.picked_color:
            mask = self.get_color_mask(base_arr, self.picked_color, self.sensitivity)
            highlight_overlay = self.create_highlight_overlay(mask)
        else:
            highlight_overlay = np.zeros((base_arr.shape[0], base_arr.shape[1], 4), dtype=np.uint8)
        
        # Line overlay
        if self.line_checkbox.isChecked() and self.anchors:
            line_overlay = np.zeros((base_arr.shape[0], base_arr.shape[1], 4), dtype=np.uint8)

            # Draw lines
            for i in range(1, len(self.anchors)):
                cv2.line(line_overlay, self.anchors[i - 1], self.anchors[i], (0, 255, 0, 150), 2)
            
            # Mouse line
            if self.temp_mouse_pos:
                cv2.line(line_overlay, self.anchors[-1], self.temp_mouse_pos, (255, 255, 0, 120), 1)
            
            # Anchor points
            for i, (x, y) in enumerate(self.anchors):
                if i == self.hovered_anchor_index:
                    color = (255, 255, 0, 200)
                else:
                    color = (0, 255, 0, 200)
                cv2.circle(line_overlay, (x, y), 4, color, -1)
        else:
            line_overlay = np.zeros((base_arr.shape[0], base_arr.shape[1], 4), dtype=np.uint8)

        # Combine overlays
        combined_overlay = highlight_overlay.copy()
        combined_overlay = cv2.add(combined_overlay, line_overlay)

        # Merge with base
        final = self.merge_overlay_with_image(base_arr, combined_overlay)
        pixmap = self.arr_to_qpixmap(final)
        self.image_label.setPixmap(pixmap.scaled(
            self.image_label.width(),
            self.image_label.height(),
            Qt.KeepAspectRatio
        ))

    def pick_color(self, checked):
        if checked:
            self.tool_mode = "color"
            self.plot_line_button.setChecked(False)
            print("Click on a color you want to highlight")
        elif not checked and not self.plot_line_button.isChecked():
            self.tool_mode = None
    
    def plot_line(self, checked):
        if checked:
            self.tool_mode = "plot"
            self.pick_color_button.setChecked(False)
            print("Click anywhere to start plotting a line")
        elif not checked and not self.pick_color_button.isChecked():
            self.tool_mode = None

    def delete_line(self):
        if self.anchors:
            self.anchors = []
            self.line_checkbox.hide()
            self.delete_line_button.hide()
            self.plot_line_button.setChecked(False)
            self.update_final_image()
            print("Line deleted")
        else:
            print("No line drawn")

    def create_field_mask(self, shape):
        mask = np.zeros((shape[0], shape[1]), dtype=np.uint8)
        if len(self.anchors) >= 3:
            pts = np.array([self.anchors], dtype=np.int32)
            cv2.fillPoly(mask, pts, 255)
        return mask
    
    def apply_field_mask(self, base_arr, field_mask):
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
        if not self.qimage or len(self.anchors) < 3:
            print("Image not loaded or polygon not defined.")
            return

        base_arr = self.qimage_to_array(self.qimage)
        field_mask = self.create_field_mask(base_arr.shape[:2])
        field_only = self.apply_field_mask(base_arr, field_mask)
        cropped_img, cropped_mask = self.crop_to_field(field_only, field_mask)

        if self.picked_color:
            mask = self.get_color_mask(cropped_img[:, :, :3], self.picked_color, self.sensitivity)
            highlight_overlay = self.create_highlight_overlay(mask)
            percent = self.calculate_pixel_percentage(cropped_img, highlight_overlay)
            print(f"Highlighted area: {percent:.2f}%")
        else:
            print("No color selected — can't compute erosion %.")

    # UX
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
                    hex = f"#{r:02x}{g:02x}{b:02x}"
                    print(f"Picked color:\nRGB: ({r}, {g}, {b})\nHEX: {hex}")
                    self.picked_color = (r, g, b)
                    self.update_final_image()
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
                            self.update_final_image()
                            self.plot_line_button.setChecked(False)
                            print("Polygon closed")

                    self.anchors.append((x, y))
                    print(f"Added anchor at: ({x}, {y})")
                    self.update_final_image()
            elif event.button() == Qt.RightButton:
                pos = self.image_label.mapFromGlobal(event.globalPos())
                mapped = self.map_click_to_image_coords(pos)

                if mapped:
                    x, y = mapped
                    for i, (ax, ay) in enumerate(self.anchors):
                        dist = np.hypot(x - ax, y - ay)
                        if dist < self.point_distance:
                            removed = self.anchors.pop(i)
                            self.update_final_image()
                            print(f"Removed anchor at: {removed}")
                            return

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
                self.update_final_image()

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
                self.update_final_image()

class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.mouse_moved_callback = True
    
    def mouseMoveEvent(self, event):
        if self.mouse_moved_callback:
            self.mouse_moved_callback(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SoilErosionUI()
    window.show()
    sys.exit(app.exec_())
