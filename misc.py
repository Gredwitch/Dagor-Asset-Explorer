from os import path
from ctypes import cdll
from typing import Iterable
from PyQt5.QtCore import QDir, Qt
from PyQt5.QtWidgets import QFileDialog, QDialog

def getPath(relativePath:str):
	return path.abspath(path.join(path.dirname(__file__), relativePath))

def loadDLL(name:str):
	dllPath = getPath(f"bin/{name}")

	if not path.exists(dllPath):
		return None
	else:
		return cdll.LoadLibrary(dllPath)

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

def formatBytes(size):
	power = 2**10
	n = 0
	power_labels = {0 : " B", 1: " KB", 2: " MB", 3: " GB", 4: " TB"}

	while size > power:
		size /= power
		n += 1
	
	return str(round(size)) + power_labels[n]