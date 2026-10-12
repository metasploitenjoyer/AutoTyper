"""A small, consistent set of line icons (24x24, 2px stroke, round caps), drawn as SVG."""

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{c}" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')

BODIES = {
    "play": '<polygon points="6 3 20 12 6 21 6 3"/>',
    "pause": '<line x1="8" y1="5" x2="8" y2="19"/><line x1="16" y1="5" x2="16" y2="19"/>',
    "stop": '<rect x="5" y="5" width="14" height="14" rx="2"/>',
    "settings": ('<line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/>'
                 '<line x1="4" y1="18" x2="20" y2="18"/><circle cx="9" cy="6" r="2.2"/>'
                 '<circle cx="15" cy="12" r="2.2"/><circle cx="8" cy="18" r="2.2"/>'),
    "sun": ('<circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="4"/>'
            '<line x1="12" y1="20" x2="12" y2="22"/><line x1="2" y1="12" x2="4" y2="12"/>'
            '<line x1="20" y1="12" x2="22" y2="12"/><line x1="4.9" y1="4.9" x2="6.3" y2="6.3"/>'
            '<line x1="17.7" y1="17.7" x2="19.1" y2="19.1"/><line x1="4.9" y1="19.1" x2="6.3" y2="17.7"/>'
            '<line x1="17.7" y1="6.3" x2="19.1" y2="4.9"/>'),
    "moon": '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
    "paste": ('<rect x="8" y="3" width="8" height="4" rx="1"/>'
              '<path d="M16 5h2a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2"/>'),
    "trash": ('<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>'
              '<path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>'),
    "clock": '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/>',
    "back": '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "alert": ('<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
              '<line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'),
}


def svg_for(name, color):
    return _SVG.format(c=color, body=BODIES[name])


def render_image(name, color, size=20, scale=2):
    """Render an icon to a QImage (works without a running QApplication)."""
    renderer = QSvgRenderer(QByteArray(svg_for(name, color).encode("utf-8")))
    img = QImage(size * scale, size * scale, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    img.setDevicePixelRatio(scale)
    return img


def make_icon(name, color, size=20):
    return QIcon(QPixmap.fromImage(render_image(name, color, size)))
