import sys
from os import path, system, mkdir, makedirs, replace, listdir, rmdir

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import shutil
import util.log as log
from PyQt5.QtWidgets import QAbstractItemView, QTreeView, QLineEdit, QHeaderView, QMenu, QAction, QStyledItemDelegate, QFileDialog, QMainWindow
from PyQt5.QtCore import QMimeData, Qt, QSortFilterProxyModel, QPoint, QFileInfo
from PyQt5.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QStandardItemModel, QStandardItem, QIcon, QPaintEvent, QPainter
from util.misc import formatBytes, getResPath, openFile, ROOT_FOLDER, LIB_FOLDER
from util.terminable import Exportable, Packed, Pack, Terminable
from util.enums import *
from pyperclip import copy as copyToClipboard
from functools import partial
from parse.material import DDSx, DDSxTexturePack2
from parse.realres import RendInst, ModelContainer, GeomNodeTree
from parse.gameres import GameResourcePack
from traceback import format_exc
from gui.progressDialog import MessageBox
from util.settings import SETTINGS
from subprocess import Popen
from glob import glob


FOLDER_ICO_PATH = getResPath("folder.bmp")
VTFCMD_PATH = path.join(LIB_FOLDER, "VTFcmd.exe")

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
		
		if isinstance(self, AssetItem):
			asset = self.asset

			menu.addAction(CopyNameToClipboard(menu, self))
		
			menu.addSeparator()

			if isinstance(asset, Packed) and self.hasParent():
				menu.addAction(Extract(menu, self))

			if isinstance(asset, DDSx):
				menu.addAction(ExportToDDS(menu, self))
			elif isinstance(asset, ModelContainer):
				level = log.curLevel

				try:
					# menu.addAction(PreviewModel(menu, self, 0))

					if isinstance(asset, GeomNodeTree):
						menu.addAction(ExportSkeletonToDMF(menu, self, 0))
					else:
						menu.addAction(ExportToDMF(menu, self, 0))
					
					if isinstance(asset, RendInst):
						menu.addAction(ExportToSource(menu, self, 0))
						menu.addAction(ExportToOBJ(menu, self, 0))

						asset.computeData()

						if asset.lodCount > 1:
							submenu = menu.addMenu("Export LOD...")

							for i in range(asset.lodCount):
								submenu.addAction(ExportToDMF(menu, self, i))

							submenu.addSeparator()
							
							for i in range(asset.lodCount):
								submenu.addAction(ExportToOBJ(menu, self, i))

							submenu.addSeparator()

							submenu.addAction(ExportLODsToDMF(menu, self))
							submenu.addAction(ExportLODsToOBJ(menu, self))
							submenu.addAction(ExportLODsToSource(menu, self))
				except Exception as e:
					print(format_exc())

					log.subLevel(log.curLevel - level)

					MessageBox("Failed to compute preliminary data. Check the console for details.").exec_()
			elif isinstance(asset, Pack):
				menu.addAction(ExtractAll(menu, self))

				if isinstance(asset, DDSxTexturePack2):
					menu.addAction(ExportAllToDDS(menu, self))
				elif isinstance(asset, GameResourcePack):
					menu.addAction(ExportAllToDMF(menu, self))
					menu.addAction(ExportAllToOBJ(menu, self))
					# menu.addAction(ExportAllLODsToOBJ(menu, self))
	
	def autoExpand(self):
		if SETTINGS.getValue(SETTINGS_EXPAND_ALL):
			self.expand()

	def expand(self):
		treeView:CustomTreeView = self.mainWindow.treeView
		treeView.expand(self.mainItem.index())

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
	

	def expand(self):
		treeView:CustomTreeView = self.mainWindow.treeView
		treeView.expandRecursively(self.mainItem.index())

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

		self.__item = item

		self.setText(self.actionText)

		self.triggered.connect(self.run)
	
	@property
	def item(self):
		return self.__item

	def run(self):
		raise NotImplementedError()
	
	@property
	def mainWindow(self):
		return self.item.mainWindow

	@property
	def actionText(self) -> str:
		raise NotImplementedError()

