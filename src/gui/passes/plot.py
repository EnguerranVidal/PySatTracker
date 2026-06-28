import numpy as np
from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import *


class VisiblePassSkyPlot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.azimuths = np.array([])
        self.elevations = np.array([])
        self.setMinimumSize(420, 420)

    def setPass(self, azimuths, elevations):
        self.azimuths = np.asarray(azimuths, dtype=float)
        self.elevations = np.asarray(elevations, dtype=float)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(24, 24, -24, -24)
        size = min(rect.width(), rect.height())
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = size / 2
        painter.fillRect(self.rect(), QColor(10, 10, 14))
        gridPen = QPen(QColor(150, 150, 160), 1)
        painter.setPen(gridPen)
        for elevation in (30, 60, 90):
            ringRadius = radius * (90 - elevation) / 90
            painter.drawEllipse(center, ringRadius, ringRadius)
        for azimuth in range(0, 360, 30):
            angle = np.deg2rad(90 - azimuth)
            end = QPointF(center.x() + radius * np.cos(angle), center.y() - radius * np.sin(angle))
            painter.drawLine(center, end)
        painter.setPen(QPen(QColor(230, 230, 230), 1))
        painter.setFont(QFont("", 12, QFont.Bold))
        labels = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
        for text, (dx, dy) in labels.items():
            point = QPointF(center.x() + dx * (radius + 14), center.y() + dy * (radius + 14))
            painter.drawText(QRectF(point.x() - 12, point.y() - 10, 24, 20), Qt.AlignCenter, text)
        painter.setFont(QFont("", 9))
        for elevation in (30, 60):
            ringRadius = radius * (90 - elevation) / 90
            painter.drawText(QPointF(center.x() + ringRadius + 4, center.y() - 4), f"{elevation} deg")
        if self.azimuths.size == 0 or self.elevations.size == 0:
            return
        points = []
        for azimuth, elevation in zip(self.azimuths, self.elevations):
            clampedElevation = np.clip(elevation, 0, 90)
            pointRadius = radius * (90 - clampedElevation) / 90
            angle = np.deg2rad(90 - azimuth)
            points.append(QPointF(center.x() + pointRadius * np.cos(angle), center.y() - pointRadius * np.sin(angle)))
        painter.setPen(QPen(QColor(0, 180, 255), 3))
        for a, b in zip(points[:-1], points[1:]):
            painter.drawLine(a, b)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 220, 120))
        painter.drawEllipse(points[0], 5, 5)
        painter.setBrush(QColor(255, 90, 60))
        painter.drawEllipse(points[-1], 5, 5)
