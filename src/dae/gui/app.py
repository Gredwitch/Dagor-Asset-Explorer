
import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import util.log as log
import gc
# from PyQt5 import uic, QtWidgets, QtCore, QtGui
from PyQt5.uic import loadUi
from PyQt5.QtCore import pyqtSignal, QDir, QThreadPool, QFileInfo, QDirIterator
from PyQt5.QtWidgets import QMainWindow, QGridLayout, QAction, QFileDialog, QApplication
from PyQt5.QtGui import QIcon, QStandardItem
from gui.customtreeview import CustomTreeView, AssetItem, FolderItem
from gui.progressDialog import ProgressDialog, BusyProgressDialog
from util.misc import openFile, getResPath, getUIPath
from util.assetmanager import AssetManager
from parse.gameres import GameResDesc
from parse.realres import RealResData
from parse.material import DDSx
from util.assetcacher import AssetCacher
from util.enums import *
from util.terminable import Exportable, Pack
from functools import partial
from traceback import format_exc

# LOADINGGIF_SIZE = QSize(150, 150)

MAINWINDOWUI_PATH = getUIPath("dae.ui")

SOUND_ICO_PATH = getResPath("asset_sound.bmp")
SHOULD_CACHE:tuple[type[Exportable]] = (
	DDSx,
	RealResData
)

def handleCaching(asset:Exportable):
	for type in SHOULD_CACHE:
		if isinstance(asset, type):
			AssetCacher.cacheAsset(asset)

			break

def generateFileFilters():
	filters = ["All supported files ("]

	for cls in AssetManager.getOpenableClasses():
		fformat = f"*.{cls.fileExtension}"

		filters[0] += f"{fformat} "

		filters.append(f"{cls.classNiceName} ({fformat})")
	
	filters[0] += "*Desc.bin)"
	filters.append("GameResDesc (*Desc.bin)")

	return filters

