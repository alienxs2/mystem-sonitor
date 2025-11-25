#!/usr/bin/env python3
"""
Mystem Sonitor - Advanced System Resource Monitor

Features:
- Multiple visualization modes (bar, gauge, arc, ring, minimal)
- Custom window decoration (no standard title bar)
- Settings menu with autostart toggle
- Layout switching
- Cairo-based custom widgets

Author: alienxs2
License: MIT
"""

import subprocess
import os
import math
from typing import Optional, Dict, Any

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Gio
import cairo

import psutil


# ============================================================================
# Configuration
# ============================================================================

APP_NAME = "Mystem Sonitor"
APP_ID = "com.alienxs2.mystemsonitor"
UPDATE_INTERVAL_MS = 1000
CONFIG_DIR = os.path.expanduser("~/.config/mystem-sonitor")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.ini")
AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "mystem-sonitor.desktop")
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Visualization modes
VIS_MODES = ["bar", "gauge", "arc", "ring", "minimal"]
LAYOUTS = ["compact", "wide", "vertical", "mini"]


def get_health_color(percent: float) -> tuple:
    """Get RGB color based on percentage (0-100)."""
    if percent <= 50:
        t = percent / 50
        return (t * 0.8, 0.8, 0.2 * (1 - t))
    elif percent <= 70:
        t = (percent - 50) / 20
        return (0.8 + t * 0.2, 0.8 - t * 0.1, 0)
    elif percent <= 85:
        t = (percent - 70) / 15
        return (1.0, 0.7 - t * 0.35, 0)
    else:
        t = min(1.0, (percent - 85) / 15)
        return (1.0, 0.35 * (1 - t), 0)


def rgb_to_hex(rgb: tuple) -> str:
    return f"#{int(rgb[0]*255):02X}{int(rgb[1]*255):02X}{int(rgb[2]*255):02X}"


# ============================================================================
# Cairo Visualization Widgets
# ============================================================================

class GaugeWidget(Gtk.DrawingArea):
    """Speedometer-style gauge widget."""

    def __init__(self, label: str = "", unit: str = "%"):
        super().__init__()
        self.label = label
        self.unit = unit
        self.value = 0
        self.details = ""
        self.set_size_request(100, 80)
        self.connect('draw', self.on_draw)

    def set_value(self, value: float, details: str = ""):
        self.value = min(100, max(0, value))
        self.details = details
        self.queue_draw()

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        cx, cy = width / 2, height * 0.6
        radius = min(width, height) * 0.4

        # Background arc
        cr.set_line_width(8)
        cr.set_source_rgb(0.2, 0.2, 0.2)
        cr.arc(cx, cy, radius, math.pi * 0.8, math.pi * 2.2)
        cr.stroke()

        # Value arc
        color = get_health_color(self.value)
        cr.set_source_rgb(*color)
        end_angle = math.pi * 0.8 + (self.value / 100) * math.pi * 1.4
        cr.arc(cx, cy, radius, math.pi * 0.8, end_angle)
        cr.stroke()

        # Needle
        needle_angle = math.pi * 0.8 + (self.value / 100) * math.pi * 1.4
        needle_len = radius * 0.7
        nx = cx + math.cos(needle_angle) * needle_len
        ny = cy + math.sin(needle_angle) * needle_len
        cr.set_source_rgb(1, 1, 1)
        cr.set_line_width(2)
        cr.move_to(cx, cy)
        cr.line_to(nx, ny)
        cr.stroke()

        # Center dot
        cr.arc(cx, cy, 4, 0, 2 * math.pi)
        cr.fill()

        # Value text
        cr.set_source_rgb(*color)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(14)
        text = f"{self.value:.0f}{self.unit}"
        extents = cr.text_extents(text)
        cr.move_to(cx - extents.width / 2, cy + radius * 0.3)
        cr.show_text(text)

        # Label
        cr.set_source_rgb(0.7, 0.7, 0.7)
        cr.set_font_size(10)
        extents = cr.text_extents(self.label)
        cr.move_to(cx - extents.width / 2, height - 5)
        cr.show_text(self.label)


