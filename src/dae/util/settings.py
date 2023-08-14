
import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from json import loads, dumps
from util.decompression import lzmaCompress, lzmaDecompress
from util.misc import ROOT_FOLDER
from util.enums import *

compressSettings = False

class Settings:
	__DEFAULT_SETTINGS = {
		SETTINGS_EXPORT_FOLDER:True,
		SETTINGS_EXPORT_PREVIEW_TEX:False,
		SETTINGS_EXTRACT_FOLDER:True,
		SETTINGS_NO_TEX_EXPORT:False,
		SETTINGS_OUTPUT_FOLDER:False,
		SETTINGS_EXPORT_GAMEINFO:False,
		SETTINGS_STUDIOMDL_PATH:"",
		SETTINGS_GAMEINFO_PATH:"",
		SETTINGS_STUDIOMDL_EXPORT_COLLISION:False,
		SETTINGS_EXPORT_SMD:True,
		SETTINGS_NO_MDL:False,
		SETTINGS_DONT_EXPORT_EXISTING_TEXTURES:False,
		SETTINGS_FORCE_DDS_CONVERSION:True
	}

	def saveSettings(self):
		f = open(self.__fpath, "wb")
		
		if compressSettings:
			f.write(lzmaCompress(dumps(self.__settings, indent = 4)))
		else:
			f.write(dumps(self.__settings, indent = 4).encode("utf-8"))
			
		f.close()

	def saveSettingsDecompressed(self):
		f = open(self.__fpath + ".json", "w")
		
		f.write(dumps(self.__settings, indent = 4))

		f.close()
	
	def getSettings(self):
		return self.__settings
	
	def getValue(self, setting):
		return self.__settings[setting]
	
	def setValue(self, setting, val):
		self.__settings[setting] = val

		self.saveSettings()
	
	def resetSettings(self):
		self.__settings = self.__DEFAULT_SETTINGS

		self.saveSettings()

	
	def loadSettings(self):
		fpath = self.__fpath
		
		if not path.isfile(fpath):
			self.resetSettings()
		else:
			f = open(fpath, "rb")
			
			try:
				settings = None

				if compressSettings:
					settings = loads(lzmaDecompress(f.read()))
				else:
					settings = loads(f.read().decode("utf-8"))
				
				settingsKeys = settings.keys()

				shouldSave = False

				for k in self.__DEFAULT_SETTINGS:
					v = self.__DEFAULT_SETTINGS[k]

					if not k in settingsKeys or type(v) != type(settings[k]):
						shouldSave = True

						settings[k] = v
						
				self.__settings = settings

				if shouldSave == True:
					self.saveSettings()
			except:
				self.resetSettings()
			finally:
				f.close()
	
	def __init__(self):
		fpath = ROOT_FOLDER + "\\settings.json"
		
		self.__fpath = fpath

		self.loadSettings()

SETTINGS = Settings()
# settings.saveSettingsDecompressed()