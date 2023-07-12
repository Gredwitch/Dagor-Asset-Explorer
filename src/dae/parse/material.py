
import sys
from os import path, getcwd, mkdir

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import PIL
import util.log as log
from util.fileread import *
from util.terminable import Packed, Pack, SafeIter, SafeRange, SafeEnumerate, SafeReversed, Terminable
from util.decompression import zstdDecompress, oodleDecompress, zlibDecompress, lzmaDecompress
from parse.mesh import MatVData
from util.enums import *
from util.assetcacher import AssetCacher

from struct import pack_into as packInto
from struct import pack
from ctypes import create_string_buffer

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
			self.w = readShort(file)
			self.h = readShort(file)

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
			if header == None:
				file = open(self.filePath, "rb")

				header = self.Header(BinFile(file.read(DDSX_HEADER_SIZE)))

				file.close()
		elif header == None:
			raise NotImplementedError(f"Missing header for packed DDSx (ofs={dataOffset})")

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

class MaterialData(Terminable): # TODO: rewrite with actual shader-based texture param names instead of arbritrary names
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

			for tex in SafeIter(self, self.detail):
				f = self.__ftm(tex)

				if f in formattedDetail or f == self.diffuse:
					continue
				
			formattedDetail.append(f)
		
		if len(self.detail) < len(self.detailNormal):
			if formattedDetail is None:
				formattedDetail = []

			for tex in SafeIter(self.detailNormal):
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

		for i in SafeRange(self, 0, len(splitted) - 1, 2):
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

class MaterialTemplateLibrary(Terminable):
	class Material(Terminable):
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

		def __saveTexture__(self, data:bytes, output:str):
			file = open(output, "wb")

			file.write(data)

			file.close()

			log.log(f"Wrote {len(data)} bytes to {output}")
		
		def getBestTex(self, ddsx:list[DDSx]):
			best = ddsx[0]
			
			for i in SafeRange(self, 1, len(ddsx)):
				cur = ddsx[i]

				if cur.getPixelCnt() > best.getPixelCnt():
					best = cur

			return best
		
		def __exportDiffuse__(self, outpath:str):
			name = self.material.diffuse.split("*")[0]

			ddsx:list[DDSx] = AssetCacher.getCachedAsset(DDSx, name)

			if not ddsx:
				log.log(f"{name} not found")
				
				return
			
			output = self.params["map_Kd"]

			# log.log(f"Exporting diffuse to {output}")
			
			data = self.getBestTex(ddsx).getDDS()

			self.__saveTexture__(data, outpath + "/" + output)
		
		def __exportNormal__(self, outpath:str):
			name = self.material.normal.split("*")[0]

			ddsx:list[DDSx] = AssetCacher.getCachedAsset(DDSx, name)

			if not ddsx:
				return
			
			output = self.params["map_bump"]

			# log.log(f"Exporting bumpmap to {output}")
			
			data = self.getBestTex(ddsx).getDDS()

			self.__saveTexture__(data, outpath + "/" + output)

		def exportTextures(self, outpath:str = getcwd()):
			if not path.exists(f"{outpath}/textures"):
				mkdir(f"{outpath}/textures")
			
			if "map_Kd" in self.params:
				self.__exportDiffuse__(outpath)
			
			if "map_bump" in self.params:
				self.__exportNormal__(outpath)
			

	def __init__(self, materials:list[MaterialData]):
		self.__mats = tuple(self.Material(material) for material in SafeIter(self, materials))
	
	def getMTL(self):
		mtl = ""

		for v in SafeIter(self, self.__mats):
			mtl += f"{v}"

		return mtl
	
	def exportTextures(self, outpath:str = getcwd()):
		log.log("Exporting MTL textures")
		log.addLevel()

		for mat in SafeIter(self, self.__mats):
			log.log(f"Exporting textures from {mat.material.getName()}")
			log.addLevel()

			mat.exportTextures(outpath)

			log.subLevel()
		
		log.subLevel()

def computeMaterialNames(mats:list[MaterialData], parent:Terminable = None):
	log.log("Computing material names")
	log.addLevel()
	
	enumerateIt = (lambda x: SafeEnumerate(parent, x)) if parent is not None else (lambda x: enumerate(x))
	iterIt = (lambda x: SafeIter(parent, x)) if parent is not None else (lambda x: iter(x))
	
	for k, mat in enumerateIt(mats):
		log.log(f"Materials #{k}: {mat.getName()}")

		cnt = 1


		for mat2 in iterIt(mats):
			if mat is mat2:
				continue
			
			if mat.getName() == mat2.getName():
				if mat == mat2:
					continue
				else:
					mat2.setName(mat2.getName() + f"_{cnt}")
					cnt += 1

	log.subLevel()

def generateMaterialData(textures:list[str], mvdMats:list[MatVData.Material], parent:Terminable = None):
	materials:list[MaterialData] = []

	iterator = (lambda x: SafeEnumerate(parent, x)) if parent is not None else (lambda x: enumerate(x))

	for k, v in iterator(mvdMats):
		mat = MaterialData()

		mat.cls = v.shaderClass
		mat.par = ""
		
		for texId, texKey in iterator(v.textures):
			if texKey == 0xFFFFFFFF:
				continue
			
			mat.addTexSlot(f"t{texId}", textures[texKey])

		materials.append(mat)
	
	return materials

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