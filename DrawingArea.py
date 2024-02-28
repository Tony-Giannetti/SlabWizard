# DrawingArea.py
from PyQt5.QtWidgets import (
    QGraphicsView, 
    QGraphicsScene, 
    QGraphicsItem, 
    QGraphicsRectItem, 
    QGraphicsLineItem,
    QLineEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QRectF, QLineF
from PyQt5.QtGui import QColor, QPen, QWheelEvent, QMouseEvent

class HoverableRectItem(QGraphicsRectItem):
    def __init__(self, rect):
        super().__init__(rect)
        self.setAcceptHoverEvents(True)
        self.normalPen = QPen(Qt.white)
        self.hoverPen = QPen(Qt.green)
        self.setPen(self.normalPen)
        self.setBrush(QColor(255, 255, 0, 200))

    def hoverEnterEvent(self, event):
        self.setPen(self.hoverPen)
        print("Hover enter")
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(self.normalPen)
        print("Hover leave")
        super().hoverLeaveEvent(event)


class DrawingArea(QGraphicsView):
    positionChanged = pyqtSignal(str)

    def __init__(self, scene: QGraphicsScene):
        super().__init__(scene)
        self.initializeScene(scene)

    def initializeScene(self, scene):
        """Set up the initial drawing area scene."""
        self.scene = scene
        self.setBackgroundBrush(QColor("black"))
        self.setMouseTracking(True)
        self.drawingMode = None
        self.firstClickPoint = None
        self.tempRect = None
        self.drawOriginCrosshair()
        self.configureScrollBars()

    def mouseMoveEvent(self, event):
        """Handle mouse movement events."""
        scenePos = self.mapToScene(event.pos())
        self.positionChanged.emit(f"Scene Position = ({scenePos.x():.2f}, {scenePos.y():.2f})")
        if self.drawingMode == 'rectangle' and self.firstClickPoint:
            self.updateTemporaryRectangle(event)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events."""
        if event.button() == Qt.LeftButton and self.drawingMode == 'rectangle':
            if not self.firstClickPoint:
                # First click - set the starting point
                self.firstClickPoint = self.mapToScene(event.pos())
            else:
                # Second click - finalize the drawing
                self.finalizeDrawing(self.mapToScene(event.pos()))
        super().mousePressEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        """Handle wheel events for zooming."""
        scaleFactor = 1.1
        if event.angleDelta().y() > 0:
            self.scale(scaleFactor, scaleFactor)
        else:
            self.scale(1.0 / scaleFactor, 1.0 / scaleFactor)

    def updateTemporaryRectangle(self, event):
        """Update or create a temporary rectangle during mouse movement."""
        # Remove temporary rectangle if exists
        if self.tempRect:
            self.scene.removeItem(self.tempRect)
            self.tempRect = None  # Remove the reference to fully delete it
        
        # Calculate rectangle coordinates for the temporary rectangle
        start = self.firstClickPoint
        end = self.mapToScene(event.pos())
        rect = QRectF(QPointF(min(start.x(), end.x()), min(start.y(), end.y())),
                      QPointF(max(start.x(), end.x()), max(start.y(), end.y())))

        # Create and add new temporary rectangle
        self.tempRect = self.scene.addRect(rect, QPen(Qt.white))

    def finalizeDrawing(self, secondClickPoint):
        """Finalize the drawing of the current shape."""
        # Remove the temporary rectangle
        if self.tempRect:
            self.scene.removeItem(self.tempRect)
            self.tempRect = None

        # Directly create and add the finalized QGraphicsRectItem to the scene
        rect = QRectF(self.firstClickPoint, secondClickPoint).normalized()
        finalRect = HoverableRectItem(rect)
        finalRect.setPen(QPen(Qt.white))
        finalRect.setBrush(QColor(255, 0, 0, 127))
        finalRect.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.scene.addItem(finalRect)
        self.firstClickPoint = None  # Reset for the next drawing

    def configureScrollBars(self):
        """Configure the scroll bars for the drawing area."""
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def drawOriginCrosshair(self):
        """Draw the origin crosshair on the scene."""
        pen = QPen(Qt.gray, 2)
        self.scene.addItem(QGraphicsLineItem(QLineF(-1000, 0, 1000, 0)).setPen(pen))
        self.scene.addItem(QGraphicsLineItem(QLineF(0, -1000, 0, 1000)).setPen(pen))

    def setDrawingMode(self, mode):
        """Set the current drawing mode."""
        self.drawingMode = mode
        print(f"Switched to {mode} mode.")
