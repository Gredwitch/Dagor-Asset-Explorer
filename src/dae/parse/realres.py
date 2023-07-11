import sys
from os import path, getcwd

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import util.log as log
from util.fileread import *
from util.enums import *
from util.decompression import CompressedData
from util.misc import vectorTransform, getResPath
from util.assetcacher import AssetCacher
from struct import unpack, pack
from parse.datablock import *
from util.terminable import Packed, SafeRange, SafeIter, SafeEnumerate
from parse.mesh import MatVData, InstShaderMeshResource, ShaderMesh
from parse.material import MaterialData, MaterialTemplateLibrary,  computeMaterialNames, generateMaterialData
from abc import abstractmethod



UNKNOWN_ICO_PATH = getResPath("unknown.bmp")
REALRES_CLASSES_LIST:list[type] = None
REALRES_CLASSES_DICT:dict[int, type] = None



class RealResData(Packed):
	@classmethod
	@property
	@abstractmethod
	def staticClassId(cls) -> int:
		...
	
	@property
	def classId(self) -> int:
		return self.staticClassId
	
	@classmethod
	@property
	def classNiceName(cls):
		return "Real Resource Data"
	
	def __repr__(self):
		return f"<{self.name}\t{hex(self.classId)}\ts={self.size}\to={self.offset}>"

	def __init__(self, filePath:str, name:str = None, size:int = 0, offset:int = 0):
		super().__init__(filePath, name, size, offset)
		
		# self.setupClassName()

		self._setValid()


class UnknownResData(RealResData):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0x0
	
	@classmethod
	@property
	def classIconName(cls) -> str:
		return "unknown.bmp"

	@property
	def classId(self) -> int:
		return self.__classId
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "rrd"

	@classmethod
	@property
	def classNiceName(cls):
		return "Unknown RRD"
	
	@property
	def niceName(self):
		return f"{self.classNiceName} ({hex(self.__classId)})"
	
	@property
	def exportable(self):
		return False
	
	def __init__(self, filePath:str, name:str = None, size:int = 0, offset:int = 0, classId:int = 0xFFFFFFFF):
		super().__init__(filePath, name, size, offset)

		self.__classId = classId

