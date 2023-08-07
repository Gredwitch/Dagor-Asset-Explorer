import sys
from os import path, getcwd

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import util.log as log
# from math import *
from struct import unpack
from util.fileread import *
from util.terminable import SafeRange, Terminable, FilePathable, SafeIter, SafeEnumerate
from util.enums import *
from parse.material import MaterialData
from abc import ABC, abstractmethod

# from misc import pprint, loadDLL
# from assetcacher import ASSETCACHER
# import pygltflibo
# from traceback import print_exc as trace


class ShaderMesh(Terminable):
	class Elem:
		def __repr__(self):
			return f"<ShaderMesh::RElem e={self.ShaderElementPtr} mat={self.mat} vData={self.vData} vdOrderIndex={self.vdOrderIndex} startV={self.startV} numV={self.numV} startI={self.startI} numFace={self.numFace} baseVertex={self.baseVertex}>"
		
		def __init__(self, file:BinFile):
			self.ShaderElementPtr = readLong(file)
			self.mat = readLong(file)
			self.vData = readLong(file)

			self.vdOrderIndex = readInt(file)
			self.startV = readInt(file)
			self.numV = readInt(file)
			self.startI = readInt(file)
			self.numFace = readInt(file)
			self.baseVertex = readInt(file)

			log.log(self)

	def __repr__(self):
		return f"stage={self.stageEndElemIdx} maxMatPass={self._deprecatedMaxMatPass} resv={self._resv} cnt={self.cnt}"

	def __init__(self, file:BinFile):
		ofs = readInt(file)
		cnt = readInt(file)

		file.seek(8, 1)

		self.stageEndElemIdx = list(readShort(file) for _ in SafeRange(self, 8))
		
		self._deprecatedMaxMatPass = readEx(4, file, True)
		self._resv = readInt(file)

		if self._deprecatedMaxMatPass < 0: # ShaderMesh::patchData
			self._deprecatedMaxMatPass &= 0x7FFFFFFF
		elif self.stageEndElemIdx[2] != 0:
			old = self.stageEndElemIdx[2]

			self.stageEndElemIdx[0] = cnt
			self.stageEndElemIdx[1] = cnt
			self.stageEndElemIdx[2] = cnt
			self.stageEndElemIdx[3] = cnt

			cnt += old

			self.stageEndElemIdx[4] = cnt
			self.stageEndElemIdx[5] = cnt
			self.stageEndElemIdx[6] = cnt
			self.stageEndElemIdx[7] = cnt
		
		self.cnt = cnt

		log.log(self)
		log.addLevel()

		self.elems = tuple(self.Elem(file) for i in SafeRange(self, cnt))
		
		log.subLevel()

class InstShaderMeshResource(Terminable):
	def __init__(self, file:BinFile):
		sz = readInt(file)
		resv = readInt(file)

		assert resv == 0

		self.shaderMesh = self.setSubTask(ShaderMesh(file.readBlock(sz)))

		self.clearSubTask()
	