class ThreadedAction(CustomAction):
	def __init__(self, parent, item:SimpleItem):
		super().__init__(parent, item)
		
		self.triggered.disconnect()

		self.triggered.connect(self.__run__)

		self.__error = False
		self.__cancel = False
	
	@property
	def taskTitle(self) -> str:
		raise NotImplementedError()
	
	@classmethod
	@property
	def dialogType(self) -> int:
		raise NotImplementedError()

	def setTerminable(self, ter:Terminable):
		self.item.mainWindow.setTerminable(ter)
	
	def setSubProcess(self, proc):
		self.item.mainWindow.setSubProcess(proc)
	
	def clearTerminable(self):
		self.item.mainWindow.clearTerminable()
	
	def clearSubProcess(self):
		self.item.mainWindow.clearSubProcess()
	
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
	
	@property
	def taskStatus(self) -> str:
		return self.mainWindow.getTaskStatus()

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
			self.mainWindow.setRequestedDialog(DIALOG_ERROR)
		
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

class CopyNameToClipboard(CustomAction):
	item:AssetItem

	def run(self):
		copyToClipboard(self.item.asset.name)
	
	@property
	def actionText(self) -> str:
		return "Copy name to clipboard"



class SaveAction(ThreadedAction):
	item:AssetItem

	def preRun(self):
		if SETTINGS.getValue(SETTINGS_OUTPUT_FOLDER):
			self.output = ROOT_FOLDER

			self.makeOutputFolder(True, "output")
		else:
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
	
	def save(self, output:str):
		raise NotImplementedError()
	
	def makeOutputFolder(self, shouldMakeFolder:bool, folderName:str):
		if not shouldMakeFolder:
			return self.output
		
		self.output = path.join(self.output, folderName)

		if not path.exists(self.output):
			mkdir(self.output)
		
		return self.output

class AssetSaveAction(SaveAction):
	def saveSingle(self, output:str, asset):
		if self.handleTermination(asset):
			return True
		
		level = log.curLevel

		log.log(self.taskStatus)
		log.addLevel()

		try:
			self.saveAsset(output, asset)

			log.subLevel()
		except Exception as e:
			print(format_exc())

			self.setErrored()

			log.subLevel(log.curLevel - level)

		return False
	
	def saveAsset(self, output:str, asset):
		raise NotImplementedError()
	
	def save(self, output:str):
		asset:Packed = self.item.asset
		
		self.saveSingle(output, asset)

		self.setTaskProgress(1)

class PackedSave(AssetSaveAction):
	def save(self, output:str):
		asset:Pack = self.item.asset

		output = self.makePackedOutputFolder(asset.name)
		
		self.setTerminable(asset)

		packedFiles = asset.getPackedFiles()

		if self.hasFilter:
			fileCnt = 0

			for v in packedFiles:
				if self.filter(v):
					fileCnt += 1
		else:
			fileCnt = len(packedFiles)

		k = 0

		for v in packedFiles:
			if self.hasFilter and not self.filter(v):
				continue

			self.setTaskStatus(f"{self.getProgressText(v)} ({k + 1}/{fileCnt})")

			if self.saveSingle(output, v):
				break
				
			self.setTaskProgress((k + 1) / fileCnt)

			k += 1
		
		self.clearTerminable()
	
	@classmethod
	@property
	def hasFilter(cls):
		return False

	def filter(self, asset):
		return True
	
	def getProgressText(self, asset:Packed) -> str:
		raise NotImplementedError()
	
	def makePackedOutputFolder(self, name:str):
		return self.makeOutputFolder(SETTINGS.getValue(SETTINGS_EXPORT_FOLDER), name)


class Extract(AssetSaveAction):
	@property
	def actionText(self) -> str:
		return "Extract"
	
	@property
	def taskTitle(self) -> str:
		return f"Extracting {self.item.asset.name}.{self.item.asset.fileExtension}"

	def saveAsset(self, output:str, asset:Packed):
		asset.save(output)

