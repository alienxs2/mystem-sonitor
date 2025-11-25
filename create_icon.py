#!/usr/bin/env python3
"""Generate application icon for Mystem Sonitor."""
import cairo
import math

size = 128
surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
cr = cairo.Context(surface)

# Background circle
cr.set_source_rgb(0.1, 0.1, 0.12)
cr.arc(size/2, size/2, size/2 - 2, 0, 2 * math.pi)
cr.fill()

# Border glow
cr.set_source_rgb(0.3, 0.75, 0.35)
cr.set_line_width(2)
cr.arc(size/2, size/2, size/2 - 3, 0, 2 * math.pi)
cr.stroke()

# Draw speedometer arcs (representing gauge visualization)
cx, cy = size/2, size/2 + 5
radius = 35

# Background arc
cr.set_line_width(8)
cr.set_source_rgb(0.2, 0.2, 0.22)
cr.arc(cx, cy, radius, math.pi * 0.75, math.pi * 2.25)
cr.stroke()

# Gradient colored arc (green to yellow to red)
for i in range(60):
    t = i / 60
    angle_start = math.pi * 0.75 + t * math.pi * 1.5
    angle_end = angle_start + math.pi * 1.5 / 60 + 0.02

    if t < 0.5:
        r, g, b = 0.3 + t * 1.0, 0.8, 0.2
    elif t < 0.75:
        r, g, b = 0.95, 0.8 - (t - 0.5) * 1.2, 0
    else:
        r, g, b = 1.0, 0.3 - (t - 0.75) * 1.2, 0

    cr.set_source_rgb(r, max(0, g), max(0, b))
    cr.arc(cx, cy, radius, angle_start, angle_end)
    cr.stroke()

# Needle pointing to ~70%
needle_angle = math.pi * 0.75 + 0.7 * math.pi * 1.5
needle_len = radius * 0.85
nx = cx + math.cos(needle_angle) * needle_len
ny = cy + math.sin(needle_angle) * needle_len
cr.set_source_rgb(1, 1, 1)
cr.set_line_width(2.5)
cr.move_to(cx, cy)
cr.line_to(nx, ny)
cr.stroke()

# Center dot
cr.set_source_rgb(0.9, 0.9, 0.9)
cr.arc(cx, cy, 4, 0, 2 * math.pi)
cr.fill()

# Mini bars below gauge
bar_colors = [(0.3, 0.8, 0.3), (0.2, 0.6, 0.9), (1.0, 0.6, 0.0), (0.8, 0.3, 0.8)]
bar_heights = [18, 25, 15, 22]
bar_width = 10
start_x = size/2 - (len(bar_colors) * (bar_width + 4)) / 2

for i, (color, h) in enumerate(zip(bar_colors, bar_heights)):
    cr.set_source_rgb(*color)
    x = start_x + i * (bar_width + 4)
    y = size - 18 - h
    # Rounded rect
    cr.arc(x + 3, y + 3, 3, math.pi, 1.5 * math.pi)
    cr.arc(x + bar_width - 3, y + 3, 3, 1.5 * math.pi, 0)
    cr.arc(x + bar_width - 3, y + h - 3, 3, 0, 0.5 * math.pi)
    cr.arc(x + 3, y + h - 3, 3, 0.5 * math.pi, math.pi)
    cr.close_path()
    cr.fill()

# Lightning bolt (representing "Mystem" / system)
cr.set_source_rgb(1.0, 0.85, 0.2)
cr.move_to(size - 28, 18)
cr.line_to(size - 35, 32)
cr.line_to(size - 30, 32)
cr.line_to(size - 36, 48)
cr.line_to(size - 25, 28)
cr.line_to(size - 30, 28)
cr.close_path()
cr.fill()

surface.write_to_png("/home/dev/mystem_sonitor/icon.png")
print("Icon created: /home/dev/mystem_sonitor/icon.png")
