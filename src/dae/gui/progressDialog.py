import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from PyQt5 import QtWidgets, QtGui, uic
from util.misc import getResPath, getUIPath
from winsound import PlaySound, SND_ALIAS, SND_ASYNC

PROGRESSDIALOG_UI_PATH = getUIPath("progressDialog.ui")
LOADING_GIF_PATH = getResPath("loading.gif")
ERROR_ICO_PATH = getResPath("failure.png")


				# PlaySound("SystemHand",SND_ALIAS | SND_ASYNC)

				# box = QMessageBox()

class MessageBox(QtWidgets.QMessageBox):
	def __init__(self, text:str):
		super().__init__()

		PlaySound("SystemHand", SND_ALIAS | SND_ASYNC)

		self.setIcon(QtWidgets.QMessageBox.Icon.Critical)
		self.setIconPixmap(QtGui.QPixmap(ERROR_ICO_PATH))
		self.setWindowTitle("Unfunny!")
		self.setText(text)
		self.setStandardButtons(QtWidgets.QMessageBox.Ok)
		
		self.exec()




class ProgressDialog(QtWidgets.QDialog):
	def __init__(self):
		super().__init__()

		uic.loadUi(PROGRESSDIALOG_UI_PATH, self)

		# self.setWindowTitle(title)
		
		movie = QtGui.QMovie(LOADING_GIF_PATH)
		# movie.setScaledSize(LOADINGGIF_SIZE)
		movie.start()

		self.movieLabel.setMovie(movie)

		# self.setFixedSize(self.size())

		self.show()
	
	def setStatus(self, status:str):
		self.progressLabel.setText(status)
		
	def setProgress(self, value:int):
		self.progressBar.setProperty("value", value)

class BusyProgressDialog(ProgressDialog):
	def __init__(self, *args, **kargs):
		super().__init__(*args, **kargs)

		self.progressBar.setMaximum(0)
		self.progressBar.setMinimum(0)
		self.progressBar.setValue(0)