class ExtractAll(Extract, PackedSave):
	@property
	def actionText(self) -> str:
		return "Extract all"
	
	@property
	def taskTitle(self) -> str:
		return f"Extracting files from {self.item.asset.name}.{self.item.asset.fileExtension}"
	
	def makePackedOutputFolder(self, name:str):
		return self.makeOutputFolder(SETTINGS.getValue(SETTINGS_EXTRACT_FOLDER), name)

	def getProgressText(self, asset:Packed):
		return f"Extracting {asset.name}.{asset.fileExtension}"


class ExportToDDS(Extract):
	@property
	def actionText(self) -> str:
		return "Export to DDS"
	
	@property
	def taskTitle(self) -> str:
		return f"Exporting to {self.item.asset.name}.dds"

	def saveAsset(self, output:str, asset:DDSx):
		asset.exportDDS(output)

class ExportAllToDDS(ExportToDDS, PackedSave):
	@property
	def actionText(self) -> str:
		return "Export all to DDS"
	
	@property
	def taskTitle(self) -> str:
		return f"Exporting files from {self.item.asset.name}.{self.item.asset.fileExtension} to DDS"

	def getProgressText(self, asset:Packed):
		return f"Extracting {asset.name}.dds"
	

class PreviewModel(CustomAction):
	def __init__(self, parent, item: SimpleItem, lod:int):
		self.lod = lod

		super().__init__(parent, item)
	
	item:AssetItem

	@property
	def actionText(self) -> str:
		return f"Preview LOD {self.lod}"
	
	@property
	def taskTitle(self) -> str:
		return f"Previewing {self.item.asset.getExportName(self.lod)}.obj"

	# def save(self):
	# 	asset:RendInst = self.item.asset
	# 	self.setTerminable(asset)
		
	# 	obj = asset.getObj(self.lod)

	# 	self.setTaskProgress(1)
	# 	self.clearTerminable()

	def run(self):
		asset:RendInst = self.item.asset

		# PreviewDialog(self.mainWindow, asset.getObj(self.lod)).show()



