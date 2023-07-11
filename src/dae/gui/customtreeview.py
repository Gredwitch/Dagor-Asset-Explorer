import sys
from os import path, system

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import util.log as log
from PyQt5.QtWidgets import QAbstractItemView, QTreeView, QLineEdit, QHeaderView, QMenu, QAction, QStyledItemDelegate, QFileDialog, QMainWindow
from PyQt5.QtCore import QMimeData, Qt, QSortFilterProxyModel, QPoint, QFileInfo
from PyQt5.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QStandardItemModel, QStandardItem, QIcon
from util.misc import formatBytes, getResPath, openFile
from util.terminable import Exportable, Packed, Pack, Terminable
from util.enums import *
from abc import abstractmethod
from pyperclip import copy as copyToClipboard
from functools import partial
from parse.material import DDSx, DDSxTexturePack2
from parse.realres import RendInst, DynModel
from parse.gameres import GameResourcePack
from traceback import format_exc
from gui.progressDialog import MessageBox


FOLDER_ICO_PATH = getResPath("folder.bmp")

class SafeStandardItem(QStandardItem):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
	
	def setParentItem(self, item):
		item.mainWindow.clearItems.append(lambda: self.clearData())

		self.setData(item, Qt.UserRole)

class SimpleItem:
	def __init__(self, mainWindow:QMainWindow, finfo:QFileInfo, type:str, icon:QIcon, name:str = None):
		self.mainWindow = mainWindow

		self.finfo = finfo

		mainItem = SafeStandardItem(name if name is not None else finfo.fileName())
		mainItem.setParentItem(self) # WARNING: if the data is not cleared manually, this will lead to memory leaks (fuck qt for that)
		mainItem.setIcon(icon)

		self.mainItem = mainItem

		fileType = SafeStandardItem(type)
		fileType.setParentItem(self)

		self.fileType = fileType

	def populateMenu(self, menu:QMenu):
		if self.hasParent():
			menu.addAction(OpenParentFileLocation(menu, self))
		else:
			menu.addAction(OpenFileLocation(menu, self))
		
		if self.finfo is not None:
			menu.addAction(CopyPathToClipboard(menu, self))
		
		# if len(menu.children()) > 0:
		# 	menu.addSeparator()
		
		menu.addSeparator()
		
		if isinstance(self, AssetItem):
			asset = self.asset

			if isinstance(asset, Packed) and self.hasParent():
				menu.addAction(Extract(menu, self))

			if isinstance(asset, DDSx):
				menu.addAction(ExportToDDS(menu, self))
			elif isinstance(asset, RendInst):
				level = log.curLevel

				try:
					menu.addAction(ExportToOBJ(menu, self, 0))

					if isinstance(asset, DynModel):
						menu.addSeparator()
						menu.addAction("WARNING: DynModel support is experimental")
						menu.addSeparator()

					asset.computeData()


					submenu = menu.addMenu("Export LOD...")

					for i in range(asset.lodCount):
						submenu.addAction(ExportToOBJ(menu, self, i))

					submenu.addSeparator()

					submenu.addAction(ExportLODsToOBJ(menu, self))
				except Exception as e:
					print(format_exc())

					log.subLevel(log.curLevel - level)

					MessageBox("Failed to compute preliminary data. Check the console for details.")

			elif isinstance(asset, Pack):
				menu.addAction(ExtractAll(menu, self))

				if isinstance(asset, DDSxTexturePack2):
					menu.addAction(ExportAllToDDS(menu, self))
				elif isinstance(asset, GameResourcePack):
					menu.addAction(ExportAllToOBJ(menu, self))
					# menu.addAction(ExportAllLODsToOBJ(menu, self))
			

	def getRow(self):
		return (self.mainItem, self.fileType, None)

	def hasParent(self):
		return False

	def getParentItem(self):
		return self

class AssetItem(SimpleItem):
	def __init__(self, mainWindow:QMainWindow, finfo:QFileInfo, icon:QIcon, asset:Exportable, parentPackage:SimpleItem = None):
		super().__init__(mainWindow,
		   finfo, 
		   asset.niceName, 
		   icon, 
		   finfo.fileName() if parentPackage is None else asset.name)

		self.parentPackage = parentPackage

		fileSize = SafeStandardItem(str(asset.size))
		fileSize.setParentItem(self)
		self.fileSize = fileSize
		
		self.asset = asset
	
	def hasParent(self):
		return self.parentPackage is not None

	def getParentItem(self):
		if self.parentPackage is None:
			return self
		else:
			return self.parentPackage.getParentItem()
	
	def getRow(self):
		return (self.mainItem, self.fileType, self.fileSize)