class MatVData(Terminable, FilePathable): # stores material and vertex data :D	
	def __init__(self, 
	      		file:BinFile, 
				name:str = None, 
				texCnt:int = 0, 
				matCnt:int = 0, 
				filePath:str = None,
				textures:list[str] = None,
				flag:int = MVD_NORMAL):
		FilePathable.__init__(self, filePath, name, file.getSize())

		self.__texCnt = texCnt
		self.__matCnt = matCnt
		self.__file = file
		self.__flag = flag
		self.__textures = textures

		self.__dataComputed = False

	def __repr__(self):
		return f"<MVD {self.name} texCnt={self.__texCnt} matCnt={self.__matCnt} computed={self.__dataComputed}>"

	def save(self, output:str = getcwd()):
		binData = self.__file.read()

		output = path.normpath(f"{output}\\{self.name}.mvd")

		file = open(output, "wb")

		file.write(binData)

		file.close()

		return output

	def computeData(self):
		if self.__dataComputed:
			return

		log.log("Computing MatVData")
		log.addLevel()

		file = self.__file

		file.seek(0, 0)

		matOfs = readInt(file)
		matCnt = readInt(file)

		self.__hasMaterials = matOfs != 0 and matCnt != 0 

		file.seek(8, 1)

		gvdOfs = readInt(file)
		gvdCnt = readInt(file)

		self.__computeMaterials__(matCnt, matOfs)
		self.__computeGVData__(gvdCnt, gvdOfs)

		log.subLevel()

		self.__dataComputed = True
	

	#-------------------------------------------------
	#
	#
	#	Material handling (v1 mvd only?)
	#
	#

	class Material:
		def __repr__(self):
			return f"<MVDMaterial cls={self.shaderClass}>"
		
		def __init__(self):
			self.shaderClass:str = None
			self.textures:tuple[int] = None # 16 elements
			self.data:BinBlock = None # 176 bytes big
			self.diff:tuple[float] = None # 16 elements
			self.amb:tuple[float] = None # 16 elements
			self.spec:tuple[float] = None # 16 elements
			self.emis:tuple[float] = None # 16 elements


	def __processMaterial__(self, ofs:int, idx:int):
		file = self.__file

		file.seek(ofs + idx * 0xA8, 0)

		log.log(f"Material {idx} @ {file.tell()}:")
		log.addLevel()

		diff = unpack("4f", file.read(0x10))
		amb = unpack("4f", file.read(0x10))
		emis = unpack("4f", file.read(0x10))
		spec = unpack("4f", file.read(0x10))

		unknown = readInt(file)

		log.log(f"unknown         = {hex(unknown)}")

		shaderOfs = readInt(file)
		
		file.seek(8, 1)

		textureIds = unpack("I" * 16, file.read(0x40))

		dataOfs = readInt(file)
		unknown2 = readInt(file)

		file.seek(8, 1)

		flags = readLong(file)

		log.log(f"flags           = {hex(flags)}")

		file.seek(shaderOfs, 0)

		shader = b""

		while True:
			b = file.read(1)

			if b == b"\x00":
				break
			
			shader += b

		shader = shader.decode("utf-8")

		log.subLevel()

		mat = MaterialData()
		mat.cls = shader

		# mat.data = BinBlock(file, dataOfs, 0xB0)
		mat.diff = diff
		mat.amb = amb
		mat.spec = spec
		mat.emis = emis
		mat.par = ""

		for slotId, texId in SafeEnumerate(self, textureIds):
			if slotId > 10:
				break

			if texId == 0xFFFFFFFF:
				continue

			if self.__textures is None:
				tex = str(texId)
			else:
				tex = self.__textures[texId]

			mat.addTexSlot(f"t{slotId}", tex)

		return mat

	def __computeMaterials__(self, cnt:int, ofs:int):
		log.log(f"Computing {cnt} materials @ {ofs}")
		log.addLevel()
		# skip if self.__textures is None?
		self.__materials = tuple(self.__processMaterial__(ofs, i) for i in SafeRange(self, cnt))

		log.subLevel()

	def getMaterials(self):
		return self.__materials

	#-------------------------------------------------
	#
	#
	#	Global vertex data handling
	#
	#

	class GlobalVertexData:
		def __init__(self, file:BinBlock, absOfs:int, idx:int, flag:int):
			self.__ofs = absOfs + idx * 0x20

			self.__idx = idx

			self.__vCnt = readInt(file)

			self.__vStride = readByte(file)
			self.__iPackedSz = readEx(3, file)

			self.__iSz = readInt(file)
			
			self.__flags = readShort(file)
			self.__bf_14 = readShort(file)

			self.__iCnt = readInt(file)

			self.__storageFormat = readInt(file) + flag * 10


			# 8 null-bytes remainder

			log.log(f"{self}")

		def __repr__(self):
			return f"<GVData {self.__idx} @ {self.__ofs}: vCnt={self.__vCnt} vStride={self.__vStride} iPackedSz={self.__iPackedSz} iSz={self.__iSz} flags={hex(self.__flags)} bf_14={hex(self.__bf_14)} iCnt={self.__iCnt} storageFormat={self.__storageFormat}>"
	
		def getStorageFormat(self):
			return self.__storageFormat

		def getVertexBlockSz(self):
			return self.__vCnt * self.__vStride
		
		def getFullVertexDataSz(self):
			if self.__iPackedSz == 0:
				return self.getVertexBlockSz() + self.__iSz
			else:
				return self.getVertexBlockSz() + self.__iPackedSz

		def getVertexCnt(self):
			return self.__vCnt

		def getVertexStride(self):
			return self.__vStride

		def getPackedIndicesSz(self):
			return self.__iPackedSz
		
		def getIndicesSz(self):
			return self.__iSz

		@property
		def idx(self):
			return self.__idx


		@property
		def flags(self):
			return self.__flags
		@property
		def bf_14(self):
			return self.__bf_14


	def __computeGVData__(self, cnt:int, ofs:int):
		file = self.__file
		
		file.seek(ofs, 0)

		log.log(f"Computing {cnt} global vertex data @ {ofs}")
		log.addLevel()

		self.__gvdata = tuple(self.GlobalVertexData(file.readBlock(0x20), ofs, i, self.__flag) for i in SafeRange(self, cnt))

		self.__vdStartOfs = ofs + cnt * 0x20

		log.subLevel()


	#-------------------------------------------------
	#
	#
	#	Vertex data decoding
	#
	#
	
	class VertexData(Terminable):
		class __decodeIndexSequence__(): # i haven't cleaned this up yet and i don't think i ever will, who cares anyway
			class __byteArrayGen__():
				def __init__(self, parent:Terminable, data:bytes, offset:int, size:int):
					self.parent = parent
					self.data = data
					self.offset = offset
					self.size = size
					self.done = False

				def __iter__(self):
					return self

				def __next__(self):
					if self.parent.shouldTerminate:
						raise StopIteration()
					else:
						return self.next()

				def next(self):
					if not self.done and self.offset < self.size:
						b = ord(self.data[self.offset:self.offset + 1])

						self.offset += 1
						self.done = (b & 0x80) == 0

						return b
					else:
						raise StopIteration()

			def __init__(self, data:bytes, size:int, mvd):
				self.data = data
				self.size = size
				self.offset = 0
				self.buffer = [0, 0]
				self.count = 0
				# self.lastCur = None
				self.fucking = False
				self.mvd:MatVData = mvd

			def __iter__(self):
				return self

			def __next__(self):
				return self.next()

			def decodeLebOld(self):
				a = bytearray(x for x in self.__byteArrayGen__(self.mvd, self.data, self.offset, self.size))
				sz = len(a)
				self.offset += sz

				decoded = 0

				for i in SafeRange(self.mvd, sz):
					decoded = decoded + ((a[i] & 0x7f) << (i * 7)) # leb128 decoding

				return decoded

			def decodeLeb(self):
				v14 = self.data[self.offset]
				self.offset += 1

				decoded = v14
				if ( v14 >= 0x80 ):
					decoded = v14 & 0x7F
					v16 = 7

					for _ in SafeRange(self.mvd, 4):
						v18 = self.data[self.offset]
						self.offset += 1
						v19 = (v18 & 0x7F) << v16
						v16 += 7
						decoded |= v19
						if ( v18 < 0x80 ):
							break
						
				return decoded

			def getIndex(self):
				decoded = self.decodeLeb()

				current = decoded & 1 # meshopt

				d = (decoded >> 2) ^ -((decoded & 2) != 0) # stolen from gaijin
				index = self.buffer[current] + d

				# print(self.count, d, index, self.buffer)

				# self.count += 1

				# if self.count < 135829 and not self.fucking:
				#	 self.fucking = True

				#	 while self.count < 135829:
				#		 self.getIndex()

				#	 return self.getIndex()
				# elif self.count >= 135829:
					# print(self.count, index, self.buffer, current == 1)

					# self.offset = self.size


				self.buffer[current] = index




				return index

			def getValidIndex(self):
				if self.offset >= self.size or self.mvd.shouldTerminate:
					raise StopIteration()

				return self.getIndex()

			def next(self):
				a = self.getValidIndex()

				if a == None:
					return self.next()

				b = self.getValidIndex()

				if b == None:
					return self.next()

				c = self.getValidIndex()

				if c == None:
					return self.next()

				return (a,b,c)

		def __repr__(self):
			return f"<VertexData {self.__gvData.idx} vCnt={self.__gvData.getVertexCnt()}>"

		def __init__(self, file:BinBlock, gvData):
			self.__verts:tuple[tuple(float, float, float)] = None
			self.__UVs:tuple[tuple(float, float)] = None
			self.__faces:tuple[tuple(int, int, int)] = None
			self.__unimplemented = False

			gvData:MatVData.GlobalVertexData = gvData

			self.__gvData = gvData

			vDataSz = gvData.getVertexBlockSz()

			log.addLevel()

			self.__processVertices__(file.readBlock(vDataSz))
			self.__processFaces__(file.readBlock(file.getSize() - vDataSz))

			log.subLevel()
		
		@property
		def globalVertexData(self):
			return self.__gvData
		
		class PARSECLASS(ABC):
			@abstractmethod
			def read(self, file:BinFile):
				...

		class VERTEX(PARSECLASS):
			...
		
		class UV(PARSECLASS):
			...

		class SHORT_VERTEX(VERTEX):
			def read(self, file:BinFile):
				return [readSignedShort(file) / 32768, readSignedShort(file) / 32768, readSignedShort(file) / 32768]

		class FLOAT_VERTEX(VERTEX):
			def read(self, file:BinFile):
				return list(unpack("fff", file.read(12)))

		class NO_UV(UV):
			def read(self, file:BinFile):
				return (0, 0)

		class SHORT_UV(UV):
			def read(self, file:BinFile):
				return (readSignedShort(file) / 4096, 1 + (-readSignedShort(file) / 4096))

		class FLOAT_UV(UV):
			def read(self, file:BinFile):
				uv = unpack("ff", file.read(8))

				return (uv[0], -uv[1])

		class PADDING(PARSECLASS):
			def __init__(self, sz:int):
				self.sz = sz
			
			def read(self, file:BinFile):
				file.seek(self.sz, 1)


		FORMATS:dict[int, dict[int, tuple[PARSECLASS]]] = {
			1:{
				12:(FLOAT_VERTEX(), NO_UV())
			  },
			2:{
				12:(SHORT_VERTEX(), PADDING(2), SHORT_UV()),
				16:(FLOAT_VERTEX(), SHORT_UV())
			  },
			3:{
				16:(SHORT_VERTEX(), PADDING(6), SHORT_UV()),
				20:(FLOAT_VERTEX(), PADDING(4), SHORT_UV()),
				24:(FLOAT_VERTEX(), PADDING(4), FLOAT_UV()),
			  },
			4:{
				20:(PADDING(4), SHORT_VERTEX(), PADDING(6), SHORT_UV()),
				# 24: # tree_02_dstr (wt)
				28:(FLOAT_VERTEX(), PADDING(4), FLOAT_UV(), PADDING(4)),
			  },
			5:{
				24:(SHORT_UV(), SHORT_VERTEX(), PADDING(14)),
				28:(FLOAT_VERTEX(), PADDING(12), SHORT_UV()),
				36:(FLOAT_VERTEX(), PADDING(4), FLOAT_UV(), PADDING(12))
			  },
			6:{
				32:(FLOAT_VERTEX(), PADDING(4), SHORT_UV(), PADDING(12)) # UVs?
			  },
			
			13:{
				16:(SHORT_VERTEX(), PADDING(6), SHORT_UV()),
			  },
			15:{
				# 24:(PADDING(8), SHORT_VERTEX(), PADDING(6), SHORT_UV()),
			 	28:(FLOAT_VERTEX(), PADDING(8), SHORT_UV(), PADDING(4)),
				32:(FLOAT_VERTEX(), PADDING(20), NO_UV())
			  },
			16:{
				28:(PADDING(12), SHORT_VERTEX(), PADDING(6), SHORT_UV()),
			 	32:(PADDING(4), FLOAT_VERTEX(), PADDING(4), SHORT_UV(), PADDING(8)),
				36:(FLOAT_VERTEX(), PADDING(14), SHORT_UV(), PADDING(6))
			  },
			17:{
				32:(NO_UV(), PADDING(8), SHORT_VERTEX(), PADDING(18)),
				36:(FLOAT_VERTEX(), PADDING(8), SHORT_UV(), PADDING(12))
			  },
			25:{
				24:(SHORT_VERTEX(), PADDING(6), SHORT_UV(), PADDING(8)),
				28:(FLOAT_VERTEX(), PADDING(4), SHORT_UV(), PADDING(8)),
				32:(FLOAT_VERTEX(), PADDING(4), FLOAT_UV(), PADDING(8))
			  },
			26:{
				32:(PADDING(4), FLOAT_VERTEX(), PADDING(4), SHORT_UV(), PADDING(8))
			},
			27:{
				36:(FLOAT_VERTEX(), PADDING(4), SHORT_UV(), PADDING(16))
			},
		}

		def getParser(self, format:int, vStride:int):
			if format in self.FORMATS:
				return self.FORMATS[format].get(vStride)
			else:
				return None

		def __processVertices__(self, file:BinBlock):
			format = self.__gvData.getStorageFormat()
			vStride = self.__gvData.getVertexStride()
			vCnt = self.__gvData.getVertexCnt()

			verts:list[list[float, float, float]] = []
			UVs:list[list[float, float]] = []

			parser = self.getParser(format, vStride)

			if parser is None:
				raise Exception(f"Unimplemented storage format {format}-{vStride}")
			else:
				log.log(f"Processing {vCnt} vertices vFormat={format} vStride={vStride}")

				for _ in SafeRange(self, vCnt):
					for parseClass in SafeIter(self, parser):
						parseClass:MatVData.VertexData.PARSECLASS

						if isinstance(parseClass, MatVData.VertexData.PADDING):
							parseClass.read(file)
						elif isinstance(parseClass, MatVData.VertexData.VERTEX):
							verts.append(parseClass.read(file))
						elif isinstance(parseClass, MatVData.VertexData.UV):
							UVs.append(parseClass.read(file))

			self.__verts = verts
			self.__UVs = UVs
			
		def __processFaces__(self, file:BinBlock):
			if self.__unimplemented:
				log.log("Unimplemented vertex format, skipping indice buffer", LOG_WARN)
				
				return
			
			log.log(f"Processing faces @ {self.__gvData.getVertexBlockSz()}")
			log.addLevel()

			pSz = self.__gvData.getPackedIndicesSz()
			sz = self.__gvData.getIndicesSz()

			if pSz == 0:
				log.log("Processing unpacked faces")

				# file.seek(1, 1)

				count = (sz // 6)  - sz % 6

				faces = tuple(unpack("HHH", file.read(6)) for i in SafeRange(self, count))

			else:
				log.log("Processing packed faces")

				file.seek(1, 1)

				# encodedSize = psize - 0x5
				# faces = tuple(f for f in self.indexBuffer(file.read(encodedSize), encodedSize, self))

				# meshopt = loadDLL("gdae_native.dll")
				meshopt = None

				if meshopt == None:
					# log.log("Failed to load gdae_native.dll: some faces may be fucked", 1)

					encodedSize = pSz - 0x5
					faces = tuple(f for f in self.__decodeIndexSequence__(file.read(encodedSize), encodedSize, self))
				else:
					...
					"""
					# file.seek(1, 1)

					dat = file.read(pSz)

					indexCount = sz // 2
					destination = create_string_buffer(sz * 2)

					if meshopt.meshopt_decodeIndexSequence(destination, indexCount, sz, dat, sz) != -3:
						raise Exception("Meshopt error")

					f = open("faces.dat","wb")
					f.write(destination.raw)
					f.close()

					faces = tuple(
						unpack("<III", destination.raw[i * 12:(i + 1) * 12]) for i in range(indexCount // 3)
					)"""

			log.log(f"Processed {len(faces)} faces")
			log.subLevel()

			self.__faces = faces

		def getVertices(self):
			return self.__verts
		
		def getUVs(self):
			return self.__UVs
		
		def getFaces(self):
			return self.__faces

		def getObj(self):
			verts, UVs, faces = self.__verts, self.__UVs, self.__faces

			if not verts:
				raise NotImplementedError("Can't get an obj out of an unimplemented model format")

			obj = ""

			log.log(f"Exporting {len(verts)} vertices")

			for v in SafeIter(self, verts):
				obj += f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n"
			
			log.log(f"Exporting {len(UVs)} UVs")

			for v in SafeIter(self, UVs):
				obj += f"vt {v[0]:.4f} {v[1]:.4f}\n"

			log.log(f"Exporting {len(faces)} faces")
			
			for face in SafeIter(self, faces):
				f = ""

				for idx in SafeIter(self, face):
					idx += 1

					f += f" {idx}/{idx}"
				
				if f == "":
					continue

				
				obj += f"f{f}\n"
			
			return obj

	def getVDCount(self):
		return len(self.__gvdata)
	
	def getVertexDataByLOD(self, lodId:int):
		if not self.__dataComputed:
			self.computeData()
		
		vDataList:list[MatVData.VertexData] = []
		
		for k, gvData in SafeEnumerate(self, self.__gvdata):
			gvData:MatVData.GlobalVertexData

			vDlodId = (gvData.flags & 0xF000) >> 12

			if vDlodId == lodId:
				vDataList.append(self.getVertexData(k))
			
		return vDataList



	def getVertexDataOffset(self, idx:int):
		if not self.__dataComputed:
			self.computeData()
		
		ofs = self.__vdStartOfs

		for i in SafeRange(self, idx):
			gvData = self.__gvdata[i]
			ofs += gvData.getFullVertexDataSz()

		return ofs
	
	def getGlobalVertexData(self, idx):
		return self.__gvdata[idx]

	def getVertexData(self, idx:int):
		if not self.__dataComputed:
			self.computeData()
		
		vdCnt = len(self.__gvdata)

		if idx < 0 or idx > vdCnt:
			raise ValueError(f"Impossible vData ID {idx} (vdCnt = {vdCnt})")
		
		file = self.__file
		gvData = self.__gvdata[idx]

		file.seek(self.__vdStartOfs, 0)

		for i in SafeRange(self, 0, idx):
			file.seek(self.__gvdata[i].getFullVertexDataSz(), 1)
		
		sz = gvData.getFullVertexDataSz()

		log.log(f"Retrieving vertex data {idx} @ {file.tell()} sz={sz}")

		return self.VertexData(file.readBlock(sz), gvData)

	def quickExportVDataToObj(self, idx:int, suffix:str = "", outdir:str = None):
		log.log(f"Quick exporting {idx} as OBJ")
		log.addLevel()

		fileName = f"{self.name}_{idx}{suffix}.obj"

		if outdir is not None:
			fileName = path.join(outdir, fileName)

		obj = self.getVertexData(idx).getObj()

		file = open(fileName, "w")
		file.write(obj)
		file.close()

		log.subLevel()

		log.log(f"Wrote {len(obj)} to {fileName}")

	@property
	def hasMaterials(self):
		return self.__hasMaterials

if __name__ == "__main__":
	from util.decompression import CompressedData
	file = BinFile("pilot_china1.rrd")
	file.seek(1512, 0)

	mvd = MatVData(CompressedData(file).decompressToBin(), filePath = "pilot_china1.rrd")
	mvd.quickExportVDataToObj(1)