class ExportToSource(SaveAction):
	def __init__(self, parent, item: SimpleItem, lod:int):
		self.lod = lod

		super().__init__(parent, item)
	
	@property
	def actionText(self) -> str:
		return f"Export LOD {self.lod} to Source engine"
	
	@property
	def taskTitle(self) -> str:
		return f"Exporting LOD {self.lod} to {self.item.asset.name}.mdl"

	def save(self, output:str):
		modelPath = "dae_out"
		asset:RendInst = self.item.asset
		exportTex = not SETTINGS.getValue(SETTINGS_NO_TEX_EXPORT)
		exportToGame = SETTINGS.getValue(SETTINGS_EXPORT_GAMEINFO)
		exportCollisionModel = SETTINGS.getValue(SETTINGS_STUDIOMDL_EXPORT_COLLISION)
		exportSMDs = SETTINGS.getValue(SETTINGS_EXPORT_SMD)
		dontCompile = SETTINGS.getValue(SETTINGS_NO_MDL)
		dontReplaceTex = SETTINGS.getValue(SETTINGS_DONT_EXPORT_EXISTING_TEXTURES)
		forceConvert = SETTINGS.getValue(SETTINGS_FORCE_DDS_CONVERSION)

		if exportTex:
			stepCnt = 5
		else:
			stepCnt = 3
		
		self.setTaskStatus("Generating model data")

		if self.handleTermination(asset):
			return
		
		smdl = asset.getSourceModel(self.lod, exportLODs = self.exportLODs)
		self.setTaskProgress(1/stepCnt)
		
		if self.handleTermination(smdl):
			return
		
		self.setTaskStatus("Exporting model data to QC, SMD and VMT")
		qc, texturePaths = smdl.export(output, modelPath, exportCollisionModel, exportSMDs)
		self.setTaskProgress(2/stepCnt)
		self.clearTerminable()
	
		if self.shouldTerminate:
			return
		
		gamePath = path.dirname(SETTINGS.getValue(SETTINGS_GAMEINFO_PATH))

		output = path.join(output, smdl.name)
		sourceExport = path.join(output, "source_export")

		makedirs(sourceExport, exist_ok = True)

		if exportSMDs and not dontCompile:
			if self.shouldTerminate:
				return
			
			self.setTaskStatus("Compiling")

			pipes = Popen([
				SETTINGS.getValue(SETTINGS_STUDIOMDL_PATH), 
				"-nop4", 
				"-verbose", 
				"-game", 
				path.dirname(SETTINGS.getValue(SETTINGS_GAMEINFO_PATH)), 
				qc])
			
			self.setSubProcess(pipes)

			if pipes.wait() != 0:
				raise Exception(f"Compile failed: return code {pipes.returncode}")
			
			self.clearSubProcess()

			if not exportToGame:
				if self.shouldTerminate:
					return
				
				modelOutPath = path.join(sourceExport, f"models/{modelPath}")

				makedirs(modelOutPath, exist_ok = True)
				
				files = glob(path.join(gamePath, f"models/{modelPath}/{asset.name}.*"))

				for f in files:
					if self.shouldTerminate:
						return
					
					log.log(f"Moving {f} to {modelOutPath}")
					replace(f, path.join(modelOutPath, path.basename(f)))
			
		self.setTaskProgress(3/stepCnt)

		if exportTex and texturePaths is not None:
			self.setTaskStatus("Exporting textures")
			log.addLevel()
			mdl = smdl.model

			if self.handleTermination(mdl):
				return
			
			mdl.exportTextures(output, texturePaths = texturePaths, forceConvert = forceConvert)
			self.clearTerminable()
			log.subLevel()

			if self.shouldTerminate:
				return

			self.setTaskProgress(4/stepCnt)
			self.setTaskStatus("Converting textures to VTF")
			log.addLevel()

			materialsPath = path.join(sourceExport, "materials")

			texDict = texturePaths.getDict()

			for k, texName in enumerate(texDict.keys()):
				if self.shouldTerminate:
					return
				
				texFile = path.join(output, f"textures/{texName}.dds")

				if not path.exists(texFile):
					log.log(f"Skipping missing texture {texName}")

					continue
				
				tex = texturePaths.get(texName)

				texOutPath = path.normpath(path.join(materialsPath, tex.texPath))

				if dontReplaceTex and path.exists(path.join(texOutPath, f"{texName}.vtf")):
					log.log(f"Skipping already exported texture {texName}")

					continue

				makedirs(texOutPath, exist_ok = True)

				pipes = Popen((
					VTFCMD_PATH,
					"-file",
					path.normpath(texFile),
					"-output",
					texOutPath
				))

				self.setSubProcess(pipes)

				pipes.wait()

				self.clearSubProcess()

				self.setTaskProgress((4 + (k + 1) / len(texDict))/stepCnt)

			if exportToGame and path.exists(materialsPath):
				log.log("Moving materials directory...")

				shutil.copytree(materialsPath, path.join(gamePath, "materials"), dirs_exist_ok = True)
				shutil.rmtree(materialsPath)
			

			if len(listdir(sourceExport)) == 0:
				rmdir(sourceExport)

			log.subLevel()
			self.setTaskProgress(5/stepCnt)

	@classmethod
	@property
	def exportLODs(cls):
		return False

class ExportLODsToSource(ExportToSource):
	def __init__(self, parent, item:SimpleItem):
		super().__init__(parent, item, 0)
	
	item:AssetItem

	@property
	def actionText(self) -> str:
		return "Export all LODs to Source engine"
	
	@property
	def taskTitle(self) -> str:
		return f"Exporting all LODs from {self.item.asset.name} to Source engine"

	@classmethod
	@property
	def exportLODs(cls):
		return True

class ExportModel(AssetSaveAction):
	def __init__(self, parent, item:SimpleItem, lod:int = 0):
		self.lod = lod
		
		super().__init__(parent, item)

	def saveAsset(self, output:str, asset:RendInst):
		exportTex = not SETTINGS.getValue(SETTINGS_NO_TEX_EXPORT)
		forceConvert = SETTINGS.getValue(SETTINGS_FORCE_DDS_CONVERSION)

		mdl = asset.getModel(self.lod)

		if self.handleTermination(mdl):
			return
		
		getattr(mdl, self.exportMethodName)(output, exportTex, forceConvert)
	
	@property
	def actionText(self) -> str:
		return f"Export LOD {self.lod} to {self.exportFormat.upper()}"
	
	@property
	def taskTitle(self) -> str:
		return f"Exporting LOD to {self.item.asset.getExportName(self.lod)}.{self.exportFormat}"
		
	@classmethod
	@property
	def exportMethodName(cls) -> str:
		raise NotImplementedError()
	
	@classmethod
	@property
	def exportFormat(cls) -> str:
		raise NotImplementedError()