class ArcWidget(Gtk.DrawingArea):
    """Arc progress widget."""

    def __init__(self, label: str = "", unit: str = "%"):
        super().__init__()
        self.label = label
        self.unit = unit
        self.value = 0
        self.details = ""
        self.set_size_request(90, 70)
        self.connect('draw', self.on_draw)

    def set_value(self, value: float, details: str = ""):
        self.value = min(100, max(0, value))
        self.details = details
        self.queue_draw()

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        cx, cy = width / 2, height * 0.45
        radius = min(width, height) * 0.35

        # Background arc (180 degrees)
        cr.set_line_width(6)
        cr.set_source_rgb(0.2, 0.2, 0.2)
        cr.arc(cx, cy, radius, math.pi, 2 * math.pi)
        cr.stroke()

        # Value arc
        color = get_health_color(self.value)
        cr.set_source_rgb(*color)
        end_angle = math.pi + (self.value / 100) * math.pi
        cr.arc(cx, cy, radius, math.pi, end_angle)
        cr.stroke()

        # Value text
        cr.set_source_rgb(*color)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(16)
        text = f"{self.value:.0f}{self.unit}"
        extents = cr.text_extents(text)
        cr.move_to(cx - extents.width / 2, cy + 8)
        cr.show_text(text)

        # Label
        cr.set_source_rgb(0.6, 0.6, 0.6)
        cr.set_font_size(9)
        extents = cr.text_extents(self.label)
        cr.move_to(cx - extents.width / 2, height - 3)
        cr.show_text(self.label)


class RingWidget(Gtk.DrawingArea):
    """Circular ring progress widget."""

    def __init__(self, label: str = "", unit: str = "%"):
        super().__init__()
        self.label = label
        self.unit = unit
        self.value = 0
        self.details = ""
        self.set_size_request(80, 80)
        self.connect('draw', self.on_draw)

    def set_value(self, value: float, details: str = ""):
        self.value = min(100, max(0, value))
        self.details = details
        self.queue_draw()

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        cx, cy = width / 2, height / 2
        radius = min(width, height) * 0.35

        # Background ring
        cr.set_line_width(5)
        cr.set_source_rgb(0.2, 0.2, 0.2)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.stroke()

        # Value ring
        color = get_health_color(self.value)
        cr.set_source_rgb(*color)
        start = -math.pi / 2
        end = start + (self.value / 100) * 2 * math.pi
        cr.arc(cx, cy, radius, start, end)
        cr.stroke()

        # Value text
        cr.set_source_rgb(*color)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(12)
        text = f"{self.value:.0f}"
        extents = cr.text_extents(text)
        cr.move_to(cx - extents.width / 2, cy + 4)
        cr.show_text(text)

        # Label below
        cr.set_source_rgb(0.6, 0.6, 0.6)
        cr.set_font_size(8)
        extents = cr.text_extents(self.label)
        cr.move_to(cx - extents.width / 2, cy + radius + 12)
        cr.show_text(self.label)


