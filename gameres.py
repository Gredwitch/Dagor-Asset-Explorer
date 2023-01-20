
from fileread import *
from struct import unpack
import log
from enums import *
from decompression import zstdDecompress, CompressedData
from datablock import *
from os import path, getcwd
from terminable import Exportable, SafeRange
from struct import pack
from mesh import MatVData, InstShaderMeshResource, ShaderMesh
from material import MaterialData


class GameResDesc:
	def __init__(self, filePath:str):
		self.__filePath = filePath
		self.__fileName = path.splitext(path.basename(filePath))[0]
		self.__datablock = None

		log.log(f"Reading GameResDesc {self.__fileName}")
		log.addLevel()

		self.__readFile__()

		log.subLevel()
	
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
	
	def hasName(self, model:str):
		try:
			if self.__datablock.getByName(model) != None:
				return True
		except:
			return False

	def getModelMaterials(self, model:str) -> list[str]:
		tex = self.getModelTextures(model)

		if tex is None:
			raise Exception

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
				else: # TODO: handle unknown block types
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

	def getFilePath(self):
		return self.__filePath
	
	def getName(self):
		return self.__fileName


class RendInst(Exportable):
	def __init__(self, name:str, file:BinBlock):
		self.setName(name)
		self.setFile(file)

		log.log(f"Loading {name}")
		log.addLevel()

		self.computeData()

		log.subLevel()

	
	def computeData(self):
		file = self.getFile()

		self.loadHeader(file)
		self.loadMatVData(file)
		self.loadModelData(file)
		self.loadShaderMesh(file)

	def loadHeader(self, file:BinBlock):
		log.log("Loading header")
		log.addLevel()

		lodHdrInfo = readInt(file)
		lodHdrSz = lodHdrInfo & 0xFFFFFF

		riStructSzAdd = 48

		if (lodHdrInfo & 0x1000000) != 0:
			riStructSzAdd = 184
		
		altStructSz = lodHdrSz + riStructSzAdd
		riStructSz = 160 #RenderableInstanceLodsResource default size. if the hdr info has something in it, then increase the struct sz 

		if altStructSz > 0xA0:
			riStructSz = altStructSz
		
		lodHdrSz = lodHdrInfo

		self.__riStructSz = riStructSz
		self.__lodHdrSz = lodHdrSz

		texCnt = readInt(file)
		matCnt = readInt(file)

		if texCnt == matCnt == 0xFFFFFFFF:
			log.log("Pulling material and texture count from GameResDesc") # TODO

			self.setTexCnt(0)
			self.setMatCnt(0)

			self.setMaterials(None)
		else:
			raise Exception("Old rendInst version detected: material parsing is not implemented")
		
		vdataNum = readInt(file)
		mvdHdrSz = readInt(file)

		log.subLevel()
	
	def loadMatVData(self, file:BinBlock):
		log.log("Loading MatVData")
		log.addLevel()

		self.setMatVData(MatVData(CompressedData(file).decompressToBin(), self.getName(), self.getTexCnt(), self.getMatCnt()))

		log.subLevel()

	def loadModelData(self, file:BinBlock):
		data = file.readBlock(readInt(file) - 4)

		self.setLodCnt(readInt(data))

		data.seek(8, 1) # ptr

		bbox = (unpack("fff", data.read(0xC)), unpack("fff", data.read(0xC)))
		bsphCenter = unpack("fff", data.read(0xC))
		bsphRad = unpack("f", data.read(4))
		bound0rad = unpack("f", data.read(4))

		impostorDataOfs = readInt(data)
		
		occ = tuple(unpack("IIfI", file.read(0x10)) for i in range(4)) # occ table is acutally a float[12]

	def loadShaderMesh(self, file:BinBlock):
		lodCnt = self.getLodCnt()

		log.log(f"Processing {lodCnt} shadermesh resources")
		log.addLevel()

		self.__shaderMesh = tuple(InstShaderMeshResource(file) for i in range(lodCnt))

		log.subLevel()



	def getObj(self, lodId:int):
		mvd = self.getMatVData()

		materials = self.getMaterials()

		assert materials != None

		mvd.computeData()
		
		vertexDataCnt = mvd.getVDCount()
		shaderMeshElems = self.__shaderMesh[lodId].shaderMesh.elems
		vertexDatas:list[MatVData.VertexData] = [None for i in range(vertexDataCnt)]


		obj = ""
		objFaces = ""

		vOfs = 0

		for k, elem in enumerate(shaderMeshElems):
			log.log(f"Processing shader mesh {k}")
			log.addLevel()

			if k != 0:
				prev = shaderMeshElems[k - 1]

				if prev.vData != elem.vData:
					vOfs += prev.numV

			if vertexDatas[elem.vData] == None:
				vertexDatas[elem.vData] = mvd.getVertexData(elem.vData)
			
			vertexData = vertexDatas[elem.vData]

			verts, UVs, faces = vertexData.getVertices(), vertexData.getUVs(), vertexData.getFaces()

			objVerts = ""
			objUV = ""

			for i in range(elem.startV, elem.startV + elem.numV):
				v = verts[i]

				objVerts += f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n"

				uv = UVs[i]

				objUV += f"vt {uv[0]:.4f} {uv[1]:.4f}\n"


			obj += objVerts + objUV

			objFaces += f"usemtl {materials[elem.mat].getName()}\n"

			curFace = elem.startI // 3

			for i in range(curFace, curFace + elem.numFace):
				face = faces[i]

				f = ""

				for idx in face:
					idx += 1 + vOfs

					f += f" {idx}/{idx}"
					
				if f == "":
					continue
				
				objFaces += f"f{f}\n"
			
			log.subLevel()

		obj += objFaces

		return obj
	
	def exportObj(self, lodId:int):
		log.log(f"Quick exporting LOD {lodId} as OBJ")
		log.addLevel()

		fileName = f"{self.getName()}_{lodId}.obj"
		obj = self.getObj(lodId)

		file = open(fileName, "w")
		file.write(obj)
		file.close()

		log.subLevel()

		log.log(f"Wrote {len(obj)} to {fileName}")



	def setFile(self, file:BinBlock):
		self.__file = file
	
	def getFile(self):
		return self.__file
	
	
	def setLodCnt(self, cnt:int):
		self.__lodCnt = cnt
	
	def getLodCnt(self):
		return self.__lodCnt
	
	def setTexCnt(self, cnt:int):
		self.__texCnt = cnt
	
	def setMatCnt(self, cnt:int):
		self.__matCnt = cnt
	

	def getMatCnt(self):
		return self.__matCnt
	
	def getTexCnt(self):
		return self.__texCnt
	
	
	def setMatVData(self, mvd:MatVData):
		self.__mvd = mvd
	
	def getMatVData(self):
		return self.__mvd


	def setMaterials(self, materials:list[MaterialData]):
		self.__materials = materials
	
	def getMaterials(self):
		return self.__materials

