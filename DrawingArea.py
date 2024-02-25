from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem
from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt5.QtGui import QColor, QPen

class DrawingArea(QGraphicsView):
    positionChanged = pyqtSignal(str)

    def __init__(self, scene: QGraphicsScene):
        super().__init__(scene)
        self.scene = scene
        self.setBackgroundBrush(QColor("black"))
        self.setMouseTracking(True)
        self.drawingMode = None
        self.firstClickPoint = None
    
    def mouseMoveEvent(self, event):
        scenePos = self.mapToScene(event.pos())
        self.positionChanged.emit(f"Scene Position = ({scenePos.x():.2f}, {scenePos.y():.2f})")

    def mousePressEvent(self, event):
        if self.drawingMode == 'rectangle':
            if not self.firstClickPoint:
                # First click - set the starting point
                self.firstClickPoint = self.mapToScene(event.pos())
                print(f"First Click point = ({self.firstClickPoint.x():.2f}, {self.firstClickPoint.y():.2f})")
            else:
                # Second click - draw the rectangle
                secondClickPoint = self.mapToScene(event.pos())
                print(f"Second Click point = ({secondClickPoint.x():.2f}, {secondClickPoint.y():.2f})")
                # rect = self.makeRectangle(self.firstClickPoint, secondClickPoint)
                # self.scene.addRect(rect, QPen(Qt.white))
                self.firstClickPoint = None  # Reset for the next rectangle
        super().mousePressEvent(event)

    def makeRectangle(self, startPoint: QPointF, endPoint: QPointF):
        """Create a QRectF based on two QPointF objects."""
        return QRectF(startPoint, endPoint)

    def setDrawingMode(self, mode):
        self.drawingMode = mode
        print(f"Switched to {mode} mode.")
