import sys
from os import path, getcwd, mkdir, makedirs

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import util.log as log
from util.fileread import *
from util.terminable import Packed, Pack, SafeIter, SafeRange, SafeEnumerate, SafeReversed, Terminable
from util.decompression import zstdDecompress, oodleDecompress, zlibDecompress, lzmaDecompress
from util.enums import *
from util.assetcacher import AssetCacher
from struct import pack_into as packInto
from struct import pack
from ctypes import create_string_buffer
from PIL import Image
from PIL.ImageChops import invert

DDSX_HEADER_SIZE = 0x20

class DDSx(Packed):
	class Header:
		def __repr__(self):
			return f"<DDSxHeader {self.getFormattedData()}>"
		
		def getFormattedData(self):
			return f"{self.d3dformat} {self.w}x{self.h}"
		
		def __init__(self, file:BinBlock):
			self.label = file.read(4)

			self.d3dformat = file.read(4)
			self.flags = readEx(3, file)
			self.cMethod = readByte(file)
			self.h = readShort(file)
			self.w = readShort(file)

			self.levels = readByte(file)
			self.hqPartLevels = readByte(file)

			self.depth = readShort(file)
			self.bitsPerPixel = readShort(file)

			b = readByte(file)

			self.lQmip = b >> 4
			self.mQmip = b & 0x0F

			b = readByte(file)

			self.dxtShift = b >> 4
			self.uQmip = b & 0x0F

			self.memSz = readInt(file)
			self.packedSz = readInt(file)

		def getBin(self):
			return pack("4s4sIHHBBHHBBII", 	self.label, 
											self.d3dformat, 
											self.cMethod * 0x1000000 + self.flags, 
											self.w, 
											self.h, 
											self.levels,
											self.hqPartLevels,
											self.depth,
											self.bitsPerPixel,
											self.lQmip * 0x10 + self.mQmip,
											self.dxtShift * 0x10 + self.uQmip,
											self.memSz,
											self.packedSz)

	__FLAGS = {
		"FLG_ADDRU_MASK"          : 0xf,
		"FLG_ADDRV_MASK"          : 0xf0,
		"FLG_ARRTEX"              : 0x200_000,
		"FLG_COMPR_MASK"          : 0xe0_000_000,
		"FLG_CONTIGUOUS_MIP"      : 0x100,
		"FLG_CUBTEX"              : 0x800,
		"FLG_GAMMA_EQ_1"          : 0x8_000,
		"FLG_GENMIP_BOX"          : 0x2_000,
		"FLG_GENMIP_KAIZER"       : 0x4_000,
		"FLG_GLES3_TC_FMT"        : 0x100_000,
		"FLG_HASBORDER"           : 0x400,
		"FLG_HOLD_SYSMEM_COPY"    : 0x10_000,
		"FLG_HQ_PART"             : 0x80_000,
		"FLG_NEED_PAIRED_BASETEX" : 0x20_000,
		"FLG_VOLTEX"              : 0x1_000,

		"FLG_REV_MIP_ORDER"       : 0x40_0, # 0

		"FLG_NONPACKED"           : 0x200,
		"FLG_ZSTD"                : 0x20_000_000,
		"FLG_7ZIP"                : 0x40_000_000, # LZMA
		"FLG_OODLE"               : 0x60_000_000,
		"FLG_ZLIB"                : 0x80_000_000
	}

	__DXT_FORMATS = (
		b"DXT1",
		b"DXT5",
		b"BC7 ",
		b"ATI1")

	__DDS_HEADER = (
		0x44, 0x44, 0x53, 0x20, 0x7C, 0x00, 0x00, 0x00,
		0x07, 0x10, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x20, 0x00, 0x00, 0x00,
		0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
	)

	__DDS_2_HEADER = (
		0x44, 0x44, 0x53, 0x20, 0x7C, 0x00, 0x00, 0x00,
		0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x20, 0x00, 0x00, 0x00,
		0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x08, 0x10, 0x40, 0x00,
		# 0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x62, 0x00, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00
	)

	__DX10_FORMATS = (
		b"BC7 ", 
		b"BC7 "
	)

	@classmethod
	@property
	def classIconName(self) -> str:
		return "asset_tex.bmp"
	
	@classmethod
	@property
	def classNiceName(cls) -> str:
		return "DDSx"
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "ddsx"
	
	def __repr__(self):
		return f"<DDsX {self.name}: {self.__header.getFormattedData()}>"

	def __init__(self, 
	      filePath:str, 
		  name:str = None, 
		  size:int = 0, 
		  dataOffset:int = DDSX_HEADER_SIZE, 
		  header:Header = None):
		super().__init__(filePath, name, size, dataOffset)

		# if file == None:
		# 	self.__loadSingleFile__()
		# else:

		self._setName(self.name.split('*')[0].split("$")[0])

		if dataOffset == DDSX_HEADER_SIZE:
			self.__singleFile = True

			if header is None:
				file = open(self.filePath, "rb")

				header = self.Header(BinFile(file.read(DDSX_HEADER_SIZE)))

				file.close()
		elif header is None:
			raise NotImplementedError(f"Missing header for packed DDSx (ofs={dataOffset})")
		else:
			self.__singleFile = False
		
		self.__header = header

		self._setSize(self.__header.packedSz)
		self._setValid()
	
	def __decompress__(self, data:bytes):
		cMethod = self.__header.cMethod

		log.log(f"Decompressing {self.__header.memSz}b using {cMethod=}")

		if cMethod == 0x20:
			data = zstdDecompress(data)
		elif cMethod == 0x60:
			data = oodleDecompress(data, maxOriginalSize = self.__header.memSz)
		elif cMethod == 0x80:
			data = zlibDecompress(data)
		elif cMethod == 0x40:
			data = lzmaDecompress(data)
		
		return data

	
	def getPixelCnt(self):
		return self.__header.w * self.__header.h
	
	def getMipSize(self, width:int, height:int, dxtVersion:bytes):
		dxtSize = max(1, (width + 3) // 4) * max(1, (height + 3) // 4)

		if dxtVersion == b"DXT1" or dxtVersion == b"ATI1":
			return dxtSize * 8
		elif dxtVersion == b"DXT5" or dxtVersion == b"BC7 ":
			return dxtSize * 16
		else:
			log.log(f"Unknown DXT version {dxtVersion}, using DXT1 scale", LOG_WARN)

			return dxtSize * 8

	def getData(self):
		return self.__decompress__(self.getBin().read())
	
	def save(self, output:str = getcwd()):
		self._save(output, self.__header.getBin() + self.getBin().read())

	def getDDS(self):
		log.log(f"Converting {self.name} to DDS")
		log.addLevel()


		d3dformat = self.__header.d3dformat
		w, h = self.__header.w, self.__header.h

		log.log(f"cMethod       =	{hex(self.__header.cMethod)}")
		log.log(f"D3D Format    =	{d3dformat}")
		log.log(f"Resolution    =	{w}x{h}")

		data = self.getData()


		if self.__header.flags & 0x40000:
			log.log("Found reversed mip order")
			
			pos = 0
			images = []


			for level in SafeRange(self, self.__header.levels - 1, -1, -1):
				width = w // (2 ** level)
				height = h // (2 ** level)

				size = self.getMipSize(width, height, d3dformat)
				images.append(data[pos:pos + size])
				pos += size

			data = bytearray()

			for image in SafeReversed(self, images):
				data.extend(image)
		
		
		if d3dformat in self.__DX10_FORMATS:
			log.log("Found DX10 texture")

			ddsData = create_string_buffer(0x94)

			packInto('148B', ddsData, 0, *self.__DDS_2_HEADER)
			packInto('I', ddsData, 0xc, w)
			packInto('I', ddsData, 0x10, h)
			packInto('I', ddsData, 0x14, self.__header.memSz)
			packInto('B', ddsData, 0x1c, self.__header.levels)
			packInto('4s', ddsData, 0x54, b"DX10")
		else:
			ddsData = create_string_buffer(0x80)

			packInto('128B', ddsData, 0, *self.__DDS_HEADER)
			packInto('I', ddsData, 0xc, w)
			packInto('I', ddsData, 0x10, h)
			packInto('I', ddsData, 0x14, self.__header.memSz)
			packInto('B', ddsData, 0x1c, self.__header.levels)
			packInto('4s', ddsData, 0x54, d3dformat)
		
		data = ddsData.raw + data

		log.log(f"Done: final size = {len(data)}")

		log.subLevel()

		return data
	
	@property
	def isSingleFile(self):
		return self.__singleFile
	
	def getParentName(self):
		if self.isSingleFile:
			return path.basename(path.dirname(self.filePath))
		else:
			fName = path.basename(self.filePath).split(".")[0]
			
			if fName.endswith("-hq"):
				fName = fName[:-3]
			
			if fName.startswith("hq_tex"):
				fName = fName[7:]
			
			return fName

	# def _setFileName(self, name:str):
	# 	self.__fileName = name

	# @property
	# def fileName(self):
	# 	return self.__fileName
	
	# @property
	# def name(self):
	# 	return self.fileName
	
	def exportDDS(self, output:str = getcwd()):
		fileName = f"{self.name}.dds"

		output = path.normpath(f"{output}\\{fileName}")

		log.log(f"Saving {fileName}")
		log.addLevel()

		binData = self.getDDS()

		file = open(output, "wb")

		file.write(binData)

		file.close()

		log.log(f"Wrote {len(binData)} bytes to {output}")
		log.subLevel()

class DDSxTexturePack2(Pack): # TODO: Add logs
	@classmethod
	@property
	def classIconName(self) -> str:
		return "folder_dxp.bmp"

	@classmethod
	@property
	def classNiceName(cls) -> str:
		return "DDSx Texture Pack"
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "dxp.bin"
	
	def __init__(self, filePath:str, name:str = None):
		super().__init__(filePath, name)

		self.__readFile__()
		self._setValid()

		self.__pulledAll = False
	
	def __readFile__(self):
		# log.addLevel()

		f = open(self.filePath, "rb")
		f.seek(0x8, 1)
		fileCnt = readInt(f)

		file = BinFile(f.read(readInt(f)))
		f.close()

		nameMapIndiciesOfs = readInt(file)
		nameMapIndiciesCnt = readInt(file)

		file.seek(8, 1)

		self.__ddsxHeadersOfs = readInt(file)
		# self.__ddsxHeaders:list[DDSx.Header] = [None for _ in SafeRange(self, readInt(file))]
		if readInt(file) != fileCnt:
			raise Exception("ddsxHeader cnt != fileCnt")

		file.seek(8, 1)

		self.__ddsxRecordsOfs = readInt(file) + 0xC
		# self.__ddsxRecords:list = [None for _ in SafeRange(self, readInt(file))]
		if readInt(file) != fileCnt:
			raise Exception("ddsxRecord cnt != fileCnt")

		file.seek(0x10, 1)

		self.__nameMap = readNameMap(file, nameMapIndiciesCnt, nameMapIndiciesOfs, 0x38, self, True)

		self.__files:list[DDSx] = []

		for i in SafeRange(self, fileCnt):
			ddsx = self.__readDDSx__(file, i)

			if ddsx is not None:
				self.__files.append(ddsx)
		
		file.close()
	
	def __readDDSx__(self, file:BinFile, id:int):
		name = self.__nameMap[id]

		log.log(f"Pulling {id}:{name} from {self.name}.dxp.bin")
		log.addLevel()

		file.seek(self.__ddsxHeadersOfs + id * DDSX_HEADER_SIZE, 0)

		header = DDSx.Header(BinFile(file.read(DDSX_HEADER_SIZE)))

		ddsx = None

		if header.packedSz == 0:
			log.log(f"Ignoring null sized DDSx")
		else:
			file.seek(self.__ddsxRecordsOfs + id * 0x18, 0) # 0x18

			offset = readInt(file)
			
			ddsx = DDSx(self.filePath, name, header.memSz, offset, header)

		log.subLevel()

		return ddsx
	
	def getDDSxById(self, id:int):
		assert id >= 0 and id <= len(self.__files)

		return self.__files[id]
	
	def getDDSxByName(self, name:str):
		for k, v in SafeRange(self, self.__nameMap):
			if v == name:
				return self.getDDSxById(k)
				
		return None
	
	def getPackedFiles(self) -> list[DDSx, False]:
		return self.__files

def ftm(tex:str): # format texture to material
	tex = tex.split("*")[0]
	splitted = tex.split("_")
	
	noTex = True

	for i in range(len(splitted) - 1, 0, -1):
		part = splitted[i]

		if part == "tex":
			if i + 1 < len(splitted) and len(splitted[i + 1]) <= 2:
				splitted.pop(i + 1)
			
			splitted.pop(i)
			noTex = False

			break
	
	if noTex and len(splitted[-1]) < 2:
		splitted.pop()
	
	return "_".join(splitted)

def addComp(list:list[str], comp:str):
	if comp is not None:
		list.append(ftm(comp))

def getBestTex(self:Terminable, ddsx:list[DDSx]):
	best = ddsx[0]
	
	for i in SafeRange(self, 1, len(ddsx)):
		cur = ddsx[i]

		if cur.getPixelCnt() > best.getPixelCnt():
			best = cur

	return best

class TexturePathDict:
	class Texture:
		def __repr__(self):
			return f"<{self.tex}:{self.texType}>"
		
		def __init__(self, tex:str, texType:int, texPath:str):
			self.__tex = tex
			self.__texType = texType
			self.__texPath = texPath

			if texType == TEXTURE_MASKED:
				self.__newName:str = self.tex + "m"
			else:
				self.__newName:str = None

		def setType(self, texType:int):
			self.__texType = texType

		@property
		def newName(self):
			return self.__newName
		
		@property
		def tex(self):
			return self.__tex
		
		@property
		def texType(self):
			return self.__texType
		
		@property
		def texPath(self):
			return self.__texPath
	
	def __init__(self, customPath:str = None):
		self.__d:dict[str, TexturePathDict.Texture] = {}
		
		if customPath is None:
			self.__customPath = "models"
		else:
			self.__customPath = f"models/{customPath}"

	def getTexPath(self, texName:str):
		cachedDDSx = AssetCacher.getCachedAsset(DDSx, texName)

		if cachedDDSx:
			cachedDDSx:DDSx = cachedDDSx[0]

			return f"{self.customPath}/{cachedDDSx.getParentName()}"
		else:
			return self.customPath
	
	def get(self, texName:str):
		return self.__d.get(texName)

	def append(self, 
			texName:str, 
			texType:int, 
			vmt:list[str],
			vmtKey:str):
		texName = MaterialData.getTexFileName(texName)
		texPath = self.getTexPath(texName)
		tex = TexturePathDict.Texture(texName, texType, texPath)

		if tex.newName:
			texName = tex.newName

		vmt.append(f'${vmtKey} "{texPath}/{texName}"')
		
		self.__d[texName] = tex

		return tex

	def getDict(self):
		return self.__d

	@property
	def customPath(self):
		return self.__customPath


class MaterialData(Terminable):
	def __repr__(self):
		return f"<MaterialData {self.getName()}>"
	
	def __init__(self):
		self.__name:str = None
		self.__params:dict[str, str] = None

		self.diff = (0, 0, 0, 1)
		self.amb = (0, 0, 0, 1)
		self.emis = (0, 0, 0, 1)
		self.spec = (0, 0, 0, 1)

		self.cls:str = None
		self.par:str = None


		self.__detailList:list[str] = None
		self.__detailNormalList:list[str, None] = None
		self.__textureSlots:list[str] = [None for _ in range(11)]
		self.textures:list[str] = []
	
	def isLayered(self):
		return self.cls.find("layered") != -1
	
	def isDynamic(self):
		return self.cls.find("dynamic") != -1
	
	def __generateName__(self):
		if len(self.textures) == 0:
			return self.cls
		
		components:list[str] = []

		# shader class families:
		# dynamic (not layered): diffuse, mask, normal, AO, eventually detail - if mask, invert diffuse's alpha
		# layered: diffuse, mask, normal, detail - should we invert the diffuse's alpha?
		# simple / other: diffuse, (none), normal 
		# rendinst_simple_layered: AABB structure (A = diffuse, B = normal) - should we do a 50% mix?
		# rendinst_tree_colored: uses alpha as mask
		# rendinst_interior_mapping: uses cubemap as diffuse and normal
		# combined: weird mask? (dynamic_combined_mixed_decal, dynamic_combined_detailed_decal)
		
		if not self.isLayered():
			addComp(components, self.__textureSlots[0])
			addComp(components, self.__textureSlots[1])

		detailStart = 4

		if not self.isDynamic() or self.isLayered():
			detailStart = 3
		
		for i in range(detailStart, len(self.__textureSlots), 2):
			detail = self.__textureSlots[i]

			addComp(components, detail)

			if detail is None and i + 1 < len(self.__textureSlots):
				addComp(components, self.__textureSlots[i + 1])

		return "_".join(components)

	def checkModifiedName(self, tex:str, texturePaths:TexturePathDict):
		if texturePaths is None or texturePaths.get(tex + "m") is None:
			return tex
		else:
			return tex + "m"
		

	@classmethod
	def getTexFileName(cls, tex:str):
		return tex.split("*")[0]
	

	def addTexSlot(self, slotName:str, tex:str):
		slotIdx = int(slotName[1:])

		self.__textureSlots[slotIdx] = tex
		self.textures.append(tex)
	
	def getName(self):
		if self.__name is None:
			self.__name = self.__generateName__()
		
		return self.__name
	
	def setName(self, name:str):
		self.__name = name
	
	
	def getParams(self):
		if self.__params is None:
			params = {}
			
			paramL = self.par.split("\n")

			for param in SafeIter(self, paramL):
				splitParam = param.split("=")

				if len(splitParam) == 1:
					key = splitParam[0]
					val = ""
				else:
					key, val = splitParam

				params[key] = val

			self.__params = params

		return self.__params

	def getTextureSlots(self):
		return self.__textureSlots

	def convertTex(self, texture:str, data:bytes, texturePaths:TexturePathDict = None, forceConvert:bool = False, texN:str = None):
		newName = None

		if texturePaths is not None and texturePaths.get(texture if texN is None else texN) is not None:
			tex = texturePaths.get(texture if texN is None else texN)

			texType = tex.texType

			if tex.newName is not None:
				newName = tex.newName
		else:
			texType = None
		
		if texType is not None or forceConvert:
			img = Image.open(BytesIO(data))

			if texType is not None and texType != TEXTURE_GENERIC:
				r, g, b, a = img.split()
				img.close()

				if texType == TEXTURE_MASKED:
					img = Image.merge("RGBA", (r, g, b, invert(a)))
				elif texType == TEXTURE_NORMAL:
					whiteChannel = Image.new("L", img.size, 255)
					img = Image.merge("RGBA", (a, g, whiteChannel, r))
			
			outBin = BytesIO()
			img.save(outBin, format = "DDS")
			data = outBin.getvalue()
			outBin.close()
			img.close()
		
		return data, newName
	
	def exportTexture(self, texture:str, output:str = getcwd(), forceConvert:bool = False, texturePaths:TexturePathDict = None, texN:str = None):
		outpath = path.join(output, "textures")

		if not path.exists(outpath):
			mkdir(outpath)
			
		
		name = texture.split("*")[0]

		ddsx:list[DDSx] = AssetCacher.getCachedAsset(DDSx, name)

		if not ddsx:
			log.log(f"{name} not found")
			
			return
		
		data = getBestTex(self, ddsx).getDDS()
		data, texN = self.convertTex(texture, data, texturePaths, forceConvert, texN)

		if texN is not None:
			name = texN

		output = path.join(outpath, f"{name}.dds")

		file = open(output, "wb")
		file.write(data)
		file.close()

		log.log(f"Wrote {len(data)} bytes to {output}")
	
	def getDMF(self):
		buffer = BBytesIO()

		name = self.getName()
		
		buffer.writeString(name)
		buffer.writeString(self.cls)
		
		buffer.write(pack("ffff", *self.diff))
		buffer.write(pack("ffff", *self.amb))
		buffer.write(pack("ffff", *self.emis))
		buffer.write(pack("ffff", *self.spec))

		for tex in SafeIter(self, self.__textureSlots):
			buffer.writeString(tex)
		
		params = self.getParams()

		buffer.writeInt(len(params))

		for k in params:
			buffer.writeString(k)
			buffer.writeString(params[k])

		value = buffer.getvalue()

		buffer.close()

		return value

	def __eq__(self, other):
		return self.__textureSlots == other.__textureSlots # and self.par == other.par

	def detail1IsDiffuse(self):
		return self.isLayered() and self.cls != "rendinst_simple_layered"

	@property
	def diffuse(self):
		if self.detail1IsDiffuse():
			self.__initDetailList__()

			if len(self.__detailList) >= 1:
				return self.__detailList[0]
			else:
				return None
		else:
			return self.__textureSlots[0]
	
	@property
	def normal(self):
		if self.detail1IsDiffuse() and len(self.__detailNormalList) > 0:
			return self.__detailNormalList[0]
		else:
			return self.__textureSlots[2]
	
	@property
	def mask(self):
		return self.__textureSlots[1]
	
	def __initDetailList__(self):
		if self.__detailList is None:
			detailList = []
			detailNormalList = []

			if self.cls != "dynamic_painted_by_mask":
				detailStart = 4

				if not self.isDynamic() or self.isLayered():
					detailStart = 3
				
				for i in range(detailStart, len(self.__textureSlots), 2):
					tex = self.__textureSlots[i]

					if tex is not None:
						detailList.append(tex)

						tex = self.__textureSlots[i + 1]

						detailNormalList.append(tex)
			
			self.__detailNormalList = detailNormalList
			self.__detailList = detailList

	@property 
	def detail(self):
		self.__initDetailList__()

		if self.detail1IsDiffuse():
			return self.__detailList[1:]
		else:
			return self.__detailList
	
	@property 
	def detailNormal(self):
		self.__initDetailList__()

		if self.detail1IsDiffuse():
			return self.__detailNormalList[1:]
		else:
			return self.__detailNormalList

	def getVMTcomments(self):
		return [
			f"// {self.cls}",
			"",
			"// params",
			"\n\t".join(tuple(f"//\t{k}={v}" for k, v in SafeIter(self, self.getParams().items()))),
			"",
			"// textures by slot",
			"\n\t".join(tuple(f"//\t{k}={v}" for k, v in SafeEnumerate(self, self.getTextureSlots()))),
			""]

	
	def getVMT(self, texturePaths:TexturePathDict):
		params = self.getParams()
		getScale = lambda x: 1 / float(params.get(x)) if x in params else 1

		vmt = self.getVMTcomments()

		if self.diffuse is not None:
			texType = TEXTURE_GENERIC
			
			if self.cls.find("masked") != -1:
				texType = TEXTURE_MASKED
			
			diffuse = texturePaths.append(self.diffuse, texType, vmt, "basetexture")

			if self.detail1IsDiffuse():
				vmt.append(f"$basetexturetransform center .5 .5 scale {getScale('detail1_tile_u')} {getScale('detail1_tile_v')} rotate 0 translate 0 0")
		else:
			diffuse = None

		if self.normal is not None:
			texturePaths.append(self.normal, TEXTURE_NORMAL, vmt, "bumpmap")

		mask = self.mask
		detail = self.detail

		if len(detail) > 0 and (mask is None or self.isLayered()):
			if self.detail1IsDiffuse():
				tileParam = "detail2"
			else:
				tileParam = "detail1"
			
			mask = detail[0]
		else:
			tileParam = "mask"

		if mask is not None:
			texturePaths.append(mask, TEXTURE_GENERIC, vmt, "detail")

			vmt.append("$detailblendmode 4")
			vmt.append(f"$detailscale [{getScale(f'{tileParam}_tile_u')} {getScale(f'{tileParam}_tile_v')}]")

			if self.isLayered():
				vmt.append("$detailblendfactor 0.5")

			gamma = params.get(f"{tileParam}_gamma_end")

			if gamma is None:
				gamma = params.get(f"{tileParam}_gamma_start")

			if gamma is not None:
				gamma = float(gamma) * 2

				vmt.append(f"$detailtint {'{'} {gamma} {gamma} {gamma} {'}'}")


		if self.cls.find("glass") != -1:
			vmt.append("$translucent 1")
			vmt.append("$nocull 1")
		elif ("atest" in params and params["atest"] != "128") or self.cls.find("atest") != -1:
			vmt.append("$alphatest 1")
			vmt.append("$nocull 1")
		elif "two_sided" in params:
			vmt.append("$nocull 1")

		fullVMT = "\n".join(('"VertexLitGeneric"', "{", "\t" + "\n\t".join(vmt), "}"))

		return fullVMT


class MaterialTemplateLibrary(Terminable):
	class Material(Terminable):
		def __repr__(self):
			return f"newmtl {self.material.getName()}\n{self.getFormattedParams()}"

		def __init__(self, material:MaterialData):
			self.material = material

			self.params = {}

			# f = lambda x: f"{x[0]} {x[1]} {x[2]} {x[3]}"

			# self.setParam("Ka", f(material.amb))
			# self.setParam("Kd", f(material.diff))
			# self.setParam("Ks", f(material.spec))

			self.setParam("illum", 3)

			matParams = material.getParams()

			if "opacity" in matParams:
				self.setParam("d", matParams["opacity"])

			if material.diffuse is not None:
				self.setParam("map_Kd", "textures/" + material.diffuse[:-1] + ".dds")
			
			if material.normal is not None:
				self.setParam("map_bump", "textures/" + material.normal[:-1] + ".dds")

			if len(material.detail) > 0:
				self.setParam("decal ", material.getName() + "_detail")
			

			log.log(f"{material}: {material.cls} - {matParams}")
		
		def setParam(self, name, value):
			if value == None:
				return
			
			self.params[name] = value
		
		def getFormattedParams(self):
			formatted = ""

			for k in SafeIter(self, self.params):
				formatted += f"\t{k} {self.params[k]}\n"

			return formatted

		def __exportDiffuse__(self, outpath:str, forceConvert:bool):
			self.material.exportTexture(self.material.diffuse, outpath, forceConvert = forceConvert)
		
		def __exportNormal__(self, outpath:str, forceConvert:bool):
			self.material.exportTexture(self.material.normal, outpath, forceConvert = forceConvert)

		def exportTextures(self, outpath:str = getcwd(), forceConvert:bool = False):
			if "map_Kd" in self.params:
				self.__exportDiffuse__(outpath, forceConvert)
			
			if "map_bump" in self.params:
				self.__exportNormal__(outpath, forceConvert)
			

	def __init__(self, materials:list[MaterialData]):
		self.__mats = tuple(self.Material(material) for material in SafeIter(self, materials))
	
	def getMTL(self):
		mtl = ""

		for v in SafeIter(self, self.__mats):
			mtl += f"{v}"

		return mtl
	
	def exportTextures(self, outpath:str = getcwd(), forceConvert:bool = False):
		log.log("Exporting MTL textures")
		log.addLevel()

		for mat in SafeIter(self, self.__mats):
			mat:MaterialTemplateLibrary.Material

			log.log(f"Exporting textures from {mat.material.getName()}")
			log.addLevel()

			mat.exportTextures(outpath, forceConvert)

			log.subLevel()
		
		log.subLevel()

def computeMaterialNames(mats:list[MaterialData], parent:Terminable = None):
	log.log("Computing material names")
	log.addLevel()
	
	enumerateIt = (lambda x: SafeEnumerate(parent, x)) if parent is not None else (lambda x: enumerate(x))
	iterIt = (lambda x: SafeIter(parent, x)) if parent is not None else (lambda x: iter(x))
	
	for k, mat in enumerateIt(mats):
		mat:MaterialData

		log.log(f"Materials #{k}: {mat.getName()}")

		cnt = 1


		for mat2 in iterIt(mats):
			mat2:MaterialData
			
			if mat is mat2:
				continue
			
			if mat.getName() == mat2.getName():
				if mat == mat2:
					continue
				else:
					mat2.setName(mat2.getName() + f"_{cnt}")
					cnt += 1

	log.subLevel()

# def generateMaterialData(textures:list[str], mvdMats:list[MatVData.Material], parent:Terminable = None):
# 	materials:list[MaterialData] = []

# 	iterator = (lambda x: SafeEnumerate(parent, x)) if parent is not None else (lambda x: enumerate(x))

# 	for k, v in iterator(mvdMats):
# 		mat = MaterialData()

# 		mat.cls = v.shaderClass
# 		mat.par = ""
# 		mat.diff = v.diff
# 		mat.amb = v.amb
# 		mat.spec = v.spec
# 		mat.emis = v.emis
		
# 		for texId, texKey in iterator(v.textures):
# 			if texKey == 0xFFFFFFFF:
# 				continue
			
# 			mat.addTexSlot(f"t{texId}", textures[texKey])

# 		materials.append(mat)
	
# 	return materials

if __name__ == "__main__":
	from gameres import GameResDesc

	dxp = DDSxTexturePack2("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\cars_ri.dxp.bin")
	
	for ddsx in dxp.getAllDDSx():
		if ddsx != False:
			AssetCacher.cacheAsset(ddsx)

	desc = GameResDesc("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\riDesc.bin")
	
	# materials = desc.getModelMaterials("dodge_wf32_abandoned_b")
	materials = desc.getModelMaterials("dodge_wf32")

	mtl = MaterialTemplateLibrary(materials)
	print(mtl.getMTL())
	mtl.exportTextures()