class ExportLODs(PackedSave, ExportModel):
	@property
	def actionText(self) -> str:
		return f"Export all LODs to {self.exportFormat.upper()}"
	
	@property
	def taskTitle(self) -> str:
		return f"Exporting all LODs from {self.item.asset.name} to {self.exportFormat.upper()}"
	
	def save(self, output:str):
		asset:RendInst = self.item.asset

		output = self.makePackedOutputFolder(asset.name)

		self.setTerminable(asset)
		asset.computeData()

		for i in range(asset.lodCount):
			self.setTaskStatus(f"{self.getProgressText(asset)} LOD {i}/{asset.lodCount - 1}")

			self.lod = i

			if self.saveSingle(output, asset):
				break

			self.setTaskProgress((i + 1) / asset.lodCount)

		self.clearTerminable()

	def getProgressText(self, asset:Packed):
		return f"Exporting {asset.name}"

class ExportAllModels(PackedSave, ExportModel):
	@classmethod
	@property
	def hasFilter(cls):
		return True

	def filter(self, asset):
		return isinstance(asset, RendInst)

	def getProgressText(self, asset:RendInst):
		return f"Exporting {asset.getExportName(0)}.{self.exportFormat}"

	@property
	def actionText(self) -> str:
		return f"Export all models to LOD 0 {self.exportFormat.upper()}"
	
	@property
	def taskTitle(self) -> str:
		return f"Exporting LOD 0 models from {self.item.asset.name}.{self.item.asset.fileExtension} to {self.exportFormat.upper()}"


class ExportToDMF(ExportModel):
	@classmethod
	@property
	def exportMethodName(cls) -> str:
		return "exportDmf"

	@classmethod
	@property
	def exportFormat(cls) -> str:
		return "dmf"
	

class ExportSkeletonToDMF(ExportToDMF):
	@property
	def actionText(self):
		return f"Export skeleton to {self.item.asset.name}.dmf"
	
	@property
	def taskTitle(self) -> str:
		return f"Exporting skeleton to {self.item.asset.name}.{self.exportFormat}"

class ExportLODsToDMF(ExportToDMF, ExportLODs):
	def __init__(self, *args, **kwargs):
		super(ExportLODs, self).__init__(*args, **kwargs)

class ExportAllToDMF(ExportToDMF, ExportAllModels):
	def __init__(self, *args, **kwargs):
		super(ExportAllModels, self).__init__(*args, **kwargs)

class ExportToOBJ(ExportModel):
	@classmethod
	@property
	def exportMethodName(cls) -> str:
		return "exportObj"

	@classmethod
	@property
	def exportFormat(cls) -> str:
		return "obj"

class ExportLODsToOBJ(ExportToOBJ, ExportLODs):
	def __init__(self, *args, **kwargs):
		super(ExportLODs, self).__init__(*args, **kwargs)

class ExportAllToOBJ(ExportToOBJ, ExportAllModels):
	def __init__(self, *args, **kwargs):
		super(ExportAllModels, self).__init__(*args, **kwargs)



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
	
	def paintEvent(self, event:QPaintEvent):
		if self.model() and self.model().rowCount() > 0:
			super().paintEvent(event)
		else:
			painter = QPainter(self.viewport())
			text = "Drag and drop files here or open assets through the \"File\" menu"
			textRect = painter.fontMetrics().boundingRect(text)
			textRect.moveCenter(self.viewport().rect().center())
			painter.drawText(textRect, Qt.AlignCenter, text)
	
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
			for i in range(1, len(paths)):
				path = paths[i]

				if path.startswith("file:///"):
					paths[i] = path[8:]
			
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