class GeomNodeTree(RealResData):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0x56f81b6d
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "gnt"

	@classmethod
	@property
	def classNiceName(cls):
		return "Skeleton"

	@classmethod
	@property
	def classIconName(self):
		return "asset_skeleton.bmp"
	
	class Node: # not a terminable
		# def __iter__(self):
		# 	return self
		
		# def __next__(self):
		# 	raise StopIteration()
		
		def readMatrix4x4(self, file:BinBlock):
			flat = unpack("f" * 16, file.read(4 * 16))

			m = ( # transpose by hand, faster than a loop
				(flat[0], flat[4], flat[8], flat[12]),
				(flat[1], flat[5], flat[9], flat[13]),
				(flat[2], flat[6], flat[10], flat[14]),
				(flat[3], flat[7], flat[11], flat[15]),
			)

			return m
			# return tuple(zip(*([iter(flat)] * 4)))

			# return tuple(unpack("ffff", file.read(4 * 4)) for i in range(4))
		
		def readStringFuzzy(self, file:BinBlock):
			name = b""

			while file.tell() < file.getSize():
				b = file.read(1)
				
				if b == b"\x00":
					break
				
				name += b
			
			return name.decode("ascii")

		def __init__(self, file:BinBlock, main:BinBlock, idx:int):
			self.tm = self.readMatrix4x4(file)
			self.wtm = self.readMatrix4x4(file)

			self.refOfs = readInt(file)
			self.refCnt = readInt(file)

			self.idx = idx

			file.seek(8, 1)

			self.pnt = readInt(file)

			file.seek(4, 1)

			nameOfs = readInt(file)

			ofs = main.tell()

			main.seek(nameOfs + 4, 0)

			self.name = self.readStringFuzzy(main)

			main.seek(ofs, 0)

			self.parent = None
			self.children = []
		
		def __repr__(self):
			return f"<{self.name}>"

		def __str__(self):
			result = self.name + ' { \n'

			result += '\ttm {\n'
			for column in self.tm:
				result += '\t\t' + ' '.join(map(str, column)) + '\n'
			result += '\t}\n'
			
			result += '\twtm {\n'
			for column in self.wtm:
				result += '\t\t' + ' '.join(map(str, column)) + '\n'
			result += '\t}\n'

			result += '}\n'

			return result

	def __init__(self, filePath:str, name:str = None, size:int = 0, offset:int = 0):
		super().__init__(filePath, name, size, offset)

		self.__nodes = None
	
	def __retrieveData__(self):
		bfile = self.getBin()
		
		file = bfile.readBlock(readInt(bfile) & 0x00_00_FF_FF)
		
		nodeCnt = readInt(file) - 1

		# self.__nodes = dict(tuple(tuple((v.name, v) for v in (self.Node(file.readBlock(160), file), ))[0] for i in range(nodeCnt)), )
		nodes = tuple(self.Node(file.readBlock(160), file, i) for i in SafeRange(self, nodeCnt))
		
		
		self.__buildTree__(nodes)

		self.__nodes = nodes
		self.__nodesDict = {v.name:v for v in SafeIter(self, nodes)}
	
	def getNodeByName(self, name:str):
		if name in self.__nodesDict:
			return self.__nodesDict[name]
		
		return None
	
	def getNode(self, nodeId:int):
		return self.getNodes()[nodeId]

	def getNodes(self):
		if self.__nodes is None:
			self.__retrieveData__()
		
		return self.__nodes

	def __buildTree__(self, nodes:dict):
		for nodeName in SafeIter(self, nodes):
			# node:GeomNodeTree.Node = nodes[nodeName]
			node:GeomNodeTree.Node = nodeName

			childOfs = node.refOfs // 160
			childCnt = node.refCnt

			if childCnt != 0:
				for i in SafeRange(self, childCnt):
					try:
						child:GeomNodeTree.Node = nodes[childOfs + i]
					except:
						break

					child.parent = node
					node.children.append(child)

	def print_tree(self, root, indent = 0):
		t = "\t"

		print(f"{t * indent} {root.idx}:{root.name}")

		for child in root.children:
			self.print_tree(child, indent + 1)

