
from functools import partial
from io import StringIO
import sys
from os import path, remove, mkdir
from traceback import format_exc

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import util.log as log
from PyQt5.QtWidgets import QDialog, QWidget, QPushButton, QLineEdit, QCheckBox, QGridLayout, QSizePolicy, QLabel, QFileDialog
from PyQt5.QtGui import QDropEvent
from PyQt5.QtCore import pyqtSignal, QMimeData
from PyQt5.uic import loadUi
from util.misc import getUIPath, ROOT_FOLDER, openFile
from util.fileread import BBytesIO
from parse.dbld import DagorBinaryLevelData
from parse.realres import RendInst, DynModel
from util.enums import *
from util.settings import SETTINGS
from util.assetcacher import AssetCacher
from struct import pack


MAPUI_PATH = getUIPath("mapDialog.ui")

class CellButton(QPushButton):
	selectedCount = 0
	postClick = pyqtSignal()

	def __init__(self, name:str, checkable:bool):
		super().__init__(name)

		self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

		self.__checked = False

		if checkable:
			self.setCheckable(True)

			self.clicked.connect(self.onClick)
		else:
			self.setEnabled(False)
		
	@property
	def checked(self):
		return self.__checked
	
	def onClick(self):
		if self.__checked:
			self.setChecked(False)
			CellButton.selectedCount -= 1
			self.__checked = False
		else:
			self.__checked = True
			self.setChecked(True)
			CellButton.selectedCount += 1
		
		self.postClick.emit()

def getCellDataByXY(cellData:list, xy:tuple[int, int]):
	for v in cellData:
		if v[1] == xy:
			return v
	
	return None
			

def getCellsMinMax(cellData:list):
	minX, minY = None, None
	maxX, maxY = 0, 0
	
	for v in cellData:
		x, y = v[1]

		if minX is None or x < minX:
			minX = x

		if minY is None or y < minY:
			minY = y
		
		if x > maxX:
			maxX = x
		
		if y > maxY:
			maxY = y

	return (minX, minY), (maxX, maxY)

def makeOutputFolder(output:str, shouldMakeFolder:bool, folderName:str):
	if not shouldMakeFolder:
		return output
	
	output = path.join(output, folderName)

	if not path.exists(output):
		mkdir(output)
	
	return output

def getOutputDir():
	if SETTINGS.getValue(SETTINGS_OUTPUT_FOLDER):
		output = ROOT_FOLDER

		output = makeOutputFolder(output, True, "output")
	else:
		dialog = openFile(title = "Save to", fileMode = QFileDialog.DirectoryOnly)

		if dialog == None:
			return None
		
		output = dialog.selectedFiles()[0]
	
	return output

