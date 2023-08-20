
from util.terminable import Exportable

class AssetCacher:
	__cachedAssets = {}
	__modelsDesc = {}

	@classmethod
	def cacheAsset(cls, asset:Exportable):
		assetClass = type(asset)
		
		if not assetClass in cls.__cachedAssets.keys():
			cls.__cachedAssets[assetClass] = {}
		
		classCache:dict = cls.__cachedAssets[assetClass]
		name = asset.name

		if not name in classCache.keys():
			classCache[name] = []
		
		classCache[name].append(asset)

		cls.__cachedAssets[assetClass] = classCache
	
	@classmethod
	def uncacheAsset(cls, asset:Exportable):
		if asset in cls.__modelsDesc.values():
			del cls.__modelsDesc[asset.filePath]

			return
		
		assetClass = type(asset)
		
		if assetClass in cls.__cachedAssets.keys():
			return
		
		classCache:dict = cls.__cachedAssets[assetClass]
		name = asset.name

		if not name in classCache.keys():
			return
		
		nameCache:list = classCache[name]
		nameCache.pop(nameCache.index(asset))
	
	@classmethod
	def clearCache(cls, assetClass:type[Exportable] = None):
		if assetClass is None:
			cls.__modelsDesc = {}
			cls.__cachedAssets = {}
		elif assetClass in cls.__cachedAssets.keys():
			cls.__cachedAssets.pop(assetClass)

	@classmethod
	def getAssetCache(cls, assetClass:type[Exportable] = None):
		if assetClass == None:
			return cls.__cachedAssets
		elif assetClass in cls.__cachedAssets.keys():
			return cls.__cachedAssets[assetClass]
		else:
			return {}
	
	@classmethod
	def getCachedAsset(cls, assetClass:type[Exportable], name:str) -> list:
		if not assetClass in cls.__cachedAssets:
			return False
		
		classCache:dict = cls.__cachedAssets[assetClass]
		if not name in classCache:
			return False
		
		return classCache[name]

	@classmethod
	def isCached(cls, asset:type[Exportable]):
		assetClass = type(asset)
		
		if not assetClass in cls.__cachedAssets:
			return False
		
		classCache:dict = cls.__cachedAssets[assetClass]
		name = asset.name

		if not name in classCache:
			return False
		
		return asset in classCache[name]
	
	# @classmethod
	# def loadGameResDesc(cls, path:str, size:int):
		# cachedDesc = settings.getValue("cachedDesc")

		# if not path in cachedDesc:
		#     return False
		
		# sdesc = cachedDesc[path]

		# if sdesc[0] != size:
		#     return False
		
		# cls.appendGameResDesc(sdesc[1])

		# return sdesc[1]
	
	# @classmethod
	# def cacheAndLoadGameResDesc(cls, path:str, size:int, desc:dict):
	#     cachedDesc = settings.getValue("cachedDesc")
	#     cachedDesc[path] = [size, desc]
	#     settings.setValue("cachedDesc", cachedDesc)
	#     settings.saveSettings()

	#     cls.appendGameResDesc(desc)

	# def appendGameResDesc(cls, desc:dict):
		# cls.__modelsDesc = {**cls.__modelsDesc, **desc}

	@classmethod
	def appendGameResDesc(cls, desc):
		cls.__modelsDesc[desc.filePath] = desc

	@classmethod
	def getModelTextures(cls, model:str) -> list[str]:
		for desc in cls.__modelsDesc.values():
			if desc.hasName(model):
				return desc.getModelTextures(model)
	
		return []

	@classmethod
	def getModelMaterials(cls, model:str) -> list[str]:
		for desc in cls.__modelsDesc.values():
			if desc.hasName(model):
				return desc.getModelMaterials(model)

	@classmethod
	def getSkinnedMaterials(cls, model:str) -> list[str]:
		for desc in cls.__modelsDesc.values():
			if desc.hasName(model):
				return desc.getSkinnedMaterials(model)
	
		return []