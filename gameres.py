
from fileread import *
from struct import unpack, pack
import log
from enums import *
from decompression import zstdDecompress, CompressedData
from datablock import *
from os import path, getcwd
from terminable import Exportable, SafeRange
from mesh import MatVData, InstShaderMeshResource, ShaderMesh
from material import MaterialData, MaterialTemplateLibrary,  computeMaterialNames, generateMaterialData
from misc import vectorTransform

###########################################
# 
# - add shaderskinnedmesh parsing (pilot_china)
# - better MTL generation
#
# - fix dynmodel transforms: move all verts to center of rigid
# 	=> make an ObjectNode class: <name> <verts> <faces> <transform> <list of ShaderMeshElems>
# 	=> export each object after making the ObjectNode list
#
# - Rewrote the RendInst OBJ exporter so it takes into account baseVertex and vdOrderIndex ShaderMesh element attributes
# - FIXED: Some RendInst have screwed up face indices
# - FIXED: Some RendInst have incoherent vertex start and end indices
#
# - look into special cases:
#   => fucked skeleton transforms: enlisted weapons (stg44)
#
# - impostor data parsing?
# 

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

		computeMaterialNames(mats)

		return mats

	def getFilePath(self):
		return self.__filePath
	
	def getName(self):
		return self.__fileName


class GeomNodeTree:
	class Node:
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

	def __init__(self, file:BinFile):
		self.__retrieveData__(file)
	
	def __retrieveData__(self, bfile:BinFile):
		
		file = bfile.readBlock(readInt(bfile) & 0x00_00_FF_FF)
		
		nodeCnt = readInt(file) - 1

		# self.__nodes = dict(tuple(tuple((v.name, v) for v in (self.Node(file.readBlock(160), file), ))[0] for i in range(nodeCnt)), )
		nodes = tuple(self.Node(file.readBlock(160), file, i) for i in range(nodeCnt))
		
		
		self.__buildTree__(nodes)

		self.__nodes = nodes
		self.__nodesDict = {v.name:v for v in nodes}
	
	def getNodeByName(self, name:str):
		if name in self.__nodesDict:
			return self.__nodesDict[name]
		
		return None
	
	def getNode(self, nodeId:int):
		return self.__nodes[nodeId]

	def getNodes(self):
		return self.__nodes

	def __buildTree__(self, nodes:dict):
		for nodeName in nodes:
			# node:GeomNodeTree.Node = nodes[nodeName]
			node:GeomNodeTree.Node = nodeName

			childOfs = node.refOfs // 160
			childCnt = node.refCnt

			if childCnt != 0:
				for i in range(childCnt):
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

