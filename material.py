
import PIL
from assetcacher import ASSETCACHER
from fileread import *
from terminable import Exportable
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
	
	def getParams(self):
		params = {}
		
		splitted = self.par.split("=")

		for i in range(0, len(splitted) - 1, 2):
			params[splitted[i]] = splitted[i + 1]

		return params

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

class MaterialTemplateLibrary:
	class Material:
		def __repr__(self):
			return f"newmtl {self.material.getName()}\n{self.getFormattedParams()}"

		def __init__(self, material:MaterialData):
			self.material = material

			self.params = {}

			f = lambda x: f"{x[0]} {x[1]} {x[2]} {x[3]}"

			# self.setParam("Ka", f(material.amb))
			# self.setParam("Kd", f(material.diff))
			# self.setParam("Ks", f(material.spec))

			self.setParam("illum", 3)

			matParams = material.getParams()

			if "opacity" in matParams:
				self.setParam("d", matParams["opacity"])

			self.setParam("map_Kd", material.diffuse[:-1] + ".dds")
			self.setParam("map_bump", material.normal[:-1] + ".dds")

			if len(material.detail) > 0:
				self.setParam("decal ", material.getName() + "_detail")
			

			print(f"{material}: {material.cls} - {matParams}")
		
		def setParam(self, name, value):
			if value == None:
				return
			
			self.params[name] = value
		
		def getFormattedParams(self):
			formatted = ""

			for k in self.params:
				formatted += f"\t{k} {self.params[k]}\n"

			return formatted

	def __init__(self, materials:list[MaterialData]):
		self.__mats = tuple(self.Material(material) for material in materials)
	
	def getMTL(self):
		mtl = ""

		for v in self.__mats:
			mtl += f"{v}"

		return mtl
	
	def exportTextures(self):
		if "diffuse" in self.params:
			ddsx = ASSETCACHER.getCachedAsset()

class DDSx(Exportable):
	class Header:
		...
	
	def __init__(self, filePath:str, name:str = None, header:Header = None, file:BinFile = None):
		self.setFilePath(filePath)

		if header == None:
			self.__loadSingleFile__(filePath)
		else:
			self.__loadFromDXP__(name, header, file)
	
	def __loadSingleFile__(self, filePath:str):
		self.setName(path.splitext(path.basename(filePath))[0])
	
	def __loadFromDXP__(self, name:str, header:Header, file:BinFile):
		self.setName(name)



class DDSxTexturePack2(Exportable):
	def __init__(self, filePath:str):
		self.setFilePath(filePath)



if __name__ == "__main__":
	from gameres import GameResDesc

	desc = GameResDesc("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\riDesc.bin")
	
	# materials = desc.getModelMaterials("dodge_wf32_abandoned_b")
	materials = desc.getModelMaterials("dodge_wf32")

	mtl = MaterialTemplateLibrary(materials)
	print(mtl.getMTL())