class FolderItem(SimpleItem):
	__ICON = None
	__TYPE = "Folder"

	def __init__(self, mainWindow:QMainWindow, finfo:QFileInfo):
		if not FolderItem.__ICON:
			FolderItem.__ICON = QIcon(FOLDER_ICO_PATH)
		
		super().__init__(mainWindow,
		   finfo, 
		   FolderItem.__TYPE, 
		   FolderItem.__ICON)



class CustomAction(QAction):
	def __init__(self, parent, item:SimpleItem):
		super().__init__(parent)

		self.setText(self.actionText)

		self.__item = item

		self.triggered.connect(self.run)
	
	@property
	def item(self):
		return self.__item

	@abstractmethod
	def run(self):
		...
	
	@property
	def mainWindow(self):
		return self.item.mainWindow

	@property
	@abstractmethod
	def actionText(self) -> str:
		...

class ThreadedAction(CustomAction):
	def __init__(self, parent, item:SimpleItem):
		super().__init__(parent, item)
		
		self.triggered.disconnect()

		self.triggered.connect(self.__run__)

		self.__error = False
		self.__cancel = False
	
	@property
	@abstractmethod
	def taskTitle(self) -> str:
		...
	
	@classmethod
	@property
	@abstractmethod
	def dialogType(self) -> int:
		...

	def setTerminable(self, ter:Terminable):
		self.item.mainWindow.setTerminable(ter)
	
	def clearTerminable(self):
		self.item.mainWindow.clearTerminable()
	
	def handleTermination(self, ter:Terminable):
		if self.shouldTerminate:
			return True
		else:
			self.setTerminable(ter)

			return False

	@property
	def shouldTerminate(self) -> bool:
		return self.item.mainWindow.shouldTerminate

	def setTaskStatus(self, text:str):
		self.mainWindow.setTaskStatus(text)

	def setTaskProgress(self, progress:float):
		self.mainWindow.setTaskProgress(progress * 100)

	def preRun(self) -> bool:
		return True
	
	def setErrored(self):
		self.__error = True
	
	def __run__(self):
		if not self.preRun():
			return

		self.mainWindow.setRequestedDialog(self.dialogType)
		self.mainWindow.setTaskTitle(self.taskTitle)
		self.setTaskStatus(self.taskTitle)

		self.mainWindow.threadPool.start(partial(self.__threadedRun__))


	def cancel(self):
		self.__cancel = True
	
	@property
	def cancelled(self):
		return self.__cancel

	def __threadedRun__(self):
		level = log.curLevel

		try:
			self.run()
		except Exception as e:
			self.setErrored()

			print(format_exc())

			log.subLevel(log.curLevel - level)
		
		if self.__error:
			MessageBox("An error occured during the process. Check the console for details.")


		self.mainWindow.setRequestedDialog(DIALOG_NONE)

class OpenFileLocation(CustomAction):
	def run(self):
		system('explorer.exe /select,"' + path.normpath(self.item.finfo.absoluteFilePath()) + '"')
	
	@property
	def actionText(self) -> str:
		return "Open file location"

class OpenParentFileLocation(OpenFileLocation):
	@property
	def actionText(self) -> str:
		return "Open parent location"
	
	
	def run(self):
		parentItem = self.item.getParentItem()

		system('explorer.exe /select,"' + path.normpath(parentItem.finfo.absoluteFilePath()) + '"')

class CopyPathToClipboard(CustomAction):
	def run(self):
		copyToClipboard(self.item.finfo.absoluteFilePath())
	
	@property
	def actionText(self) -> str:
		return "Copy path to clipboard"


class SaveAction(ThreadedAction):
	def preRun(self):
		dialog = openFile(title = "Save to", fileMode = QFileDialog.DirectoryOnly)

		if dialog == None:
			return
		
		self.output = dialog.selectedFiles()[0]

		return self.output is not None

	def run(self):
		self.save(self.output)
	
	@classmethod
	@property
	def dialogType(self) -> int:
		return DIALOG_PROGRESS
	
	@abstractmethod
	def save(self, output:str):
		...


