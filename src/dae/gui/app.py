
import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import util.log as log
import gc
from PyQt5.uic import loadUi
from PyQt5.QtCore import pyqtSignal, QDir, QFileInfo, QDirIterator, QRunnable, QThreadPool, QObject
from PyQt5.QtWidgets import QMainWindow, QGridLayout, QAction, QFileDialog, QApplication
from PyQt5.QtGui import QIcon, QStandardItem
from gui.customtreeview import CustomTreeView, AssetItem, FolderItem, SimpleItem
from gui.progressDialog import ProgressDialog, BusyProgressDialog, MessageBox
from gui.mapDialog import MapTab
from util.misc import openFile, getResPath, getUIPath
from util.assetmanager import AssetManager
from util.settings import SETTINGS
from parse.gameres import GameResDesc
from parse.realres import GeomNodeTree, DynModel, RendInst, CollisionGeom
from parse.material import DDSx
from parse.dbld import DagorBinaryLevelData
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
	GeomNodeTree,
	CollisionGeom,
	DynModel, # for maps
	RendInst # for maps
)

DBLD_FILTER = ["Dagor Binary Level Data (*.bin)"]


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
	itemsCreated = pyqtSignal()

	gridLayout:QGridLayout
	treeView:CustomTreeView

	actionOpenFolder:QAction
	actionOpenFiles:QAction
	actionUnmount:QAction
	actionClose:QAction
	actionSettings:QAction
	actionCollapse:QAction
	actionExpand:QAction
	# actionOpenMap:QAction

	mapTab:MapTab

	def __init__(self):
		super().__init__()
		
		loadUi(MAINWINDOWUI_PATH, self)

		self.gridLayout.setContentsMargins(-1, -1, -1, -1)
		
		self.treeView.initModel(self.lineEdit)

		self.clearItems:list[function] = []

		self.actionClose.triggered.connect(self.close)
		self.actionOpenFolder.triggered.connect(self.openFolder)
		self.actionOpenFiles.triggered.connect(self.openAssets)
		# self.actionOpenMap.triggered.connect(self.openMap)
		self.actionUnmount.triggered.connect(self.unmountAssets)
		self.actionSettings.triggered.connect(self.openSettings)
		self.actionExpand.triggered.connect(self.treeView.expandAll)
		self.actionCollapse.triggered.connect(self.treeView.collapseAll)
		self.itemsCreated.connect(self.treeView.expandAll)

		self.threadPool = QThreadPool()
		self.activeTerminable:Terminable = None
		self.activeSubProcess = None
		self.shouldTerminate = False
		self.treeView.mainWindow = self
		self.__taskStatus:str = ""

		self.cachedIcons:dict[str:QIcon] = {}

		self.mapTab.mainWindow = self
		
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
	
	def openLevelFile(self, enlisted:bool):
		dialog = openFile(title = "Open level file", nameFilters = DBLD_FILTER, fileMode = QFileDialog.ExistingFile)

		if dialog is None:
			return
		
		self.loadMap(dialog.selectedFiles()[0], enlisted)
		# self.loadMap("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\levels\\avg_normandy.bin", enlisted)
	
	def loadMap(self, path:str, enlisted:bool):
		map = DagorBinaryLevelData(path)
		cellData:list[tuple[int, tuple[int, int], int, int]] = []

		thread = MapLoadThread(self, map, cellData, enlisted)
		thread.setAutoDelete(True)
		thread.sig.finished.connect(partial(self.__mapLoadFinished, map, cellData))

		self.threadPool.start(thread)
	
	def exportMap(self, path:str):
		thread = MapExportThread(self, path)
		thread.setAutoDelete(True)

		self.threadPool.start(thread)
	
	def __mapLoadFinished(self, map:DagorBinaryLevelData, cellData:list):
		self.mapTab.mapLoadFinished(map, cellData)
	
	def mountAssets(self, paths:list[str]):
		self.threadPool.start(partial(self.__mountAssetsInternal__, paths))
	
	def __mountAssetsInternal__(self, paths:list[str]):
		self.setRequestedDialog(DIALOG_STATUS)
		
		self.setTaskTitle("Mounting assets")
		self.setTaskStatus("Loading files...")
	
		for p in paths:
			self.exploreFileInfo(QFileInfo(p), self.treeView.treeModel)

		if SETTINGS.getValue(SETTINGS_EXPAND_ALL):
			self.setTaskStatus("Expanding items...")
			self.itemsCreated.emit()
		
		self.setRequestedDialog(DIALOG_NONE)
	
	def setRequestedDialog(self, rType:int):
		self.requestedDialog.emit(rType)

	def setTaskTitle(self, title:str):
		self.taskTitle.emit(title)

	def setTaskProgress(self, progress:float):
		self.taskProgress.emit(progress)

	def setTaskStatus(self, status:str):
		self.__taskStatus = status

		self.taskStatus.emit(status)
	
	
	def getTaskStatus(self):
		return self.__taskStatus
	
	def setTerminable(self, ter:Terminable):
		self.activeTerminable = ter
	
	def clearTerminable(self):
		self.activeTerminable = None
	
	def setSubProcess(self, proc):
		self.activeSubProcess = proc
	
	def clearSubProcess(self):
		self.activeSubProcess = None

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
		
		if self.activeSubProcess is not None:
			self.activeSubProcess.kill()
		
		self.threadPool.waitForDone()
		self.clearTerminable()

		self.shouldTerminate = False
		
		log.subLevel(log.curLevel)
		
		self.setRequestedDialog(DIALOG_NONE)




