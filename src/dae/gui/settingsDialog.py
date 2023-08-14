
import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from PyQt5.QtWidgets import QDialog, QWidget, QGridLayout, QCheckBox, QLineEdit, QPushButton, QFileDialog, QVBoxLayout
from PyQt5.uic import loadUi
from util.misc import getUIPath, openFile
from util.enums import *
from util.settings import SETTINGS


SETTINGSUI_PATH = getUIPath("settings.ui")

class SettingsDialog(QDialog):
	vLayout:QVBoxLayout

	exportFolder:QCheckBox
	exportPreviewTex:QCheckBox
	extractFolder:QCheckBox
	noTexExport:QCheckBox
	outputFolder:QCheckBox
	exportSourceCollision:QCheckBox
	exportGameInfo:QCheckBox
	exportSMD:QCheckBox
	noMDL:QCheckBox
	dontExportExistingTextures:QCheckBox
	convertTex:QCheckBox

	studiomdlLine:QLineEdit
	studioMdlBtn:QPushButton
	gameInfoLine:QLineEdit
	gameInfoBtn:QPushButton

	exportGameInfoLayout:QVBoxLayout
	exportSMDLayout:QVBoxLayout

	
	def __init__(self, parent:QWidget):
		super().__init__(parent)

		loadUi(SETTINGSUI_PATH, self)

		self.vLayout.setContentsMargins(-1, -1, -1, -1)

		self.setupCheckBox(self.exportFolder, SETTINGS_EXPORT_FOLDER)
		self.setupCheckBox(self.convertTex, SETTINGS_FORCE_DDS_CONVERSION)
		self.setupCheckBox(self.exportPreviewTex, SETTINGS_EXPORT_PREVIEW_TEX)
		self.setupCheckBox(self.extractFolder, SETTINGS_EXTRACT_FOLDER)
		self.setupCheckBox(self.noTexExport, SETTINGS_NO_TEX_EXPORT)
		self.setupCheckBox(self.outputFolder, SETTINGS_OUTPUT_FOLDER)
		self.setupCheckBox(self.exportSourceCollision, SETTINGS_STUDIOMDL_EXPORT_COLLISION)
		self.setupCheckBox(self.exportGameInfo, SETTINGS_EXPORT_GAMEINFO, self.exportGameInfoLayout)
		self.setupCheckBox(self.exportSMD, SETTINGS_EXPORT_SMD, self.exportSMDLayout)
		self.setupCheckBox(self.noMDL, SETTINGS_NO_MDL)
		self.setupCheckBox(self.dontExportExistingTextures, SETTINGS_DONT_EXPORT_EXISTING_TEXTURES)


		self.studiomdlLine.setText(SETTINGS.getValue(SETTINGS_STUDIOMDL_PATH))
		self.studioMdlBtn.clicked.connect(lambda: self.selectFile("Select StudioMDL binary", ["studiomdl.exe"], SETTINGS_STUDIOMDL_PATH, self.studiomdlLine))

		self.gameInfoLine.setText(SETTINGS.getValue(SETTINGS_GAMEINFO_PATH))
		self.gameInfoBtn.clicked.connect(lambda: self.selectFile("Select gameinfo.txt", ["gameinfo.txt"], SETTINGS_GAMEINFO_PATH, self.gameInfoLine))
	
	def selectFile(self, title:str, nameFilters:list[str], settingKey:str, lineEdit:QLineEdit):
		dialog = openFile(self, title = title, nameFilters = nameFilters, fileMode = QFileDialog.ExistingFile)

		if dialog is None:
			return
		
		path = dialog.selectedFiles()[0]

		lineEdit.setText(path)
		SETTINGS.setValue(settingKey, path)
		SETTINGS.saveSettings()

	def setupCheckBox(self, cBox:QCheckBox, setting:str, layout:QVBoxLayout = None):
		val = SETTINGS.getValue(setting)
		cBox.setChecked(val)
		cBox.stateChanged.connect(lambda: self.toggleSetting(setting, layout))

		if layout is not None:
			self.handleLayout(layout, not val)

	def handleLayout(self, layout:QVBoxLayout, enable:bool):
		for i in range(layout.count()):
			child = layout.itemAt(i).widget()

			if not isinstance(child, QCheckBox):
				continue

			child.setDisabled(enable)

	def toggleSetting(self, setting:str, layout:QVBoxLayout = None):
		newVal = not SETTINGS.getValue(setting)

		SETTINGS.setValue(setting, newVal)

		if layout is not None:
			self.handleLayout(layout, not newVal)