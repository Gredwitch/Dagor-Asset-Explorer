
from io import StringIO
import sys
from os import path, remove

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from PyQt5.QtWidgets import QDialog, QWidget, QOpenGLWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QMatrix4x4, QVector3D
from PyQt5.uic import loadUi
from util.misc import getUIPath
from util.enums import *
from util.settings import SETTINGS
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
# from pywavefront import Wavefront, material, mesh
from tempfile import NamedTemporaryFile
from traceback import format_exc
from random import randint

PREVIEWUI_PATH = getUIPath("preview.ui")

class ObjModel:
	def __init__(self, buf:StringIO):
		vertices:list[tuple[float, float, float]] = []
		faces:list[tuple[int, int, int]] = []

		while True:
			line = buf.readline()

			if not line:
				break
			
			comps = line.strip().split(" ")

			if comps[0] == "v":
				vertices.append(tuple(float(x) for x in comps[1:]))
			elif comps[0] == "f":
				faces.append(tuple(int(x.split("/")[0]) for x in comps[1:]))
			else:
				continue
		
		self.__vertices = vertices
		self.__faces = faces
	
	@property
	def vertices(self):
		return self.__vertices
	
	@property
	def faces(self):
		return self.__faces
		

class CustomOpenGL(QOpenGLWidget):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		self.faces:list[tuple[int, int, int]] = None
		self.vertices:list[tuple[float, float, float]] = None
		
		self.rotation = QMatrix4x4()
		self.zoom = 0.6
	
	def initializeGL(self):
		glClearColor(0.0, 0.0, 0.0, 1.0)
		# glDepthFunc(GL_LESS)

	def paintGL(self):
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		glMultMatrixf(self.rotation.data())
		glScalef(self.zoom, self.zoom, self.zoom)

		
		glBegin(GL_TRIANGLES)
		glColor3f(0.5, 0.5, 0.5)

		self.drawModel()
		glEnd()

	def drawModel(self):
		for face in self.faces:
			for idx in face:
				glVertex3f(*self.vertices[idx - 1])


	
	def resizeGL(self, width, height):
		# Set the viewport
		glViewport(0, 0, width, height)

	def mousePressEvent(self, event):
		if event.button() == Qt.LeftButton:
			self.last_pos = event.pos()

	def mouseMoveEvent(self, event):
		if event.buttons() & Qt.LeftButton:
			dx = event.x() - self.last_pos.x()
			dy = event.y() - self.last_pos.y()

			sensitivity = 0.2

			self.rotation.rotate(sensitivity * dy, 1.0, 0.0, 0.0)
			self.rotation.rotate(sensitivity * dx, 0.0, 1.0, 0.0)

			self.last_pos = event.pos()
			self.update()

	def wheelEvent(self, event):
		angle_delta = event.angleDelta().y()
		if angle_delta > 0:
			self.zoom *= 1.1
		else:
			self.zoom /= 1.1
		
		self.update()

class CustomOpenGL2(QOpenGLWidget): ...

class PreviewDialog(QDialog):
	gl:CustomOpenGL
	
	def __init__(self, parent:QWidget, obj:str):
		super().__init__(parent)
		
		loadUi(PREVIEWUI_PATH, self)

		self.obj = ObjModel(StringIO(obj))

		self.gl.vertices = self.obj.vertices
		self.gl.faces = self.obj.faces


	
	def __delModelFile__(self, tfName:str):
		self.__delTempFile__(tfName)
		# self.__delTempFile__(f"{tfName}.mtl")
	
	def __delTempFile__(self, fileName:str):
		try:
			remove(fileName)
		except Exception as e:
			print(f"Failed to remove temp file {fileName}")

			print(format_exc())

		


if __name__ == "__main__":
	from PyQt5.QtWidgets import QApplication

	app = QApplication([])
	
	file = open(r"C:\Users\Gredwitch\Documents\WTBS\DagorAssetExplorer\output\arctic_tayga_patrul_551_0.obj", "r")
	obj = file.read()
	file.close()

	widget = PreviewDialog(None, obj)
	widget.show()
	app.exec_()