class MapLoadThread(QRunnable):
	class Signals(QObject):
		finished = pyqtSignal()

		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
		
	
	def __init__(self, mainWindow:MainWindow, map:DagorBinaryLevelData, cellData:list, enlisted:bool):
		super().__init__()

		self.sig = MapLoadThread.Signals()
		
		self.map = map
		self.cellData = cellData
		self.mainWindow = mainWindow
		self.enlisted = enlisted
	
	def run(self):
		mainWindow = self.mainWindow
		map = self.map
		cellData = self.cellData
		
		
		mainWindow.setRequestedDialog(DIALOG_STATUS)
		
		mainWindow.setTaskTitle("Loading map...")
		mainWindow.setTaskStatus("Loading map data...")

		try:
			mainWindow.setTerminable(map)

			map.computeData()

			mainWindow.setTaskStatus("Loading cell entities...")

			riGen = map.riGenLayers[0]

			for ofs in riGen.riDataRel:
				cell = riGen.riDataRel[ofs]

				entities = {}
				_, nonVegCnt, vegCnt = riGen.getCellEntities(cell.id, entities, self.enlisted, False, True)
				cellData.append((cell.id,
								riGen.getCellXY(cell), 
								nonVegCnt,
								vegCnt,
								len(entities)))
			
			self.sig.finished.emit()
		except Exception as e:
			print(format_exc())

			log.subLevel(log.curLevel)

			mainWindow.setRequestedDialog(DIALOG_ERROR)

		mainWindow.clearTerminable()

		mainWindow.setRequestedDialog(DIALOG_NONE)

class MapExportThread(QRunnable):
	class Signals(QObject):
		finished = pyqtSignal()

		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
		
	
	def __init__(self, mainWindow:MainWindow, path:str):
		super().__init__()

		self.sig = MapLoadThread.Signals()
		
		self.path = path
		self.mainWindow = mainWindow
	
	def run(self):
		mainWindow = self.mainWindow
		output = self.path
		mapTab = mainWindow.mapTab
		
		mainWindow.setRequestedDialog(DIALOG_STATUS)
		
		mainWindow.setTaskTitle("Loading map...")
		mainWindow.setTaskStatus("Loading map data...")

		try:
			mainWindow.setTaskStatus("Loading cell entities")
			mainWindow.setTaskProgress(0/3)
			mainWindow.setTerminable(mapTab.map.riGenLayers[0])
			entities = mapTab.getEntities()
			mainWindow.clearTerminable()
			mainWindow.setTaskProgress(1/3)
			mainWindow.setTaskStatus("Writing DPL")
			mapTab.writeToFile(output, entities)
			mainWindow.setTaskProgress(2/3)
			
			if mapTab.exportAssets.isChecked():
				mainWindow.setTaskStatus("Exporting assets")
				mapTab.exportAssetsFunc(output, entities)
			
			mainWindow.setTaskProgress(1.0)
			
			self.sig.finished.emit()
		except Exception as e:
			print(format_exc())

			log.subLevel(log.curLevel)

			mainWindow.setRequestedDialog(DIALOG_ERROR)

		mainWindow.clearTerminable()

		mainWindow.setRequestedDialog(DIALOG_NONE)


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
			elif dialogType == DIALOG_ERROR:
				box = MessageBox("An error occured during the process. Check the console for details.")
				box.exec_()

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