import sys
from os import path
from typing import Union

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import util.log as log
from parse.gameres import *
from parse.material import DDSx, DDSxTexturePack2
from util.enums import *
from util.terminable import Exportable

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
