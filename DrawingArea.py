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
from PyQt5.QtGui import QColor, QPen, QBrush, QWheelEvent, QMouseEvent
import ezdxf

class HoverableRectItem(QGraphicsRectItem):
    def __init__(self, rect):
        super().__init__(rect)
        self.setAcceptHoverEvents(True)
        self.normalPen = QPen(Qt.white)
        self.hoverPen = QPen(QColor(50, 100, 200))
        self.normalBrush = QBrush(QColor(20, 100, 160, 127))
        self.hoverBrush = QBrush(QColor(20, 100, 160, 200))
        self.setPen(self.normalPen)
        self.setBrush(self.normalBrush)

    def hoverEnterEvent(self, event):
        self.setPen(self.hoverPen)
        self.setBrush(self.hoverBrush)
        # print("Hover enter")
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(self.normalPen)
        self.setBrush(self.normalBrush)
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

        self.snapPointVisuals = [] 
        self.snapPoints = []  # List to hold QPointF objects for snap points
        self.snapDetectionRadius = 20  # Pixels within which snapping should occur
        self.currentlyDraggingItem = None  # Track the item being dragged
        self.dragOffset = QPointF(0, 0)  # Initialize dragOffset

    def initializeScene(self, scene):
        """Set up the initial drawing area scene."""
        self.scene = scene
        self.setBackgroundBrush(QColor("black"))
        self.setMouseTracking(True)
        self.drawingMode = None
        self.firstClickPoint = None
        self.tempRect = None
        self.configureScrollBars()
        self.drawOriginCrosshair()

    def mouseMoveEvent(self, event):
        scenePos = self.mapToScene(event.pos())
        self.positionChanged.emit(f"Scene Position = ({scenePos.x():.2f}, {scenePos.y():.2f})")

        if self.currentlyDraggingItem:
            newPos = scenePos - self.dragOffset
            closestSnapPoint, minDistance = self.findClosestSnapPoint(newPos + self.dragOffset)  # Adjust for dragOffset
            if minDistance <= self.snapDetectionRadius:
                # Snap by setting the position to the closest snap point adjusted by dragOffset.
                self.currentlyDraggingItem.setPos(closestSnapPoint)
            else:
                self.currentlyDraggingItem.setPos(newPos)
            self.showSnapPoints(True)  # Refresh snap points.

        elif self.drawingMode == 'rectangle' and self.firstClickPoint:
            # This block is for drawing rectangles; it updates the temporary rectangle and the dimension inputs.
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
        else:
            # Hide snap points when not dragging or drawing.
            self.showSnapPoints(False)

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
        item = self.itemAt(event.pos())
        if item and isinstance(item, QGraphicsRectItem):  # Adjust based on your item type
            self.currentlyDraggingItem = item
            # Calculate the offset from the item's top-left corner to the mouse position
            self.dragOffset = self.mapToScene(event.pos()) - item.pos()
        else:
            self.currentlyDraggingItem = None
            self.dragOffset = QPointF(0, 0)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.currentlyDraggingItem:
            self.currentlyDraggingItem = None
            self.showSnapPoints(False)  # Hide snap points
        super().mouseReleaseEvent(event)
        
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

    def finalizeDrawing(self, secondClickPoint=None):
        """
        Finalize the drawing of the current shape.
        This method uses a provided second click point or input from the LineEdits to finalize the rectangle.
        """
        if self.firstClickPoint is None:
            print("No starting point defined. Exiting without drawing.")
            return

        if secondClickPoint is None and self.lengthEdit.isVisible():
            try:
                length = float(self.lengthEdit.text())
                width = float(self.widthEdit.text())
                secondClickPoint = QPointF(self.firstClickPoint.x() + length, self.firstClickPoint.y() + width)
            except ValueError:
                print("Invalid input for dimensions. Exiting without drawing.")
                return

        # Proceed to create and add the rectangle to the scene
        if self.tempRect:
            self.scene.removeItem(self.tempRect)
            self.tempRect = None

        rect = QRectF(self.firstClickPoint, secondClickPoint).normalized()
        finalRect = HoverableRectItem(rect)
        finalRect.setPen(QPen(Qt.white))
        finalRect.setBrush(QColor(20, 100, 160, 127))
        finalRect.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.scene.addItem(finalRect)

        # Reset the state for next drawing
        self.firstClickPoint = None
        self.lengthEdit.clear()
        self.widthEdit.clear()
        self.lengthEdit.hide()
        self.widthEdit.hide()

    def configureScrollBars(self):
        """Configure the scroll bars for the drawing area."""
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def drawOriginCrosshair(self):
        """Draw the origin crosshair on the scene."""
        pen = QPen(Qt.white, 2)
        self.scene.addItem(QGraphicsLineItem(QLineF(-1000, 0, 1000, 0)).setPen(pen))
        self.scene.addItem(QGraphicsLineItem(QLineF(0, -1000, 0, 1000)).setPen(pen))
        pass

    def setDrawingMode(self, mode):
        """Set the current drawing mode."""
        self.drawingMode = mode
        print(f"Switched to {mode} mode.")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_E and event.modifiers() == Qt.ControlModifier:
            self.exportToDXF("your_drawing.dxf")
        else:
            super().keyPressEvent(event)

    # def getClosestSnapPoint(self, pos):
    #     print ("Get closest snap point")
    #     closestPoint = None
    #     minDistance = float('inf')
    #     for point in self.snapPoints:
    #         distance = (pos - point).manhattanLength()
    #         if distance < minDistance and distance <= self.snapDetectionRadius:
    #             closestPoint = point
    #             minDistance = distance
    #     return closestPoint
        
    def updateSnapPoints(self):
        self.snapPoints.clear()
        for item in self.scene.items():
            if isinstance(item, QGraphicsRectItem):
                rect = item.rect()
                # Assuming the item's position is the top-left point of the rectangle
                self.snapPoints.extend([
                    item.pos() + rect.topLeft(),
                    item.pos() + rect.topRight(),
                    item.pos() + rect.bottomLeft(),
                    item.pos() + rect.bottomRight(),
                ])

    def showSnapPoints(self, show):
        # Remove all existing snap point markers
        while self.snapPointVisuals:
            marker = self.snapPointVisuals.pop(0)  # Remove the first element
            self.scene.removeItem(marker)

        # If showing snap points, add them to the scene
        if show:
            self.updateSnapPoints()  # Update the list of snap points based on current scene items
            for point in self.snapPoints:
                marker = self.scene.addRect(point.x() - 10, point.y() - 10, 20, 20, QPen(Qt.yellow))
                self.snapPointVisuals.append(marker)

    def findClosestSnapPoint(self, pos):
        print("Find closest snap point")
        closestPoint = None
        minDistance = float('inf')
        for point in self.snapPoints:
            distance = (pos - point).manhattanLength()  # You can also use Euclidean distance
            if distance < minDistance:
                closestPoint = point
                minDistance = distance
                print((closestPoint.x(), closestPoint.y()))
        return closestPoint, minDistance

    def exportToDXF(self, filename):
        import ezdxf
        doc = ezdxf.new(setup=True)
        msp = doc.modelspace()

        for item in self.scene().items():
            if isinstance(item, QGraphicsRectItem):
                rect = item.rect()
                # Add a rectangle for each QGraphicsRectItem
                # Note: You might need to adjust the points based on your coordinate system
                msp.add_lwpolyline([
                    (rect.x(), rect.y()),
                    (rect.x() + rect.width(), rect.y()),
                    (rect.x() + rect.width(), rect.y() + rect.height()),
                    (rect.x(), rect.y() + rect.height()),
                    (rect.x(), rect.y())
                ], close=True)

        doc.saveas(filename)