class BarWidget(Gtk.Box):
    """Progress bar widget with label."""

    def __init__(self, label: str = "", unit: str = "%"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.label_text = label
        self.unit = unit
        self._css = Gtk.CssProvider()

        self.get_style_context().add_class('bar-widget')

        # Label row
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.label = Gtk.Label(label=label)
        self.label.set_halign(Gtk.Align.START)
        self.label.get_style_context().add_class('bar-label')
        header.pack_start(self.label, True, True, 0)

        self.value_label = Gtk.Label(label="0%")
        self.value_label.set_halign(Gtk.Align.END)
        self.value_label.get_style_context().add_class('bar-value')
        header.pack_end(self.value_label, False, False, 0)
        self.pack_start(header, False, False, 0)

        # Progress bar
        self.progress = Gtk.ProgressBar()
        self.progress.set_fraction(0)
        self.progress.get_style_context().add_class('health-bar')
        self.progress.get_style_context().add_provider(self._css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.pack_start(self.progress, False, False, 0)

        # Details
        self.details_label = Gtk.Label(label="")
        self.details_label.set_halign(Gtk.Align.START)
        self.details_label.get_style_context().add_class('bar-details')
        self.pack_start(self.details_label, False, False, 0)

    def set_value(self, value: float, details: str = ""):
        color = get_health_color(value)
        hex_color = rgb_to_hex(color)

        self.value_label.set_markup(f'<span foreground="{hex_color}" weight="bold">{value:.0f}{self.unit}</span>')
        self.progress.set_fraction(min(value / 100.0, 1.0))

        css = f".health-bar progress {{ background-color: {hex_color}; }}"
        self._css.load_from_data(css.encode())

        if details:
            self.details_label.set_text(details)


class MinimalWidget(Gtk.Box):
    """Minimal text-only widget."""

    def __init__(self, label: str = "", unit: str = "%"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.unit = unit

        self.label = Gtk.Label(label=label)
        self.label.get_style_context().add_class('mini-label')
        self.pack_start(self.label, False, False, 0)

        self.value_label = Gtk.Label(label=f"0{unit}")
        self.value_label.get_style_context().add_class('mini-value')
        self.pack_start(self.value_label, False, False, 0)

    def set_value(self, value: float, details: str = ""):
        color = rgb_to_hex(get_health_color(value))
        self.value_label.set_markup(f'<span foreground="{color}" weight="bold" size="large">{value:.0f}{self.unit}</span>')


class IOWidget(Gtk.Box):
    """I/O display widget."""

    def __init__(self, label: str = ""):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=1)

        self.label = Gtk.Label(label=label)
        self.label.get_style_context().add_class('io-label')
        self.pack_start(self.label, False, False, 0)

        self.read_label = Gtk.Label(label="↓ 0 B/s")
        self.read_label.get_style_context().add_class('io-read')
        self.pack_start(self.read_label, False, False, 0)

        self.write_label = Gtk.Label(label="↑ 0 B/s")
        self.write_label.get_style_context().add_class('io-write')
        self.pack_start(self.write_label, False, False, 0)

    def set_values(self, read: float, write: float):
        self.read_label.set_text(f"↓ {self._fmt(read)}")
        self.write_label.set_text(f"↑ {self._fmt(write)}")

    def _fmt(self, v: float) -> str:
        if v < 1024: return f"{v:.0f} B/s"
        if v < 1024**2: return f"{v/1024:.0f} KB/s"
        if v < 1024**3: return f"{v/1024**2:.1f} MB/s"
        return f"{v/1024**3:.1f} GB/s"


class TileContainer(Gtk.EventBox):
    """Clickable container for tiles with popup settings menu and drag-drop."""

    # Class-level drag data
    _drag_source = None
    _drag_targets = [Gtk.TargetEntry.new("TILE_DRAG", Gtk.TargetFlags.SAME_APP, 0)]

    def __init__(self, tile_name: str, inner_widget, config, on_mode_change, on_reorder):
        super().__init__()
        self.tile_name = tile_name
        self.inner = inner_widget
        self.config = config
        self.on_mode_change = on_mode_change
        self.on_reorder = on_reorder

        self.add(inner_widget)
        self.get_style_context().add_class('tile-container')

        # Click for settings (right-click)
        self.connect('button-press-event', self._on_click)

        # Drag and drop setup
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, self._drag_targets, Gdk.DragAction.MOVE)
        self.drag_dest_set(Gtk.DestDefaults.ALL, self._drag_targets, Gdk.DragAction.MOVE)

        self.connect('drag-begin', self._on_drag_begin)
        self.connect('drag-data-get', self._on_drag_data_get)
        self.connect('drag-data-received', self._on_drag_data_received)
        self.connect('drag-end', self._on_drag_end)

        # Track last value for forwarding
        self._last_value = 0
        self._last_details = ""

    def _on_drag_begin(self, widget, context):
        TileContainer._drag_source = self.tile_name
        self.get_style_context().add_class('dragging')

    def _on_drag_end(self, widget, context):
        self.get_style_context().remove_class('dragging')
        TileContainer._drag_source = None

    def _on_drag_data_get(self, widget, context, selection, info, time):
        selection.set_text(self.tile_name, -1)

    def _on_drag_data_received(self, widget, context, x, y, selection, info, time):
        source_name = TileContainer._drag_source
        if source_name and source_name != self.tile_name:
            self.on_reorder(source_name, self.tile_name)

    def _on_click(self, widget, event):
        if event.button == 3:  # Right click for settings
            self._show_settings_menu(event)
            return True
        return False

    def _show_settings_menu(self, event):
        menu = Gtk.Menu()

        # Header label
        header = Gtk.MenuItem(label=f"📊 {self.tile_name.upper()}")
        header.set_sensitive(False)
        menu.append(header)
        menu.append(Gtk.SeparatorMenuItem())

        # Visualization mode options (radio group)
        current_mode = self.config.get_tile_mode(self.tile_name)
        group = []

        for mode in VIS_MODES:
            item = Gtk.RadioMenuItem.new_with_label(group, f"  {mode.capitalize()}")
            group = item.get_group()
            item.set_active(mode == current_mode)
            item.connect('toggled', self._on_mode_select, mode)
            menu.append(item)

        menu.append(Gtk.SeparatorMenuItem())

        # Reset to global
        reset_item = Gtk.MenuItem(label="↺ Use global default")
        reset_item.connect('activate', self._on_reset_to_global)
        menu.append(reset_item)

        menu.show_all()
        menu.popup_at_pointer(event)

    def _on_mode_select(self, item, mode):
        if item.get_active() and self.config.get_tile_mode(self.tile_name) != mode:
            self.config.set_tile_mode(self.tile_name, mode)
            self.on_mode_change(self.tile_name)

    def _on_reset_to_global(self, item):
        self.config.tile_modes.pop(self.tile_name, None)
        self.config.save()
        self.on_mode_change(self.tile_name)

    def set_value(self, value: float, details: str = ""):
        self._last_value = value
        self._last_details = details
        self.inner.set_value(value, details)

    def set_values(self, read: float, write: float):
        """For IOWidget compatibility."""
        self.inner.set_values(read, write)


# ============================================================================
# GPU Monitor
# ============================================================================

class GPUMonitor:
    @staticmethod
    def get_info() -> Optional[Dict[str, Any]]:
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,name",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2
            )
            if r.returncode == 0:
                p = r.stdout.strip().split(", ")
                if len(p) >= 5:
                    return {
                        "util": float(p[0]), "mem_used": float(p[1]),
                        "mem_total": float(p[2]), "temp": float(p[3]),
                        "name": p[4].replace("NVIDIA ", "").replace("GeForce ", "")
                    }
        except: pass
        return None