class DynModel(RendInst):
	class Lod:
		class RigidObject:
			def __init__(self, file:BinBlock):
				self.shaderMeshPtr = readLong(file)
				self.sph_c = unpack("fff", file.read(4 * 3))
				self.sph_r = unpack("f", file.read(4))[0]
				self.nodeId = readInt(file)
				self._resv = readInt(file)

		def __init__(self, file:BinBlock, lodIdx:int):
			log.log(f"Processing LOD {lodIdx}")
			log.addLevel()

			hdrSz = readInt(file)
			rigidCnt = readInt(file)

			file.seek(8, 1)

			skinOfs = readInt(file)
			skinCnt = readInt(file)

			file.seek(8, 1)

			log.log(f"Loading {rigidCnt} rigid objects")
			log.addLevel()

			self.rigids = tuple(self.RigidObject(file.readBlock(0x20)) for i in range(rigidCnt))

			if skinOfs > 0:
				file.seek(hdrSz + 8, 1)
			
			log.subLevel()
			
			log.log(f"Loading {rigidCnt} shader mesh resources")
			log.addLevel()

			self.shaderMesh = tuple(ShaderMesh(file) for i in range(rigidCnt))

			log.subLevel()

			log.subLevel()
		
	
	def computeData(self):
		file = self.getFile()

		self.loadHeader(file)
		self.loadMatVData(file)
		self.loadModelData(file)
		self.loadSceneNodes(file.readBlock(readInt(file)))
		self.loadLods(file)
		self.loadShaderSkinnedMesh(file)

	def loadModelData(self, file:BinBlock):
		data = file.readBlock(readInt(file) - 4)

		self.setLodCnt(readInt(data))

		data.seek(8, 1) # ptr

		bbox = (unpack("fff", data.read(0xC)), unpack("fff", data.read(0xC)))

		bpC254 = unpack("ffff", data.read(0x10))
		self.__bpC255 = unpack("ffff", data.read(0x10))
		
		occ = tuple(unpack("IIfI", file.read(0x10)) for i in range(4)) # occ table is acutally a float[12]

	def loadSceneNodes(self, file:BinBlock):
		log.log("Processing scene nodes")
		log.addLevel()

		indicesOfs = readInt(file)
		nameCnt = readInt(file)

		file.seek(8, 1)

		skinNodesOfs = readInt(file)
		skinNodeCnt = readInt(file)

		file.seek(8, 1)

		nameMapData = file.read(indicesOfs - 0x20)

		nameMap = []

		prev = readLong(file) - 0x20
		
		for i in SafeRange(self, nameCnt):
			next = nameCnt == i + 1 and -1 or readLong(file) - 0x20
			
			nameMap.append(nameMapData[prev:next].decode("utf-8").rstrip("\x00"),)
			
			prev = next
		
		self.__nodeNames = nameMap
		
		log.log(f"Processed {nameCnt} nodes")
		
		self.__skinNodes = {readShort(file):i for i in range(skinNodeCnt)}

		log.log(f"Processed {skinNodeCnt} skin nodes")

		file.seek(4, 1)

		log.subLevel()

	def loadLods(self, file:BinBlock):
		lodCnt = self.getLodCnt()

		log.log(f"Processing {lodCnt} LODs")
		log.addLevel()
		
		self.__lods = tuple(self.Lod(file, i) for i in range(lodCnt))

		log.subLevel()

	def loadShaderSkinnedMesh(self, mfile:BinBlock):
		cnt = readInt(mfile)

		log.log(f"Loading {cnt} shader skinned mesh resources")
		log.addLevel()

		for i in range(cnt):
			log.log(f"{cnt}:")
			log.addLevel()

			file = mfile.readBlock(readInt(mfile))
			ptr = readLong(file)

			texCnt = readInt(file)
			matCnt = readInt(file)

			unknown = readInt(file)
			unknown = readInt(file)

			mvd = MatVData(CompressedData(file).decompressToBin(), self.getName())



			log.subLevel()

		log.subLevel()


	def getObj(self, lodId:int):
		log.log(f"Generating LOD {lodId} OBJ for {self.getName()}")
		log.addLevel()

		mvd = self.getMatVData()
		
		# materials = self.getMaterials()

		# assert materials != None

		mvd.computeData()

		lod = self.__lods[lodId]
		
		
		vertexDataCnt = mvd.getVDCount()
		lodShaderMesh = lod.shaderMesh
		vertexDatas:list[list[MatVData.VertexData, int]] = [None for i in range(vertexDataCnt)]


		obj = ""
		objFaces = ""
		objVerts = ""
		objUV = ""

		vOfs = 0

		log.log("Processing nodes")
		log.addLevel()

		for shaderMeshId, shaderMesh in enumerate(lodShaderMesh):
			name = self.__nodeNames[self.__skinNodes[lod.rigids[shaderMeshId].nodeId]]
			
			log.log(f"Processing rigid {name}")
			log.addLevel()

			objFaces += f"g {name}\n"

			for k, elem in enumerate(shaderMesh.elems):
				log.log(f"Processing shader mesh {k}")
				log.addLevel()

				if vertexDatas[elem.vData] == None:
					vertexData = mvd.getVertexData(elem.vData)

					vertexDatas[elem.vData] = [vertexData, vOfs]

					verts, UVs = vertexData.getVertices(), vertexData.getUVs()
					vCnt = len(verts)

					for i in range(vCnt):
						x, y, z = verts[i]

						x *= self.__bpC255[0]
						y *= self.__bpC255[1]
						z *= self.__bpC255[2]

						objVerts += f"v {x:.4f} {y:.4f} {z:.4f}\n"

						uv = UVs[i]

						objUV += f"vt {uv[0]:.4f} {uv[1]:.4f}\n"
					
					vOfs += vCnt
				
				vertexData = vertexDatas[elem.vData][0]
				indiceOffset = vertexDatas[elem.vData][1]

				faces = vertexData.getFaces()

				objFaces += f"usemtl {elem.mat}\n"
				# objFaces += f"usemtl {materials[elem.mat].getName()}\n"
				# print(k)

				vS = elem.startI // 3

				for i in range(vS, vS + elem.numFace):
					face = faces[i]

					f = ""

					for idx in face:
						idx += 1 + indiceOffset

						f += f" {idx}/{idx}"
						
					if f == "":
						continue
					
					objFaces += f"f{f}\n"

				log.subLevel()

			
			log.subLevel()
		
		log.subLevel()
		
		obj += objVerts + objUV + objFaces

		log.subLevel()

		return obj
	