class RendInst(Exportable):
	def __init__(self, name:str, file:BinBlock):
		self.setName(name)
		self.setFile(file)

		self.dataComputed = False
		self.__textures = None
		self.__materials = None

		log.log(f"Loading {name}")
		log.addLevel()

		self.computeData()

		log.subLevel()

	
	def computeData(self):
		if self.dataComputed:
			return
		
		file = self.getFile()

		self.readHeader(file)
		self.readMatVData(file)
		self.readModelData(file)
		self.readShaderMesh(file)

		self.dataComputed = True

	def readHeader(self, file:BinBlock):
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

			self.setTexCnt(0)
			self.setMatCnt(0)

			self.setMaterials(None)
		else:
			self.setTexCnt(texCnt)
			self.setMatCnt(matCnt)

			self.readTextures(file)

		log.subLevel()
	
	def readTextures(self, file:BinBlock):
		texMapSz = readInt(file)
		texIndicesOfs = readInt(file)
		texCnt = readInt(file)

		file.seek(8, 1)

		nameMapData = file.read(texIndicesOfs - 0x10)
		nameMap = []

		prev = readInt(file) - 0x10
		
		for i in range(texCnt):
			next = texCnt == i + 1 and -1 or readInt(file) - 0x10
			
			nameMap.append(nameMapData[prev:next].decode("utf-8").rstrip("\x00"),)
			
			prev = next
		
		self.setTextures(nameMap)

	def setTextures(self, textures:list[str]):
		self.__textures = textures
	
	def getTextures(self):
		return self.__textures


	def readMatVData(self, file:BinBlock):
		log.log("Loading MatVData")
		log.addLevel()

		self.setMatVData(MatVData(CompressedData(file).decompressToBin(), self.getName(), self.getTexCnt(), self.getMatCnt()))

		log.subLevel()

	def readModelData(self, file:BinBlock):
		ofs = file.tell()

		data = file.readBlock(readInt(file) - 4)

		self.setLodCnt(readInt(data))

		data.seek(8, 1) # ptr

		bbox = (unpack("fff", data.read(0xC)), unpack("fff", data.read(0xC)))
		bsphCenter = unpack("fff", data.read(0xC))
		bsphRad = unpack("f", data.read(4))
		bound0rad = unpack("f", data.read(4))

		impostorDataOfs = readInt(data)
		
		occ = tuple(unpack("IIfI", file.read(0x10)) for i in range(self.getLodCnt())) # occ table is acutally a float[12]

		if impostorDataOfs > 0:
			file.seek(ofs + impostorDataOfs, 0)

			impostorShaderMeshOfs = readLong(file)
			impostorSz = readLong(file)

			self.readImposorData(file.readBlock(impostorSz - (file.tell() - ofs)))
	
	def readImposorData(self, file:BinBlock):
		# cMethod = readLong(file)

		# impostor = CompressedData(file.readRest(), 0x60).decompressToBin()
		# impostor.quickSave("impostor.imp")

		...

	def readShaderMesh(self, file:BinBlock):
		lodCnt = self.getLodCnt()

		log.log(f"Processing {lodCnt} shadermesh resources")
		log.addLevel()

		self.__shaderMesh = tuple(InstShaderMeshResource(file) for i in range(lodCnt))

		log.subLevel()

	def generateMaterials(self):
		if self.getMaterials() is not None or self.__textures is None:
			return
		
		mvd = self.getMatVData()
		mvd.computeData()

		materials = generateMaterialData(self.getTextures(), mvd.getMaterials())
		computeMaterialNames(materials)

		self.setMaterials(materials)


	def getObj(self, lodId:int):
		self.generateMaterials()

		if self.getMaterials() is None and self.__textures is None:
			log.log("No materials were loaded: material groups will be unnamed", LOG_WARN)

		mvd = self.getMatVData()
		mvd.computeData()
		
		vertexDataCnt = mvd.getVDCount()
		shaderMeshElems = self.__shaderMesh[lodId].shaderMesh.elems
		vertexDatas:list[list[MatVData.VertexData, int]] = [None for i in range(vertexDataCnt)]


		obj = ""
		objFaces = ""

		vOfs = 0

		vertexOrder:dict[int, list[ShaderMesh.Elem]] = {}

		for k, elem in enumerate(shaderMeshElems):
			if not elem.vdOrderIndex in vertexOrder:
				vertexOrder[elem.vdOrderIndex] = []
			
			if vertexDatas[elem.vData] == None:
				vData = mvd.getVertexData(elem.vData)
				vertexDatas[elem.vData] = [vData, vOfs]
				
				objVerts = ""
				objUV = ""
				
				verts, UVs = vData.getVertices(), vData.getUVs()
				vCnt = len(verts)

				for i in range(vCnt):
					v = verts[i]

					objVerts += f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n"

					uv = UVs[i]

					objUV += f"vt {uv[0]:.4f} {uv[1]:.4f}\n"

				obj += objVerts + objUV
				vOfs += vCnt

			vertexOrder[elem.vdOrderIndex].append(elem)

			elem.smid = k # TODO: put this in the class constructor

		for orderElems in vertexOrder.values():
			for elem in orderElems:
				log.log(f"Processing shader mesh {elem.smid}")
				log.addLevel()

				vertexData = vertexDatas[elem.vData][0]
				vOfs = vertexDatas[elem.vData][1] + elem.baseVertex

				faces = vertexData.getFaces()

				objFaces += f"usemtl {self.getMaterialName(elem.mat)}\n"
				
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
	
	def exportObj(self, lodId:int, output:str = getcwd()):
		log.log(f"Quick exporting LOD {lodId} as OBJ")
		log.addLevel()

		name = f"{self.getName()}_{lodId}"
		
		self.generateMaterials()
		
		materials = self.getMaterials()

		fileName = f"{name}.obj"
		obj = self.getObj(lodId)

		if materials is not None:
			log.log("Writing MTL")
			log.addLevel()

			mtl = MaterialTemplateLibrary(materials)
			
			file = open(output + "/" + name + ".mtl", "w")
			file.write(mtl.getMTL())
			file.close()

			mtl.exportTextures()

			log.subLevel()

			obj = "mtllib " + name + ".mtl\n" + obj

		file = open(output + "/" + fileName, "w")
		file.write(obj)
		file.close()

		log.subLevel()

		log.log(f"Wrote {len(obj)} bytes to {fileName}")



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
	
	def getMaterialName(self, mat:int):
		if self.__materials is None:
			return mat
		
		return self.__materials[mat].getName()
		
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
		if self.dataComputed:
			return
		
		file = self.getFile()

		self.setGeomNodeTree(None)

		self.readHeader(file)
		self.readMatVData(file)
		self.readModelData(file)
		self.readSceneNodes(file.readBlock(readInt(file)))
		self.readLods(file)
		self.readShaderSkinnedMesh(file)

		self.dataComputed = True

	def readModelData(self, file:BinBlock):
		blockSz = readInt(file)

		data = file.readBlock(blockSz - 4)

		self.setLodCnt(readInt(data))

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
		
		occ = tuple(unpack("IIfI", file.read(0x10)) for i in range(self.getLodCnt())) # occ table is acutally a float[4 * lodCnt]
		

	def readSceneNodes(self, file:BinBlock):
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

		# file.seek(4, 1)

		log.subLevel()

	def readLods(self, file:BinBlock):
		lodCnt = self.getLodCnt()

		log.log(f"Processing {lodCnt} LODs")
		log.addLevel()
		
		self.__lods = tuple(self.Lod(file, i) for i in range(lodCnt))

		log.subLevel()

	def readShaderSkinnedMesh(self, mfile:BinBlock):
		if mfile.tell() + 4 >= mfile.getSize():
			return
		
		cnt = readInt(mfile)

		if cnt == 0:
			return

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

	def setGeomNodeTree(self, skeleton:GeomNodeTree):
		self.__skeleton = skeleton

	def getGeomNodeTree(self):
		return self.__skeleton

	def getObj(self, lodId:int): # TODO: rewrite - use vdorderindex and basevertex attributes
		
		log.log(f"Generating LOD {lodId} OBJ for {self.getName()}")
		log.addLevel()

		mvd = self.getMatVData()
		
		if self.getMaterials() is None:
			log.log("No materials were loaded: material groups will be unnamed", LOG_WARN)
		
		skeleton = self.getGeomNodeTree()

		if skeleton is None:
			log.log("No skeleton was loaded: rigids will not be positionned correctly", LOG_WARN)

		mvd.computeData()

		lod = self.__lods[lodId]
		
		
		vertexDataCnt = mvd.getVDCount()
		lodShaderMesh = lod.shaderMesh
		vertexDatas:list[list[MatVData.VertexData, int, int]] = [None for i in range(vertexDataCnt)]


		obj = ""
		objFaces = ""
		objVerts = ""
		objUV = ""

		vOfs = 0

		vertexDataOrder = []

		log.log("Processing nodes")
		log.addLevel()

		# rootUndo = inverse_matrix(skeleton.getNodeByName("").wtm)

		for shaderMeshId, shaderMesh in enumerate(lodShaderMesh):
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

			for k, elem in enumerate(shaderMesh.elems):
				# log.log(f"Processing shader mesh {k}")
				log.addLevel()

				if vertexDatas[elem.vData] == None:
					vertexDataOrder.append(elem.vData)

					vertexData = mvd.getVertexData(elem.vData)

					verts, UVs = vertexData.getVertices(), vertexData.getUVs()

					vertexDatas[elem.vData] = [vertexData, vOfs, verts]

					vCnt = len(verts)

					for i in range(vCnt):
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
				
					for i in range(elem.startV, elem.startV + elem.numV):
						vert = verts[i]

						if self.__noScale:
							x, y, z = vectorTransform(tm, vert)
						else:
							x, y, z = vert

						vert[0] = x + tm[0][3]
						vert[1] = y + tm[1][3]
						vert[2] = z + tm[2][3]


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
		
		for i in vertexDataOrder:
			for vert in vertexDatas[i][2]:
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