# ============================================================================
# Config Manager
# ============================================================================

class ConfigManager:
    # Default tile orders for each layout
    DEFAULT_ORDERS = {
        "compact": ["cpu", "ram", "swap", "gpu", "vram", "disk", "net", "temp"],
        "wide": ["cpu", "ram", "gpu", "temp"],
        "vertical": ["cpu", "ram", "swap", "gpu", "vram", "temp", "disk", "net"],
        "mini": ["cpu", "ram", "gpu"],
    }

    def __init__(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.layout = "compact"
        self.vis_mode = "bar"  # Default/global mode
        self.autostart = False
        # Individual tile visualization modes
        self.tile_modes = {}  # e.g. {"cpu": "gauge", "ram": "ring"}
        # Tile order per layout
        self.tile_orders = {}  # e.g. {"compact": ["ram", "cpu", ...]}
        self.load()

    def load(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE) as f:
                    for line in f:
                        if '=' in line:
                            k, v = line.strip().split('=', 1)
                            if k == 'layout' and v in LAYOUTS: self.layout = v
                            elif k == 'vis_mode' and v in VIS_MODES: self.vis_mode = v
                            elif k == 'autostart': self.autostart = v == 'true'
                            elif k.startswith('tile_') and v in VIS_MODES:
                                tile_name = k[5:]  # Remove 'tile_' prefix
                                self.tile_modes[tile_name] = v
                            elif k.startswith('order_'):
                                layout_name = k[6:]  # Remove 'order_' prefix
                                self.tile_orders[layout_name] = v.split(',')
        except: pass

    def save(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                f.write(f"layout={self.layout}\n")
                f.write(f"vis_mode={self.vis_mode}\n")
                f.write(f"autostart={'true' if self.autostart else 'false'}\n")
                for tile_name, mode in self.tile_modes.items():
                    f.write(f"tile_{tile_name}={mode}\n")
                for layout_name, order in self.tile_orders.items():
                    f.write(f"order_{layout_name}={','.join(order)}\n")
        except: pass

    def get_tile_mode(self, tile_name: str) -> str:
        """Get visualization mode for specific tile, or global default."""
        return self.tile_modes.get(tile_name, self.vis_mode)

    def set_tile_mode(self, tile_name: str, mode: str):
        """Set visualization mode for specific tile."""
        if mode == self.vis_mode:
            # If same as global, remove individual setting
            self.tile_modes.pop(tile_name, None)
        else:
            self.tile_modes[tile_name] = mode
        self.save()

    def get_tile_order(self, layout: str = None) -> list:
        """Get tile order for current or specified layout."""
        layout = layout or self.layout
        if layout in self.tile_orders:
            return self.tile_orders[layout]
        return self.DEFAULT_ORDERS.get(layout, self.DEFAULT_ORDERS["compact"])

    def set_tile_order(self, order: list, layout: str = None):
        """Set tile order for current or specified layout."""
        layout = layout or self.layout
        self.tile_orders[layout] = order
        self.save()

    def swap_tiles(self, tile1: str, tile2: str, layout: str = None):
        """Swap positions of two tiles."""
        layout = layout or self.layout
        order = self.get_tile_order(layout).copy()
        if tile1 in order and tile2 in order:
            i1, i2 = order.index(tile1), order.index(tile2)
            order[i1], order[i2] = order[i2], order[i1]
            self.set_tile_order(order, layout)

    def set_autostart(self, enabled: bool):
        self.autostart = enabled
        self.save()
        os.makedirs(AUTOSTART_DIR, exist_ok=True)

        if enabled:
            desktop = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Exec=env DISPLAY=:1 /usr/bin/python3 {APP_DIR}/mystem_sonitor.py
Icon={APP_DIR}/icon.png
Terminal=false
Categories=System;Monitor;
X-GNOME-Autostart-enabled=true
"""
            with open(AUTOSTART_FILE, 'w') as f:
                f.write(desktop)
        else:
            if os.path.exists(AUTOSTART_FILE):
                os.remove(AUTOSTART_FILE)


# ============================================================================
# Main Window
# ============================================================================

class MystemSonitor(Gtk.Window):
    def __init__(self):
        super().__init__()

        psutil.cpu_percent(interval=None)

        self.config = ConfigManager()
        self.tiles = {}
        self._dragging = False
        self._drag_x = 0
        self._drag_y = 0

        # Window setup - no decorations
        self.set_title(APP_NAME)
        self.set_decorated(False)
        self.set_resizable(True)
        self.set_keep_above(True)
        self.set_app_paintable(True)

        # Enable window drag
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect('button-press-event', self._on_button_press)
        self.connect('button-release-event', self._on_button_release)
        self.connect('motion-notify-event', self._on_motion)

        self._set_icon()
        self._apply_css()

        # Main container
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.main_box.get_style_context().add_class('main-container')
        self.add(self.main_box)

        # Custom header bar
        self._create_header()

        # Content
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.content.set_margin_start(8)
        self.content.set_margin_end(8)
        self.content.set_margin_bottom(8)
        self.main_box.pack_start(self.content, True, True, 0)

        self._build_tiles()

        # I/O tracking
        self._last_disk = psutil.disk_io_counters()
        self._last_net = psutil.net_io_counters()

        # Update timer
        GLib.timeout_add(500, lambda: (self._update(), False)[-1])
        GLib.timeout_add(UPDATE_INTERVAL_MS, self._update)

    def _on_button_press(self, w, e):
        if e.button == 1 and e.y < 35:  # Header area
            self._dragging = True
            self._drag_x = e.x
            self._drag_y = e.y

    def _on_button_release(self, w, e):
        self._dragging = False

    def _on_motion(self, w, e):
        if self._dragging:
            x, y = self.get_position()
            self.move(x + int(e.x - self._drag_x), y + int(e.y - self._drag_y))

    def _create_header(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        header.set_margin_start(10)
        header.set_margin_end(5)
        header.set_margin_top(5)
        header.set_margin_bottom(5)
        header.get_style_context().add_class('custom-header')

        # App icon/title
        title = Gtk.Label(label=f"⚡ {APP_NAME}")
        title.get_style_context().add_class('header-title')
        header.pack_start(title, False, False, 0)

        # Spacer
        header.pack_start(Gtk.Box(), True, True, 0)

        # Settings button
        settings_btn = Gtk.MenuButton()
        settings_btn.set_relief(Gtk.ReliefStyle.NONE)
        settings_btn.add(Gtk.Label(label="⚙"))
        settings_btn.get_style_context().add_class('header-btn')

        # Settings menu
        menu = Gtk.Menu()

        # Visualization submenu (radio group)
        vis_menu = Gtk.Menu()
        vis_item = Gtk.MenuItem(label="Visualization")
        vis_item.set_submenu(vis_menu)
        vis_group = []
        for mode in VIS_MODES:
            item = Gtk.RadioMenuItem.new_with_label(vis_group, mode.capitalize())
            vis_group = item.get_group()
            item.set_active(mode == self.config.vis_mode)
            item.connect('toggled', self._on_vis_change, mode)
            vis_menu.append(item)
        menu.append(vis_item)

        # Layout submenu (radio group)
        layout_menu = Gtk.Menu()
        layout_item = Gtk.MenuItem(label="Layout")
        layout_item.set_submenu(layout_menu)
        layout_group = []
        for layout in LAYOUTS:
            item = Gtk.RadioMenuItem.new_with_label(layout_group, layout.capitalize())
            layout_group = item.get_group()
            item.set_active(layout == self.config.layout)
            item.connect('toggled', self._on_layout_change, layout)
            layout_menu.append(item)
        menu.append(layout_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Autostart toggle
        autostart_item = Gtk.CheckMenuItem(label="Autostart")
        autostart_item.set_active(self.config.autostart)
        autostart_item.connect('toggled', self._on_autostart_toggle)
        menu.append(autostart_item)

        menu.append(Gtk.SeparatorMenuItem())

        # About
        about_item = Gtk.MenuItem(label="About")
        about_item.connect('activate', self._show_about)
        menu.append(about_item)

        menu.show_all()
        settings_btn.set_popup(menu)
        header.pack_end(settings_btn, False, False, 0)

        # Minimize button
        min_btn = Gtk.Button(label="─")
        min_btn.set_relief(Gtk.ReliefStyle.NONE)
        min_btn.get_style_context().add_class('header-btn')
        min_btn.connect('clicked', lambda b: self.iconify())
        header.pack_end(min_btn, False, False, 0)

        # Close button
        close_btn = Gtk.Button(label="✕")
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.get_style_context().add_class('header-btn-close')
        close_btn.connect('clicked', lambda b: Gtk.main_quit())
        header.pack_end(close_btn, False, False, 0)

        self.main_box.pack_start(header, False, False, 0)

    def _on_vis_change(self, item, mode):
        if item.get_active() and self.config.vis_mode != mode:
            self.config.vis_mode = mode
            self.config.save()
            self._build_tiles()
            self.show_all()

    def _on_layout_change(self, item, layout):
        if item.get_active() and self.config.layout != layout:
            self.config.layout = layout
            self.config.save()
            self._build_tiles()
            self.show_all()

    def _on_autostart_toggle(self, item):
        self.config.set_autostart(item.get_active())

    def _show_about(self, item):
        dialog = Gtk.AboutDialog(transient_for=self)
        dialog.set_program_name(APP_NAME)
        dialog.set_version("1.0.0")
        dialog.set_authors(["alienxs2"])
        dialog.set_comments("Advanced System Resource Monitor")
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.run()
        dialog.destroy()

    def _create_widget(self, tile_name: str, label: str, unit: str = "%"):
        """Create widget with tile-specific visualization mode."""
        mode = self.config.get_tile_mode(tile_name)
        if mode == "gauge": widget = GaugeWidget(label, unit)
        elif mode == "arc": widget = ArcWidget(label, unit)
        elif mode == "ring": widget = RingWidget(label, unit)
        elif mode == "minimal": widget = MinimalWidget(label, unit)
        else: widget = BarWidget(label, unit)
        return widget

    def _wrap_tile(self, tile_name: str, widget):
        """Wrap widget in TileContainer for click settings and drag-drop."""
        return TileContainer(tile_name, widget, self.config, self._on_tile_mode_change, self._on_tile_reorder)

    def _on_tile_mode_change(self, tile_name: str):
        """Rebuild tiles when individual tile mode changes."""
        self._build_tiles()
        self.show_all()

    def _on_tile_reorder(self, source: str, target: str):
        """Handle tile reorder via drag-drop."""
        self.config.swap_tiles(source, target)
        self._build_tiles()
        self.show_all()

    def _build_tiles(self):
        for child in self.content.get_children():
            self.content.remove(child)

        self.tiles = {}
        layout = self.config.layout

        if layout == "compact":
            self._build_compact()
        elif layout == "wide":
            self._build_wide()
        elif layout == "vertical":
            self._build_vertical()
        else:  # mini
            self._build_mini()

        self._apply_size()

    def _build_compact(self):
        order = self.config.get_tile_order("compact")
        row1 = Gtk.Box(spacing=5, homogeneous=True)
        row2 = Gtk.Box(spacing=5, homogeneous=True)

        # Create all widgets
        tile_widgets = {
            "cpu": self._wrap_tile("cpu", self._create_widget("cpu", "CPU")),
            "ram": self._wrap_tile("ram", self._create_widget("ram", "RAM")),
            "swap": self._wrap_tile("swap", self._create_widget("swap", "Swap")),
            "gpu": self._wrap_tile("gpu", self._create_widget("gpu", "GPU")),
            "vram": self._wrap_tile("vram", self._create_widget("vram", "VRAM")),
            "disk": self._wrap_tile("disk", IOWidget("Disk")),
            "net": self._wrap_tile("net", IOWidget("Network")),
            "temp": self._wrap_tile("temp", self._create_widget("temp", "Temp", "°C")),
        }

        self.tiles = tile_widgets

        # Add in order
        for i, name in enumerate(order):
            if name in tile_widgets:
                if i < 4:
                    row1.pack_start(tile_widgets[name], True, True, 0)
                else:
                    row2.pack_start(tile_widgets[name], True, True, 0)

        self.content.pack_start(row1, False, False, 0)
        self.content.pack_start(row2, False, False, 0)

    def _build_wide(self):
        order = self.config.get_tile_order("wide")
        row = Gtk.Box(spacing=3, homogeneous=True)

        tile_widgets = {
            "cpu": self._wrap_tile("cpu", self._create_widget("cpu", "CPU")),
            "ram": self._wrap_tile("ram", self._create_widget("ram", "RAM")),
            "gpu": self._wrap_tile("gpu", self._create_widget("gpu", "GPU")),
            "temp": self._wrap_tile("temp", self._create_widget("temp", "Temp", "°C")),
        }

        self.tiles = tile_widgets

        for name in order:
            if name in tile_widgets:
                row.pack_start(tile_widgets[name], True, True, 0)

        self.content.pack_start(row, False, False, 0)

    def _build_vertical(self):
        order = self.config.get_tile_order("vertical")

        tile_widgets = {
            "cpu": self._wrap_tile("cpu", self._create_widget("cpu", "CPU")),
            "ram": self._wrap_tile("ram", self._create_widget("ram", "RAM")),
            "swap": self._wrap_tile("swap", self._create_widget("swap", "Swap")),
            "gpu": self._wrap_tile("gpu", self._create_widget("gpu", "GPU")),
            "vram": self._wrap_tile("vram", self._create_widget("vram", "VRAM")),
            "temp": self._wrap_tile("temp", self._create_widget("temp", "Temp", "°C")),
            "disk": self._wrap_tile("disk", IOWidget("Disk")),
            "net": self._wrap_tile("net", IOWidget("Network")),
        }

        self.tiles = tile_widgets

        for name in order:
            if name in tile_widgets:
                self.content.pack_start(tile_widgets[name], False, False, 2)

    def _build_mini(self):
        order = self.config.get_tile_order("mini")
        row = Gtk.Box(spacing=5, homogeneous=True)

        tile_widgets = {
            "cpu": self._wrap_tile("cpu", self._create_widget("cpu", "CPU")),
            "ram": self._wrap_tile("ram", self._create_widget("ram", "RAM")),
            "gpu": self._wrap_tile("gpu", self._create_widget("gpu", "GPU")),
        }

        self.tiles = tile_widgets

        for name in order:
            if name in tile_widgets:
                row.pack_start(tile_widgets[name], True, True, 0)

        self.content.pack_start(row, False, False, 0)

    def _apply_size(self):
        sizes = {
            "compact": (480, 220 if self.config.vis_mode in ["gauge", "arc", "ring"] else 180),
            "wide": (400, 120 if self.config.vis_mode in ["gauge", "arc", "ring"] else 100),
            "vertical": (130, 550 if self.config.vis_mode in ["gauge", "arc", "ring"] else 450),
            "mini": (300, 100 if self.config.vis_mode in ["gauge", "arc", "ring"] else 80),
        }
        w, h = sizes.get(self.config.layout, (480, 180))
        self.set_default_size(w, h)
        self.resize(w, h)

    def _set_icon(self):
        icon_path = os.path.join(APP_DIR, "icon.png")
        if os.path.exists(icon_path):
            self.set_icon_from_file(icon_path)

    def _apply_css(self):
        css = b"""
        .main-container {
            background-color: #1a1a1e;
            border-radius: 10px;
            border: 1px solid #333;
        }

        .custom-header {
            background-color: #252528;
            border-radius: 10px 10px 0 0;
        }

        .header-title {
            color: #4CAF50;
            font-weight: bold;
            font-size: 12px;
        }

        .header-btn {
            color: #888;
            min-width: 24px;
            min-height: 24px;
            padding: 0;
            border-radius: 4px;
        }
        .header-btn:hover { background-color: #444; color: #fff; }

        .header-btn-close {
            color: #888;
            min-width: 24px;
            min-height: 24px;
            padding: 0;
            border-radius: 4px;
        }
        .header-btn-close:hover { background-color: #e53935; color: #fff; }

        .bar-widget { padding: 5px; }
        .bar-label { color: #888; font-size: 11px; }
        .bar-value { font-size: 12px; }
        .bar-details { color: #555; font-size: 9px; }

        .health-bar, .health-bar trough {
            min-height: 6px;
            border-radius: 3px;
            background-color: #333;
        }
        .health-bar progress { min-height: 6px; border-radius: 3px; }

        .mini-label { color: #888; font-size: 10px; }
        .mini-value { font-size: 14px; }

        .io-label { color: #888; font-size: 10px; font-weight: bold; }
        .io-read { color: #4FC3F7; font-size: 11px; font-weight: bold; }
        .io-write { color: #FFB74D; font-size: 11px; font-weight: bold; }

        menu { background-color: #2a2a2e; }
        menuitem { color: #ccc; }
        menuitem:hover { background-color: #444; }

        .tile-container {
            border-radius: 6px;
            transition: all 200ms ease;
        }
        .tile-container:hover {
            background-color: rgba(255, 255, 255, 0.05);
        }
        .dragging {
            opacity: 0.6;
            background-color: rgba(76, 175, 80, 0.2);
            border: 1px dashed #4CAF50;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _update(self):
        try:
            # CPU
            cpu = psutil.cpu_percent(interval=None)
            freq = psutil.cpu_freq()
            if "cpu" in self.tiles:
                self.tiles["cpu"].set_value(cpu, f"{freq.current:.0f}MHz" if freq else "")

            # RAM
            mem = psutil.virtual_memory()
            if "ram" in self.tiles:
                self.tiles["ram"].set_value(mem.percent, f"{mem.used/(1024**3):.1f}/{mem.total/(1024**3):.0f}G")

            # Swap
            swap = psutil.swap_memory()
            if "swap" in self.tiles:
                self.tiles["swap"].set_value(swap.percent, f"{swap.used/(1024**3):.1f}/{swap.total/(1024**3):.0f}G")

            # GPU
            gpu = GPUMonitor.get_info()
            if gpu:
                if "gpu" in self.tiles:
                    self.tiles["gpu"].set_value(gpu["util"], gpu["name"])
                if "vram" in self.tiles:
                    vram = (gpu["mem_used"] / gpu["mem_total"]) * 100
                    self.tiles["vram"].set_value(vram, f"{gpu['mem_used']:.0f}/{gpu['mem_total']:.0f}M")
                if "temp" in self.tiles:
                    self.tiles["temp"].set_value(gpu["temp"], "GPU")
            else:
                if "gpu" in self.tiles: self.tiles["gpu"].set_value(0, "N/A")
                if "vram" in self.tiles: self.tiles["vram"].set_value(0, "N/A")
                if "temp" in self.tiles: self.tiles["temp"].set_value(0, "N/A")

            # Disk
            disk = psutil.disk_io_counters()
            if disk and self._last_disk and "disk" in self.tiles:
                r = disk.read_bytes - self._last_disk.read_bytes
                w = disk.write_bytes - self._last_disk.write_bytes
                self.tiles["disk"].set_values(max(0, r), max(0, w))
            self._last_disk = disk

            # Network
            net = psutil.net_io_counters()
            if net and self._last_net and "net" in self.tiles:
                r = net.bytes_recv - self._last_net.bytes_recv
                s = net.bytes_sent - self._last_net.bytes_sent
                self.tiles["net"].set_values(max(0, r), max(0, s))
            self._last_net = net

        except Exception as e:
            print(f"Update error: {e}")

        return True


def main():
    win = MystemSonitor()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
