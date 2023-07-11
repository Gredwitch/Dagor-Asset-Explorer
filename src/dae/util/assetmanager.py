import sys
from os import path
from typing import Union

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import util.log as log
from parse.gameres import *
# from parse.mesh import MatVData
from parse.material import DDSx, DDSxTexturePack2
# from parse.sound import FModBank, FModFSB

from util.enums import *
from util.terminable import Exportable
# from settings import settings

def extend(d:dict, key, value):
	d[key] = value

	return d

GAMERESDESC_HACK = ("*Desc.bin", "GameResDesc")

class AssetManager:
	__OPENABLE_CLASSES:tuple[type[Exportable]] = (
		GameResourcePack,
		DDSx,
		DDSxTexturePack2,
	)

	__OPENABLE_EXTENSIONS:dict[str, type[Exportable]] = {v.fileExtension:v for v in __OPENABLE_CLASSES}
	__EXTENSIONS:dict[str, str] = extend({f"*.{v.fileExtension}":v.classNiceName for v in __OPENABLE_CLASSES}, *GAMERESDESC_HACK)

	@classmethod
	def isOpenable(cls, suffix:str):
		return suffix in cls.__OPENABLE_EXTENSIONS
	
	# @classmethod
	# def getNiceName(cls, suffix:str):
	# 	return cls.__EXTENSIONS[suffix]
	
	@classmethod
	def getOpenableFiles(cls):
		return cls.__EXTENSIONS
	
	@classmethod
	def getOpenableClasses(cls):
		return cls.__OPENABLE_CLASSES
	
	@classmethod
	def initializeAsset(cls, absFilePath, suffix) -> Union[Exportable, None]:
		asset:Exportable = None

		if suffix in cls.__OPENABLE_EXTENSIONS:
			fileClass = cls.__OPENABLE_EXTENSIONS[suffix]

			asset = fileClass(absFilePath)
		else:
			log.log(f"Unknown file format '{absFilePath}'", LOG_ERROR)

		return asset
