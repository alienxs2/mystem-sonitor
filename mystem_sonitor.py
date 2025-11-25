#!/usr/bin/env python3
"""
Mystem Sonitor - Advanced System Resource Monitor

Features:
- Multiple visualization modes (click to cycle)
- Color themes
- Custom window decoration
- Layout switching

Author: Goncharenko Anton (alienxs2)
License: MIT
"""

import subprocess
import os
import math
from typing import Optional, Dict, Any

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk
import cairo

import psutil


# ============================================================================
# Configuration
# ============================================================================

APP_NAME = "Mystem Sonitor"
UPDATE_INTERVAL_MS = 1000
CONFIG_DIR = os.path.expanduser("~/.config/mystem-sonitor")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.ini")
AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "mystem-sonitor.desktop")
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Visualization modes for regular tiles (terminal is default)
VIS_MODES = ["terminal", "gauge", "text", "wave", "glow"]
# Visualization modes for IO tiles (Disk/Net)
IO_MODES = ["terminal", "bars", "text"]
# Layouts
LAYOUTS = ["compact", "wide", "vertical", "mini", "dashboard", "panel"]

# Color themes
THEMES = {
    "default": {
        "name": "Default",
        "bg": "#1a1a1e",
        "header": "#252528",
        "tile_bg": "#222226",
        "accent": "#4CAF50",
        "text": "#ffffff",
        "text_dim": "#888888",
        "good": (0.30, 0.85, 0.40),
        "warn": (1.00, 0.75, 0.20),
        "danger": (1.00, 0.35, 0.30),
    },
    "ocean": {
        "name": "Ocean",
        "bg": "#0d1b2a",
        "header": "#1b263b",
        "tile_bg": "#152238",
        "accent": "#00b4d8",
        "text": "#e0f4ff",
        "text_dim": "#6b8fa3",
        "good": (0.00, 0.75, 0.90),
        "warn": (0.30, 0.90, 0.70),
        "danger": (0.95, 0.45, 0.55),
    },
    "sunset": {
        "name": "Sunset",
        "bg": "#1a1423",
        "header": "#2d1f3d",
        "tile_bg": "#261a35",
        "accent": "#ff6b6b",
        "text": "#ffe8e8",
        "text_dim": "#9a7a8a",
        "good": (1.00, 0.55, 0.45),
        "warn": (1.00, 0.85, 0.35),
        "danger": (1.00, 0.30, 0.40),
    },
    "matrix": {
        "name": "Matrix",
        "bg": "#0a0f0a",
        "header": "#0f1a0f",
        "tile_bg": "#0d150d",
        "accent": "#00ff41",
        "text": "#00ff41",
        "text_dim": "#306030",
        "good": (0.00, 1.00, 0.25),
        "warn": (0.50, 1.00, 0.00),
        "danger": (1.00, 0.25, 0.25),
    },
    "nord": {
        "name": "Nord",
        "bg": "#2e3440",
        "header": "#3b4252",
        "tile_bg": "#353c4a",
        "accent": "#88c0d0",
        "text": "#eceff4",
        "text_dim": "#7b88a1",
        "good": (0.53, 0.75, 0.82),
        "warn": (0.92, 0.80, 0.55),
        "danger": (0.75, 0.38, 0.42),
    },
    "purple": {
        "name": "Purple",
        "bg": "#13111c",
        "header": "#1e1a2e",
        "tile_bg": "#1a1628",
        "accent": "#bd93f9",
        "text": "#f8f0ff",
        "text_dim": "#7a6a9a",
        "good": (0.74, 0.58, 0.98),
        "warn": (1.00, 0.72, 0.42),
        "danger": (1.00, 0.33, 0.44),
    },
}
THEME_ORDER = list(THEMES.keys())


def get_health_color(percent: float, theme: dict) -> tuple:
    """Get RGB color based on percentage and theme."""
    good = theme["good"]
    warn = theme["warn"]
    danger = theme["danger"]

    if percent <= 50:
        return good
    elif percent <= 75:
        t = (percent - 50) / 25
        return (
            good[0] + t * (warn[0] - good[0]),
            good[1] + t * (warn[1] - good[1]),
            good[2] + t * (warn[2] - good[2])
        )
    else:
        t = min(1.0, (percent - 75) / 25)
        return (
            warn[0] + t * (danger[0] - warn[0]),
            warn[1] + t * (danger[1] - warn[1]),
            warn[2] + t * (danger[2] - warn[2])
        )


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple (0-1 range)."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))


# ============================================================================
# Visualization Widgets
# ============================================================================

class BaseWidget(Gtk.DrawingArea):
    """Base class for visualization widgets."""

    def __init__(self, label: str = "", unit: str = "%"):
        super().__init__()
        self.label = label
        self.unit = unit
        self.value = 0
        self.theme = THEMES["default"]
        self.set_size_request(100, 70)
        self.connect('draw', self.on_draw)

    def set_value(self, value: float, details: str = ""):
        self.value = min(100, max(0, value))
        self.queue_draw()

    def set_theme(self, theme: dict):
        self.theme = theme
        self.queue_draw()

    def on_draw(self, widget, cr):
        pass

    def _draw_tile_bg(self, cr, w, h, radius=6):
        """Draw rounded tile background."""
        bg = hex_to_rgb(self.theme["tile_bg"])
        cr.set_source_rgb(*bg)
        self._rounded_rect(cr, 1, 1, w - 2, h - 2, radius)
        cr.fill()

    def _rounded_rect(self, cr, x, y, w, h, r):
        """Draw rounded rectangle path."""
        cr.new_path()
        cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
        cr.arc(x + w - r, y + r, r, 1.5 * math.pi, 2 * math.pi)
        cr.arc(x + w - r, y + h - r, r, 0, 0.5 * math.pi)
        cr.arc(x + r, y + h - r, r, 0.5 * math.pi, math.pi)
        cr.close_path()


