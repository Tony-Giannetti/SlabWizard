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
from PyQt5.QtGui import QColor, QPen, QBrush, QWheelEvent, QMouseEvent, QCursor
import ezdxf
from math import atan2, degrees

class BaseEntity(QGraphicsItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptHoverEvents(True)
        self.isTemporary = False
        self.normalPen = QPen(Qt.black, 2)
        self.hoverPen = QPen(QColor(50, 100, 250), 2.5)  # Enhanced hover style
        self.updatePenStyle()

    def setTemporary(self, temporary=True):
        """Mark the entity as temporary or permanent."""
        self.isTemporary = temporary
        self.updatePenStyle()

    def updatePenStyle(self):
        """Update the pen style based on the entity state (temporary or not)."""
        if self.isTemporary:
            self.setPen(QPen(Qt.gray, 2, Qt.DashLine))
        else:
            self.setPen(self.normalPen)

    def hoverEnterEvent(self, event):
        """Handle hover enter events to change the appearance of the entity."""
        self.setPen(self.hoverPen)
        self.update()  # Refresh the item

    def hoverLeaveEvent(self, event):
        """Handle hover leave events to reset the appearance of the entity."""
        self.updatePenStyle()
        self.update()

    def paint(self, painter, option, widget=None):
        """Custom paint method, to be implemented by derived classes."""
        pass

class LineEntity(QGraphicsLineItem):
    def __init__(self, start_point=None, end_point=None, temporary=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_point = start_point
        self.end_point = end_point if end_point else start_point
        self.setTemporary(temporary)  # Call to base class method
        self.updatePenStyle()
        self.setAcceptHoverEvents(True)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.hoverPen = QPen(QColor(50, 100, 250), 2.5)  # Define hover pen style

    def setEndPoint(self, end_point):
        self.end_point = end_point
        self.setLine(QLineF(self.start_point, self.end_point))
        self.update()

    def setTemporary(self, temporary=True):
        self.isTemporary = temporary
        self.updatePenStyle()

    def updatePenStyle(self):
        if self.isTemporary:
            self.setPen(QPen(Qt.gray, 2, Qt.DashLine))
        else:
            self.setPen(QPen(Qt.white, 4))

    def hoverEnterEvent(self, event):
        print("Line hover enter")
        self.setPen(self.hoverPen)
        self.update()  # Refresh the item to apply the new pen style

    def hoverLeaveEvent(self, event):
        print("line hover leave")
        self.updatePenStyle()  # Reset the pen style when the cursor leaves the item
        self.update()

    # def paint(self, painter, option, widget=None):
    #     super().paint(painter, option, widget)


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

class SnapManager:
    def __init__(self, scene):
        self.scene = scene
        self.snap_radius = 50
        self.snap_point_pen = QPen(QColor(Qt.yellow))
        self.snap_point_pen.setWidth(4)
        self.fixed_snap_points = []  # Stores fixed snap points with type info
        self.dragging_snap_points = []  # Temporarily stores snap points for the currently dragged item
        self.snap_visuals = []  # Visual elements showing snap points
        self.snap_types_enabled = {
            'end_points': True,
            'corners': True,
            'centers': True,
            'midpoints': True,
            'nearest': True
        }
        self.hovering_snap_points = []

    def calculateFixedSnapPoints(self, excludeItem=None):
        # print("Calculate fixed snap points: ")
        snapPoints = [QPointF(0, 0)]
        for item in self.scene.items():
            if item != excludeItem and isinstance(item, QGraphicsRectItem):
                rect = item.rect()
                snapPoints += [
                    item.mapToScene(rect.topLeft()),
                    item.mapToScene(rect.topRight()),
                    item.mapToScene(rect.bottomLeft()),
                    item.mapToScene(rect.bottomRight())
                ]
        self.fixed_snap_points = snapPoints
        # for point in self.fixed_snap_points:
        #     print(f"({point.x()}, {point.y()})")

    def display_hovering_snap_points(self, cursor_pos):
        self.clear_snap_visuals()  # Clear existing visuals first

        nearest_snap_point = None 
        min_distance = float('inf')  # Initialize with infinity

        # Find the nearest snap point within the snap radius
        for point in self.fixed_snap_points:
            distance = (point - cursor_pos).manhattanLength()
            if distance <= self.snap_radius and distance < min_distance:
                nearest_snap_point = point
                min_distance = distance

        # If a nearest snap point is found, display it
        if nearest_snap_point is not None:
            visual = self.scene.addRect(
                nearest_snap_point.x() - (self.snap_radius / 2),
                nearest_snap_point.y() - (self.snap_radius / 2),
                self.snap_radius, self.snap_radius, self.snap_point_pen)
            self.snap_visuals.append(visual)

    def clear_snap_visuals(self):
        """Clear existing snap visuals from the scene."""
        for visual in self.snap_visuals:
            if visual in self.scene.items():
                self.scene.removeItem(visual)
        self.snap_visuals.clear()

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
        self._isPanning = False
        self._lastPanPoint = QPointF()

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

        self.rectanglePen = QPen(QColor(Qt.white))
        self.rectanglePen.setWidth(4)

        self.lastCursorPos = QPointF(0, 0)

        self.snapManager = SnapManager(self.scene)

        # Define tool states
        self.activeTool = None
        self.toolState = 'Idle'
        self.lineStartPoint = None
        self.lineEndPoint = None
        self.tempLine = None  # Temporary line for preview

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
        self.lastCursorPos = scenePos
        self.positionChanged.emit(f"Scene Position = ({scenePos.x():.2f}, {scenePos.y():.2f})")

        if not self.currentlyDraggingItem:
            # print("Not dragging")
            self.snapManager.display_hovering_snap_points(scenePos)
        else:
            if self._isDraggingStarted:
                points = self.calculateFixedSnapPoints(excludeItem=self.currentlyDraggingItem)
                self.displaySnapPoints(points, self.fixedSnapPoints)  # Use fixedSnapPoints here
                self._isDraggingStarted = False

            self.handleDragging(event.pos())

        if self.drawingMode == 'line' and self.toolState == 'drawing':
            self.handleLineTool(event, 'move')

        if self.drawingMode == 'rectangle' and self.firstClickPoint:
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

        elif self._isPanning:
            delta = event.pos() - self._lastPanPoint
            self._lastPanPoint = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            scenePos = self.mapToScene(event.pos())

            if self.drawingMode == 'line':
                self.handleLineTool(event, 'click')

            elif self.drawingMode == 'rectangle':
                if not self.firstClickPoint:
                    self.firstClickPoint = scenePos
                else:
                    self.finalizeDrawing(scenePos)
                    
            else:
                item = self.itemAt(event.pos())
                if item and isinstance(item, (QGraphicsRectItem, LineEntity)):  # Handle other entity types similarly
                    self.currentlyDraggingItem = item
                    self.dragOffset = scenePos - item.pos()
                    self._isDraggingStarted = True

        elif event.button() == Qt.MiddleButton:
            self.handleMiddleButtonPressEvent(event)

        else:
            super().mousePressEvent(event)


    def handleMiddleButtonPressEvent(self, event: QMouseEvent):
        self._isPanning = True
        self._lastPanPoint = event.pos()
        self.setCursor(Qt.ClosedHandCursor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.drawingMode == 'line' and self.toolState == 'drawing':
            self.handleLineTool(event, 'release', self.mapToScene(event.pos()))

        if self.currentlyDraggingItem:
            self.currentlyDraggingItem = None
            # self.showSnapPoints(False)  # Hide snap points
            self.removeSnapPoints(self.fixedSnapPoints)
            self.removeSnapPoints(self.draggingSnapPoints)
        super().mouseReleaseEvent(event)

        if event.button() == Qt.MiddleButton and self._isPanning:
            self._isPanning = False
            self.setCursor(Qt.ArrowCursor)

        self.snapManager.calculateFixedSnapPoints()

    def wheelEvent(self, event: QWheelEvent):
        """Handle wheel events for zooming."""
        scaleFactor = 1.1
        if event.angleDelta().y() > 0:
            self.scale(scaleFactor, scaleFactor)
        else:
            self.scale(1.0 / scaleFactor, 1.0 / scaleFactor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_E and event.modifiers() == Qt.ControlModifier:
            self.exportToDXF("your_drawing.dxf")

        if event.key() == Qt.Key_S:
            for visual in self.draggingSnapPoints:
                # Assuming each visual is a QGraphicsRectItem and you want the center of the rectangle
                rect = visual.rect()  # This gets the rectangle defining the QGraphicsRectItem
                center = visual.mapToScene(rect.center())  # Converts the rectangle's center to scene coordinates
                print(f"({center.x()}, {center.y()})")

        if event.key() == Qt.Key_Q:
            self.snapManager.calculateFixedSnapPoints()

        if event.key() == Qt.Key_Enter:
            self.finalizeDrawing()

        if event.key() == Qt.Key_D:
            pass
            
        else:
            super().keyPressEvent(event)

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

    def handleLineTool(self, event, eventType, scenePos=None):
        scenePos = self.mapToScene(event.pos())

        if eventType == 'click' and self.toolState == 'idle':
            self.lineStartPoint = scenePos
            self.tempLine = LineEntity(start_point=scenePos, temporary=True)
            self.scene.addItem(self.tempLine)
            self.toolState = 'drawing'
            self.constrainedEndPoint = scenePos

        elif eventType == 'move' and self.toolState == 'drawing' and self.tempLine:
            # Direct distance between the start point and current cursor position
            direct_distance = (scenePos - self.lineStartPoint).manhattanLength()

            # Calculate the horizontal and vertical deviations
            horizontal_deviation = abs(scenePos.y() - self.lineStartPoint.y())
            vertical_deviation = abs(scenePos.x() - self.lineStartPoint.x())

            # Define the threshold for snapping
            snap_threshold = 16  # Pixels

            if horizontal_deviation <= snap_threshold:
                # Snap horizontally if the deviation in the y-axis is within the threshold
                self.constrainedEndPoint = QPointF(scenePos.x(), self.lineStartPoint.y())
            elif vertical_deviation <= snap_threshold:
                # Snap vertically if the deviation in the x-axis is within the threshold
                self.constrainedEndPoint = QPointF(self.lineStartPoint.x(), scenePos.y())
            else:
                # No snapping; use the actual cursor position
                self.constrainedEndPoint = scenePos

            self.tempLine.setEndPoint(self.constrainedEndPoint)

        elif eventType == 'click' and self.toolState == 'drawing':
            # First, remove the temporary line from the scene
            if self.tempLine:
                finalLine = LineEntity(start_point=self.lineStartPoint, end_point=self.constrainedEndPoint, temporary=False)
                finalLine.setEndPoint(self.constrainedEndPoint)
                self.scene.addItem(finalLine)
                self.scene.removeItem(self.tempLine)
                self.toolState = 'idle'
                self.tempLine = None


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
        
        # Get the current cursor position relative to the scene
        cursorPos = self.mapToScene(self.mapFromGlobal(QCursor.pos()))
        
        # Determine the direction for length (x-axis)
        if cursorPos.x() < self.firstClickPoint.x():
            length = -length  # Apply length negatively if cursor is to the left
        
        # Determine the direction for width (y-axis)
        if cursorPos.y() < self.firstClickPoint.y():
            width = -width  # Apply width negatively if cursor is above
            
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

                # Assume cursorPos is the last known position of the cursor stored in self.lastCursorPos
                cursorPos = self.lastCursorPos
                
                # Determine the direction for length (x-axis)
                if cursorPos.x() < self.firstClickPoint.x():
                    length = -length

                # Determine the direction for width (y-axis)
                if cursorPos.y() < self.firstClickPoint.y():
                    width = -width
                    
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
        finalRect.setPen(self.rectanglePen)
        
        finalRect.setBrush(QColor(20, 100, 160, 127))
        finalRect.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.scene.addItem(finalRect)

        self.snapManager.calculateFixedSnapPoints()

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
        # Ensure pen is defined with desired properties for visibility
        pen = QPen(Qt.gray, 1)

        # Create line items for the crosshair
        horizontalLine = QGraphicsLineItem(-10000, 0, 10000, 0)
        verticalLine = QGraphicsLineItem(0, -10000, 0, 10000)

        # Set the pen for each line item
        horizontalLine.setPen(pen)
        verticalLine.setPen(pen)

        # Add the line items to the scene
        self.scene.addItem(horizontalLine)
        self.scene.addItem(verticalLine)

    def setDrawingMode(self, mode):
        """Set the current drawing mode."""
        self.drawingMode = mode
        if mode == 'line':
            self.toolState = 'idle'
            self.lineStartPoint = None
            self.lineEndPoint = None
        
        print(f"Switched to {mode} mode.")
        
    def calculateFixedSnapPoints(self, excludeItem=None):
        snapPoints = [QPointF(0, 0)]
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
