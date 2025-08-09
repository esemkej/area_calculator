# Changelog

## v0.2-beta
- **Strict Mode**: Cluster-based filter that ignores isolated pixels and thin lines; keeps only larger contiguous regions. Strictness level is adjustable.
- **Manual Mode**: Add highlight patches manually with adjustable **radius**, **sensitivity**, and **strictness**, with live preview.
- **Persistent Settings**: Save and load settings (line width, preview width, anchor radius, font size) via `QSettings`.
- **Anchor Radius Control**: Adjustable anchor point size.
- **Font Size Control**: Adjustable global font size for the UI.
- **Overlay Improvements**: Fixed discoloration issues for a cleaner highlight layer.
- **Fullscreen & Resize Support**: Image resizes correctly when toggling fullscreen or resizing the window.
- **Right-Click Removal for Manual Patches**: Quickly remove manual patches without restarting analysis.
- **General UI/UX Improvements**.

## v0.1-beta
- **Initial Prototype Release**.
- Basic polygon drawing and anchor editing.
- Color picking with adjustable sensitivity.
- Highlight mask toggle.
- Percentage calculation for highlighted pixels.
- Basic image loading and scaling.