class GaugeWidget(BaseWidget):
    """Speedometer-style gauge - clean and readable."""

    def __init__(self, label: str = "", unit: str = "%"):
        super().__init__(label, unit)
        self.set_size_request(110, 85)

    def on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        self._draw_tile_bg(cr, w, h)

        color = get_health_color(self.value, self.theme)
        dim_color = hex_to_rgb(self.theme["text_dim"])

        cx, cy = w / 2, h * 0.52
        radius = min(w, h) * 0.36

        # Background arc
        cr.set_line_width(8)
        cr.set_source_rgb(0.18, 0.18, 0.20)
        cr.arc(cx, cy, radius, math.pi * 0.75, math.pi * 2.25)
        cr.stroke()

        # Value arc
        cr.set_source_rgb(*color)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        end_angle = math.pi * 0.75 + (self.value / 100) * math.pi * 1.5
        cr.arc(cx, cy, radius, math.pi * 0.75, end_angle)
        cr.stroke()

        # Value text (center)
        cr.set_source_rgb(*color)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(20)
        text = f"{self.value:.0f}"
        ext = cr.text_extents(text)
        cr.move_to(cx - ext.width / 2, cy + 8)
        cr.show_text(text)

        # Label (bottom)
        cr.set_source_rgb(*dim_color)
        cr.set_font_size(11)
        ext = cr.text_extents(self.label)
        cr.move_to(cx - ext.width / 2, h - 6)
        cr.show_text(self.label)


class TextWidget(BaseWidget):
    """Large text display - bold and clear."""

    def __init__(self, label: str = "", unit: str = "%"):
        super().__init__(label, unit)
        self.set_size_request(90, 65)

    def on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        self._draw_tile_bg(cr, w, h)

        color = get_health_color(self.value, self.theme)
        dim_color = hex_to_rgb(self.theme["text_dim"])

        # Large value
        cr.set_source_rgb(*color)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(28)
        text = f"{self.value:.0f}"
        ext = cr.text_extents(text)
        x = w / 2 - ext.width / 2 - 5
        cr.move_to(x, h * 0.55)
        cr.show_text(text)

        # Unit
        cr.set_font_size(14)
        cr.move_to(x + ext.width + 3, h * 0.55)
        cr.show_text(self.unit)

        # Label
        cr.set_source_rgb(*dim_color)
        cr.set_font_size(11)
        ext = cr.text_extents(self.label)
        cr.move_to(w / 2 - ext.width / 2, h - 8)
        cr.show_text(self.label)


class WaveWidget(BaseWidget):
    """Wave/tank indicator - animated feel."""

    def __init__(self, label: str = "", unit: str = "%"):
        super().__init__(label, unit)
        self.set_size_request(90, 70)
        self._phase = 0

    def set_value(self, value: float, details: str = ""):
        super().set_value(value, details)
        self._phase += 0.15

    def on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        self._draw_tile_bg(cr, w, h)

        color = get_health_color(self.value, self.theme)
        dim_color = hex_to_rgb(self.theme["text_dim"])

        # Tank container
        tank_x, tank_y = 12, 18
        tank_w, tank_h = w - 24, h - 40

        cr.set_source_rgb(0.12, 0.12, 0.14)
        self._rounded_rect(cr, tank_x, tank_y, tank_w, tank_h, 4)
        cr.fill()

        # Wave fill
        fill_h = tank_h * (self.value / 100)
        base_y = tank_y + tank_h - fill_h

        if fill_h > 2:
            cr.save()
            self._rounded_rect(cr, tank_x, tank_y, tank_w, tank_h, 4)
            cr.clip()

            cr.set_source_rgb(*color)
            cr.move_to(tank_x, base_y)
            for x in range(int(tank_x), int(tank_x + tank_w) + 1):
                wave_y = base_y + math.sin((x - tank_x) * 0.12 + self._phase) * 3
                cr.line_to(x, wave_y)
            cr.line_to(tank_x + tank_w, tank_y + tank_h)
            cr.line_to(tank_x, tank_y + tank_h)
            cr.close_path()
            cr.fill()
            cr.restore()

        # Value on top
        cr.set_source_rgb(*color)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(12)
        text = f"{self.value:.0f}{self.unit}"
        ext = cr.text_extents(text)
        cr.move_to(w / 2 - ext.width / 2, 13)
        cr.show_text(text)

        # Label
        cr.set_source_rgb(*dim_color)
        cr.set_font_size(10)
        ext = cr.text_extents(self.label)
        cr.move_to(w / 2 - ext.width / 2, h - 5)
        cr.show_text(self.label)


class GlowWidget(BaseWidget):
    """Glowing orb style - like a sun/lamp with radial gradient."""

    def __init__(self, label: str = "", unit: str = "%"):
        super().__init__(label, unit)
        self.set_size_request(100, 80)

    def on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        self._draw_tile_bg(cr, w, h)

        color = get_health_color(self.value, self.theme)
        dim_color = hex_to_rgb(self.theme["text_dim"])

        cx, cy = w / 2, h * 0.45
        radius = min(w, h) * 0.32

        # Create radial gradient for glow effect
        # Intensity based on value (brighter when higher)
        intensity = 0.3 + (self.value / 100) * 0.7

        gradient = cairo.RadialGradient(cx, cy, 0, cx, cy, radius * 1.5)

        # Inner glow (bright)
        gradient.add_color_stop_rgba(0, color[0], color[1], color[2], intensity)
        # Middle (fading)
        gradient.add_color_stop_rgba(0.5, color[0], color[1], color[2], intensity * 0.5)
        # Outer (very faint)
        gradient.add_color_stop_rgba(1.0, color[0], color[1], color[2], 0.05)

        cr.set_source(gradient)
        cr.arc(cx, cy, radius * 1.5, 0, 2 * math.pi)
        cr.fill()

        # Inner bright core
        core_gradient = cairo.RadialGradient(cx, cy, 0, cx, cy, radius * 0.6)
        core_gradient.add_color_stop_rgba(0, 1.0, 1.0, 1.0, intensity * 0.8)
        core_gradient.add_color_stop_rgba(0.5, color[0], color[1], color[2], intensity)
        core_gradient.add_color_stop_rgba(1.0, color[0], color[1], color[2], intensity * 0.3)

        cr.set_source(core_gradient)
        cr.arc(cx, cy, radius * 0.6, 0, 2 * math.pi)
        cr.fill()

        # Value text in center
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(18)
        text = f"{self.value:.0f}"
        ext = cr.text_extents(text)
        cr.move_to(cx - ext.width / 2, cy + 6)
        cr.show_text(text)

        # Label below
        cr.set_source_rgb(*dim_color)
        cr.set_font_size(11)
        ext = cr.text_extents(self.label)
        cr.move_to(cx - ext.width / 2, h - 5)
        cr.show_text(self.label)