class RendInst(RealResData):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0x77f8232f
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "ri"

	@classmethod
	@property
	def classNiceName(cls):
		return "Renderable instance"

	@classmethod
	@property
	def classIconName(cls):
		return "asset_rendinst.bmp"
	
	def __init__(self, filePath:str, name:str = None, size:int = 0, offset:int = 0):
		super().__init__(filePath, name, size, offset)
		

		self.__dataComputed = False
		self.__textures = None
		self.__materials = None

		self.__texCnt = 0
		self.__matCnt = 0

		self._setValid()

	@property
	def dataComputed(self):
		return self.__dataComputed

	def _setDataComputed(self):
		self.__dataComputed = True

	def computeData(self):
		if self.dataComputed:
			return

		log.log(f"Loading {self.name}")
		log.addLevel()

		file = self.getBin()

		self._readHeader(file)
		self._readMatVData(file)
		self._readModelData(file)
		self._readShaderMesh(file)

		self._setDataComputed()

		log.subLevel()

	def _readHeader(self, file:BinBlock):
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
		
		vdataNum = readInt(file)
		mvdHdrSz = readInt(file)

		if texCnt == matCnt == 0xFFFFFFFF:
			log.log("Pulling material and texture count from GameResDesc") # TODO

			mats = AssetCacher.getModelMaterials(self.name)

			if len(mats) == 0:
				self._setTextureCount(0)
				self._setMaterialCount(0)

				self._setMaterials(None)
			else:
				self._setTextures(AssetCacher.getModelTextures(self.name))
				self._setMaterials(mats)

		else:
			self._setTextureCount(texCnt)
			self._setMaterialCount(matCnt)

			self._readTextures(file)

		log.subLevel()
	
	def _readTextures(self, file:BinBlock):
		texMapSz = readInt(file)
		texIndicesOfs = readInt(file)
		texCnt = readInt(file)

		file.seek(8, 1)

		nameMapData = file.read(texIndicesOfs - 0x10)
		nameMap = []

		prev = readInt(file) - 0x10
		
		for i in SafeRange(self, texCnt):
			next = texCnt == i + 1 and -1 or readInt(file) - 0x10
			
			nameMap.append(nameMapData[prev:next].decode("utf-8").rstrip("\x00"),)
			
			prev = next
		
		self.setTextures(nameMap)

	def _setTextures(self, textures:list[str]):
		self.__textures = textures

		self._setMaterialCount(len(textures) if textures is not None else 0)
	
	@property
	def textures(self):
		return self.__textures


	def _readMatVData(self, file:BinBlock):
		log.log("Loading MatVData")
		log.addLevel()

		bin = CompressedData(file).decompressToBin()
		mvd = MatVData(bin, self.name, self.textureCount, self.materialCount)
		 
		self._setMatVData(mvd)
		
		log.subLevel()

	def _readModelData(self, file:BinBlock):
		ofs = file.tell()

		data = file.readBlock(readInt(file) - 4)

		self._setLodCount(readInt(data))

		data.seek(8, 1) # ptr

		bbox = (unpack("fff", data.read(0xC)), unpack("fff", data.read(0xC)))
		bsphCenter = unpack("fff", data.read(0xC))
		bsphRad = unpack("f", data.read(4))
		bound0rad = unpack("f", data.read(4))

		impostorDataOfs = readInt(data)
		
		occ = tuple(unpack("IIfI", file.read(0x10)) for i in SafeRange(self, self.lodCount)) # occ table is acutally a float[12]

		if impostorDataOfs > 0:
			file.seek(ofs + impostorDataOfs, 0)

			impostorShaderMeshOfs = readLong(file)
			impostorSz = readLong(file)

			self.readImposorData(file.readBlock(impostorSz - (file.tell() - ofs)))
	
	def _readImposorData(self, file:BinBlock):
		# cMethod = readLong(file)

		# impostor = CompressedData(file.readRest(), 0x60).decompressToBin()
		# impostor.quickSave("impostor.imp")

		...

	def _readShaderMesh(self, file:BinBlock):
		log.log(f"Processing {self.lodCount} shadermesh resources")
		log.addLevel()

		self.__shaderMesh = tuple(InstShaderMeshResource(file) for i in SafeRange(self, self.lodCount))

		log.subLevel()

	def generateMaterials(self):
		if self.materials is not None or self.textures is None:
			return
		
		mvd = self.mvd
		mvd.computeData()

		materials = generateMaterialData(self.textures, mvd.getMaterials(), self)
		computeMaterialNames(materials, self)

		self._setMaterials(materials)


	def getObj(self, lodId:int):
		self.generateMaterials()

		if self.materials is None and self.textures is None:
			log.log("No materials were loaded: material groups will be unnamed", LOG_WARN)

		mvd = self.mvd
		mvd.computeData()
		
		vertexDataCnt = mvd.getVDCount()
		shaderMeshElems = self.__shaderMesh[lodId].shaderMesh.elems
		vertexDatas:list[list[MatVData.VertexData, int]] = [None for i in SafeRange(self, vertexDataCnt)]


		obj = ""
		objFaces = ""

		vOfs = 0

		vertexOrder:dict[int, list[ShaderMesh.Elem]] = {}

		for k, elem in SafeEnumerate(self, shaderMeshElems):
			if not elem.vdOrderIndex in vertexOrder:
				vertexOrder[elem.vdOrderIndex] = []
			
			if vertexDatas[elem.vData] == None:
				vData = mvd.getVertexData(elem.vData)
				vertexDatas[elem.vData] = [vData, vOfs]
				
				objVerts = ""
				objUV = ""
				
				verts, UVs = vData.getVertices(), vData.getUVs()
				vCnt = len(verts)

				for i in SafeRange(self, vCnt):
					v = verts[i]

					objVerts += f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n"

					uv = UVs[i]

					objUV += f"vt {uv[0]:.4f} {uv[1]:.4f}\n"

				obj += objVerts + objUV
				vOfs += vCnt

			vertexOrder[elem.vdOrderIndex].append(elem)

			elem.smid = k # TODO: put this in the class constructor

		for orderElems in SafeIter(self, vertexOrder.values()):
			for elem in SafeIter(self, orderElems):
				log.log(f"Processing shader mesh {elem.smid}")
				log.addLevel()

				vertexData = vertexDatas[elem.vData][0]
				vOfs = vertexDatas[elem.vData][1] + elem.baseVertex

				faces = vertexData.getFaces()

				objFaces += f"usemtl {self.getMaterialName(elem.mat)}\n"
				
				curFace = elem.startI // 3

				for i in SafeRange(self, curFace, curFace + elem.numFace):
					face = faces[i]

					f = ""

					for idx in SafeIter(self, face):
						idx += 1 + vOfs

						f += f" {idx}/{idx}"
						
					if f == "":
						continue
					
					objFaces += f"f{f}\n"

				log.subLevel()

		obj += objFaces

		return obj
	
	def getExportName(self, lodId:int):
		return f"{self.name}_{lodId}"

	def exportObj(self, lodId:int, output:str = getcwd()):
		log.log(f"Quick exporting LOD {lodId} as OBJ")
		log.addLevel()

		self.computeData()

		name = self.getExportName(lodId)
		
		self.generateMaterials()
		
		materials = self.materials

		fileName = f"{name}.obj"
		obj = self.getObj(lodId)

		if materials is not None:
			log.log("Writing MTL")
			log.addLevel()

			mtl = MaterialTemplateLibrary(materials)
			
			file = open(output + "/" + name + ".mtl", "w")
			file.write(mtl.getMTL())
			file.close()

			mtl.exportTextures(output)

			log.subLevel()

			obj = "mtllib " + name + ".mtl\n" + obj

		file = open(output + "/" + fileName, "w")
		file.write(obj)
		file.close()

		log.subLevel()

		log.log(f"Wrote {len(obj)} bytes to {fileName}")

		
	def _setLodCount(self, cnt:int):
		self.__lodCnt = cnt
	
	@property
	def lodCount(self):
		return self.__lodCnt
	
	def _setTextureCount(self, cnt:int):
		self.__texCnt = cnt
	
	def _setMaterialCount(self, cnt:int):
		self.__matCnt = cnt
	
	def getMaterialName(self, mat:int):
		if self.__materials is None:
			return mat
		elif mat >= 0 and mat < len(self.__materials):
			return self.__materials[mat].getName()
		else:
			return f"unknwon_{mat}"
	
	@property
	def materialCount(self):
		return self.__matCnt
	
	@property
	def textureCount(self):
		return self.__texCnt
	
	
	def _setMatVData(self, mvd:MatVData):
		self.__mvd = mvd
	
	@property
	def mvd(self):
		return self.__mvd


	def _setMaterials(self, materials:list[MaterialData]):
		self.__materials = materials

		self._setMaterialCount(len(materials) if materials is not None else 0)
	
	@property
	def materials(self):
		return self.__materials