class Skeleton:
	...


class GameResourcePack(Exportable): # may need cleanup
	class RealResData(Exportable):
		isValid = False

		classNames = {
			0x77f8232f:"rendInst", # Renderable Instance
			0x56f81b6d:"skeleton", # Skeleton
			0xace50000:"collision", # Collision
			0x88b7a117:"fx", # Particle effect
			0xb4b7d9c4:"dynModel", # Dynamic model
			0xd543e771:"physObj", # Physics object
			0x855a1be6:"fastPhys", # Fast physics object
			0x40c586f9:"anim", # Anim 2 Data (a2d)
			0xa6f87a9b:"char", # character
		}

		def __repr__(self):
			return f"<{self.getName()}\t{hex(self.__classId)}\ts={self.getSize()}\to={self.__offset}>"

		def __init__(
				self, filePath:str, classId:int = None,
				offset:int = 0, size:int = None, name:str = None):
			
			self.setFilePath(filePath)
			self.__classId = classId
			self.__offset = offset

			self.setSize(size == None and path.getsize(filePath) or size)
			self.setName(name == None and path.splitext(path.basename(filePath))[0] or name)

			self.__child = None

			if classId == None:
				self.__singleFile = True
				
				file = open(filePath, "rb")
				self.__classId = readInt(file)
				file.close()

				self.setSize(self.getSize() - 4)
			else:
				self.__singleFile = False

			self.__bin:BinFile = None
			self.setupClassName()

			self.isValid = True
		
		def getOffset(self):
			return self.__offset

		def getClassId(self):
			return self.__classId
		
		def getIsSingleFile(self):
			return self.__singleFile
		
		def getClassName(self):
			return self.__className

		def getIcon(self):
			if self.__classId == 0x77f8232f:
				return "res/asset_rendinst.bmp"
			elif self.__classId == 0x56f81b6d:
				return "res/asset_skeleton.bmp"
			elif self.__classId == 0xace50000:
				return "res/asset_collision.bmp"
			elif self.__classId == 0x88b7a117:
				return "res/asset_fx.bmp"
			elif self.__classId == 0xb4b7d9c4:
				return "res/asset_dynmodel.bmp"
			elif self.__classId == 0xd543e771:
				return "res/asset_physobj.bmp"
			elif self.__classId == 0x855a1be6:
				return "res/asset_fastphys.bmp"
			elif self.__classId == 0x40c586f9:
				return "res/asset_animTree.bmp"
			elif self.__classId == 0xa6f87a9b:
				return "res/asset_character.bmp"
			else:
				return "res/unknown.bmp"

		def setBin(self, file:BinFile): # in case our rrd isn't coming from a grp - shouldn't happen tho
			self.__bin = file

		def getBin(self):
			if self.__bin == None:
				file = open(self.getFilePath(), "rb")

				file.seek(self.__offset, 1)

				self.__bin = BinFile(file.read(self.getSize()))
				# binData = file.read(self.getSize() + (self.__singleFile and 4 or 0))

				file.close()

			return self.__bin

		def getClassObject(self):
			if self.__child != None:
				return self.__child
			else:
				if self.__classId == 0xb4b7d9c4: # dynModel or rendInst
					child = DynModel(self.getName(), self.getBin())
				elif self.__classId == 0x77f8232f:
					child = RendInst(self.getName(), self.getBin())
				elif self.__classId == 0x56f81b6d:
					child = Skeleton(self.getName(), self.getBin())
				else:
					log.log(f"Unimplemented class {hex(self.__classId)}",2)

					child = None

				self.__child = child

				return child
		
		def getChild(self):
			return self.getClassObject()
		
		def setupClassName(self):
			if self.__classId in self.classNames:
				self.__className = self.classNames[self.__classId]
			else:
				self.__className = f"Unknown classId '{self.__classId == None and 'None' or hex(self.__classId)}'"

		def getExportable(self):
			return self.__classId == 0x77f8232f or self.__classId == 0xb4b7d9c4

		def save(self, output:str = getcwd()):
			binData = pack("L", self.__classId) + self.getBin().read()
			output = path.normpath(f"{output}\\{self.getName()}.rrd")

			file = open(output,"wb")

			file.write(binData)

			file.close()

			return output

	class RealResEntry: # TODO: parents do not work
		def __repr__(self):
			return f"<RealResEntry [{hex(self.__classId)}] #{self.__realResId} p={self.__parentCnt} @ {self.__offset}:{self.__name}>"
		
		def __init__(self, grp, idx:int, name:str, classId:int, offset:int, realResId:int, _resv:int):
			self.__grp:GameResourcePack = grp
			self.__classId = classId
			self.__offset = offset
			self.__realResId = realResId
			self.__resv = _resv
			self.__name = name

			self.__parentCnt = 0
			self.__pOffset = 0
			self.__parentRes:list[GameResourcePack.RealResEntry] = []

			self.__resData = None

			if (idx != realResId):
				log.log(f"{self}: inconsistant idx={idx} realResId={realResId}", LOG_ERROR)

			# print(idx, hex(classId), offset, realResId, _resv)
		
		def getParentOffset(self):
			return self.__pOffset
		
		def getParentCnt(self):
			return self.__parentCnt
		
		def appendParentRes(self, parent):
			self.__parentRes.append(parent)
		
		def getParentRes(self):
			return self.__parentRes

		def getRealResData(self):
			if self.__resData == None:
				log.log(f"Pulling {self.__name} from {self.__grp.getName()}")

				resCnt = self.__grp.getRealResEntryCnt()

				size = 0

				if self.__realResId + 1 >= resCnt:
					size = self.__grp.getSize() - self.__offset
				else:
					size = self.__grp.getRealResEntry(self.__realResId + 1).__offset - self.__offset
				
				self.__resData = GameResourcePack.RealResData(self.__grp.getFilePath(), self.__classId, self.__offset, size, self.__name)
			
			return self.__resData
		
		def getName(self):
			return self.__name

		def appendData(self, classId:int, resId:int, resDataId:int, pOffset:int, parentCnt:int, l:int):
			if resId != resDataId:
				log.log(f"{self}: inconsistant resId={resId} resDataId={resDataId}", LOG_ERROR)
			
			self.__parentCnt = parentCnt
			self.__pOffset = pOffset

		
	def __init__(self, filePath:str):
		self.setFilePath(filePath)
		self.setName(path.splitext(path.basename(filePath))[0])


		self.__realResources = {}
		self.isValid = False

		self.__readFile__()

		log.log(self)

	def __repr__(self):
		return f"<{self.getName()}.grp\tnmo={self.__nameMapOffset}\tnmn={self.__nameMapNum}\treo={self.__realResEntriesOffset}\trd2={self.__resData2}\trd2n={self.__resData2Num}>"

	def __readFile__(self):
		f = open(self.getFilePath(), "rb")
		file = BinFile(f.read())
		f.close()

		file.seek(0xC, 1)

		dataSize = readInt(file) + 0x4
		self.setSize(dataSize + 0xC)

		nameMapOffset = file.tell() + readInt(file) - 0x10
		nameMapNum = readInt(file)

		self.__nameMapOffset = nameMapOffset
		self.__nameMapNum = nameMapNum

		file.seek(8, 1)

		realResEntriesOffset = file.tell() + readInt(file) - 0x20
		realResNum = readInt(file)

		self.__realResEntriesOffset = realResEntriesOffset

		file.seek(8, 1)

		resData2 = file.tell() + readInt(file) - 0x20
		resData2Num = readInt(file)

		self.__resData2 = resData2
		self.__resData2Num = resData2Num

		file.seek(8, 1)

		nameMapData = file.read(nameMapOffset - file.tell())

		nameMap = []

		prev = readInt(file) - 0x40
		
		for i in SafeRange(self, nameMapNum):
			next = nameMapNum == i + 1 and nameMapOffset - 0x40 or readInt(file) - 0x40
			
			nameMap.append(nameMapData[prev:next].decode("utf-8").rstrip("\x00"),)
			
			prev = next
		
		log.addLevel()

		self.__resEntriesOfs = file.tell()

		realResEntries = tuple(GameResourcePack.RealResEntry(self, i, nameMap[i],
								readInt(file), # classId
								readInt(file), # offset
								readShort(file), # realResId
								readShort(file)) # _resv
								for i in SafeRange(self, realResNum))
		
		# file.seek(0x10 - file.tell() % 0x10, 1)


		for i in SafeRange(self, resData2Num):
			realResEntries[i].appendData(readInt(file), # classId
								readShort(file), # resId
								readShort(file), # realResId
								readInt(file),
								readInt(file),
								readLong(file))

		for resEntry in realResEntries:
			file.seek(resEntry.getParentOffset(), 0)

			for i in range(resEntry.getParentCnt()):
				resEntry.appendParentRes(realResEntries[readShort(file)])

		log.subLevel()

		# file.close()

		self.__realResEntries = realResEntries

		self.isValid = True

	
	def getRealResEntry(self, resId:int):
		return self.__realResEntries[resId]
	
	def getRealResEntryCnt(self):
		return len(self.__realResEntries)
	
	def getRealResource(self, realResId:int):
		assert realResId >= 0 and realResId <= len(self.__realResEntries)

		return self.__realResEntries[realResId].getRealResData()
	
	def getAllRealResources(self):
		return tuple(self.getRealResource(i) for i in SafeRange(self, len(self.__realResEntries)))

	def getRealResId(self, name:str):
		for k, v in enumerate(self.__realResEntries):
			if v.getName() == name:
				return k


	def getResourceByName(self, name:str):
		return self.getRealResource(self.getRealResId(name))
	
	def getResEntryOffsets(self, realResId:int):
		ofs = self.__resEntriesOfs + realResId * 0xC
		return f"realResDataOfs1={ofs} realResDataOfs2={ofs + realResId * 0x18}"