class MapExportDialog(QDialog):
	browse:QPushButton
	lineEdit:QLineEdit
	exportButton:QPushButton

	enlistedMap:QCheckBox
	exportVegetation:QCheckBox
	exportNonVegetation:QCheckBox
	exportAssets:QCheckBox
	infoLabel:QLabel

	gridLayout:QGridLayout
	
	def __init__(self, parent:QWidget):
		super().__init__(parent)
		
		loadUi(MAPUI_PATH, self)
		
		self.browse.setAcceptDrops(True)
		self.browse.clicked.connect(self.openMap)
		self.browse.dropEvent = self.buttonDropEvent
		self.browse.dragEnterEvent = self.buttonDragEvent
		self.browse.dragMoveEvent = self.buttonDragEvent
		# self.browse.setDragEnabled(True)
		# self.browse.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)

		self.map:DagorBinaryLevelData = None
		self.cellData:list = None

		self.exportButton.clicked.connect(self.export)
		self.cellsToExport = set()

		self.mainWindow = parent
	
	def buttonDropEvent(self, event:QDropEvent):
		path:str = self.getEventPath(event.mimeData())

		if path is not None:
			self.mainWindow.loadMap(path, self.enlistedMap.isChecked())
	
	def buttonDragEvent(self, event):
		if self.getEventPath(event.mimeData()) == False:
			event.ignore()
		else:
			event.accept()

	def getEventPath(self, data:QMimeData):
		if data.hasText():
			text = data.text()

			paths = text.split("\n")

			if len(paths) == 1:
				fpath = paths[0]

				if fpath[:8] == "file:///":
					fpath = fpath[8:]

				if path.exists(fpath):
					return fpath
		
		return None
		
	# def dragEnterEvent(self, event:QDragEnterEvent):
	# 	if self.getEventPath(event.mimeData()) is None:
	# 		event.ignore()
	# 	else:
	# 		event.accept()
	
	def openMap(self):
		if self.mainWindow is not None:
			self.mainWindow.openLevelFile(self.enlistedMap.isChecked())
	
	def clearGrid(self):
		for i in reversed(range(self.gridLayout.count())):
			self.gridLayout.itemAt(i).widget().setParent(None)

	def toggleExportButton(self, cellIdx:int = None):
		if self.map is None or CellButton.selectedCount == 0:
			self.exportButton.setEnabled(False)

			if cellIdx is not None:
				self.cellsToExport.remove(cellIdx)
		else:
			self.exportButton.setEnabled(True)

			if cellIdx is not None:
				self.cellsToExport.add(cellIdx)
		
	def mapLoadFinished(self, map:DagorBinaryLevelData, cellData:list):
		self.map = map
		self.cellData = cellData

		self.clearGrid()

		self.lineEdit.setText(map.filePath)

		minXY, maxXY = getCellsMinMax(cellData)

		totalVegCnt = 0
		totalNonVegCnt = 0
		totalEntCnt = 0

		for x in range(minXY[0], maxXY[0] + 1):
			for y in range(minXY[1], maxXY[1] + 1):
				data = getCellDataByXY(cellData, (x, y))

				checkable = data is not None
				cellIdx = None

				if checkable:
					cellIdx = data[0]
					text = f"\n{data[4]} unique models\n{data[2]} props\n{data[3]} vegetation"

					totalNonVegCnt += data[2]
					totalVegCnt += data[3]
					totalEntCnt += data[2] + data[3]
				else:
					text = ""

				btn = CellButton(f"{x} ; {y}{text}", checkable)

				btn.postClick.connect(partial(self.toggleExportButton, cellIdx))
				
				self.gridLayout.addWidget(btn, y - minXY[1], x - minXY[0])

		layer = map.riGenLayers[0]

		cellSz = layer.grid2world * layer.cellSz
		
		cellLength = int(abs(cellSz / layer.calculatedScale[0]))
		cellWidth = int(abs(cellSz  / layer.calculatedScale[2]))
		
		self.infoLabel.setText(" | ".join((
			f"Total cell count: {layer.cellCnt}",
			f"Exportable cells count: {len(layer.riDataRel)}",
			f"Cell size: {cellLength}x{cellWidth}",
			f"Total prop count: {totalNonVegCnt}",
			f"Total vegetation count: {totalVegCnt}"
			# f"Total entity count: {totalVegCnt}",
		)))

	def __getEntities(self):
		entities = {}

		riGen = self.map.riGenLayers[0]

		enlisted = self.enlistedMap.isChecked()
		veg = self.exportVegetation.isChecked()
		vegOnly = not self.exportNonVegetation.isChecked()

		for cellIdx in self.cellsToExport:
			riGen.getCellEntities(cellIdx, entities, enlisted, veg, vegOnly)

		return entities

	def __exportAssets(self, output:str, entities:dict[str, list]):
		outpath = makeOutputFolder(output, True, self.map.name + "_props")

		log.log(f"Exporting {len(entities)} assets to {outpath}")
		log.addLevel()

		for ent in entities:
			asset = AssetCacher.getCachedAsset(RendInst, ent)

			if not asset:
				asset = AssetCacher.getCachedAsset(DynModel, ent)

				if not asset:
					log.log(f"Skipping not loaded model {ent}", LOG_WARN)

				continue
			
			asset:RendInst = asset[0]

			level = log.curLevel
			
			try:
				log.log(f"Exporting {ent}")
				log.addLevel()
				asset.exportDmf(0, outpath, not SETTINGS.getValue(SETTINGS_NO_TEX_EXPORT))
				log.subLevel()
			except:
				print(format_exc())

				log.subLevel(log.curLevel - level)

		log.subLevel()

	def __writeToFile(self, output:str, entities:dict[str, list]):
		filepath = path.join(output, self.map.name + ".dpl")

		log.log(f"Writing {len(entities)} entities into {self.map.name + '.dpl'}")

		buffer = BBytesIO()
		buffer.writeInt(len(entities))

		for k in entities:
			v = entities[k]

			buffer.writeString(k)
			buffer.writeInt(len(v))

			for pos_matrix in v:
				pos = pos_matrix[0]
				matrix = pos_matrix[1]

				buffer.write(pack("fff", *pos))

				buffer.write(pack("ffff", *matrix[0]))
				buffer.write(pack("ffff", *matrix[2])) # works but wtf?
				buffer.write(pack("ffff", *matrix[1]))
				buffer.write(pack("ffff", *matrix[3]))
		
		value = buffer.getvalue()

		buffer.close()

		file = open(filepath, "wb")
		file.write(value)
		file.close()

	def export(self):
		if self.map is None or len(self.cellsToExport) == 0:
			return
		
		output = getOutputDir()

		if output is None:
			return

		entities = self.__getEntities()
		self.__writeToFile(output, entities)
		
		if self.exportAssets.isChecked():
			self.__exportAssets(output, entities)
		


if __name__ == "__main__":
	from PyQt5.QtWidgets import QApplication

	app = QApplication([])

	widget = MapExportDialog(None)
	widget.show()
	app.exec_()