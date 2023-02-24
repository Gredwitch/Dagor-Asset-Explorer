
from os import path, getcwd
from struct import unpack


# from ctypes import create_string_buffer

from fileread import *
from terminable import SafeRange, Terminable, Exportable
from math import * #acos, degrees
from enums import *
import log

# from misc import pprint, loadDLL
# from assetcacher import ASSETCACHER
# import pygltflibo
# from traceback import print_exc as trace



class MaterialData:
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

class ShaderMesh:
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

	def __init__(self, file:BinFile):
		ofs = readInt(file)
		cnt = readInt(file)

		file.seek(8, 1)

		self.stageEndElemIdx = list(readShort(file) for i in range(8))
		
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

		log.log(f"stage={self.stageEndElemIdx} maxMatPass={self._deprecatedMaxMatPass} resv={self._resv} cnt={cnt}")
		log.addLevel()

		self.elems = tuple(self.Elem(file) for i in range(cnt))
		
		log.subLevel()

class InstShaderMeshResource:
	def __init__(self, file:BinFile):
		sz = readInt(file)
		resv = readInt(file)

		assert resv == 0

		self.shaderMesh = ShaderMesh(file.readBlock(sz))
	

class MatVData(Exportable): # stores material and vertex data :D	
	def __init__(self, file:BinFile, name:str = None, texCnt:int = 0, matCnt:int = 0, filePath:str = None):
		if filePath: # filepath is used for debugging purposes only when loading an MVD individually - in practice it is never used
			self.setFilePath(filePath)

			
			self.setName(path.splitext(path.basename(filePath))[0] if name is None else name)
		else:
			self.setName(name)
		
		self.setSize(file.getSize())

		self.__texCnt = texCnt
		self.__matCnt = matCnt
		self.__file = file

		self.__dataComputed = False
		self.isValid = True

	def __repr__(self):
		return f"<MVD {self.getName()} texCnt={self.__texCnt} matCnt={self.__matCnt} computed={self.__dataComputed}>"

	def save(self, output:str = getcwd()):
		binData = self.__file.read()

		output = path.normpath(f"{output}\\{self.getName()}.mvd")

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
			self.floatArray:tuple[float] = None # 16 elements


	def __processMaterial__(self, mat:Material, ofs:int, idx:int):
		file = self.__file

		file.seek(ofs + idx * 0xA8, 0)

		log.log(f"Material {idx} @ {file.tell()}:")
		log.addLevel()

		floatArray = unpack("f" * 16, file.read(0x40))

		log.log(f"float array     = {floatArray}")

		unknown = readInt(file)

		log.log(f"unknown         = {hex(unknown)}")

		shaderOfs = readInt(file)
		
		file.seek(8, 1)

		textureIDs = unpack("I" * 16, file.read(0x40))

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

		log.log(f"shader          = {shader}")

		log.subLevel()

		mat.shaderClass = shader
		mat.textures = textureIDs
		mat.data = BinBlock(file, dataOfs, 0xB0)
		mat.floatArray = floatArray

		return mat

	def __computeMaterials__(self, cnt:int, ofs:int):
		log.log(f"Computing {cnt} materials @ {ofs}")
		log.addLevel()

		self.__materials = tuple(self.__processMaterial__(self.Material(), ofs, i) for i in range(cnt))

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
		def __init__(self, file:BinBlock, absOfs:int, idx:int):
			self.__ofs = absOfs + idx * 0x20

			self.__idx = idx

			self.__vCnt = readInt(file)

			self.__vStride = readByte(file)
			self.__iPackedSz = readEx(3, file)

			self.__iSz = readInt(file)
			
			self.__flags = readShort(file)
			self.__bf_14 = readShort(file)

			self.__iCnt = readInt(file)

			self.__storageFormat = readInt(file)

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


	def __computeGVData__(self, cnt:int, ofs:int):
		file = self.__file
		
		file.seek(ofs, 0)

		log.log(f"Computing {cnt} global vertex data @ {ofs}")
		log.addLevel()

		self.__gvdata = tuple(self.GlobalVertexData(file.readBlock(0x20), ofs, i) for i in range(cnt))

		self.__vdStartOfs = ofs + cnt * 0x20

		log.subLevel()


	#-------------------------------------------------
	#
	#
	#	Vertex data decoding
	#
	#
	
	class VertexData(Terminable):
		class __decodeIndexSequence__(object): # i haven't cleaned this up yet and i don't think i ever will, who cares anyway
			class __byteArrayGen__(object):
				def __init__(self,data:bytes,offset:int,size:int):
					self.data = data
					self.offset = offset
					self.size = size
					self.done = False

				def __iter__(self):
					return self

				def __next__(self):
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
				self.mvd = mvd

			def __iter__(self):
				return self

			def __next__(self):
				return self.next()

			def decodeLebOld(self):
				a = bytearray(x for x in self.__byteArrayGen__(self.data,self.offset,self.size))
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

					for i in range(4):
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

				if d == -self.buffer[current] and d < -1000:
					log.log("Potential fucked faces detected", 2)
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
				if self.offset >= self.size or self.mvd.shouldTerminate():
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
		
		def __unpackShortUV__(self, file:BinFile):
			return (readSignedShort(file) / 4096, 1 + (-readSignedShort(file) / 4096))

		def __unpackUV__(self, file:BinFile):
			uv = unpack("ff",file.read(8))

			return (uv[0], -uv[1])

		def __unpackVertex__(self, file:BinFile):
			return list(unpack("fff", file.read(12)))

		def __unpackShortVertex__(self, file:BinFile):
			return [readSignedShort(file) / 32768, readSignedShort(file) / 32768, readSignedShort(file) / 32768]
			# return (-readSignedShort(file),readSignedShort(file),readSignedShort(file))
		


		def __processVertices__(self, file:BinBlock):
			format = self.__gvData.getStorageFormat()
			vStride = self.__gvData.getVertexStride()
			vCnt = self.__gvData.getVertexCnt()

			shortVerts = False
			verts = []
			UVs = []

			log.log(f"Processing {vCnt} vertices vFormat={format} vStride={vStride}")

			if format == 3:
				stride = vStride - 20

				if vStride == 16:
					shortVerts = True

					for i in SafeRange(self, vCnt):
						verts.append(self.__unpackShortVertex__(file))

						file.seek(6,1)

						UVs.append(self.__unpackShortUV__(file))
				elif vStride == 24:
					# { float[3] Coords, byte[4] Unknown, float[2] UVs }

					bigUVs = True

					for i in SafeRange(self, vCnt):
						verts.append(self.__unpackVertex__(file))

						file.seek(4,1)

						UVs.append(self.__unpackUV__(file)) # not working!!
				elif vStride >= 20:
					for i in SafeRange(self, vCnt):
						verts.append(self.__unpackVertex__(file))

						file.seek(4,1)

						UVs.append(self.__unpackShortUV__(file))

						file.seek(max(0, stride), 1)
				elif vStride == 12:
					shortVerts = True

					for i in SafeRange(self, vCnt):
						UVs.append(self.__unpackShortUV__(file))

						verts.append(self.__unpackShortVertex__(file))

						file.seek(2,1)
				else:
					log.log(f"Unimplemented vertex stride {vStride} for storage format {format}", LOG_ERROR)

					self.__unimplemented = True
					file.seek(vCnt * vStride,1)

			elif format == 4:
				stride = vStride - 20

				if vStride == 20:
					# { byte[4] Unknown, short[3] Coords, byte[6] Unknown, short[2] UVs }

					shortVerts = True

					for i in SafeRange(self, vCnt):
						file.seek(4,1)

						verts.append(self.__unpackShortVertex__(file))

						file.seek(6,1)

						UVs.append(self.__unpackShortUV__(file))
				elif vStride == 28:
					bigUVs = True

					for i in SafeRange(self, vCnt):
						verts.append(self.__unpackVertex__(file))

						file.seek(4,1) # flags?

						UVs.append(self.__unpackUV__(file))

						file.seek(4,1) # idk
				else:
					log.log(f"Unimplemented vertex stride {vStride} for storage format {format}", LOG_ERROR)

					self.__unimplemented = True
					file.seek(vCnt * vStride,1)
			elif format == 2:
				# if vStride == 16:
				# 	stride = vStride - 16

				# 	for i in SafeRange(self, vCnt):
				# 		verts.append(self.__unpackVertex__(file))

				# 		UVs.append(self.__unpackShortUV__(file))

				# 		file.seek(stride, 1)
				# elif vStride == 12:
				stride = vStride - 10
				shortVerts = True

				for i in SafeRange(self, vCnt):
					verts.append(self.__unpackShortVertex__(file))

					UVs.append(self.__unpackShortUV__(file))

					file.seek(stride, 1)
				# else:
				# 	log.log(f"Unimplemented vertex stride {vStride} for storage format {format}", LOG_ERROR)

					# self.__unimplemented = True
			elif format == 5:
				if vStride == 24:
					shortVerts = True
					
					for i in SafeRange(self, vCnt):
						file.seek(8, 1)

						verts.append(self.__unpackShortVertex__(file))

						file.seek(6, 1)

						UVs.append(self.__unpackShortUV__(file))
				elif vStride == 28:
					for i in SafeRange(self, vCnt):
						verts.append(self.__unpackVertex__(file))

						file.seek(12, 1)

						UVs.append(self.__unpackShortUV__(file))
				elif vStride == 36:
					for i in SafeRange(self, vCnt):
						verts.append(self.__unpackVertex__(file))

						file.seek(4, 1)

						UVs.append(self.__unpackUV__(file))

						file.seek(12, 1)
				else:
					log.log(f"Unimplemented vertex stride {vStride} for storage format {format}", LOG_ERROR)

					self.__unimplemented = True
			elif format == 1:
				if vStride == 8:
					shortVerts = True

					for i in SafeRange(self, vCnt):
						verts.append(self.__unpackShortVertex__(file))

						file.seek(2,1)

						# UVs.append(self.__unpackShortUV__(file))
						bigUVs = True # work around to bypass line "if not bigUVs"
				else:
					log.log(f"Unimplemented vertex stride {vStride} for storage format {format}", LOG_ERROR)
			# elif format == 6:
			# 	if vStride == 28:
			# 		for i in SafeRange(self, vCnt):
			# 			verts.append(self.__unpackVertex__(file))

			# 			file.seek(vStride - 3 * 4, 1)
			# 	else:
			# 		log.log(f"Unimplemented vertex stride {vStride} for storage format {format}", LOG_ERROR)
				
			else:
				log.log(f"Unimplemented storage format {format}", LOG_ERROR)

				self.__unimplemented = True
			
			if shortVerts:
				log.log("Short vertex format warning !", LOG_WARN)
				# log.log("Processing short verts")

				# maxVx = max(map(lambda pair: abs(pair[0]), verts))
				# maxVy = max(map(lambda pair: abs(pair[1]), verts))
				# maxVz = max(map(lambda pair: abs(pair[2]), verts))
				# maxV = max(maxVx, maxVy, maxVz)
				# print(maxV)

				# if maxV == 0:
				# 	getV = lambda c: 0
				# else:
				# 	getV = lambda c: c / maxV

				# verts = tuple([getV(vert[0]), getV(vert[1]), getV(vert[2])] for vert in verts)
			
			# if shortVerts: # old
			# 	log.log("Processing short verts")

			# 	maxVx = max(map(lambda pair: abs(pair[0]), verts))
			# 	maxVy = max(map(lambda pair: abs(pair[1]), verts))
			# 	maxVz = max(map(lambda pair: abs(pair[2]), verts))
			# 	maxV = max(maxVx,maxVy,maxVz)
			# 	print(maxV)
			# 	if maxV == 0:
			# 		getV = lambda c: 0
			# 	else:
			# 		getV = lambda c: c / maxV

			# 	verts = tuple((getV(vert[0]), getV(vert[1]), getV(vert[2])) for vert in verts)

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

			for v in verts:
				obj += f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n"
			
			log.log(f"Exporting {len(UVs)} UVs")

			for v in UVs:
				obj += f"vt {v[0]:.4f} {v[1]:.4f}\n"

			log.log(f"Exporting {len(faces)} faces")
			
			for face in (faces):
				f = ""

				for idx in face:
					idx += 1

					f += f" {idx}/{idx}"
				
				if f == "":
					continue

				
				obj += f"f{f}\n"
			
			return obj

	def getVDCount(self):
		return len(self.__gvdata)

	def getVertexData(self, idx:int):
		if not self.__dataComputed:
			self.computeData()
		
		vdCnt = len(self.__gvdata)

		if idx < 0 or idx > vdCnt:
			raise ValueError(f"Impossible vData ID {idx} (vdCnt = {vdCnt})")
		
		file = self.__file
		gvData = self.__gvdata[idx]

		file.seek(self.__vdStartOfs, 0)

		for i in range(0, idx):
			file.seek(self.__gvdata[i].getFullVertexDataSz(), 1)
		
		sz = gvData.getFullVertexDataSz()

		log.log(f"Retrieving vertex data {idx} @ {file.tell()} sz={sz}")

		return self.VertexData(file.readBlock(sz), gvData)

	def quickExportVDataToObj(self, idx:int):
		log.log(f"Quick exporting {idx} as OBJ")
		log.addLevel()

		fileName = f"{self.getName()}_{idx}.obj"
		obj = self.getVertexData(idx).getObj()

		file = open(fileName, "w")
		file.write(obj)
		file.close()

		log.subLevel()

		log.log(f"Wrote {len(obj)} to {fileName}")


if __name__ == "__main__":
	from decompression import CompressedData
	file = BinFile("pilot_china1.rrd")
	file.seek(1512, 0)

	mvd = MatVData(CompressedData(file).decompressToBin(), filePath = "pilot_china1.rrd")
	mvd.quickExportVDataToObj(1)