class TerminalWidget(BaseWidget):
    """Terminal-style display - looks like mini console."""

    def __init__(self, label: str = "", unit: str = "%"):
        super().__init__(label, unit)
        self.set_size_request(120, 80)
        self._cursor = True
        self._tick = 0

    def set_value(self, value: float, details: str = ""):
        super().set_value(value, details)
        self._tick += 1
        if self._tick % 2 == 0:
            self._cursor = not self._cursor

    def on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        # Terminal background
        cr.set_source_rgb(0.05, 0.06, 0.05)
        self._rounded_rect(cr, 1, 1, w - 2, h - 2, 5)
        cr.fill()

        # Title bar
        cr.set_source_rgb(0.12, 0.14, 0.12)
        self._rounded_rect(cr, 1, 1, w - 2, 14, 5)
        cr.fill()
        cr.rectangle(1, 10, w - 2, 5)
        cr.fill()

        # Window buttons
        for i, c in enumerate([(0.9, 0.35, 0.35), (0.9, 0.75, 0.25), (0.35, 0.85, 0.35)]):
            cr.set_source_rgb(*c)
            cr.arc(10 + i * 11, 8, 3.5, 0, 2 * math.pi)
            cr.fill()

        color = get_health_color(self.value, self.theme)

        # Terminal text
        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(11)

        y = 30
        lh = 13

        # Prompt line
        cr.set_source_rgb(0.3, 0.75, 0.35)
        cr.move_to(8, y)
        cr.show_text("$")
        cr.set_source_rgb(0.6, 0.65, 0.6)
        cr.move_to(18, y)
        cr.show_text(f"stat {self.label.lower()}")

        # Value line
        cr.set_source_rgb(*color)
        cr.set_font_size(13)
        cr.move_to(8, y + lh)
        bar_fill = int(self.value / 10)
        bar = "[" + "#" * bar_fill + "-" * (10 - bar_fill) + "]"
        cr.show_text(f"{self.value:5.1f}{self.unit} {bar}")

        # Status line
        cr.set_source_rgb(0.45, 0.5, 0.45)
        cr.set_font_size(10)
        status = "OK" if self.value < 60 else ("WARN" if self.value < 80 else "CRIT")
        cr.move_to(8, y + lh * 2)
        cr.show_text(f"status: {status}")

        # Blinking cursor
        if self._cursor:
            cr.set_source_rgb(0.3, 0.85, 0.35)
            cr.rectangle(8, y + lh * 2 + 4, 7, 11)
            cr.fill()


class CompactWidget(BaseWidget):
    """Very compact widget for narrow vertical layout."""

    def __init__(self, label: str = "", unit: str = "%"):
        super().__init__(label, unit)
        self.set_size_request(55, 40)

    def on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        self._draw_tile_bg(cr, w, h, 4)

        color = get_health_color(self.value, self.theme)
        dim_color = hex_to_rgb(self.theme["text_dim"])

        # Label (top)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(9)
        cr.set_source_rgb(*dim_color)
        ext = cr.text_extents(self.label)
        cr.move_to((w - ext.width) / 2, 12)
        cr.show_text(self.label)

        # Value (center)
        cr.set_source_rgb(*color)
        cr.set_font_size(14)
        text = f"{self.value:.0f}"
        ext = cr.text_extents(text)
        cr.move_to((w - ext.width) / 2, h - 8)
        cr.show_text(text)


class CompactIOWidget(Gtk.DrawingArea):
    """Compact I/O widget for narrow vertical layout."""

    def __init__(self, label: str = ""):
        super().__init__()
        self.label_text = label
        self.read_val = 0
        self.write_val = 0
        self.theme = THEMES["default"]
        self.set_size_request(55, 40)
        self.connect('draw', self.on_draw)

    def set_values(self, read: float, write: float):
        self.read_val = read
        self.write_val = write
        self.queue_draw()

    def set_theme(self, theme: dict):
        self.theme = theme
        self.queue_draw()

    def _fmt_short(self, v: float) -> str:
        if v < 1024: return f"{v:.0f}B"
        if v < 1024**2: return f"{v/1024:.0f}K"
        if v < 1024**3: return f"{v/1024**2:.0f}M"
        return f"{v/1024**3:.0f}G"

    def _rounded_rect(self, cr, x, y, w, h, r):
        cr.new_path()
        cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
        cr.arc(x + w - r, y + r, r, 1.5 * math.pi, 2 * math.pi)
        cr.arc(x + w - r, y + h - r, r, 0, 0.5 * math.pi)
        cr.arc(x + r, y + h - r, r, 0.5 * math.pi, math.pi)
        cr.close_path()

    def on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        # Background
        bg = hex_to_rgb(self.theme["tile_bg"])
        cr.set_source_rgb(*bg)
        self._rounded_rect(cr, 1, 1, w - 2, h - 2, 4)
        cr.fill()

        dim_color = hex_to_rgb(self.theme["text_dim"])

        # Label
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(9)
        cr.set_source_rgb(*dim_color)
        ext = cr.text_extents(self.label_text)
        cr.move_to((w - ext.width) / 2, 12)
        cr.show_text(self.label_text)

        # R/W values
        cr.set_font_size(9)
        cr.set_source_rgb(*self.theme["good"])
        r_text = f"↓{self._fmt_short(self.read_val)}"
        ext = cr.text_extents(r_text)
        cr.move_to((w - ext.width) / 2, 25)
        cr.show_text(r_text)

        cr.set_source_rgb(*self.theme["warn"])
        w_text = f"↑{self._fmt_short(self.write_val)}"
        ext = cr.text_extents(w_text)
        cr.move_to((w - ext.width) / 2, 36)
        cr.show_text(w_text)


