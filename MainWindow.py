#MainWindow.py
from PyQt5.QtWidgets import (
    QMainWindow,
    QApplication,
    QWidget,
    QVBoxLayout,
    QToolBar,
    QAction,
    QGraphicsScene,
    QLabel
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from DrawingArea import DrawingArea
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Slab Wizard')
        self.setGeometry(200, 100, 1200, 800)
        self.setupCentralWidget()
        self.setupToolBar()
        
    def setupCentralWidget(self):
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        layout = QVBoxLayout(centralWidget)

        # Drawing area setup
        scene = QGraphicsScene()
        self.drawingArea = DrawingArea(scene)
        layout.addWidget(self.drawingArea)

        # Position label setup
        self.positionLabel = QLabel("Scene Position: ")
        layout.addWidget(self.positionLabel)

        # Connect position label
        self.drawingArea.positionChanged.connect(self.updatePositionLabel)

    def setupToolBar(self):
        self.leftToolBar = QToolBar("Left Toolbar")
        self.leftToolBar.setIconSize(QSize(64, 64))
        self.addToolBar(Qt.LeftToolBarArea, self.leftToolBar)

        # Toolbar actions
        rectangleAction = QAction(QIcon('rectangleButton.png'), "Draw Rectangle", self)

        # Add actions to toolbar
        self.leftToolBar.addAction(rectangleAction)

        # Connect actions to methods
        rectangleAction.triggered.connect(lambda: self.drawingArea.setDrawingMode('rectangle'))

    def updatePositionLabel(self, text):
        self.positionLabel.setText(text)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.drawingArea.setDrawingMode('selection')

        if event.key() == Qt.Key_R:
            self.drawingArea.setDrawingMode('rectangle')

        if event.key() == Qt.Key_Enter:
            self.drawingArea.finalizeDrawing()
            # print("Enter pressed")

        if event.key() == Qt.Key_C:
            self.drawingArea.calculateAllSnapPoints()
            print("Calculate all snap points")

        if event.key() == Qt.Key_D:
            points = self.drawingArea.calculateAllSnapPoints()
            self.drawingArea.displaySnapPoints(points)
            print("Display snap points")

        else:
            super().keyPressEvent(event)
            

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    mainWindow.drawingArea.setFocus()
    sys.exit(app.exec_())