class MainWindow(QMainWindow):
	__FILE_FILTERS = generateFileFilters()

	requestedDialog = pyqtSignal(int)
	taskProgress = pyqtSignal(int)
	taskStatus = pyqtSignal(str)
	taskTitle = pyqtSignal(str)
	dialogClosed = pyqtSignal(bool)

	gridLayout:QGridLayout
	treeView:CustomTreeView

	actionOpenFolder:QAction
	actionOpenFiles:QAction
	actionUnmount:QAction
	actionClose:QAction

	def __init__(self):
		super().__init__()
		
		loadUi(MAINWINDOWUI_PATH, self)

		self.gridLayout.setContentsMargins(-1, -1, -1, -1)
		
		self.treeView.initModel(self.lineEdit)

		self.clearItems:list[function] = []

		self.actionClose.triggered.connect(self.close)
		self.actionOpenFolder.triggered.connect(self.openFolder)
		self.actionOpenFiles.triggered.connect(self.openAssets)
		self.actionUnmount.triggered.connect(self.unmountAssets)

		self.threadPool = QThreadPool()
		self.cachedIcons:dict[str:QIcon] = {}
		
		self.show()
	
	def unmountAssets(self):
		for v in self.clearItems: 
			try: 
				v() 
			except Exception as e: 
				print(format_exc())

		self.clearItems:list[function] = []

		self.treeView.clear()
		AssetCacher.clearCache()

		gc.collect()

	
	def getIcon(self, icon:str):
		if not icon in self.cachedIcons:
			self.cachedIcons[icon] = QIcon(getResPath(icon))
		
		return self.cachedIcons[icon]

	def openFolder(self):
		dialog = openFile(title = "Open asset folder", fileMode = QFileDialog.DirectoryOnly)

		if dialog is None:
			return
		
		self.mountAssets(dialog.selectedFiles())
	
	def openAssets(self):
		dialog = openFile(title = "Open assets", nameFilters = self.__FILE_FILTERS)

		if dialog is None:
			return
		
		self.mountAssets(dialog.selectedFiles())
	
	def mountAssets(self, paths:list[str]):
		self.threadPool.start(partial(self.__mountAssetsInternal__, paths))
	
	def __mountAssetsInternal__(self, paths:list[str]):
		self.requestedDialog.emit(DIALOG_STATUS)
		
		self.taskTitle.emit("Mounting assets")
		self.taskStatus.emit("Loading files...")

		for p in paths:
			self.exploreFileInfo(QFileInfo(p), self.treeView.treeModel)

		self.requestedDialog.emit(DIALOG_NONE)
	


	def exploreFileInfo(self, finfo:QFileInfo, parent:QStandardItem):
		if finfo.isFile():
			absFilePath = finfo.absoluteFilePath()
			suffix = finfo.completeSuffix()
			isDesc = absFilePath[-8:] == "Desc.bin"
			
			if isDesc or AssetManager.isOpenable(suffix):
				self.taskStatus.emit(f"Loading {absFilePath}")

				log.log(f"Found {absFilePath}")
				log.addLevel()

				if isDesc:
					AssetCacher.appendGameResDesc(GameResDesc(absFilePath))
				else:
					level = log.curLevel

					try:
						# pass
						asset = AssetManager.initializeAsset(absFilePath, suffix)

						handleCaching(asset)

						if asset == None or not asset.valid:
							log.log(f"Failed to mount '{finfo.absoluteFilePath()}'", LOG_ERROR)
						else:
							item:AssetItem = self.getAssetItem(asset, finfo)
							
							parent.appendRow(item.getRow())
					except Exception as ex:
						log.log(f"Couldn't initialize '{absFilePath}'", LOG_ERROR)
						print(format_exc())

						log.subLevel(log.curLevel - level)

						pass
				
				log.subLevel()
		elif finfo.isDir():
			iterator = QDirIterator(
				finfo.absoluteFilePath(),
				AssetManager.getOpenableFiles(),
				QDir.Files | QDir.AllDirs | QDir.NoDotAndDotDot | QDir.NoSymLinks,
				QDirIterator.NoIteratorFlags)
			

			if iterator.hasNext():
				item = FolderItem(self, finfo)

				while iterator.hasNext():
					self.exploreFileInfo(QFileInfo(iterator.next()), item.mainItem)
				
				parent.appendRow(item.getRow())
	

	def getAssetItem(self, asset:Exportable, finfo:QFileInfo = None, parentAsset:AssetItem = None) -> AssetItem:
		if asset.iconName is None:
			raise Exception(f"{asset} has no icon name")

		item = AssetItem(self, finfo, self.getIcon(asset.iconName), asset, parentAsset)
		
		if isinstance(asset, Pack):
			for v in asset.getPackedFiles():
				handleCaching(v)

				item.mainItem.appendRow(self.getAssetItem(v, None, item).getRow())
		
		return item



class App(QApplication):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.__dialogVal = False
		
		window = MainWindow()
		
		window.requestedDialog.connect(self.handleDialogRequest)
		window.taskTitle.connect(self.handleDialogTitle)
		window.taskStatus.connect(self.handleDialogStatus)
		window.taskProgress.connect(self.handleDialogProgress)
		window.dialogClosed.emit(self.__dialogVal)

		self.window = window
		self.progressDialog:ProgressDialog = None
	
	def handleDialogRequest(self, dialogType:int):
		if dialogType == DIALOG_NONE:
			self.progressDialog.close()
			self.progressDialog = None
			
			self.window.setEnabled(True)
		else:
			self.window.setEnabled(False)
			
			if dialogType == DIALOG_PROGRESS:
				self.progressDialog = ProgressDialog()
			elif dialogType == DIALOG_STATUS:
				self.progressDialog = BusyProgressDialog()
		
		self.__curDialogType = dialogType

	def handleDialogTitle(self, txt:str):
		self.progressDialog.setWindowTitle(txt)

	def handleDialogStatus(self, txt:str):
		self.progressDialog.setStatus(txt)

	def handleDialogProgress(self, progress:int):
		self.progressDialog.setProgress(progress)



if __name__ == "__main__":
	sys.excepthook = lambda cls, e, t: sys.__excepthook__(cls, e, t)

	app = App(sys.argv)
	# app.window.mountAssets([r"C:/Program Files (x86)/Steam/steamapps/common/War Thunder/content/base/res/aircrafts"])
	exitCode = app.exec_()

	sys.exit(exitCode)