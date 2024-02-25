import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QGraphicsItem, QFileDialog
from PyQt5.QtCore import QRectF, QPointF, Qt
from PyQt5.QtGui import QPen, QPainter
import ezdxf

class LineItem(QGraphicsItem):
    def __init__(self, start_point, end_point, parent=None):
        super().__init__(parent)
        self.start_point = QPointF(*start_point)  # Convert tuple to QPointF
        self.end_point = QPointF(*end_point)  # Convert tuple to QPointF

    def boundingRect(self):
        # Calculate the bounding rectangle of the line
        return QRectF(self.start_point, self.end_point).normalized()

    def paint(self, painter, option, widget=None):
        # Paint the line
        pen = QPen(Qt.black, 2)  # Set the pen to draw the line
        painter.setPen(pen)
        painter.drawLine(self.start_point, self.end_point)

class CADView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setSceneRect(0, 0, 1000, 1000)  # Define the initial scene size
        self.setDragMode(QGraphicsView.ScrollHandDrag)  # Enable hand drag for scrolling

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2D CAD Application")
        self.setGeometry(100, 100, 800, 600)  # Initial window size

        self.scene = QGraphicsScene()  # Create a scene for drawing
        self.view = CADView(self.scene)  # Create a view to display the scene
        self.setCentralWidget(self.view)

        # Example: Add a simple line to the scene
        self.scene.addItem(LineItem((100, 100), (300, 300)))
      
    def open(self):
        # Open a dialog to load a DXF file
        options = QFileDialog.Options()
        filePath, _ = QFileDialog.getOpenFileName(self, "Open DXF File", "", "DXF Files (*.dxf);;All Files (*)", options=options)
        if filePath:
            self.loadDXF(filePath)

    def loadDXF(self, filePath):
        self.scene.clear()  # Clear the scene first
        doc = ezdxf.readfile(filePath)
        msp = doc.modelspace()

        for e in msp.query('LINE'):
            start_point = e.dxf.start
            end_point = e.dxf.end
            self.scene.addItem(LineItem((start_point.x, start_point.y), (end_point.x, end_point.y)))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
