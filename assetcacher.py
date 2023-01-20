
class AssetCacher:
	def __init__(self):
		self.__cachedAssets = {}
		self.__modelsDesc = {}
	
	def cacheAsset(self, asset):
		assetClass = type(asset)
		
		if not assetClass in self.__cachedAssets.keys():
			self.__cachedAssets[assetClass] = {}
		
		classCache:dict = self.__cachedAssets[assetClass]
		name = asset.getName()

		if not name in classCache.keys():
			classCache[name] = []
		
		classCache[name].append(asset)

		self.__cachedAssets[assetClass] = classCache
	
	def uncacheAsset(self, asset):
		if asset in self.__modelsDesc.values():
			del self.__modelsDesc[asset.getFilePath()]

			return
		
		assetClass = type(asset)
		
		if assetClass in self.__cachedAssets.keys():
			return
		
		classCache:dict = self.__cachedAssets[assetClass]
		name = asset.getName()

		if not name in classCache.keys():
			return
		
		nameCache:list = classCache[name]
		nameCache.pop(nameCache.index(asset))
	
	def clearCache(self, assetClass = None):
		if assetClass == None:
			self.__cachedAssets = {}
		elif assetClass in self.__cachedAssets.keys():
			self.__cachedAssets.pop(assetClass)

	def getAssetCache(self, assetClass = None):
		if assetClass == None:
			return self.__cachedAssets
		elif assetClass in self.__cachedAssets.keys():
			return self.__cachedAssets[assetClass]
		else:
			return {}
	
	def getCachedAsset(self, assetClass, name) -> list:
		if not assetClass in self.__cachedAssets:
			return False
		
		classCache:dict = self.__cachedAssets[assetClass]

		if not name in classCache:
			return False
		
		return classCache[name]

	def isCached(self, asset):
		assetClass = type(asset)
		
		if not assetClass in self.__cachedAssets:
			return False
		
		classCache:dict = self.__cachedAssets[assetClass]
		name = asset.getName()

		if not name in classCache:
			return False
		
		return asset in classCache[name]
	
	# def loadGameResDesc(self, path:str, size:int):
		# cachedDesc = settings.getValue("cachedDesc")

		# if not path in cachedDesc:
		#     return False
		
		# sdesc = cachedDesc[path]

		# if sdesc[0] != size:
		#     return False
		
		# self.appendGameResDesc(sdesc[1])

		# return sdesc[1]
	
	# def cacheAndLoadGameResDesc(self, path:str, size:int, desc:dict):
	#     cachedDesc = settings.getValue("cachedDesc")
	#     cachedDesc[path] = [size, desc]
	#     settings.setValue("cachedDesc", cachedDesc)
	#     settings.saveSettings()

	#     self.appendGameResDesc(desc)

	# def appendGameResDesc(self, desc:dict):
		# self.__modelsDesc = {**self.__modelsDesc, **desc}

	def appendGameResDesc(self, desc):
		self.__modelsDesc[desc.getFilePath()] = desc

	def getModelTextures(self, model:str):
		for desc in self.__modelsDesc.values():
			if desc.hasName(model):
				return desc.getModelTextures(model)
	
		return []

	def getModelMaterials(self, model:str):
		for desc in self.__modelsDesc.values():
			if desc.hasName(model):
				return desc.getModelMaterials(model)
	
		return []

ASSETCACHER = AssetCacher()
