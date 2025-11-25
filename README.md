# Mystem Sonitor

Advanced System Resource Monitor for Linux with GTK3

![Mystem Sonitor](icon.png)

## Features

- **Multiple Visualization Modes**: Bar, Gauge, Arc, Ring, Text, Wave, Terminal
- **I/O Widgets**: Disk and Network with 4 styles (Bars, Split, Compact, Terminal)
- **Color Themes**: Default, Ocean, Sunset, Matrix, Nord, Purple
- **Multiple Layouts**: Compact, Wide, Vertical, Mini, Dashboard, Panel
- **Custom Window**: No standard title bar, drag from header
- **Real-time Monitoring**: CPU, RAM, Swap, GPU, VRAM, Temperature, Disk I/O, Network
- **Click to Change**: Left-click any tile to cycle through visualization modes
- **Persistent Settings**: Saves your preferences automatically

## Screenshots

The application supports various visualization styles and themes:

- **Bar** - Clean horizontal progress bar
- **Gauge** - Speedometer-style gauge
- **Arc** - Half-circle arc indicator
- **Ring** - Full circular ring
- **Text** - Large bold text display
- **Wave** - Animated tank/wave fill
- **Terminal** - Mini console style

## Requirements

- Python 3
- GTK3 (python3-gi)
- Cairo bindings (python3-gi-cairo)
- psutil
- NVIDIA GPU (optional, for GPU/VRAM/Temperature monitoring)

## Installation

### Ubuntu/Debian

```bash
# Install dependencies
sudo apt install python3-gi python3-gi-cairo python3-psutil

# Clone repository
git clone https://github.com/alienxs2/mystem-sonitor.git
cd mystem-sonitor

# Run
python3 mystem_sonitor.py

# Or install to applications menu
cp mystem-sonitor.desktop ~/.local/share/applications/
```

### Arch Linux

```bash
sudo pacman -S python-gobject python-cairo python-psutil
```

### Fedora

```bash
sudo dnf install python3-gobject python3-cairo python3-psutil
```

## Usage

### Window Controls
- **Drag window**: Click and drag from the header area
- **Layout**: Click `▦` button to cycle layouts
- **Theme**: Click `◐` button to cycle color themes
- **Settings**: Click `⚙` button for autostart toggle
- **Minimize**: Click `─` button
- **Close**: Click `✕` button

### Tile Interaction
- **Left-click** any tile to cycle through visualization modes
- Each tile remembers its own visualization preference
- Settings are saved automatically

### Layouts
| Layout | Description |
|--------|-------------|
| Compact | 2x4 grid with all metrics |
| Wide | Single row, horizontal |
| Vertical | Stacked vertically |
| Mini | Minimal 3-tile view |
| Dashboard | Main gauges + secondary row |
| Panel | Horizontal panel strip |

### Themes
- **Default** - Green/Yellow/Red classic
- **Ocean** - Blue tones
- **Sunset** - Warm orange/red
- **Matrix** - Green terminal style
- **Nord** - Nord color palette
- **Purple** - Purple/violet tones

## Configuration

Settings are stored in `~/.config/mystem-sonitor/config.ini`

## Autostart

Enable autostart from the settings menu, or manually copy the desktop file:

```bash
cp mystem-sonitor.desktop ~/.config/autostart/
```

## GPU Monitoring

GPU monitoring requires NVIDIA drivers with `nvidia-smi`. If no NVIDIA GPU is detected, GPU/VRAM/Temp tiles will show 0.

## Author

**Goncharenko Anton** (alienxs2)

## License

MIT License - see [LICENSE](LICENSE) file for details.