class Extract(SaveAction):
	item:AssetItem

	@property
	def actionText(self) -> str:
		return "Extract"
	
	@property
	def taskTitle(self) -> str:
		return f"Extracting {self.item.asset.name}.{self.item.asset.fileExtension}"

	def save(self, output:str):
		asset:Packed = self.item.asset

		self.setTerminable(asset)
		
		asset.save(output)

		self.clearTerminable()

		self.setTaskProgress(1)

class ExtractAll(SaveAction):
	item:AssetItem

	@property
	def actionText(self) -> str:
		return "Extract all"
	
	@property
	def taskTitle(self) -> str:
		return f"Extracting files from {self.item.asset.name}.{self.item.asset.fileExtension}"
	
	def save(self, output:str):
		asset:Pack = self.item.asset
		self.setTerminable(asset)

		packedFiles = asset.getPackedFiles()
		fileCnt = len(packedFiles)

		for k, v in enumerate(packedFiles):
			if self.handleTermination(v):
				break
			
			self.setTaskStatus(f"Extracting {v.name}.{v.fileExtension}... ({k + 1}/{fileCnt})")

			v.save(output)

			self.setTaskProgress((k + 1) / fileCnt)
		
		self.clearTerminable()


class ExportToDDS(SaveAction):
	item:AssetItem

	@property
	def actionText(self) -> str:
		return "Export to DDS"
	
	@property
	def taskTitle(self) -> str:
		return f"Exporting to {self.item.asset.name}.dds"

	def save(self, output:str):
		asset:DDSx = self.item.asset
		self.setTerminable(asset)
		
		asset.exportDDS(output)

		self.clearTerminable()

		self.setTaskProgress(100)

class ExportAllToDDS(SaveAction):
	item:AssetItem

	@property
	def actionText(self) -> str:
		return "Export all to DDS"
	
	@property
	def taskTitle(self) -> str:
		return f"Exporting files from {self.item.asset.name}.{self.item.asset.fileExtension} to DDS"
	
	def save(self, output:str):
		asset:DDSxTexturePack2 = self.item.asset
		self.setTerminable(asset)

		packedFiles = asset.getPackedFiles()
		fileCnt = len(packedFiles)

		for k, v in enumerate(packedFiles):
			if self.handleTermination(v):
				break

			self.setTaskStatus(f"Exporting {v.name}.dds... ({k + 1}/{fileCnt})")

			v.exportDDS(output)

			self.setTaskProgress((k + 1) / fileCnt)
		
		self.clearTerminable()


class ExportToOBJ(SaveAction):
	def __init__(self, parent, item: SimpleItem, lod:int):
		self.lod = lod

		super().__init__(parent, item)
	
	item:AssetItem

	@property
	def actionText(self) -> str:
		return f"Export LOD {self.lod} to OBJ"
	
	@property
	def taskTitle(self) -> str:
		return f"Exporting LOD to {self.item.asset.getExportName(self.lod)}.obj"

	def save(self, output:str):
		asset:RendInst = self.item.asset
		self.setTerminable(asset)
		
		asset.exportObj(self.lod, output)

		self.clearTerminable()
		

		self.setTaskProgress(1)

class ExportLODsToOBJ(SaveAction):
	item:AssetItem

	@property
	def actionText(self) -> str:
		return "Export all LODs to OBJ"
	
	@property
	def taskTitle(self) -> str:
		return f"Exporting all LODs from {self.item.asset.name} to OBJ"

	def save(self, output:str):
		asset:RendInst = self.item.asset
		self.setTerminable(asset)
		asset.computeData()

		for i in range(asset.lodCount):
			if self.handleTermination(asset):
				break

			asset.exportObj(i, output)

			self.setTaskProgress((i + 1) / asset.lodCount)
		
		self.clearTerminable()

