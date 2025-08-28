# Area Calculator

A PyQt5-based tool designed primarily for calculating the percentage of eroded soil in fields.  
While originally intended for agricultural use, it can be adapted to many other scenarios where pixel-based percentage analysis is useful.

---

## Features

- **Color Picking (Highlight):** Click on the image to pick a color you want to highlight.
- **Second Auto Layer (Transient):** Pick a second color for semi-eroded areas. The transient layer is computed independently and does **not** overlap the highlight layer.
- **Dynamic Sensitivity & Strict Mode:** Adjust sensitivity live and optionally filter out isolated pixels/thin lines by keeping only **larger contiguous regions** (tunable strictness) for each auto layer.
- **Manual Patches:** Add extra patches manually with adjustable radius, sensitivity, and strictness, with live preview. Remove patches with right-click near the center.
- **Area Panel:** Shows four values — **Highlight**, **Manual**, **Transient**, and **Combined** — after calculation.
- **Comparison View:** Optional side-by-side pane to show the original image next to the processed one. Both panes resize evenly with the window.
- **Highlight/Layer Toggles:** Show or hide the highlight, manual, and transient layers independently.
- **Persistent Settings:** Settings such as line width, preview line width, anchor radius, font size, and quick-settings visibility are saved between sessions.
- **Image Auto-Resize:** Automatically resizes with the window, including fullscreen mode.

---

## Usage

1. **Open an Image:** Use the "Open Image" button or `Ctrl+O` to load your target image.
2. **Pick a Color (Highlight):** Click "Pick a Color" and select a pixel in the image. Adjust **Sensitivity** and optionally **Strict**.
3. **Pick Transient Color (optional):** Select a second color for semi-eroded areas. Adjust **Sensitivity** and **Strict**. This layer is separate from highlight and does not overlap it.
4. **Manual Mode (optional):** Add custom highlight patches with **radius / sensitivity / strict** sliders and live preview before applying. Right-click to remove a patch near the cursor.
5. **Draw a Polygon:** Click "Plot Line" and place anchors around the area you want to analyze; close by clicking the first point. This is intended as the **last step** before calculation, but it does not strictly matter when you draw it.
6. **Calculate Area:** Press **Calculate Area** to compute and update the panel with **Highlight**, **Manual**, **Transient**, and **Combined** percentages for the polygon.
7. **Toggles & Comparison:** Use checkboxes to hide/show individual layers, and enable the comparison view to see the original image alongside the processed result.

---

## What's New (v0.3-beta)

- **Second auto layer (Transient):** Independent color pick with its own sensitivity/strict settings; calculated without overlapping the highlight layer.
- **Area panel:** Displays **Highlight**, **Manual**, **Transient**, and **Combined** percentages.
- **Comparison view:** Side-by-side original vs processed image with equal resizing.
- **Strict mode improvements:** Morphology + connected components for more robust noise removal.
- **Settings persistence expanded:** Line width, preview width, anchor radius, font size, and quick-settings visibility saved between sessions.
- **Rendering optimizations:** Overlays cached and repainted with a short timer to reduce redundant work.
- **Bug fix:** Resolved an issue where the line disappeared after closing the polygon.

---

## License

This project is licensed under the terms described in the `LICENSE` file.
