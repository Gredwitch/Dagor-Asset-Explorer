
from fileread import *
from struct import unpack
import log
from enums import *
from decompression import zstdDecompress, CompressedData
from datablock import *
from os import path, getcwd
from terminable import Exportable, SafeRange
from struct import pack
from mesh import MatVData, InstShaderMeshResource


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

class DynModel:
	...
class RendInst(Exportable):
	def __init__(self, name:str, file:BinBlock):
		self.setName(name)

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

			texCnt = 0
			matCnt = 0
		
		vdataNum = readInt(file)
		mvdHdrSz = readInt(file)


		self.__matVData = MatVData(CompressedData(file).decompressToBin(), name, texCnt, matCnt)

		data = file.readBlock(readInt(file) - 4)

		lodCnt = readInt(data)

		data.seek(8, 1) # ptr

		bbox = (unpack("fff", data.read(0xC)), unpack("fff", data.read(0xC)))
		bsphCenter = unpack("fff", data.read(0xC))
		bsphRad = unpack("f", data.read(4))
		bound0rad = unpack("f", data.read(4))

		impostorDataOfs = readInt(data)
		
		occ = tuple(unpack("IIfI", file.read(0x10)) for i in range(4)) # occ table is acutally a float[12]

		log.log(f"Processing {lodCnt} shadermesh resources")
		log.addLevel()

		self.__shaderMesh = tuple(InstShaderMeshResource(file) for i in range(lodCnt))

		log.subLevel()
	
	def getObj(self, lodId:int):
		self.__matVData.computeData()

		vertexData = self.__matVData.getVertexData(self.__matVData.getVDCount() - lodId - 1)

		verts, UVs, faces = vertexData.getVertices(), vertexData.getUVs(), vertexData.getFaces()

		shaderMesh = self.__shaderMesh[lodId].shaderMesh.elems
		
		obj = ""

		log.log(f"Exporting {len(verts)} vertices")

		for v in verts:
			obj += f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n"
		
		log.log(f"Exporting {len(UVs)} UVs")

		for v in UVs:
			obj += f"vt {v[0]:.4f} {v[1]:.4f}\n"

		log.log(f"Exporting {len(faces)} faces with {len(shaderMesh)} shaderMesh elems")
		
		# TODO: make each shader mesh retrieve its vertexData

		curShaderMesh = -1
		nextShaderMesh = -1

		for k, face in enumerate(faces):
			if k >= nextShaderMesh:
				curShaderMesh += 1

				shaderMeshElem = shaderMesh[curShaderMesh]

				nextShaderMesh = k + shaderMeshElem.numFace

				obj += f"usemtl {shaderMeshElem.mat}\n" # TODO: retrive material name

			f = ""

			for idx in face:
				idx += 1

				f += f" {idx}/{idx}"
			
			if f == "":
				continue

			
			obj += f"f{f}\n"
		
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
				
				self.__resData = GameResourcePack.RealResData(grp.getFilePath(), self.__classId, self.__offset, size, self.__name)
			
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
	# sblk = GameResDesc("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\riDesc.bin").getDataBlock()
	# sblk = GameResDesc("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content\\base\\res\\dynModelDesc.bin").getDataBlock()
	# desc = GameResDesc("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\content.hq\\pkg_cockpits\\res\\dynModelDesc.bin")
	# desc = GameResDesc("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\patch\\content\\base\\res\\dynModelDesc.bin")

	# print(desc.getModelMaterials("su_17m2_cockpit"))

	grp = GameResourcePack("samples\\cars_ri.grp")
	
	# resId = grp.getRealResId("chevrolet_150_a_abandoned_a")
	resId = grp.getRealResId("chevrolet_150_a")
	rrd = grp.getRealResource(resId)
	# resEntry = grp.getRealResEntry(resId)
	# print(resId, grp.getResEntryOffsets(resId), resEntry.getRealResData().getOffset())
	# rrd.save()
	ri:RendInst = rrd.getChild()
	ri.exportObj(0)
	# rrd.save()
	# print(rrd)