class IOWidget(Gtk.DrawingArea):
    """I/O display widget for Disk/Network - Terminal style only."""

    def __init__(self, label: str = ""):
        super().__init__()
        self.label_text = label
        self.read_val = 0
        self.write_val = 0
        self.theme = THEMES["default"]
        self.set_size_request(120, 70)
        self.connect('draw', self.on_draw)

    def set_values(self, read: float, write: float):
        self.read_val = read
        self.write_val = write
        self.queue_draw()

    def set_theme(self, theme: dict):
        self.theme = theme
        self.queue_draw()

    def _fmt_long(self, v: float) -> str:
        if v < 1024: return f"{v:.0f} B/s"
        if v < 1024**2: return f"{v/1024:.1f} KB/s"
        if v < 1024**3: return f"{v/1024**2:.1f} MB/s"
        return f"{v/1024**3:.1f} GB/s"

    def _rounded_rect(self, cr, x, y, w, h, r):
        cr.new_path()
        cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
        cr.arc(x + w - r, y + r, r, 1.5 * math.pi, 2 * math.pi)
        cr.arc(x + w - r, y + h - r, r, 0, 0.5 * math.pi)
        cr.arc(x + r, y + h - r, r, 0.5 * math.pi, math.pi)
        cr.close_path()

    def on_draw(self, widget, cr):
        """Terminal/console style."""
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        # Terminal background
        cr.set_source_rgb(0.05, 0.06, 0.05)
        self._rounded_rect(cr, 1, 1, w - 2, h - 2, 5)
        cr.fill()

        # Title bar
        cr.set_source_rgb(0.12, 0.14, 0.12)
        self._rounded_rect(cr, 1, 1, w - 2, 12, 5)
        cr.fill()
        cr.rectangle(1, 8, w - 2, 5)
        cr.fill()

        # Window buttons
        for i, c in enumerate([(0.9, 0.35, 0.35), (0.9, 0.75, 0.25), (0.35, 0.85, 0.35)]):
            cr.set_source_rgb(*c)
            cr.arc(9 + i * 9, 7, 2.5, 0, 2 * math.pi)
            cr.fill()

        # Terminal text
        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(10)

        y = 26
        lh = 12

        # Label line
        cr.set_source_rgb(0.3, 0.75, 0.35)
        cr.move_to(6, y)
        cr.show_text(f"$ iostat {self.label_text.lower()}")

        # Read line
        cr.set_source_rgb(*self.theme["good"])
        cr.move_to(6, y + lh)
        cr.show_text(f"rx: {self._fmt_long(self.read_val)}")

        # Write line
        cr.set_source_rgb(*self.theme["warn"])
        cr.move_to(6, y + lh * 2)
        cr.show_text(f"tx: {self._fmt_long(self.write_val)}")


class IOBarsWidget(Gtk.DrawingArea):
    """I/O display with horizontal bars for read/write."""

    def __init__(self, label: str = ""):
        super().__init__()
        self.label_text = label
        self.read_val = 0
        self.write_val = 0
        self.max_val = 1024 * 1024  # 1MB/s default max
        self.theme = THEMES["default"]
        self.set_size_request(120, 70)
        self.connect('draw', self.on_draw)

    def set_values(self, read: float, write: float):
        self.read_val = read
        self.write_val = write
        # Dynamic scaling
        max_v = max(read, write, self.max_val * 0.1)
        self.max_val = max(self.max_val * 0.95, max_v * 1.2)
        self.queue_draw()

    def set_theme(self, theme: dict):
        self.theme = theme
        self.queue_draw()

    def _fmt_short(self, v: float) -> str:
        if v < 1024: return f"{v:.0f}B"
        if v < 1024**2: return f"{v/1024:.0f}K"
        if v < 1024**3: return f"{v/1024**2:.1f}M"
        return f"{v/1024**3:.1f}G"

    def _rounded_rect(self, cr, x, y, w, h, r):
        cr.new_path()
        cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
        cr.arc(x + w - r, y + r, r, 1.5 * math.pi, 2 * math.pi)
        cr.arc(x + w - r, y + h - r, r, 0, 0.5 * math.pi)
        cr.arc(x + r, y + h - r, r, 0.5 * math.pi, math.pi)
        cr.close_path()

    def on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        # Background
        bg = hex_to_rgb(self.theme["tile_bg"])
        cr.set_source_rgb(*bg)
        self._rounded_rect(cr, 1, 1, w - 2, h - 2, 5)
        cr.fill()

        dim_color = hex_to_rgb(self.theme["text_dim"])

        # Label
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(11)
        cr.set_source_rgb(*dim_color)
        ext = cr.text_extents(self.label_text)
        cr.move_to((w - ext.width) / 2, 14)
        cr.show_text(self.label_text)

        bar_x = 10
        bar_w = w - 20
        bar_h = 8
        bar_r = 4  # Radius for rounded ends

        # Read bar
        read_pct = min(1.0, self.read_val / self.max_val) if self.max_val > 0 else 0

        # Background track
        cr.set_source_rgb(0.15, 0.15, 0.18)
        cr.rectangle(bar_x, 24, bar_w, bar_h)
        cr.fill()

        # Fill bar (simple rectangle, no rounding issues)
        if read_pct > 0.02:
            fill_w = bar_w * read_pct
            cr.set_source_rgb(*self.theme["good"])
            cr.rectangle(bar_x, 24, fill_w, bar_h)
            cr.fill()

        # Read text
        cr.set_font_size(9)
        cr.set_source_rgb(*self.theme["good"])
        cr.move_to(bar_x, 44)
        cr.show_text(f"↓ {self._fmt_short(self.read_val)}")

        # Write bar
        write_pct = min(1.0, self.write_val / self.max_val) if self.max_val > 0 else 0

        # Background track
        cr.set_source_rgb(0.15, 0.15, 0.18)
        cr.rectangle(bar_x, 50, bar_w, bar_h)
        cr.fill()

        # Fill bar
        if write_pct > 0.02:
            fill_w = bar_w * write_pct
            cr.set_source_rgb(*self.theme["warn"])
            cr.rectangle(bar_x, 50, fill_w, bar_h)
            cr.fill()

        # Write text
        cr.set_source_rgb(*self.theme["warn"])
        cr.move_to(bar_x, h - 5)
        cr.show_text(f"↑ {self._fmt_short(self.write_val)}")


