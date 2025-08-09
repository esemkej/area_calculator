# Area Calculator

A PyQt5-based tool designed primarily for calculating the percentage of eroded soil in fields.  
While originally intended for agricultural use, it can be adapted to many other scenarios where pixel-based percentage analysis is useful.

---

## Features

- **Polygon Selection:** Draw a polygon to define the analysis area.
- **Anchor Point Editing:** Remove anchors by right-clicking them.
- **Color Picking:** Click on the image to pick a color you want to highlight.
- **Dynamic Sensitivity:** Adjust sensitivity live to refine the highlighted area.
- **Strict Mode:** Optionally filter out isolated pixels/thin lines by keeping only **larger contiguous regions** (clustering-based; tunable).
- **Manual Patches:** Add extra patches manually with adjustable radius, sensitivity, and strictness, with live preview.
- **Highlight Toggle:** Show or hide the highlight mask at will (and the manual layer separately).
- **Live Preview:** See changes in sensitivity, radius, and strictness instantly before adding manual patches.
- **Persistent Settings:** Settings such as line width, preview width, anchor radius, and font size are saved in `AppData`.
- **Image Auto-Resize:** Automatically resizes with the window, including fullscreen mode.

---

## Usage

1. **Open an Image:** Use the "Open Image" button or `Ctrl+O` to load your target image.
2. **Draw a Polygon:**
   - Click "Plot Line" and place anchors around the area you want to analyze.
   - Right-click to remove an anchor if needed.
   - Closing the polygon enables the analysis functions.
3. **Pick a Color:** Click "Pick a Color" and select a pixel in the image.
4. **Adjust Sensitivity:** Use the top slider to fine-tune detection.
5. **(Optional) Strict Mode:** Enable **Strict mode** to ignore tiny specks and thin lines. Increase the **strictness** level to require larger clusters of matching pixels.
6. **Manual Mode (optional):** Add custom highlight patches with **radius / sensitivity / strict** sliders and live preview before applying.
7. **Calculate Area:** Press "Calculate Area" to get the highlighted percentage within your polygon.
8. **Toggles:** Use checkboxes to hide/show overlays (global highlight, manual layer) without losing data.

---

## Known Limitations

- Polygon must be closed for area calculation.
- No undo for manual patches yet — patches must be removed individually via right-click.
- Large images may slightly slow live preview updates.

---

## What's New (v0.2-beta)

- **Strict Mode:** New clustering filter that keeps only larger contiguous regions and drops isolated pixels/thin lines (tunable level).
- **Manual Mode:** Add custom patches with live preview and per-patch sensitivity/strictness.
- **Persistent Settings:** Stored via `QSettings` (line width, preview width, anchor radius, font size).
- Font size, line widths, and anchor radius now adjustable and remembered.
- Fixed discoloration overlay issue for cleaner visuals.
- **Fullscreen-aware resizing** so the image always fits the window.
- Right-click removal for manual patches.
- Multiple UI/UX improvements for smoother interaction.

---

## License

This project is licensed under the terms described in the `LICENSE` file.