class DynModel(RendInst):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0xb4b7d9c4
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "dyn"

	@classmethod
	@property
	def classNiceName(cls):
		return "Dynamic model" # Dynamic renderable scene

	@classmethod
	@property
	def classIconName(self):
		return "asset_dynmodel.bmp"
	
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
		if self.dataComputed:
			return
		
		file = self.getBin()

		self.setGeomNodeTree(None)

		self._readHeader(file)
		self._readMatVData(file)
		self._readModelData(file)
		self._readSceneNodes(file.readBlock(readInt(file)))
		self._readLods(file)
		self._readShaderSkinnedMesh(file)

		self._setDataComputed()

	def _readModelData(self, file:BinBlock):
		blockSz = readInt(file)

		data = file.readBlock(blockSz - 4)

		self._setLodCount(readInt(data))

		data.seek(8, 1) # ptr

		bbox = (unpack("fff", data.read(0xC)), unpack("fff", data.read(0xC)))

		if blockSz > 0x28:
			log.log(f"Big modeldata header {hex(blockSz)}: node transforms may be fucked", LOG_WARN)

			self.__bpC254 = unpack("ffff", data.read(0x10))
			self.__bpC255 = unpack("ffff", data.read(0x10))

			self.__noScale = False
		else:
			self.__bpC254 = (1.0, 1.0, 1.0, 1.0)
			self.__bpC255 = (1.0, 1.0, 1.0, 1.0)

			self.__noScale = True
		
		occ = tuple(unpack("IIfI", file.read(0x10)) for i in SafeRange(self, self.lodCount)) # occ table is acutally a float[4 * lodCnt]
		

	def _readSceneNodes(self, file:BinBlock):
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
		
		self.__skinNodes = {readShort(file):i for i in SafeRange(self, skinNodeCnt)}

		log.log(f"Processed {skinNodeCnt} skin nodes")

		# file.seek(4, 1)

		log.subLevel()

	def _readLods(self, file:BinBlock):
		lodCnt = self.lodCount

		log.log(f"Processing {lodCnt} LODs")
		log.addLevel()
		
		self.__lods = tuple(self.Lod(file, i) for i in SafeRange(self, lodCnt))

		log.subLevel()

	def _readShaderSkinnedMesh(self, mfile:BinBlock):
		if mfile.tell() + 4 >= mfile.getSize():
			return
		
		cnt = readInt(mfile)

		if cnt == 0:
			return

		log.log(f"Loading {cnt} shader skinned mesh resources")
		log.addLevel()

		for i in SafeRange(self, cnt):
			log.log(f"{cnt}:")
			log.addLevel()

			file = mfile.readBlock(readInt(mfile))
			ptr = readLong(file)

			texCnt = readInt(file)
			matCnt = readInt(file)

			unknown = readInt(file)
			unknown = readInt(file)

			mvd = MatVData(CompressedData(file).decompressToBin(), self.name)



			log.subLevel()

		log.subLevel()

	def setGeomNodeTree(self, skeleton:GeomNodeTree):
		self.__skeleton = skeleton

	def getGeomNodeTree(self):
		return self.__skeleton

	def getObj(self, lodId:int): # TODO: rewrite - use vdorderindex and basevertex attributes
		
		log.log(f"Generating LOD {lodId} OBJ for {self.name}")
		log.addLevel()

		mvd = self.mvd
		
		if self.materials is None:
			log.log("No materials were loaded: material groups will be unnamed", LOG_WARN)
		
		skeleton = self.getGeomNodeTree()

		if skeleton is None:
			log.log("No skeleton was loaded: rigids will not be positionned correctly", LOG_WARN)

		mvd.computeData()

		lod = self.__lods[lodId]
		
		
		vertexDataCnt = mvd.getVDCount()
		lodShaderMesh = lod.shaderMesh
		vertexDatas:list[list[MatVData.VertexData, int, int]] = [None for i in SafeRange(self, vertexDataCnt)]


		obj = ""
		objFaces = ""
		objVerts = ""
		objUV = ""

		vOfs = 0

		vertexDataOrder = []

		log.log("Processing nodes")
		log.addLevel()

		# rootUndo = inverse_matrix(skeleton.getNodeByName("").wtm)

		for shaderMeshId, shaderMesh in SafeEnumerate(self, lodShaderMesh):
			rigid = lod.rigids[shaderMeshId]
			nodeId = self.__skinNodes[rigid.nodeId]

			name = self.__nodeNames[nodeId]
			
			log.log(f"Processing rigid {name}")
			# log.log(f"Processing rigid {shaderMeshId=} {lod.rigids[shaderMeshId].nodeId=} {self.__skinNodes[lod.rigids[shaderMeshId].nodeId]=} {self.__skinNodes[shaderMeshId]=} {name}")
			log.addLevel()

			objFaces += f"g {name}\n"

			node = None
			
			if skeleton is not None:
				node = skeleton.getNodeByName(name)

				if node is None:
					# tm = [[1, 0, 0, 0],
					# 	  [0, 1, 0, 0],
					# 	  [0, 0, 1, 0],
					# 	  [0, 0, 0, 1]
					# ]
					node = skeleton.getNodeByName("")

					log.log("Null node warning", LOG_WARN)

				tm = node.wtm

				# tm = [
				# 	[tm[0][0], tm[0][1], tm[0][2], tm[0][3],],
				# 	[tm[1][0], tm[1][1], tm[1][2], tm[1][3],],
				# 	[tm[2][0], tm[2][1], tm[2][2], tm[2][3],],
				# 	[tm[3][0], tm[3][1], tm[3][2], tm[3][3],],
				# ]
				
				# tm =[	[1, 0, 0, tm[0][3]],
				# 		[0, 1, 0, tm[1][3]],
				# 		[0, 0, 1, tm[2][3]],
				# 		[0, 0, 0, tm[3][3]]
				# ]
					
			# VirtualDynModelEntity::setup

			for k, elem in SafeEnumerate(self, shaderMesh.elems):
				# log.log(f"Processing shader mesh {k}")
				log.addLevel()

				if vertexDatas[elem.vData] == None:
					vertexDataOrder.append(elem.vData)

					vertexData = mvd.getVertexData(elem.vData)

					verts, UVs = vertexData.getVertices(), vertexData.getUVs()

					vertexDatas[elem.vData] = [vertexData, vOfs, verts]

					vCnt = len(verts)

					for i in SafeRange(self, vCnt):
						verts[i][0] *= self.__bpC255[0]
						verts[i][1] *= self.__bpC255[1]
						verts[i][2] *= self.__bpC255[2]

						uv = UVs[i]

						objUV += f"vt {uv[0]:.4f} {uv[1]:.4f}\n"
					
					vOfs += vCnt
				
				vertexData = vertexDatas[elem.vData][0]
				indiceOffset = vertexDatas[elem.vData][1]

				faces = vertexData.getFaces()

				objFaces += f"usemtl {self.getMaterialName(elem.mat)}\n"

				vS = elem.startI // 3
				
				
				if node is not None:
					verts = vertexDatas[elem.vData][2]
				
					for i in SafeRange(self, elem.startV, elem.startV + elem.numV):
						vert = verts[i]

						if self.__noScale:
							x, y, z = vectorTransform(tm, vert)
						else:
							x, y, z = vert

						vert[0] = x + tm[0][3]
						vert[1] = y + tm[1][3]
						vert[2] = z + tm[2][3]


				for i in SafeRange(self, vS, vS + elem.numFace):
					face = faces[i]

					f = ""

					for idx in SafeIter(self, face):
						idx += 1 + indiceOffset

						f += f" {idx}/{idx}"
						
					if f == "":
						continue
					
					objFaces += f"f{f}\n"

				log.subLevel()

			
			log.subLevel()
		
		for i in SafeIter(self, vertexDataOrder):
			for vert in SafeIter(self, vertexDatas[i][2]):
				x, y, z = vert

				objVerts += f"v {-x:.6f} {y:.6f} {z:.6f}\n"

		log.subLevel()
		# print(self.__bpC254)
		"""
		objUV = ""
		objFaces = ""
		objVerts = ""

		for k, node in enumerate(skeleton.getNodes()):
			tm = node.wtm

			vec = [0, 0, 0]

			x, y, z, w = transform_vector(tm,vec)

			# x *= self.__bpC254[0]
			# y *= self.__bpC254[1]
			# z *= self.__bpC254[2]

			add = 0.1

			objVerts += f"v {x:.4f} {y:.4f} {z:.4f}\n"
			objVerts += f"v {x + add:.4f} {y:.4f} {z:.4f}\n"
			objVerts += f"v {x:.4f} {y + add:.4f} {z:.4f}\n"

			objFaces += f"g {node.name}\n"

			idx = (k * 3) + 1

			f = ""

			for i in range(3):
				f += f" {idx + i}/{idx + i}"

			objFaces += f"f {f}\n"
			
		"""
		"""

		objUV = ""
		objFaces = ""
		objVerts = ""

		for shaderMeshId, shaderMesh in enumerate(lodShaderMesh):
			rigid = lod.rigids[shaderMeshId]
			nodeId = self.__skinNodes[rigid.nodeId]

			name = self.__nodeNames[nodeId]
			
			# tm = node.wtm

			# vec = [0, 0, 0]

			# x, y, z, w = transform_vector(tm,vec)

			x, y, z = rigid.sph_c

			# x *= self.__bpC254[0]
			# y *= self.__bpC254[1]
			# z *= self.__bpC254[2]

			add = 0.1

			objVerts += f"v {x:.4f} {y:.4f} {z:.4f}\n"
			objVerts += f"v {x + add:.4f} {y:.4f} {z:.4f}\n"
			objVerts += f"v {x:.4f} {y + add:.4f} {z:.4f}\n"

			objFaces += f"g {name}\n"

			idx = (k * 3) + 1

			f = ""

			for i in range(3):
				f += f" {idx + i}/{idx + i}"

			objFaces += f"f {f}\n"
"""

		obj += objVerts + objUV + objFaces
		
		log.subLevel()

		return obj