class IOTextWidget(Gtk.DrawingArea):
    """Simple text-based I/O display."""

    def __init__(self, label: str = ""):
        super().__init__()
        self.label_text = label
        self.read_val = 0
        self.write_val = 0
        self.theme = THEMES["default"]
        self.set_size_request(100, 65)
        self.connect('draw', self.on_draw)

    def set_values(self, read: float, write: float):
        self.read_val = read
        self.write_val = write
        self.queue_draw()

    def set_theme(self, theme: dict):
        self.theme = theme
        self.queue_draw()

    def _fmt_short(self, v: float) -> str:
        if v < 1024: return f"{v:.0f}B"
        if v < 1024**2: return f"{v/1024:.0f}K"
        if v < 1024**3: return f"{v/1024**2:.1f}M"
        return f"{v/1024**3:.1f}G"

    def _rounded_rect(self, cr, x, y, w, h, r):
        cr.new_path()
        cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
        cr.arc(x + w - r, y + r, r, 1.5 * math.pi, 2 * math.pi)
        cr.arc(x + w - r, y + h - r, r, 0, 0.5 * math.pi)
        cr.arc(x + r, y + h - r, r, 0.5 * math.pi, math.pi)
        cr.close_path()

    def on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        # Background
        bg = hex_to_rgb(self.theme["tile_bg"])
        cr.set_source_rgb(*bg)
        self._rounded_rect(cr, 1, 1, w - 2, h - 2, 5)
        cr.fill()

        dim_color = hex_to_rgb(self.theme["text_dim"])

        # Label
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(11)
        cr.set_source_rgb(*dim_color)
        ext = cr.text_extents(self.label_text)
        cr.move_to((w - ext.width) / 2, 16)
        cr.show_text(self.label_text)

        # Read value
        cr.set_font_size(16)
        cr.set_source_rgb(*self.theme["good"])
        r_text = f"↓{self._fmt_short(self.read_val)}"
        ext = cr.text_extents(r_text)
        cr.move_to((w - ext.width) / 2, 36)
        cr.show_text(r_text)

        # Write value
        cr.set_source_rgb(*self.theme["warn"])
        w_text = f"↑{self._fmt_short(self.write_val)}"
        ext = cr.text_extents(w_text)
        cr.move_to((w - ext.width) / 2, 55)
        cr.show_text(w_text)


# ============================================================================
# Clickable Tile Container
# ============================================================================

class TileContainer(Gtk.EventBox):
    """Clickable container - left click cycles visualization mode."""

    def __init__(self, tile_name: str, on_mode_cycle):
        super().__init__()
        self.tile_name = tile_name
        self.on_mode_cycle = on_mode_cycle
        self.inner = None

        self.set_above_child(True)  # EventBox receives events before child
        self.set_visible_window(False)  # Transparent window
        self.get_style_context().add_class('tile-container')
        self.connect('button-press-event', self._on_click)

    def set_widget(self, widget):
        if self.inner:
            self.remove(self.inner)
        self.inner = widget
        self.add(widget)
        widget.show()

    def _on_click(self, widget, event):
        if event.button == 1:
            self.on_mode_cycle(self.tile_name)
            return True
        return False

    def set_value(self, value: float, details: str = ""):
        if self.inner and hasattr(self.inner, 'set_value'):
            self.inner.set_value(value, details)

    def set_values(self, read: float, write: float):
        if self.inner and hasattr(self.inner, 'set_values'):
            self.inner.set_values(read, write)

    def set_theme(self, theme: dict):
        if self.inner and hasattr(self.inner, 'set_theme'):
            self.inner.set_theme(theme)


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
        except:
            pass
        return None


# ============================================================================
# Config Manager
# ============================================================================