class ExportAllToOBJ(SaveAction):
	item:AssetItem

	@property
	def actionText(self) -> str:
		return "Export all models to LOD 0 OBJ"
	
	@property
	def taskTitle(self) -> str:
		return f"Exporting LOD 0 models from {self.item.asset.name}.{self.item.asset.fileExtension} to OBJ"
	
	def save(self, output:str):
		asset:GameResourcePack = self.item.asset
		self.setTerminable(asset)

		packedFiles = asset.getPackedFiles()
		fileCnt = 0

		for v in packedFiles:
			if isinstance(v, RendInst):
				fileCnt += 1

		k = 0

		for v in packedFiles:
			if isinstance(v, RendInst):
				if self.handleTermination(v):
					break
				k += 1

				self.setTaskStatus(f"Exporting {v.getExportName(0)}.obj... ({k}/{fileCnt})")

				level = log.curLevel

				try:
					v.exportObj(0, output)
				except Exception as e:
					print(format_exc())

					self.setErrored()

					log.subLevel(log.curLevel - level)

				self.setTaskProgress(k / fileCnt)
		
		self.clearTerminable()


class FileSizeSortProxyModel(QSortFilterProxyModel):
	def lessThan(self, left, right):
		if left.column() == right.column() == 2: 
			leftData = self.sourceModel().data(left)
			rightData = self.sourceModel().data(right)

			if leftData is None:
				return False
			elif rightData is None:
				return True
			else:
				return int(leftData) < int(rightData)

		return super().lessThan(left, right)
	

class OptimizedModel(QStandardItemModel):
	__HEADER_LABELS = ("Name", "Type", "Size")

	def __init__(self, parent:QTreeView, lineEdit:QLineEdit):
		super().__init__(parent)
		
		self.lineEdit = lineEdit
		self.lineEdit.textEdited.connect(self.textChanged)

		self.reset()
	
	def textChanged(self, text):
		self.proxyModel.setFilterRegExp(text)
	
	def reset(self):
		self.clear()

		self.setHorizontalHeaderLabels(OptimizedModel.__HEADER_LABELS)

		self.proxyModel = FileSizeSortProxyModel(self.parent())
		self.proxyModel.setSourceModel(self)
		self.proxyModel.setFilterCaseSensitivity(Qt.CaseInsensitive)
		self.proxyModel.setFilterKeyColumn(0)
		self.proxyModel.setRecursiveFilteringEnabled(True)

class FileSizeDelegate(QStyledItemDelegate):
	def displayText(self, value, locale):
		return formatBytes(int(value))

class CustomTreeView(QTreeView):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
		self.setContextMenuPolicy(Qt.CustomContextMenu)
		self.setAcceptDrops(True)
		self.setDragEnabled(True)
		self.mainWindow = None

		self.customContextMenuRequested.connect(self.rightClickEvent)
	
	def rightClickEvent(self, pos:QPoint):
		index = self.indexAt(pos)
		item:SimpleItem = index.data(Qt.UserRole)

		# print((pos.x(), pos.y()), index.model())

		if item == None or not isinstance(item, SimpleItem): # TODO: add multi selection support
			return
		
		menu = QMenu()

		item.populateMenu(menu)

		action:CustomAction = menu.exec_(self.mapToGlobal(pos))

	def dropEvent(self, event:QDropEvent):
		paths = self.getEventPaths(event.mimeData())

		if paths is not None:
			self.mainWindow.mountAssets(paths)
	
	def getEventPaths(self, data:QMimeData):
		if data.hasText():
			text = data.text()

			paths = text.split("\n")

			for id, fpath in enumerate(paths):
				if fpath[:8] == "file:///":
					fpath = fpath[8:]

					paths[id] = fpath

					if path.exists(fpath):
						return paths
		
		return None
		
	def dragMoveEvent(self, event:QDragMoveEvent):
		if self.getEventPaths(event.mimeData()) == False:
			event.ignore()
		else:
			event.accept()

	def dragEnterEvent(self, event:QDragEnterEvent):
		if self.getEventPaths(event.mimeData()) == False:
			event.ignore()
		else:
			event.accept()
	
	def edit(self, index, trigger, event):
		if trigger == QAbstractItemView.DoubleClicked:
			return False
		else:
			return True

	def initModel(self, lineEdit:QLineEdit):
		self.treeModel = OptimizedModel(self, lineEdit)

		self.__reinitModel__()
		
	
	def __reinitModel__(self):
		self.setSortingEnabled(True)
		self.setModel(self.treeModel.proxyModel)

		header = self.header()
		header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
		header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
		header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
		
		header.setSortIndicator(0, Qt.AscendingOrder)
		self.setItemDelegateForColumn(2, FileSizeDelegate())


	def clear(self):
		self.treeModel.reset()
		
		self.__reinitModel__()
