
from fileread import *
from struct import unpack
import log
from enums import *
from decompression import zstdDecompress
from datablock import *
from os import path

class MaterialData: # TODO: rewrite with actual shader-based texture param names instead of arbritrary names
	def __init__(self):
		self.diffuse = None
		self.mask = None
		self.normal = None
		self.ambientOcclusion = None

		self.two_sided = False

		self.detail = []
		self.detailNormal = []

		self.name = None

		self.diff = (0, 0, 0, 1)
		self.amb = (0, 0, 0, 1)
		self.emis = (0, 0, 0, 1)
		self.spec = (0, 0, 0, 1)

		self.cls = None
		self.par = None

		self.properties = {}
	
	def __ftm(self, tex:str): # format texture to material
		tex = tex.split("*")[0]
		splitted = tex.split("_")

		if len(splitted[-1]) > 2:
			return tex
		else:
			return "_".join(splitted[:-1])
	
	def __mn(self, *args): # make name
		return "_".join(args)

	def __generateName__(self):
		formattedDetail = None

		if len(self.detail) > 0:
			formattedDetail = []

			for tex in self.detail:
				f = self.__ftm(tex)

				if f in formattedDetail or f == self.diffuse:
					continue
				
			formattedDetail.append(f)
		
		if len(self.detail) < len(self.detailNormal):
			if formattedDetail is None:
				formattedDetail = []

			for tex in self.detailNormal:
				f = self.__ftm(tex)

				if f in formattedDetail or f == self.diffuse:
					continue
				
				formattedDetail.append(f)

		if self.diffuse is None:
			if self.mask is None:
				if formattedDetail is None:
					return self.cls
				else:
					return self.__mn(self.cls, *formattedDetail)
			else:
				if formattedDetail is None:
					return self.cls + "_" + self.__ftm(self.mask)
				else:
					return self.__mn(self.cls, self.__ftm(self.mask), *formattedDetail)

		
		if self.mask is None or self.mask == self.diffuse:
			if formattedDetail is None:
				return self.__ftm(self.diffuse)
			else:
				return self.__mn(self.diffuse, *formattedDetail)
		else:
			if formattedDetail is None:
				return self.__mn(self.__ftm(self.diffuse), self.__ftm(self.mask))
			else:
				return self.__mn(self.__ftm(self.diffuse), self.__ftm(self.mask), *formattedDetail)

	def getTexFileName(self, tex:str):
		return tex.split("*")[0]
	

	def addTexSlot(self, slotName:str, tex:str):
		if slotName == "t0":
			self.diffuse = tex
		elif slotName == "t1":
			self.mask = tex
		elif slotName == "t2":
			self.normal = tex
		elif tex[-4:] == "_ao*":
			self.ambientOcclusion = tex
		elif tex[-3] == "_n*":
			self.detailNormal.append(tex)
		else:
			self.detail.append(tex)
	
	def getName(self):
		if self.name is None:
			self.name = self.__generateName__()
		
		return self.name
	
	def setName(self, name:str):
		self.name = name
	
	def __repr__(self):
		return f"<MaterialData {self.getName()}>"

	def __eq__(self, other):
		return (self.diffuse == other.diffuse and
				self.normal == other.normal and 
				self.ambientOcclusion == other.ambientOcclusion and (
					(self.mask == other.mask) or 
					(self.mask == self.diffuse and other.mask is None) or 
					(other.mask == other.diffuse and self.mask is None)) and
				self.detail == other.detail and 
				self.detailNormal == other.detailNormal and
				# self.cls == other.cls and
				# self.par == other.par and
				self.properties == other.properties)

class GameResDesc:
	def __init__(self, filePath:str):
		self.__filePath = filePath
		self.__fileName = path.splitext(path.basename(filePath))[0]
		self.__datablock = None

		self.__readFile__()
	
	def __getDecompressed__(self):
		file = open(self.__filePath, "rb")


		if readByte(file) != 2:
			file.close()

			raise Exception("bin magic != 2")

		log.log("Decompressing...")
		
		size = readEx(3, file) # - 5
		decompressed = BinFile(zstdDecompress(file.read(size)))

		# if readByte(file) != 1:
		# 	file.close()
			
		# 	raise Exception("data magic != 1")

		file.close()

		return decompressed
	
	def __readFile__(self):
		self.__datablock = loadDataBlock(self.__getDecompressed__())
	
	def getDataBlock(self):
		return self.__datablock

	def getModelTextures(self, model:str) -> list[str]:
		blk = None
		tex = None

		try:
			blk = self.__datablock.getByName(model)
			tex = blk.getByName("tex")

			if tex is None:
				raise Exception
		except Exception as er:
			return tuple()

		return tuple(tex.getParamById(i)[1] for i in range(tex.getParamsCount()))
	
	def getModelMaterials(self, model:str) -> list[str]:
		tex = self.getModelTextures(model)

		if tex is None:
			raise Exception
		
		# blk = None
		# mat = None

		blk = self.__datablock.getByName(model)
		matB = blk.getByName("matR")

		if matB is None:
			matB = blk.getByName("mat")
		

		# mats = []
		mats:list[MaterialData] = []
		
		for matBlock in (matB.getChildren()):
			mat = MaterialData()


			log.log(f"{matBlock}")
			log.addLevel()

			for i in range(matBlock.getParamsCount()):
				flags, params = matBlock.getParamById(i)
				blockName = matBlock.getParamNameByFlags(flags)
				blockType = flags & 0xF000000

				if blockType == 0x2000000:
					mat.addTexSlot(blockName, tex[params])

					log.log(f"{i}:{blockName}:{tex[params]}")
				else:
					setattr(mat, blockName, params)

					log.log(f"{i}:{blockName}:{params}")

			log.subLevel()

			mats.append(mat)

		log.log("Computing material names")
		log.addLevel()

		for k, mat in enumerate(mats):
			log.log(f"Materials #{k}: {mat.getName()}")

			cnt = 1

			for mat2 in mats:
				if mat is mat2:
					continue
				
				if mat.getName() == mat2.getName():
					if mat == mat2:
						continue
					else:
						mat2.setName(mat2.getName() + f"_{cnt}")
						cnt += 1

		log.subLevel()

		return mats


if __name__ == "__main__": ...
	# sblk = GameResDesc("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\riDesc.bin").getDataBlock()
	# sblk = GameResDesc("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\dynModelDesc.bin").getDataBlock()
	# desc = GameResDesc("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content.hq\\pkg_cockpits\\res\\dynModelDesc.bin")
	# desc = GameResDesc("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\patch\\content\\base\\res\\dynModelDesc.bin")

	# print(desc.getModelMaterials("su_17m2_cockpit"))