class ConfigManager:
    def __init__(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.layout = "compact"
        self.vis_mode = "terminal"  # Default mode
        self.io_mode = "terminal"   # Default IO mode
        self.theme = "default"
        self.autostart = False
        self.tile_modes = {}    # For regular tiles
        self.io_tile_modes = {} # For IO tiles (disk, net)
        self.window_x = -1
        self.window_y = -1
        self.tile_order = []
        self.load()

    def load(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE) as f:
                    for line in f:
                        if '=' in line:
                            k, v = line.strip().split('=', 1)
                            if k == 'layout' and v in LAYOUTS:
                                self.layout = v
                            elif k == 'vis_mode' and v in VIS_MODES:
                                self.vis_mode = v
                            elif k == 'io_mode' and v in IO_MODES:
                                self.io_mode = v
                            elif k == 'theme' and v in THEMES:
                                self.theme = v
                            elif k == 'autostart':
                                self.autostart = v == 'true'
                            elif k == 'window_x':
                                self.window_x = int(v)
                            elif k == 'window_y':
                                self.window_y = int(v)
                            elif k == 'tile_order' and v:
                                self.tile_order = v.split(',')
                            elif k.startswith('io_') and v in IO_MODES:
                                self.io_tile_modes[k[3:]] = v
                            elif k.startswith('tile_') and v in VIS_MODES:
                                self.tile_modes[k[5:]] = v
        except:
            pass

    def save(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                f.write(f"layout={self.layout}\n")
                f.write(f"vis_mode={self.vis_mode}\n")
                f.write(f"io_mode={self.io_mode}\n")
                f.write(f"theme={self.theme}\n")
                f.write(f"autostart={'true' if self.autostart else 'false'}\n")
                f.write(f"window_x={self.window_x}\n")
                f.write(f"window_y={self.window_y}\n")
                if self.tile_order:
                    f.write(f"tile_order={','.join(self.tile_order)}\n")
                for name, mode in self.tile_modes.items():
                    f.write(f"tile_{name}={mode}\n")
                for name, mode in self.io_tile_modes.items():
                    f.write(f"io_{name}={mode}\n")
        except:
            pass

    def get_tile_mode(self, name: str) -> str:
        return self.tile_modes.get(name, self.vis_mode)

    def get_io_mode(self, name: str) -> str:
        return self.io_tile_modes.get(name, self.io_mode)

    def set_window_pos(self, x: int, y: int):
        self.window_x = x
        self.window_y = y
        self.save()

    def cycle_tile_mode(self, name: str):
        current = self.get_tile_mode(name)
        idx = VIS_MODES.index(current) if current in VIS_MODES else 0
        new_mode = VIS_MODES[(idx + 1) % len(VIS_MODES)]
        self.tile_modes[name] = new_mode
        self.save()
        return new_mode

    def cycle_io_mode(self, name: str):
        current = self.get_io_mode(name)
        idx = IO_MODES.index(current) if current in IO_MODES else 0
        new_mode = IO_MODES[(idx + 1) % len(IO_MODES)]
        self.io_tile_modes[name] = new_mode
        self.save()
        return new_mode

    def cycle_layout(self):
        idx = LAYOUTS.index(self.layout) if self.layout in LAYOUTS else 0
        self.layout = LAYOUTS[(idx + 1) % len(LAYOUTS)]
        self.save()
        return self.layout

    def cycle_theme(self):
        idx = THEME_ORDER.index(self.theme) if self.theme in THEME_ORDER else 0
        self.theme = THEME_ORDER[(idx + 1) % len(THEME_ORDER)]
        self.save()
        return self.theme

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

        # Window setup
        self.set_title(APP_NAME)
        self.set_decorated(False)
        self.set_resizable(True)
        self.set_keep_above(True)
        self.set_app_paintable(True)
        self.set_wmclass("mystem-sonitor", "Mystem Sonitor")

        # Window drag
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                       Gdk.EventMask.BUTTON_RELEASE_MASK |
                       Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect('button-press-event', self._on_button_press)
        self.connect('button-release-event', self._on_button_release)
        self.connect('motion-notify-event', self._on_motion)

        self._set_icon()
        self._apply_css()

        # Main container
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.main_box.get_style_context().add_class('main-container')
        self.add(self.main_box)

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

        # Restore window position
        self.connect('realize', self._on_realize)
        self.connect('configure-event', self._on_configure)
        self.connect('destroy', self._on_destroy)

    def _on_realize(self, widget):
        """Restore window position after window is realized."""
        if self.config.window_x >= 0 and self.config.window_y >= 0:
            self.move(self.config.window_x, self.config.window_y)

    def _on_configure(self, widget, event):
        """Save window position on move."""
        x, y = self.get_position()
        if x != self.config.window_x or y != self.config.window_y:
            self.config.window_x = x
            self.config.window_y = y
        return False

    def _on_destroy(self, widget):
        """Save config on close."""
        self.config.save()

    def _on_button_press(self, w, e):
        if e.button == 1 and e.y < 40:
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
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.set_margin_start(10)
        header.set_margin_end(6)
        header.set_margin_top(6)
        header.set_margin_bottom(6)
        header.get_style_context().add_class('custom-header')

        # Title
        self.title_label = Gtk.Label(label=f"⚡ {APP_NAME}")
        self.title_label.get_style_context().add_class('header-title')
        header.pack_start(self.title_label, False, False, 0)

        header.pack_start(Gtk.Box(), True, True, 0)

        # Layout button
        self.layout_btn = Gtk.Button(label="▦")
        self.layout_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.layout_btn.get_style_context().add_class('header-btn')
        self.layout_btn.set_tooltip_text("Switch layout")
        self.layout_btn.connect('clicked', self._on_layout_click)
        header.pack_end(self.layout_btn, False, False, 0)

        # Theme button
        self.theme_btn = Gtk.Button(label="◐")
        self.theme_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.theme_btn.get_style_context().add_class('header-btn')
        self.theme_btn.set_tooltip_text("Switch theme")
        self.theme_btn.connect('clicked', self._on_theme_click)
        header.pack_end(self.theme_btn, False, False, 0)

        # Settings button
        settings_btn = Gtk.MenuButton()
        settings_btn.set_relief(Gtk.ReliefStyle.NONE)
        settings_btn.add(Gtk.Label(label="⚙"))
        settings_btn.get_style_context().add_class('header-btn')

        menu = Gtk.Menu()

        autostart_item = Gtk.CheckMenuItem(label="Autostart")
        autostart_item.set_active(self.config.autostart)
        autostart_item.connect('toggled', lambda i: self.config.set_autostart(i.get_active()))
        menu.append(autostart_item)

        menu.append(Gtk.SeparatorMenuItem())

        about_item = Gtk.MenuItem(label="About")
        about_item.connect('activate', self._show_about)
        menu.append(about_item)

        menu.show_all()
        settings_btn.set_popup(menu)
        header.pack_end(settings_btn, False, False, 0)

        # Minimize
        min_btn = Gtk.Button(label="─")
        min_btn.set_relief(Gtk.ReliefStyle.NONE)
        min_btn.get_style_context().add_class('header-btn')
        min_btn.connect('clicked', lambda b: self.iconify())
        header.pack_end(min_btn, False, False, 0)

        # Close
        close_btn = Gtk.Button(label="✕")
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.get_style_context().add_class('header-btn-close')
        close_btn.connect('clicked', lambda b: Gtk.main_quit())
        header.pack_end(close_btn, False, False, 0)

        self.main_box.pack_start(header, False, False, 0)

    def _on_layout_click(self, btn):
        self.config.cycle_layout()
        self._build_tiles()
        self.show_all()

    def _on_theme_click(self, btn):
        self.config.cycle_theme()
        self._apply_css()
        self._apply_theme_to_tiles()

    def _on_tile_click(self, tile_name: str):
        self.config.cycle_tile_mode(tile_name)
        self._rebuild_tile(tile_name)

    def _show_about(self, item):
        dialog = Gtk.AboutDialog(transient_for=self)
        dialog.set_program_name(APP_NAME)
        dialog.set_version("2.0.0")
        dialog.set_authors(["Goncharenko Anton (alienxs2)"])
        dialog.set_comments("System Monitor\nClick tiles to change style")
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.run()
        dialog.destroy()

    def _create_widget(self, tile_name: str, label: str, unit: str = "%"):
        mode = self.config.get_tile_mode(tile_name)
        theme = THEMES[self.config.theme]

        widgets = {
            "terminal": TerminalWidget,
            "gauge": GaugeWidget,
            "text": TextWidget,
            "wave": WaveWidget,
            "glow": GlowWidget,
        }

        widget_class = widgets.get(mode, TerminalWidget)
        w = widget_class(label, unit)
        w.set_theme(theme)
        return w

    def _rebuild_tile(self, tile_name: str):
        if tile_name not in self.tiles:
            return

        container = self.tiles[tile_name]
        labels = {"cpu": "CPU", "ram": "RAM", "swap": "Swap", "gpu": "GPU",
                  "vram": "VRAM", "temp": "Temp", "disk": "Disk", "net": "Net"}
        units = {"temp": "°C"}

        if tile_name in ["disk", "net"]:
            return

        label = labels.get(tile_name, tile_name.upper())
        unit = units.get(tile_name, "%")
        widget = self._create_widget(tile_name, label, unit)
        container.set_widget(widget)
        container.show_all()

    def _apply_theme_to_tiles(self):
        theme = THEMES[self.config.theme]
        for container in self.tiles.values():
            container.set_theme(theme)

    def _build_tiles(self):
        for child in self.content.get_children():
            self.content.remove(child)

        self.tiles = {}
        layout = self.config.layout

        builders = {
            "compact": self._build_compact,
            "wide": self._build_wide,
            "vertical": self._build_vertical,
            "mini": self._build_mini,
            "dashboard": self._build_dashboard,
            "panel": self._build_panel,
        }
        builders.get(layout, self._build_compact)()
        self._apply_size()

    def _make_tile(self, name: str, label: str, unit: str = "%"):
        container = TileContainer(name, self._on_tile_click)
        widget = self._create_widget(name, label, unit)
        container.set_widget(widget)
        return container

    def _on_io_tile_click(self, tile_name: str):
        self.config.cycle_io_mode(tile_name)
        self._rebuild_io_tile(tile_name)

    def _create_io_widget(self, tile_name: str, label: str):
        mode = self.config.get_io_mode(tile_name)
        theme = THEMES[self.config.theme]

        widgets = {
            "terminal": IOWidget,
            "bars": IOBarsWidget,
            "text": IOTextWidget,
        }

        widget_class = widgets.get(mode, IOWidget)
        w = widget_class(label)
        w.set_theme(theme)
        return w

    def _rebuild_io_tile(self, tile_name: str):
        if tile_name not in self.tiles:
            return

        container = self.tiles[tile_name]
        labels = {"disk": "Disk", "net": "Net"}
        label = labels.get(tile_name, tile_name.upper())
        widget = self._create_io_widget(tile_name, label)
        container.set_widget(widget)
        container.show_all()

    def _make_io_tile(self, name: str, label: str):
        container = TileContainer(name, self._on_io_tile_click)
        widget = self._create_io_widget(name, label)
        container.set_widget(widget)
        return container

    def _build_compact(self):
        """Compact 2x4 grid layout."""
        row1 = Gtk.Box(spacing=5, homogeneous=True)
        row2 = Gtk.Box(spacing=5, homogeneous=True)

        self.tiles = {
            "cpu": self._make_tile("cpu", "CPU"),
            "ram": self._make_tile("ram", "RAM"),
            "gpu": self._make_tile("gpu", "GPU"),
            "temp": self._make_tile("temp", "Temp", "°C"),
            "swap": self._make_tile("swap", "Swap"),
            "vram": self._make_tile("vram", "VRAM"),
            "disk": self._make_io_tile("disk", "Disk"),
            "net": self._make_io_tile("net", "Net"),
        }

        for name in ["cpu", "ram", "gpu", "temp"]:
            row1.pack_start(self.tiles[name], True, True, 0)
        for name in ["swap", "vram", "disk", "net"]:
            row2.pack_start(self.tiles[name], True, True, 0)

        self.content.pack_start(row1, True, True, 0)
        self.content.pack_start(row2, True, True, 0)

    def _build_wide(self):
        """Wide single row layout."""
        row = Gtk.Box(spacing=5, homogeneous=True)

        self.tiles = {
            "cpu": self._make_tile("cpu", "CPU"),
            "ram": self._make_tile("ram", "RAM"),
            "gpu": self._make_tile("gpu", "GPU"),
            "temp": self._make_tile("temp", "Temp", "°C"),
            "disk": self._make_io_tile("disk", "Disk"),
            "net": self._make_io_tile("net", "Net"),
        }

        for name in ["cpu", "ram", "gpu", "temp", "disk", "net"]:
            row.pack_start(self.tiles[name], True, True, 0)

        self.content.pack_start(row, True, True, 0)

    def _make_compact_tile(self, name: str, label: str, unit: str = "%"):
        """Create compact tile for vertical layout."""
        container = TileContainer(name, self._on_tile_click)
        widget = CompactWidget(label, unit)
        widget.set_theme(THEMES[self.config.theme])
        container.set_widget(widget)
        return container

    def _make_compact_io_tile(self, name: str, label: str):
        """Create compact IO tile for vertical layout."""
        container = TileContainer(name, lambda n: None)
        widget = CompactIOWidget(label)
        widget.set_theme(THEMES[self.config.theme])
        container.set_widget(widget)
        return container

    def _build_vertical(self):
        """Vertical stacked layout - compact narrow version."""
        self.tiles = {
            "cpu": self._make_compact_tile("cpu", "CPU"),
            "ram": self._make_compact_tile("ram", "RAM"),
            "gpu": self._make_compact_tile("gpu", "GPU"),
            "temp": self._make_compact_tile("temp", "Temp", "°C"),
            "disk": self._make_compact_io_tile("disk", "Disk"),
            "net": self._make_compact_io_tile("net", "Net"),
        }

        for name in ["cpu", "ram", "gpu", "temp", "disk", "net"]:
            self.content.pack_start(self.tiles[name], False, False, 0)

    def _build_mini(self):
        """Mini compact layout."""
        row = Gtk.Box(spacing=4, homogeneous=True)

        self.tiles = {
            "cpu": self._make_tile("cpu", "CPU"),
            "ram": self._make_tile("ram", "RAM"),
            "gpu": self._make_tile("gpu", "GPU"),
        }

        for name in ["cpu", "ram", "gpu"]:
            row.pack_start(self.tiles[name], True, True, 0)

        self.content.pack_start(row, True, True, 0)

    def _build_dashboard(self):
        """Dashboard style with main + secondary."""
        main_row = Gtk.Box(spacing=6, homogeneous=True)
        secondary_row = Gtk.Box(spacing=4, homogeneous=True)

        self.tiles = {
            "cpu": self._make_tile("cpu", "CPU"),
            "ram": self._make_tile("ram", "RAM"),
            "gpu": self._make_tile("gpu", "GPU"),
            "temp": self._make_tile("temp", "Temp", "°C"),
            "swap": self._make_tile("swap", "Swap"),
            "vram": self._make_tile("vram", "VRAM"),
            "disk": self._make_io_tile("disk", "Disk"),
            "net": self._make_io_tile("net", "Net"),
        }

        for name in ["cpu", "ram", "gpu"]:
            main_row.pack_start(self.tiles[name], True, True, 0)
        for name in ["temp", "swap", "vram", "disk", "net"]:
            secondary_row.pack_start(self.tiles[name], True, True, 0)

        self.content.pack_start(main_row, True, True, 0)
        self.content.pack_start(secondary_row, False, False, 0)

    def _build_panel(self):
        """Horizontal panel strip."""
        row = Gtk.Box(spacing=8, homogeneous=False)

        self.tiles = {
            "cpu": self._make_tile("cpu", "CPU"),
            "ram": self._make_tile("ram", "RAM"),
            "gpu": self._make_tile("gpu", "GPU"),
            "temp": self._make_tile("temp", "°C", ""),
        }

        for name in ["cpu", "ram", "gpu", "temp"]:
            row.pack_start(self.tiles[name], True, True, 0)

        self.content.pack_start(row, True, True, 0)

    def _apply_size(self):
        sizes = {
            "compact": (440, 175),
            "wide": (660, 95),
            "vertical": (70, 290),  # Compact narrow vertical
            "mini": (300, 85),
            "dashboard": (520, 180),
            "panel": (420, 85),
        }
        w, h = sizes.get(self.config.layout, (440, 175))
        self.set_default_size(w, h)
        self.resize(w, h)

        # Adjust margins for vertical layout
        if self.config.layout == "vertical":
            self.content.set_margin_start(4)
            self.content.set_margin_end(4)
            self.content.set_margin_bottom(4)
        else:
            self.content.set_margin_start(8)
            self.content.set_margin_end(8)
            self.content.set_margin_bottom(8)

    def _set_icon(self):
        icon_path = os.path.join(APP_DIR, "icon.png")
        if os.path.exists(icon_path):
            self.set_icon_from_file(icon_path)

    def _apply_css(self):
        theme = THEMES[self.config.theme]
        css = f"""
        .main-container {{
            background-color: {theme['bg']};
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.1);
        }}

        .custom-header {{
            background-color: {theme['header']};
            border-radius: 10px 10px 0 0;
        }}

        .header-title {{
            color: {theme['accent']};
            font-weight: bold;
            font-size: 12px;
        }}

        .header-btn {{
            color: #999;
            min-width: 26px;
            min-height: 26px;
            padding: 0;
            border-radius: 5px;
            font-size: 13px;
        }}
        .header-btn:hover {{ background-color: rgba(255,255,255,0.1); color: #fff; }}

        .header-btn-close {{
            color: #999;
            min-width: 26px;
            min-height: 26px;
            padding: 0;
            border-radius: 5px;
            font-size: 13px;
        }}
        .header-btn-close:hover {{ background-color: #e53935; color: #fff; }}

        .tile-container {{
            border-radius: 6px;
        }}
        .tile-container:hover {{
            background-color: rgba(255, 255, 255, 0.03);
        }}

        menu {{ background-color: {theme['header']}; border-radius: 6px; }}
        menuitem {{ color: {theme['text']}; padding: 6px 12px; }}
        menuitem:hover {{ background-color: rgba(255,255,255,0.1); }}
        """.encode()

        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _update(self):
        try:
            # CPU
            if "cpu" in self.tiles:
                cpu = psutil.cpu_percent(interval=None)
                self.tiles["cpu"].set_value(cpu)

            # RAM
            if "ram" in self.tiles:
                mem = psutil.virtual_memory()
                self.tiles["ram"].set_value(mem.percent)

            # Swap
            if "swap" in self.tiles:
                swap = psutil.swap_memory()
                self.tiles["swap"].set_value(swap.percent)

            # GPU
            gpu = GPUMonitor.get_info()
            if gpu:
                if "gpu" in self.tiles:
                    self.tiles["gpu"].set_value(gpu["util"])
                if "vram" in self.tiles:
                    vram = (gpu["mem_used"] / gpu["mem_total"]) * 100
                    self.tiles["vram"].set_value(vram)
                if "temp" in self.tiles:
                    self.tiles["temp"].set_value(gpu["temp"])
            else:
                if "gpu" in self.tiles:
                    self.tiles["gpu"].set_value(0)
                if "vram" in self.tiles:
                    self.tiles["vram"].set_value(0)
                if "temp" in self.tiles:
                    self.tiles["temp"].set_value(0)

            # Disk
            disk = psutil.disk_io_counters()
            if disk and self._last_disk and "disk" in self.tiles:
                r = max(0, disk.read_bytes - self._last_disk.read_bytes)
                w = max(0, disk.write_bytes - self._last_disk.write_bytes)
                self.tiles["disk"].set_values(r, w)
            self._last_disk = disk

            # Network
            net = psutil.net_io_counters()
            if net and self._last_net and "net" in self.tiles:
                r = max(0, net.bytes_recv - self._last_net.bytes_recv)
                s = max(0, net.bytes_sent - self._last_net.bytes_sent)
                self.tiles["net"].set_values(r, s)
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