class CollisionGeom(RealResData):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0xace50000
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "col"
	
	@classmethod
	@property
	def classNiceName(cls):
		return "Collision geometry" # Dynamic renderable scene

	@classmethod
	@property
	def classIconName(self):
		return "asset_collision.bmp"
	

	def __init__(self, filePath:str, name:str = None, size:int = 0, offset:int = 0):
		super().__init__(filePath, name, size, offset)

		self._setValid()
	
	def __readHeader__(self, file:BinFile):
		magic = readInt(file)
		unknown = readInt(file)

		dataSz = readInt(file)

		file.seek(dataSz, 1)

		fileSz = readInt(file)

		hasNodes = readInt(file)

		if hasNodes == 2:
			self.__nodeCnt = readInt(file)
		elif hasNodes == 1:
			self.__nodeCnt = 1
		else:
			raise Exception(f"CollisionGeom {hasNodes=}")

	class CollNode:
		def __init__(self, file:BinFile):
			name = file.read(readInt(file)).decode("utf-8")

			file.seek(2, 1)

			sz = readInt(file)

			if sz > 0:
				self.__className = name
				self.setName(file.read(sz).decode("utf-8"))

				file.seek(2, 1)
			else:
				self.setName(name)

			file.seek(96, 1)

			self.__verts:tuple[tuple[float, float, float]] = tuple(unpack("3f", file.read(12)) for _ in SafeRange(self, readInt(file)))
			self.__faces:tuple[tuple[int, int, int]] = tuple(unpack("3I", file.read(12)) for _ in SafeRange(self, readInt(file) // 3))

		def getVerts(self):
			return self.__verts
	
		def getFaces(self):
			return self.__faces

	def __readFile__(self):
		if self.__nodes is None:
			return
		
		file = self.getBin()

		self.__readHeader__(file)

		self.__nodes = tuple(CollisionGeom.CollNode(file) for _ in SafeRange(self, self.__nodeCnt))
	
	def getObj(self):
		self.__readFile__()

		obj = ""

		vOfs = 0

		for node in SafeEnumerate(self, self.__nodes):
			verts = node.getVerts()

			for v in SafeIter(self, verts):
				obj += f"v {v[0]:.4f} {v[2]:.4f} {v[1]:.4f}\n"
				obj += f"vt 0.0 0.0\n"
			
			for f in SafeIter(self, node.getFaces()):
				obj += "f"

				for idx in SafeIter(self, f):
					idx += 1 + vOfs

					obj += f" {idx}/{idx}"
				
				obj += "\n"

			vOfs += len(verts)
			
		return obj

	def exportObj(self, path:str = getcwd()):
		obj = self.getObj()

		file = open(f"{path}/{self.name}.obj", "w")
		file.write(obj)
		file.close()

class FX(RealResData):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0x88b7a117
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "fx"
	
	@classmethod
	@property
	def classNiceName(cls):
		return "Particle effect"

	@classmethod
	@property
	def classIconName(cls):
		return "asset_fx.bmp"

class PhysObj(RealResData):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0xd543e771
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "phy"
	
	@classmethod
	@property
	def classNiceName(cls):
		return "Physics object"

	@classmethod
	@property
	def classIconName(cls):
		return "asset_physobj.bmp"

class FastPhys(RealResData):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0x855a1be6
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "fphy"
	
	@classmethod
	@property
	def classNiceName(cls):
		return "Fast physics"

	@classmethod
	@property
	def classIconName(self):
		return "asset_fastphys.bmp"

class Anim2Data(RealResData):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0x40c586f9
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "a2d"
	
	@classmethod
	@property
	def classNiceName(cls):
		return "Anim2Data"

	@classmethod
	@property
	def classIconName(self):
		return "asset_a2d.bmp"

class AnimTree(RealResData):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0x8f2a701a
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "anm"
	
	@classmethod
	@property
	def classNiceName(cls):
		return "AnimTree"

	@classmethod
	@property
	def classIconName(self):
		return "asset_animTree.bmp"

class Char(RealResData):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0xa6f87a9b
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "char"
	
	@classmethod
	@property
	def classNiceName(cls):
		return "Character"

	@classmethod
	@property
	def classIconName(self):
		return "asset_character.bmp"

class LandClass(RealResData):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0x3fb59c4
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "lcls"
	
	@classmethod
	@property
	def classNiceName(cls):
		return "Land class"

	@classmethod
	@property
	def classIconName(self):
		return "asset_land.bmp"

class MaterialClass(RealResData):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0x39b5b09e
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "mtl"
	
	@classmethod
	@property
	def classNiceName(cls):
		return "Material"

	@classmethod
	@property
	def classIconName(self):
		return "asset_mat.bmp"

class ImpostorData(RealResData):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0x2ad457f0
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "imp"
	
	@classmethod
	@property
	def classNiceName(cls):
		return "Impostor data"

	@classmethod
	@property
	def classIconName(self):
		return "asset_rndgrass.bmp"

class ShaderGraph(RealResData):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0xcd5b9736
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "sdr"
	
	@classmethod
	@property
	def classNiceName(cls):
		return "Shader graph"

	@classmethod
	@property
	def classIconName(self):
		return "asset_shaderGraph.bmp"

class RndGrass(RealResData):
	@classmethod
	@property
	def staticClassId(cls) -> int:
		return 0xa7d3ed6a
	
	@classmethod
	@property
	def fileExtension(cls) -> str:
		return "rnd"
	
	@classmethod
	@property
	def classNiceName(cls):
		return "Random grass"

	@classmethod
	@property
	def classIconName(self):
		return "asset_rndgrass.bmp"

# unknown classes :
# 0x73a10e01
# 0x5dff175


REALRES_CLASSES_LIST:tuple[type[RealResData]] = (
	RendInst,
	DynModel,
	CollisionGeom,
	FX,
	GeomNodeTree,
	PhysObj,
	FastPhys,
	Anim2Data,
	AnimTree,
	LandClass,
	MaterialClass,
	ImpostorData,
	ShaderGraph,
	RndGrass, # look for getResClassId in IDA
	Char
)

REALRES_CLASSES_DICT:dict[int, type[RealResData]] = {v.staticClassId:v for v in REALRES_CLASSES_LIST}
