import sys
import math
from os import path
from ctypes import cdll
from typing import Iterable
from PyQt5.QtCore import QDir, Qt
from PyQt5.QtWidgets import QFileDialog, QDialog

# def getPath(relativePath:str):
# 	return path.abspath(path.join(path.dirname(__file__), relativePath))

def getParentDir(filePath:str, level:int = 1):
	if level <= 0:
		return filePath
	else:
		return getParentDir(path.dirname(filePath), level - 1)

if getattr(sys, "frozen", False):
	ROOT_FOLDER = path.dirname(sys.executable)
else:
	ROOT_FOLDER = getParentDir(path.abspath(__file__), 4)

RES_FOLDER = path.join(ROOT_FOLDER, "res")
LIB_FOLDER = path.join(ROOT_FOLDER, "lib")
UI_FOLDER = path.join(ROOT_FOLDER, "ui")

def getResPath(fileName:str):
	return path.join(RES_FOLDER, fileName)

def loadDLL(name:str):
	dllPath = path.join(LIB_FOLDER, name)

	if not path.exists(dllPath):
		return None
	else:
		return cdll.LoadLibrary(dllPath)

def getUIPath(fileName:str):
	return path.join(UI_FOLDER, fileName)

def matrix_mul(A, B):
	if len(A[0]) != len(B):
		raise ValueError("Matrix dimensions do not match")
	
	# Initialize the result matrix with zeros
	result = [[0 for _ in range(len(B[0]))] for _ in range(len(A))]
	
	# Compute the matrix multiplication
	for i in range(len(A)):
		for j in range(len(B[0])):
			for k in range(len(B)):
				result[i][j] += A[i][k] * B[k][j]
	
	return result
	
def vectorTransform(matrix, vector):
	result = [0, 0, 0]

	for i in range(3):
		for j in range(3):
			result[i] += matrix[i][j] * vector[j]
	
	result[0] += matrix[0][3]
	result[1] += matrix[1][3]
	result[2] += matrix[2][3]

	return result


def matrixToEuler(matrix):
	# Extract the rotational part of the matrix (upper-left 3x3 submatrix)
	r11, r12, r13 = matrix[0][:3]
	r21, r22, r23 = matrix[1][:3]

	# Calculate yaw (rotation around the y-axis)
	yaw = math.atan2(r13, math.sqrt(r11**2 + r12**2))

	# Calculate pitch (rotation around the x-axis)
	pitch = math.atan2(-r23, math.sqrt(r21**2 + r22**2))

	# Calculate roll (rotation around the z-axis)
	roll = math.atan2(r21, r22)

	return pitch, roll, yaw


def getVertCenter(verts:list[list[float, float, float]], startV:int, numV:int):
	x, y, z = 0, 0, 0

	for i in range(startV, startV + numV):
		x += verts[i][0]
		y += verts[i][0]
		z += verts[i][0]
	
	return (x / numV, y / numV, z / numV)


def openFile(window = None, title:str = "", nameFilters:Iterable = None, shouldAccept = lambda x: True, fileMode:int = QFileDialog.ExistingFiles):
	selectedFolderValid = False

	while not selectedFolderValid:
		dialog = QFileDialog()
		dialog.setWindowTitle(title)
		dialog.setDirectory(QDir.currentPath())
		dialog.setFileMode(fileMode)
		
		# dialog.setOption(QFileDialog.Option.DontUseNativeDialog,True)

		# listView = dialog.findChild(QListView,name = "listView")
		
		# if listView != None:
		#     listView.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
		
		# treeView = dialog.findChild(QTreeView)

		# if treeView != None:
		#     treeView.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
		
		if nameFilters != None:
			dialog.setNameFilters(nameFilters)

		if dialog.exec_() == QDialog.Accepted:
			selectedFolderValid = shouldAccept(dialog)
		else:
			return None
	
	if window != None:
		window.setWindowState(window.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
		window.activateWindow()
	
	return dialog

def istable(v):
	return isinstance(v, dict) or isinstance(v, list) or isinstance(v, tuple)

def pprintInternal(k, v, level:str, maxLevel:int = None):
	if istable(v):
		if maxLevel == None or len(level) * 0.5 < maxLevel:
			print(f"{level}{k}: ")

			pprint(v, level + "\t", maxLevel)
		else:
			print(f"{level}{k}: {type(v)}")
	else:
		print(f"{level}{k}: {v}")

def pprint(tab, level:str = "", maxLevel:int = None):
	if isinstance(tab, dict):
		for k in tab:
			pprintInternal(k, tab[k], level, maxLevel)
	else:
		for k, v in enumerate(tab):
			pprintInternal(k, v, level, maxLevel)

powerLabels = {0 : " B", 1: " KB", 2: " MB", 3: " GB", 4: " TB"}

def formatBytes(size):
	power = 2**10
	n = 0

	while size > power:
		size /= power
		n += 1
	
	return str(round(size)) + powerLabels[n]