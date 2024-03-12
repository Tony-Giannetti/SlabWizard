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
        # self.normalPen.setWidth(10)
        self.hoverPen.setWidth(2)
        self.normalBrush = QBrush(QColor(20, 100, 160, 127))
        self.hoverBrush = QBrush(QColor(20, 100, 160, 200))
        self.setPen(self.normalPen)
        self.setBrush(self.normalBrush)

    def hoverEnterEvent(self, event):
        # self.setPen(self.hoverPen)
        self.setBrush(self.hoverBrush)
        # print("Hover enter")
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        # self.setPen(self.normalPen)
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

        self._isDraggingStarted = False  # Initialize the drag operation flag

        # Connect the textChanged signals
        self.lengthEdit.textChanged.connect(self.updateRectFromInput)
        self.widthEdit.textChanged.connect(self.updateRectFromInput)

        self.currentlyDraggingItem = None  # Track the item being dragged
        self.dragOffset = QPointF(0, 0)  # Initialize dragOffset

        self.fixedSnapPoints = []
        self.draggingSnapPoints = []
        self.snapDetectionRadius = 50

        self.snapPointPen = QPen(QColor(Qt.yellow))
        self.snapPointPen.setWidth(4)

    def initializeScene(self, scene):
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

            if self._isDraggingStarted:
                points = self.calculateFixedSnapPoints(excludeItem=self.currentlyDraggingItem)
                self.displaySnapPoints(points, self.fixedSnapPoints)  # Use fixedSnapPoints here
                self._isDraggingStarted = False

            self.handleDragging(event.pos())

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
            # self.showSnapPoints(False)
            super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
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
            print(f"Item pos = ({item.pos().x()}, {item.pos().y()})")
            print(f"Drag offset = ({self.dragOffset.x()}, {self.dragOffset.y()})")
            self._isDraggingStarted = True  # Dragging starts
        else:
            self.currentlyDraggingItem = None
            self.dragOffset = QPointF(0, 0)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.currentlyDraggingItem:
            self.currentlyDraggingItem = None
            # self.showSnapPoints(False)  # Hide snap points
            self.removeSnapPoints(self.fixedSnapPoints)
            self.removeSnapPoints(self.draggingSnapPoints)
        super().mouseReleaseEvent(event)
        
    def wheelEvent(self, event: QWheelEvent):
        """Handle wheel events for zooming."""
        scaleFactor = 1.1
        if event.angleDelta().y() > 0:
            self.scale(scaleFactor, scaleFactor)
        else:
            self.scale(1.0 / scaleFactor, 1.0 / scaleFactor)

    def handleDragging(self, mousePosition):
        # Remove old dragging snap points
        self.removeSnapPoints(self.draggingSnapPoints)

        scenePos = self.mapToScene(mousePosition)
        newPos = scenePos - self.dragOffset
        self.currentlyDraggingItem.setPos(newPos)

        # Calculate new dragging snap points
        draggingSnapPoints = self.calculateDraggingItemSnapPoints()
        self.displaySnapPoints(draggingSnapPoints, self.draggingSnapPoints)  # Use draggingSnapPoints here
        # self.checkSnapPointsProximity()
        self.checkSnapPointsProximityAndSnap()

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

        if event.key() == Qt.Key_S:
            for visual in self.draggingSnapPoints:
                # Assuming each visual is a QGraphicsRectItem and you want the center of the rectangle
                rect = visual.rect()  # This gets the rectangle defining the QGraphicsRectItem
                center = visual.mapToScene(rect.center())  # Converts the rectangle's center to scene coordinates
                print(f"({center.x()}, {center.y()})")

        else:
            super().keyPressEvent(event)
        
    def calculateFixedSnapPoints(self, excludeItem=None):
        snapPoints = []
        for item in self.scene.items():
            if item != excludeItem and isinstance(item, QGraphicsRectItem):
                rect = item.rect()
                snapPoints += [
                    item.mapToScene(rect.topLeft()),
                    item.mapToScene(rect.topRight()),
                    item.mapToScene(rect.bottomLeft()),
                    item.mapToScene(rect.bottomRight())
                ]
        return snapPoints

    def calculateDraggingItemSnapPoints(self):
        if not self.currentlyDraggingItem:
            return []

        snapPoints = []
        if isinstance(self.currentlyDraggingItem, QGraphicsRectItem):
            rect = self.currentlyDraggingItem.rect()
            # Calculate snap points (e.g., corners for a rectangle)
            snapPoints = [
                self.currentlyDraggingItem.mapToScene(rect.topLeft()),
                self.currentlyDraggingItem.mapToScene(rect.topRight()),
                self.currentlyDraggingItem.mapToScene(rect.bottomLeft()),
                self.currentlyDraggingItem.mapToScene(rect.bottomRight())
            ]
        return snapPoints

    def displaySnapPoints(self, snapPoints, targetList):
        for point in snapPoints:
            visual = self.scene.addRect(point.x() - (self.snapDetectionRadius / 2), point.y() - (self.snapDetectionRadius / 2), self.snapDetectionRadius, self.snapDetectionRadius, QPen(self.snapPointPen))
            targetList.append(visual)

    def removeSnapPoints(self, visuals):
        for visual in visuals:
            self.scene.removeItem(visual)
        visuals.clear()

    def checkSnapPointsProximity(self):
        specified_distance = self.snapDetectionRadius  # or any other value you'd like to use

        for fixedVisual in self.fixedSnapPoints:
            fixedCenter = fixedVisual.mapToScene(fixedVisual.rect().center())

            for draggingVisual in self.draggingSnapPoints:
                draggingCenter = draggingVisual.mapToScene(draggingVisual.rect().center())

                distance = (fixedCenter - draggingCenter).manhattanLength()
                if distance <= specified_distance:
                    # Perform your action here
                    print(f"Snap point from dragging is within {specified_distance} units of a fixed snap point.")
                    # Example action: snapping the dragging item to the fixed item's position
                    # This is where you could adjust positions or take other actions as needed

    def checkSnapPointsProximityAndSnap(self):
        specified_distance = self.snapDetectionRadius
        for fixedVisual in self.fixedSnapPoints:
            for draggingVisual in self.draggingSnapPoints:
                fixedPoint = fixedVisual.mapToScene(fixedVisual.rect().center())
                draggingPoint = draggingVisual.mapToScene(draggingVisual.rect().center())

                if (fixedPoint - draggingPoint).manhattanLength() <= specified_distance:
                    self.snapObjectToFixedPoint(draggingPoint, fixedPoint - draggingPoint)
                    return  # Assuming only one snap action per drag operation for simplicity

    def snapObjectToFixedPoint(self, draggingPoint, offset):
        # Calculate the new position for the currentlyDraggingItem by applying the offset
        if self.currentlyDraggingItem:
            newPos = self.currentlyDraggingItem.pos() + offset
            self.currentlyDraggingItem.setPos(newPos)
            # After snapping, you might want to clear the visuals or update them according to the new position
            self.updateAfterSnap()

    def updateAfterSnap(self):
        # Clear dragging visuals
        self.removeSnapPoints(self.draggingSnapPoints)
        # Optionally, recalculate and display new snap points based on the new positions
        # This might not be necessary if the snapping action concludes the drag operation
        # and the user needs to initiate a new drag to move objects again.
