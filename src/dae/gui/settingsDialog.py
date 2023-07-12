
import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from PyQt5.QtWidgets import QDialog, QWidget, QGridLayout, QCheckBox
from PyQt5.uic import loadUi
from util.misc import getUIPath
from util.enums import *
from util.settings import SETTINGS


SETTINGSUI_PATH = getUIPath("settings.ui")

class SettingsDialog(QDialog):
	gridLayout:QGridLayout

	exportFolder:QCheckBox
	exportPreviewTex:QCheckBox
	extractFolder:QCheckBox
	noTexExport:QCheckBox
	outputFolder:QCheckBox

	
	def __init__(self, parent:QWidget):
		super().__init__(parent)

		loadUi(SETTINGSUI_PATH, self)

		self.gridLayout.setContentsMargins(-1, -1, -1, -1)

		self.setupCheckBox(self.exportFolder, SETTINGS_EXPORT_FOLDER)
		self.setupCheckBox(self.exportPreviewTex, SETTINGS_EXPORT_PREVIEW_TEX)
		self.setupCheckBox(self.extractFolder, SETTINGS_EXTRACT_FOLDER)
		self.setupCheckBox(self.noTexExport, SETTINGS_NO_TEX_EXPORT)
		self.setupCheckBox(self.outputFolder, SETTINGS_OUTPUT_FOLDER)
	
	def setupCheckBox(self, cBox:QCheckBox, setting:str):
		cBox.setChecked(SETTINGS.getValue(setting))
		cBox.stateChanged.connect(lambda: self.toggleSetting(setting))

	def toggleSetting(self, setting:str):
		SETTINGS.setValue(setting, not SETTINGS.getValue(setting))