if __name__ == "__main__":
	from assetcacher import ASSETCACHER

	# desc = GameResDesc("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\riDesc.bin")
	# ASSETCACHER.appendGameResDesc(desc)

	# desc = GameResDesc("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\dynModelDesc.bin")
	# ASSETCACHER.appendGameResDesc(desc)

	# desc = GameResDesc("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content.hq\\pkg_cockpits\\res\\dynModelDesc.bin")
	# desc = GameResDesc("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\patch\\content\\base\\res\\dynModelDesc.bin")

	grp = GameResourcePack("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\germ_gm.grp")
	# grp = GameResourcePack("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\cars_ri.grp")
	
	resId = grp.getRealResId("pzkpfw_IV_ausf_F")
	# resId = grp.getRealResId("dodge_wf32")
	rrd = grp.getRealResource(resId)
	# print(rrd.getOffset())
	ri:DynModel = rrd.getChild()
	# ri.setMaterials(ASSETCACHER.getModelMaterials(ri.getName()))
	ri.exportObj(0)
	# rrd.save()
	# print(ri.getMTL())

	# mvd = ri.getMatVData()
	# mvd.quickExportVDataToObj(6)
	# mvd.quickExportVDataToObj(5)

	# for rrd in grp.getAllRealResources():
	# 	if rrd.getClassName() != "rendInst":
	# 		continue
			
	# 	log.log(f"Processing {rrd.getName()}")
	# 	log.addLevel()

	# 	ri:RendInst = rrd.getChild()
		
	# 	ri.getObj(0)

	# 	log.subLevel()