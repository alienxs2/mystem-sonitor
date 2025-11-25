# Mystem Sonitor

Advanced System Resource Monitor for Linux with GTK3

## Features

- **Multiple Visualization Modes**: Bar, Gauge (speedometer), Arc, Ring, Minimal
- **Custom Window Decoration**: No standard title bar, drag from header
- **Real-time Monitoring**: CPU, RAM, Swap, GPU, VRAM, Temperature, Disk I/O, Network
- **Settings Menu**: Visualization mode, Layout, Autostart toggle
- **Multiple Layouts**: Compact, Wide, Vertical, Mini
- **Color Gradient**: Green (normal) → Yellow → Orange → Red (critical)

## Requirements

- Python 3
- GTK3 (python3-gi)
- Cairo bindings (python3-gi-cairo)
- psutil
- NVIDIA GPU (optional, for GPU monitoring)

## Installation

```bash
# Install dependencies
sudo apt install python3-gi python3-gi-cairo python3-psutil

# Run
python3 mystem_sonitor.py

# Or add to applications
cp mystem-sonitor.desktop ~/.local/share/applications/
```

## Usage

- **Drag window**: Click and drag from the header area
- **Settings**: Click ⚙ button
- **Minimize**: Click ─ button
- **Close**: Click ✕ button

## Author

alienxs2

## License

MIT
