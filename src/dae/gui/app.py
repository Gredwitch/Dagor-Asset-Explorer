
import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import util.log as log
import gc
# from PyQt5 import uic, QtWidgets, QtCore, QtGui
from PyQt5.uic import loadUi
from PyQt5.QtCore import pyqtSignal, QDir, QFileInfo, QDirIterator, QRunnable, QThreadPool
from PyQt5.QtWidgets import QMainWindow, QGridLayout, QAction, QFileDialog, QApplication
from PyQt5.QtGui import QIcon, QStandardItem
from gui.customtreeview import CustomTreeView, AssetItem, FolderItem
from gui.progressDialog import ProgressDialog, BusyProgressDialog
from util.misc import openFile, getResPath, getUIPath
from util.assetmanager import AssetManager
from util.settings import SETTINGS
from parse.gameres import GameResDesc
from parse.realres import RealResData
from parse.material import DDSx
from util.assetcacher import AssetCacher
from util.enums import *
from util.terminable import Exportable, Pack, Terminable
from gui.settingsDialog import SettingsDialog
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
	actionSettings:QAction

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
		self.actionSettings.triggered.connect(self.openSettings)

		self.threadPool = QThreadPool()
		self.activeTerminable:Terminable = None
		self.shouldTerminate = False
		self.treeView.mainWindow = self

		self.cachedIcons:dict[str:QIcon] = {}
		
		self.show()
	
	def openSettings(self):
		settings = SettingsDialog(self)
		settings.exec_()

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
		# self.activeThread = QRunnable(partial(self.__mountAssetsInternal__, paths))
		# thread = threading.Thread(target = partial(self.__mountAssetsInternal__, paths))
		# thread.start()
		# self.threadPool.start(self.activeThread)
		self.threadPool.start(partial(self.__mountAssetsInternal__, paths))
	
	def __mountAssetsInternal__(self, paths:list[str]):
		self.setRequestedDialog(DIALOG_STATUS)
		
		self.setTaskTitle("Mounting assets")
		self.setTaskStatus("Loading files...")

		for p in paths:
			self.exploreFileInfo(QFileInfo(p), self.treeView.treeModel)

		self.setRequestedDialog(DIALOG_NONE)
	
	def setRequestedDialog(self, rType:int):
		self.requestedDialog.emit(rType)

	def setTaskTitle(self, title:str):
		self.taskTitle.emit(title)

	def setTaskProgress(self, progress:int):
		self.taskProgress.emit(progress)

	def setTaskStatus(self, status:str):
		self.taskStatus.emit(status)
	
	def setTerminable(self, ter:Terminable):
		self.activeTerminable = ter
	
	def clearTerminable(self):
		self.activeTerminable = None

	def exploreFileInfo(self, finfo:QFileInfo, parent:QStandardItem):
		if self.shouldTerminate:
			return False

		if finfo.isFile():
			absFilePath = finfo.absoluteFilePath()
			suffix = finfo.completeSuffix()
			isDesc = absFilePath[-8:] == "Desc.bin"
			
			if isDesc or AssetManager.isOpenable(suffix):
				self.setTaskStatus(f"Loading {absFilePath}")
				success = False

				log.log(f"Found {absFilePath}")
				log.addLevel()

				if isDesc:
					grd = GameResDesc(absFilePath)

					AssetCacher.appendGameResDesc(grd)

					self.setTerminable(grd)
					grd.loadDataBlock()
					self.clearTerminable()

					success = True
				else:
					level = log.curLevel

					try:
						# pass
						asset = AssetManager.initializeAsset(absFilePath, suffix)

						handleCaching(asset)

						self.setTerminable(asset)

						if asset == None or not asset.valid:
							log.log(f"Failed to mount '{finfo.absoluteFilePath()}'", LOG_ERROR)
						else:
							item:AssetItem = self.getAssetItem(asset, finfo)
							
							parent.appendRow(item.getRow())

							success = True
					except Exception as ex:
						log.log(f"Couldn't initialize '{absFilePath}'", LOG_ERROR)
						print(format_exc())

						log.subLevel(log.curLevel - level)

						pass
				
				log.subLevel()

				self.clearTerminable()

				return success
		elif finfo.isDir():
			iterator = QDirIterator(
				finfo.absoluteFilePath(),
				AssetManager.getOpenableFiles(),
				QDir.Files | QDir.AllDirs | QDir.NoDotAndDotDot | QDir.NoSymLinks,
				QDirIterator.NoIteratorFlags)
			

			if iterator.hasNext():
				item = FolderItem(self, finfo)
				fileCnt = 0
				hasFile = False

				while iterator.hasNext():
					foundFile = self.exploreFileInfo(QFileInfo(iterator.next()), item.mainItem)

					if not hasFile and foundFile:
						hasFile = True
				
				if hasFile:
					parent.appendRow(item.getRow())

				return hasFile
		
		return False
	
	def getAssetItem(self, asset:Exportable, finfo:QFileInfo = None, parentAsset:AssetItem = None) -> AssetItem:
		if asset.iconName is None:
			raise Exception(f"{asset} has no icon name")

		item = AssetItem(self, finfo, self.getIcon(asset.iconName), asset, parentAsset)
		
		if isinstance(asset, Pack):
			for v in asset.getPackedFiles():
				handleCaching(v)

				item.mainItem.appendRow(self.getAssetItem(v, None, item).getRow())
		
		return item

	
	def terminateThreads(self):
		print("!!! Terminating thread !!!")

		self.shouldTerminate = True

		if self.activeTerminable is not None:
			self.activeTerminable.terminate()
		
		self.threadPool.waitForDone()
		self.clearTerminable()

		self.shouldTerminate = False
		
		log.subLevel(log.curLevel)
		
		self.setRequestedDialog(DIALOG_NONE)


class App(QApplication):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		window = MainWindow()
		
		window.requestedDialog.connect(self.handleDialogRequest)
		window.taskTitle.connect(self.handleDialogTitle)
		window.taskStatus.connect(self.handleDialogStatus)
		window.taskProgress.connect(self.handleDialogProgress)

		self.window = window
		self.progressDialog:ProgressDialog = None
	
	def handleDialogRequest(self, dialogType:int):
		if dialogType == DIALOG_NONE:
			if self.progressDialog is not None:
				self.progressDialog.close()
				self.progressDialog = None
			
			self.window.setEnabled(True)
		else:
			self.window.setEnabled(False)
			
			if dialogType == DIALOG_PROGRESS:
				self.progressDialog = ProgressDialog(self.window)
			elif dialogType == DIALOG_STATUS:
				self.progressDialog = BusyProgressDialog(self.window)

	def handleDialogTitle(self, txt:str):
		if self.progressDialog is not None:
			self.progressDialog.setWindowTitle(txt)

	def handleDialogStatus(self, txt:str):
		if self.progressDialog is not None:
			self.progressDialog.setStatus(txt)

	def handleDialogProgress(self, progress:int):
		if self.progressDialog is not None:
			self.progressDialog.setProgress(progress)



if __name__ == "__main__":
	sys.excepthook = lambda cls, e, t: sys.__excepthook__(cls, e, t)

	app = App(sys.argv)
	# app.window.mountAssets([r"C:/Program Files (x86)/Steam/steamapps/common/War Thunder/content/base/res/aircrafts"])
	exitCode = app.exec_()

	sys.exit(exitCode)