class GameResourcePack(Exportable): # may need cleanup / TODO: rewrite like DXP2
	class RealResData(Exportable):
		isValid = False

		classNames = {
			0x77f8232f:"rendInst", # Renderable Instance
			0x56f81b6d:"geomNodeTree", # Skeleton
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
					# child = SkeletonLegacy(self.getBin())
					child = GeomNodeTree(self.getBin())
				elif self.__classId == 0xACE50000:
					child = CollisionGeom(self.getName(), self.getBin())
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

			file = open(output, "wb")

			file.write(binData)

			file.close()

			log.log(f"Wrote {len(binData)} bytes to {output}")

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
			# if resId != resDataId:
			# 	log.log(f"{self}: inconsistant resId={resId} resDataId={resDataId}", LOG_ERROR)
			
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

		# for resEntry in realResEntries:
			# file.seek(resEntry.getParentOffset(), 0)

			# for i in range(resEntry.getParentCnt()):
			# 	resEntryIdx = readShort(file)

			# 	try:
			# 		resEntry.appendParentRes(realResEntries[resEntryIdx])
			# 	except Exception as e: 
			# 		log.log(f"{e}: {i=} {resEntryIdx=}", LOG_ERROR)

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

		raise ValueError(f"No such resource {name} in gameres {self}")

	def getResourceByName(self, name:str):
		return self.getRealResource(self.getRealResId(name))
	
	def getResEntryOffsets(self, realResId:int):
		ofs = self.__resEntriesOfs + realResId * 0xC
		return f"realResDataOfs1={ofs} realResDataOfs2={ofs + realResId * 0x18}"


class CollisionGeom(Exportable):
	def __init__(self, name:str, file:BinFile):
		self.setName(name)

		self.__readFile__(file)
	
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

	class CollNode(Exportable):
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

			self.__verts:tuple[tuple[float, float, float]] = tuple(unpack("3f", file.read(12)) for _ in range(readInt(file)))
			self.__faces:tuple[tuple[int, int, int]] = tuple(unpack("3I", file.read(12)) for _ in range(readInt(file) // 3))

		def getVerts(self):
			return self.__verts
	
		def getFaces(self):
			return self.__faces

	def __readFile__(self, file:BinFile):
		self.__readHeader__(file)

		self.__nodes = tuple(CollisionGeom.CollNode(file) for _ in range(self.__nodeCnt))
	
	def getObj(self):
		obj = ""

		vOfs = 0

		for node in self.__nodes:
			verts = node.getVerts()

			for v in verts:
				obj += f"v {v[0]:.4f} {v[2]:.4f} {v[1]:.4f}\n"
				obj += f"vt 0.0 0.0\n"
			
			for f in node.getFaces():
				obj += "f"

				for idx in f:
					idx += 1 + vOfs

					obj += f" {idx}/{idx}"
				
				obj += "\n"

			vOfs += len(verts)
			
		return obj

	def exportObj(self, path:str = getcwd()):
		obj = self.getObj()

		file = open(f"{path}/{self.getName()}.obj", "w")
		file.write(obj)
		file.close()


if __name__ == "__main__":
	from assetcacher import ASSETCACHER
	import material
	import trimesh
	# grp = GameResourcePack("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\pilots.grp")
	grp = GameResourcePack("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\collision_pack.grp")
	# grp = GameResourcePack("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\cars_ri.grp")
	# grp = GameResourcePack("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\nvrsk_buildings.grp")
	# grp = GameResourcePack("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\abandoned_factory.grp")

	# ASSETCACHER.appendGameResDesc(GameResDesc("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\riDesc.bin"))

	# def loadDXP(path):
	# 	dxp = material.DDSxTexturePack2(path)

	# 	for ddsx in dxp.getAllDDSx():
	# 		if ddsx != False:
	# 			ASSETCACHER.cacheAsset(ddsx)
	# loadDXP("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\cars_ri.dxp.bin")
	# loadDXP("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content.hq\\hq_tex\\res\\hq_tex_cars_ri.dxp.bin")
	
	# grp.getAllRealResources()
	# rrd = grp.getResourceByName("c")
	# rrd = grp.getResourceByName("pzkpfw_IV_ausf_F")
	# rrd = grp.getResourceByName("pilot_china1")
	# rrd = grp.getResourceByName("af_central_building")
	rrd = grp.getResourceByName("normandy_village_house_2_floor_d_collision")
	# rrd = grp.getResourceByName("chevrolet_150_a_collision")
	# rrd = grp.getResourceByName("pzkpfw_IV_ausf_F_collision")
	# rrd.save()
	# print(rrd.getOffset())
	ri:CollisionGeom = rrd.getChild()
	ri.exportObj()

	mesh = trimesh.load_mesh(rrd.getName() + ".obj", "obj")
	# col = trimesh.interfaces.vhacd.convex_decomposition(mesh)

	print(col)
	# ri.getMatVData().save()
	# ri.setMaterials(ASSETCACHER.getModelMaterials(rrd.getName()))
	# rrd.save()
	# ri.exportObj(0)
	