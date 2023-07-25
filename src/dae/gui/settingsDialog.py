
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

	studiomdlLine:QLineEdit
	studioMdlBtn:QPushButton
	gameInfoLine:QLineEdit
	gameInfoBtn:QPushButton

	
	def __init__(self, parent:QWidget):
		super().__init__(parent)

		loadUi(SETTINGSUI_PATH, self)

		self.vLayout.setContentsMargins(-1, -1, -1, -1)

		self.setupCheckBox(self.exportFolder, SETTINGS_EXPORT_FOLDER)
		self.setupCheckBox(self.exportPreviewTex, SETTINGS_EXPORT_PREVIEW_TEX)
		self.setupCheckBox(self.extractFolder, SETTINGS_EXTRACT_FOLDER)
		self.setupCheckBox(self.noTexExport, SETTINGS_NO_TEX_EXPORT)
		self.setupCheckBox(self.outputFolder, SETTINGS_OUTPUT_FOLDER)

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

	def setupCheckBox(self, cBox:QCheckBox, setting:str):
		cBox.setChecked(SETTINGS.getValue(setting))
		cBox.stateChanged.connect(lambda: self.toggleSetting(setting))

	def toggleSetting(self, setting:str):
		SETTINGS.setValue(setting, not SETTINGS.getValue(setting))