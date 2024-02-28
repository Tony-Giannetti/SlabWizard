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
        # print("Hover enter")
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(self.normalPen)
        # print("Hover leave")
        super().hoverLeaveEvent(event)


class DrawingArea(QGraphicsView):
    positionChanged = pyqtSignal(str)

    def __init__(self, scene: QGraphicsScene):
        super().__init__(scene)
        self.initializeScene(scene)
       # Initialize QLineEdit widgets for dimension display
        self.lengthEdit = QLineEdit(self)
        self.widthEdit = QLineEdit(self)
        self.lengthEdit.setReadOnly(False)  # Allow user input
        self.widthEdit.setReadOnly(False)
        self.lengthEdit.hide()
        self.widthEdit.hide()
        self.setFocusPolicy(Qt.StrongFocus)

        # Connect the textChanged signals
        self.lengthEdit.textChanged.connect(self.updateRectFromInput)
        self.widthEdit.textChanged.connect(self.updateRectFromInput)

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
            # Only update the QLineEdit widgets and temporary rectangle if there's no direct input happening
            if not self.lengthEdit.hasFocus() and not self.widthEdit.hasFocus():
                currentRect = QRectF(self.firstClickPoint, scenePos).normalized()
                self.lengthEdit.setText(f"{currentRect.width():.2f}")
                self.widthEdit.setText(f"{currentRect.height():.2f}")
                self.updateTemporaryRectangleDirectly(self.firstClickPoint, scenePos)
            
            # Adjust QLineEdit positions
            self.lengthEdit.move(10, self.viewport().height() - 60)
            self.widthEdit.move(10, self.viewport().height() - 30)
            self.lengthEdit.show()
            self.widthEdit.show()
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

        if self.drawingMode == 'rectangle' and self.firstClickPoint:
            endPoint = self.mapToScene(event.pos())
            self.updateTemporaryRectangleDirectly(self.firstClickPoint, endPoint)

    def updateTemporaryRectangleDirectly(self, startPoint, endPoint):
        if self.tempRect:
            self.scene.removeItem(self.tempRect)
        rect = QRectF(startPoint, endPoint).normalized()
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
        self.lengthEdit.hide()
        self.widthEdit.hide()

    def finalizeDrawingFromInput(self):
        print("finalizeDrawingFromInput called")
        # Check if we have a starting point and no existing temporary rectangle
        if not self.firstClickPoint or not self.tempRect:
            print("Either no starting point or temporary rectangle does not exist.")
            return  # Return early if the conditions are not met

        try:
            # Retrieve and convert input dimensions to float
            length = float(self.lengthEdit.text())
            width = float(self.widthEdit.text())
            print(f"Length: {length}, Width: {width}")
        except ValueError:
            print("Invalid input for rectangle dimensions.")
            return

        # Calculate the second point based on input dimensions
        secondPoint = QPointF(self.firstClickPoint.x() + length, self.firstClickPoint.y() + width)
        print(f"First Point: {self.firstClickPoint}, Second Point: {secondPoint}")

        # Remove the existing temporary rectangle, if any
        if self.tempRect:
            self.scene.removeItem(self.tempRect)
            self.tempRect = None

        # Create and add the final rectangle based on input dimensions
        rect = QRectF(self.firstClickPoint, secondPoint).normalized()
        finalRect = HoverableRectItem(rect)
        finalRect.setPen(QPen(Qt.white))
        finalRect.setBrush(QColor(255, 0, 0, 127))
        finalRect.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.scene.addItem(finalRect)

        # Reset the drawing state
        self.firstClickPoint = None
        self.lengthEdit.hide()
        self.widthEdit.hide()
        self.lengthEdit.clear()
        self.widthEdit.clear()


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

    def updateRectFromInput(self):
        if not self.firstClickPoint or not self.tempRect:
            return  # Do nothing if we don't have a starting point or an active rectangle
        
        try:
            length = float(self.lengthEdit.text())
            width = float(self.widthEdit.text())
        except ValueError:
            return  # Do nothing if the input can't be converted to float

        # Calculate the second point of the rectangle based on length and width input
        secondPoint = QPointF(self.firstClickPoint.x() + length, self.firstClickPoint.y() + width)

        # Update or create the temporary rectangle
        self.updateTemporaryRectangleDirectly(self.firstClickPoint, secondPoint)

    def keyPressEvent(self, event):
        print("keyPressEvent")
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            print("Enter pressed")
            self.finalizeDrawingFromInput()
        else:
            super().keyPressEvent(event)
