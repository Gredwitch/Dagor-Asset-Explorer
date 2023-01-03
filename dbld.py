
from os import path, getcwd


from fileread import *
from decompression import CompressedData, zlibDecompress
# from math import * #acos, degrees
from terminable import Exportable
from struct import unpack, pack
from enums import *

import log
# from terminable import Exportable
# from ddsx import DDSxPack
from mesh import MatVData, MaterialData
from datablock import loadDataBlock
from pprint import pprint


def formatMagic(magic:bytes):
	return magic.decode("utf-8").replace("\x00", "")

class ShaderMesh:
	def __init__(self, file:BinFile, vDataCnt:int):
		data = file.readBlock(readInt(file))

		self.dptr = readLong(data)
		self.dcnt = readLong(data)

		self.stageEndElemIdx = tuple(readShort(data) for i in range(vDataCnt + 1))
		
		self._deprecatedMaxMatPass = readInt(data)
		self._resv = readInt(data)

		data.seek(0x14, 1)

		self.vData = readInt(data)
		self.vdOrderIndex = readInt(data)
		self.startV = readInt(data)
		self.numV = readInt(data)
		self.startI = readInt(data)
		self.numFace = readInt(data)
		self.baseVertex = readInt(data)
	
	def __repr__(self):
		return f"<sm seei={self.stageEndElemIdx} dmmp={self._deprecatedMaxMatPass} vData={self.vData} vdOrderIndex={self.vdOrderIndex} startV={self.startV} numV={self.numV} startI={self.startI} numFace={self.numFace} baseVertex={self.baseVertex}>"

class RoHugeHierBitMap2d:
	def __repr__(self):
		return f"<RoHugeHierBitMap2d[{self.s1}, {self.s2}] @ {self.ofs}: w={self.w} h={self.h} bitMapOfs={self.bitMapOfs}>"
	
	def __init__(self, file:BinFile):
		# RoHugeHierBitMap2d<4,3>::create

		self.ofs = file.tell()
		
		assert(readLong(file) == 0x300000004)

		self.data = file.readBlock(readInt(file)) # bitMapOfs
		# w = readInt(self.data)
		# h = readInt(self.data)


class DagorBinaryLevelData(Exportable):
	"""
	VDATA REFRESH	
		ShaderResUnitedVdata<RenderableInstanceLodsResource>::doUpdateJob
			ShaderResUnitedVdata<RenderableInstanceLodsResource>::updateVdata
				ShaderMatVdata::unpackBuffersTo
					ShaderMatVdata::reloadVdataSrc
	RENDINST LOAD : 

		LandMeshManager::loadDump
			LandMeshManager::loadLandClasses
				get_one_game_resource_ex
					get_game_resource_ex
						LandClassGameResFactory::getGameResource
							load_game_resource_pack
								loadGameResPack
									GameResPackInfo::loadPack
										GameResPackInfo::processGrData
											LandClassGameResFactory::createGameResource
												RendInstGameResFactory::getGameResource

	C.f. AcesScene::loadLevel -> load_binary_dump -> AcesScene::bdlCustomLoad

	FRT = FastRayTraceDump
	RIGz = RendInstGenerator (rendinst::loadRIGen)
		rendinst::prepareRIGen
		RendInstGenData::prepareRtData
		
		AcesScene::bdlCustomLoad
			rendinst::loadRIGen
				RendInstGenData::create
	Obj = ObjectsToPlace
	lmap = LandMesh (LandMeshManager::loadDump)
		LandMeshManager::LandMeshManager
		then
		LandMeshManager::loadDump -> LandMeshManager::loadMeshData -> ShaderMatVdata::loadMatVdata -> GlobalVertexData::create -> GlobalVertexData::unpackToBuffers
		
		GenericHeightMapService::exportToGameLandMesh -> ShaderMaterialsSaver::writeMatVdata -> GenericHeightMapService::exportToGameLandMesh

	
	"""
	class DecompressedBlock:
		def __init__(self, file):
			blockSz = readInt(file)
			blockParamsCnt = readInt(file)
			file.seek(blockSz - 4, 1)

	
	def __init__(self, filePath:str):
		self.setFilePath(filePath)
		self.setName(path.splitext(path.basename(filePath))[0])


		self.isValid = False
		
		log.log(f"Loading map {self.getName()}")
		log.addLevel()

		self.__readFile__()

		log.subLevel()
	
	def readTexName(self, file):
		sz = readInt(file)
		name = file.read(sz)

		padding = sz % 4

		if (padding != 0):
			file.seek(4 - padding, 1)
		
		return name
	
	class BlockHeader:
		def __init__(self, file, idx:int):
			self.data = file.read(20)
			self.name = file.read(4)

			log.log(f"BlockHeader {idx}: {formatMagic(self.name)}")
			# log.log(f"BlockHeader {idx}: {formatMagic(self.name)}\t{' '.join(tuple(hex(self.data[i])[2:].upper() for i in range(20)))}")
	

	class RendInstGenData:
		class PregEntCounter:
			structSize = 8

			def __repr__(self):
				return f"<PregEntCounter @ {self.ofs}: p={hex(self.p)}>"

			def __init__(self, file:BinFile):
				# self.ofs = ofs

				# oldO = file.tell()
				# file.seek(ofs, 0)
				self.ofs = file.tell()
				self.p = readLong(file)

				# file.seek(oldO, 0)
			
		class Cell:
			class LandClassCoverage:
				structSize = 8

				def __repr__(self):
					return f"<LandClassCoverage @ {self.ofs}: landClsIdx={self.landClsIdx} msq={hex(self.msq)}>"

				def __init__(self, file:BinFile):
					self.ofs = file.tell()

					# oldO = file.tell()
					# file.seek(ofs, 0)
					
					self.landClsIdx = readInt(file)
					self.msq = readInt(file)

					# file.seek(oldO, 0)
				
			structSize = 32

			def __repr__(self):
				return f"<Cell @ {self.ofs}: rtData={hex(self.rtData)} htMin={self.htMin} htDelta={self.htDelta} riDataRelOfs={hex(self.riDataRelOfs)}>"

			def __init__(self, file:BinFile, id:int):
				# log.log(f"Cell #{id}:")
				# log.addLevel()

				self.ofs = file.tell()

				coverageOfs = readInt(file)
				self.coverageCnt = readInt(file)

				file.seek(coverageOfs, 0)

				self.coverage = tuple(self.LandClassCoverage(file) for i in range(self.coverageCnt))
				
				# log.log("Coverage:")
				# log.addLevel()

				# for k, v in enumerate(self.coverage):
				# 	log.log(f"{k}: {v}")

				# log.subLevel()

				file.seek(self.ofs + 0x10, 0)

				self.rtData = readLong(file)

				self.htMin = readShort(file)
				self.htDelta = readShort(file)
				self.riDataRelOfs = readInt(file)

				# log.log(f"rtData           = {self.rtData}")
				# log.log(f"htMin            = {self.htMin}")
				# log.log(f"htDelta          = {self.htDelta}")
				# log.log(f"riDataRelOfs     = {self.riDataRelOfs}")
				
				entOfs = file.tell()

				# self.entCnt = tuple(Map.RendInstGenData.PregEntCounter(file, entOfs + i * Map.RendInstGenData.PregEntCounter.structSize)
				# 					for i in range(65))

				self.entCnt = tuple(Map.RendInstGenData.PregEntCounter(file) for i in range(65))
				
				# log.log("entCnt:")
				# log.addLevel()

				# for k, v in enumerate(self.entCnt):
				# 	log.log(f"{k}: {v}")

				# log.subLevel()

				# log.subLevel()

		class LandClassRec:
			def __repr__(self):
				return f"<LandClassRec @ {self.ofs}: name={self.landClassName} asset={self.asset} mask={hex(self.mask)}>"
			def __init__(self, file:BinFile):
				self.ofs = file.tell()

				self.landClassNameOfs = readLong(file)
				self.landClassName = None
				self.asset = readLong(file)
				self.mask = readLong(file)
				self.riResMap = readLong(file)
		
		class PregenEntPoolDesc:
			def __repr__(self):
				return f"<PregenEntPoolDesc @ {self.ofs}: name={self.riName}>"
			
			def __init__(self, file:BinFile):
				self.ofs = file.tell()

				self.riResOfs = readLong(file)
				self.riNameOfs = readLong(file)
				self.riName = None
				self.colPair = (readInt(file), readInt(file))
				
				v = readInt(file) # unknown: check if the below is correct

				self.posInst = v & 1
				self.paletteRotation = (v >> 1) & 1
				self._resv30 = v & 0xFFFFFF00

				self.paletteRotationCount = readInt(file)

		def __init__(self, file:BinFile, size:int):
			self.rtData = readLong(file)

			cellsOfs = readInt(file)
			cellCnt = readInt(file)

			log.log(f"Size = {size}b")


			file.seek(8, 1)

			self.numCellW = readInt(file)
			self.numCellH = readInt(file)
			self.cellSz = readShort(file)
			self.dataFlags = readByte(file)
			self.perInstDataDwords = readByte(file)
			self.sweepMaskScale = unpack("f", file.read(4))[0]
			
			file.seek(8, 1) # RoHugeHierBitMap2d<4,3>

			log.log(f"{self.numCellW}x{self.numCellH} cells (total size = {self.cellSz})")
			log.log(f"rtData             = {self.rtData}")
			log.log(f"dataFlags          = {self.dataFlags}")
			log.log(f"perInstDataDwords  = {self.perInstDataDwords}")
			log.log(f"sweepMaskScale     = {self.sweepMaskScale}")

			self.cellCnt = cellCnt

			landClsOfs = readInt(file)
			landClsCnt = readInt(file)

			log.log(f"Found {landClsCnt} landclasses @ {landClsOfs}")

			file.seek(8, 1)

			self.world0Vxz = unpack("ffff", file.read(4 * 4))
			self.invGridCellSzV = unpack("ffff", file.read(4 * 4))
			self.lastCellXZXZ = unpack("ffff", file.read(4 * 4))

			log.log(f"world0Vxz          = {self.world0Vxz}")
			log.log(f"invGridCellSzV     = {self.invGridCellSzV}")
			log.log(f"lastCellXZXZ       = {self.lastCellXZXZ}")

			self.grid2world = unpack("f", file.read(4))[0]
			self.densMapPivotX = unpack("f", file.read(4))[0]
			self.densMapPivotZ = unpack("f", file.read(4))[0]
			self.pregenDataBaseOfs = readInt(file)

			log.log(f"grid2world         = {self.grid2world}")
			log.log(f"densMapPivotX      = {self.densMapPivotX}")
			log.log(f"densMapPivotZ      = {self.densMapPivotZ}")
			log.log(f"pregenDataBaseOfs  = {self.pregenDataBaseOfs}")


			pregenEntOfs = readInt(file)
			pregenEntCnt = readInt(file)

			log.log(f"Found {pregenEntCnt} pregen ents @ {pregenEntOfs}")

			self.fpLevelBin = readLong(file)

			log.log(f"fpLevelBin         = {self.fpLevelBin}")

			file.seek(0x10, 1)

			
			log.log(f"Found {cellCnt} cells @ {cellsOfs}")
			log.addLevel()

			file.seek(cellsOfs, 0)
			self.cells = tuple(self.Cell(file, i) for i in range(cellCnt))

			for k, v in enumerate(self.cells):
				log.log(f"{k}: {v}")

			log.subLevel()

			log.log("Land classes:")
			log.addLevel()

			self.landClasses = []

			for k in range(landClsCnt):
				file.seek(landClsOfs + k * 32, 0)

				v = self.LandClassRec(file)
				
				self.landClasses.append(v)

				if k > 0:
					prev = self.landClasses[k - 1]

					file.seek(prev.landClassNameOfs, 0)

					prev.landClassName = formatMagic(file.read(v.landClassNameOfs - prev.landClassNameOfs))
			
			file.seek(self.landClasses[-1].landClassNameOfs, 0)

			self.landClasses[-1].landClassName = formatMagic(file.read(landClsOfs - self.landClasses[-1].landClassNameOfs))
			
			for k, v in enumerate(self.landClasses):
				log.log(f"{k}: {v}")

			log.subLevel()

			log.log("Pregen ents:")
			log.addLevel()

			self.pregenEnts = []

			for k in range(pregenEntCnt):
				file.seek(pregenEntOfs + k * 32, 0)

				v = self.PregenEntPoolDesc(file)
				
				self.pregenEnts.append(v)

				if k > 0:
					prev = self.pregenEnts[k - 1]

					file.seek(prev.riNameOfs, 0)
					
					prev.riName = formatMagic(file.read(v.riNameOfs - prev.riNameOfs))
			
			file.seek(self.pregenEnts[-1].riNameOfs, 0)

			self.pregenEnts[-1].riName = formatMagic(file.read(size - self.pregenEnts[-1].riNameOfs))

			for k, v in enumerate(self.pregenEnts):
				log.log(f"{k}: {v}")
			
			log.subLevel()
	
	def processBin(self, name:str, file:BinFile, absOfs:int):
		if name == "RqRL":
			sz = readInt(file)
			cnt = readInt(file)

			file.seek(8, 1)

			nameList = file.read(sz - 24)

			file.seek(8, 1)

			indexList = tuple(readLong(file) for i in range(cnt))

			self.resList = tuple(nameList[indexList[k] - indexList[0]:indexList[k + 1] - indexList[0]][:-1].decode("utf-8") for k in range(len(indexList) - 1))
			
			for k, v in enumerate(self.resList):
				log.log(f"{k}:	{v}")
		elif name == "DxP2":
			unknown = readInt(file)
			listSz = readInt(file)
			listCnt = readInt(file)

			padding = lambda x: x + (4 - (x % 4) if x % 4 != 0 else 0)

			self.dxpList = tuple(formatMagic(file.read(padding(readInt(file)))) for i in range(listCnt))

			for k, v in enumerate(self.dxpList):
				log.log(f"{k}:	{v}")
		elif name == "TEX":
			sz = readInt(file)
			# name = file.read(sz)

			# log.log(name.decode("utf-8"))
		elif name == "TEX.":
			pass
		elif name == "lmap":
			lndmMagic = file.read(4) # lndm: land materials
			cnt = readInt(file)

			sz1, sz2 = unpack("ff", file.read(4 * 2))
			mapSizeX = readInt(file)
			mapSizeY = readInt(file)
			fuck1 = readInt(file)
			fuck2 = readInt(file)
			u0 = readInt(file)
			u1 = readInt(file)
			dataBlockOfs = readInt(file)
			unknownOfs1 = readInt(file)
			unknownOfs2 = readInt(file)
			texCnt = readInt(file)
			matCnt = readInt(file)
			vdataCnt = readInt(file) # basically LOD count
			unknownSz = readInt(file)

			texBlockSz = readInt(file)

			texSz = readInt(file)
			texCnt = readInt(file)

			self.cellCnt = mapSizeX * mapSizeY

			file.seek(8, 1)
			
			log.log(f"cnt:		  {cnt}")
			log.log(f"sz1:	      {sz1}")
			log.log(f"sz2:	      {sz2}")
			log.log(f"mapSizeX:   {mapSizeX}")
			log.log(f"mapSizeY:   {mapSizeY}")
			log.log(f"fuck1:      {hex(fuck1)}")
			log.log(f"fuck2:      {hex(fuck2)}")
			log.log(f"u0:         {u0}")
			log.log(f"u1:         {u1}")
			log.log(f"uOfs1:      {unknownOfs1}")
			log.log(f"uOfs2:      {unknownOfs2}")
			log.log(f"vdataCnt:   {vdataCnt}")
			log.log(f"matCnt:     {matCnt}")
			log.log(f"texSz:	  {texSz}")
			log.log(f"texCnt:	  {texCnt}")

			ofs = file.tell()

			nameList = file.read(texSz - 0x10)
			indexList = tuple(readInt(file) for i in range(texCnt))
			
			mMax = lambda x: -1 if x == texCnt else indexList[x] - indexList[0]

			self.lndTex = tuple(formatMagic(nameList[indexList[k - 1] - indexList[0]:mMax(k)]) for k in range(1, texCnt + 1))

			log.log(f"TexList @ +{ofs}:")

			log.addLevel()

			for k, v in enumerate(self.lndTex):
				log.log(f"{k}:	{v}")
			
			log.subLevel()
			
			log.log(f"MVD @ +{file.tell()}")
			
			self.mvd = MatVData(self.getFilePath(), BinFile(CompressedData(file).decompress()), name = self.getName())
			
			ofs = file.tell()

			shaderMesh = file.readBlock(readInt(file))

			log.log(f"ResShaderMesh @ +{ofs}: ")
			log.addLevel()

			# nodeData = [{}]
			
			for i in range(self.cellCnt):
				# log.log(f"Cell {i} @ +{file.tell()}:")
				# log.addLevel()

				block = BinFile(shaderMesh.read(readInt(shaderMesh)))

				fBlock = BinFile(block.read(readInt(block)))

				try:
					landShaderMesh = tuple(ShaderMesh(fBlock, vdataCnt) for i in range(2))
				except Exception as e:
					log.log(e, LOG_ERROR)
					pass
				
				# for v in landShaderMesh:
				# 	log.log(v)
				
				# nodeData[0][str(i)] = (landShaderMesh[0].startV, landShaderMesh[0].numV)
				# log.subLevel()
			# self.nodeData = nodeData
			log.subLevel()


			ofs = file.tell()

			log.log(f"Datablock @ +{ofs}: ")
			log.addLevel()
			
			blockSz = readInt(file)
			blockCnt = readInt(file)
			
			log.log(f"blockSz:		{blockSz}")
			log.log(f"blockCnt:		{blockCnt}")

			for i in range(blockCnt):
				log.log(f"MatBlk {i}:")
				log.addLevel()

				blkSz = readInt(file)
				# nameSz = readInt(file)
				name = self.readTexName(file)

				log.log(f"name:		{name}")
				log.log(f"blkSz:	{blkSz}")
				
				
				ofs = file.tell()

				log.log(f"blk @ +{ofs}:")
				log.addLevel()

				self.datablock = loadDataBlock(file)

				# log.log("Shared namemap: ")
				# log.addLevel()

				# for k, v in enumerate(self.datablock.getSharedBlk().getSharedNameMap()):
				# 	log.log(f"{k}: {v}")

				# log.subLevel()

				log.log("Debuged data: ")
				log.addLevel()

				for v in self.datablock.debug().split("\n"):
					log.log(v)
				
				log.subLevel()

				log.subLevel()
				log.subLevel()

			log.subLevel()

			self.lastLandMeshOfs = absOfs + file.tell()
		elif name == "HM2":
			# if True:
			# 	return
			
			log.log(f"{1}: {unpack('ffff', file.read(0x4 * 4))}")
			log.log(f"{2}: {unpack('fff', file.read(0x4 * 3))}")
			log.log(f"{3}: {unpack('IIII', file.read(0x4 * 4))}")

			try:
				self.hm2CData = CompressedData(file)
				self.hm2CData.decompress(self.getName() + ".hm2")
			except Exception as er:
				log.log(f"Decompession failed: {er}", LOG_ERROR)
		elif name == "RIGz":
			"""
			
			How ARE RIGZ Loaded ?
			AcesScene::bdlCustomLoad:126
				loaded tag and size
				rendinst::loadRIGen(crd, add_resource_cb, 0, &pregenEntStor)
					while (whole block not parsed) => RendInstGenData::create(crd3, layer_idx);
						c
			"""

			sz = file.getSize()
			
			for i in range(1): # 2
				log.log(f"Processing primary rigen layer {i}:")
				log.addLevel()

				ofs = file.tell()

				rigz = CompressedData(file)
				dat = rigz.decompress(self.getName() + f"_main_{i}.rigz")

				riGen = self.processBin("RIGzPrim", BinFile(pack("B", i) + dat), ofs + absOfs) # ADD ONE BYTE TO INDETIFY LAYER IDX

				log.subLevel()

				blockSz = readInt(file)
				o = file.tell() 
				

				"""
				subcells are decompressed as so:
				`scheduleRIGenPrepare'::`2'::RegenRiCell::doJob 
					RendInstGenData::generateCell
				
				Rt = Rotation?

				// CRASH 	24D01D : E8 BE 2B = AcesScene::bdlCustomLoad -> rendinst::loadRIGen
				// CRASH 	3D02DF : E8 0C 58 00 00 E8 = AcesScene::bdlCustomLoad -> rendinst::loadRIGen -> rendinst::prepareRIGen(bool)
				// CRASH 	24D032 : E8 B9 8A 18 00 E8 = AcesScene::bdlCustomLoad -> rendinst::prepareRIGen(bool)

				// CRASH	3CA71C : E8 AF 08 = `scheduleRIGenPrepare'::`2'::RegenRiCell::doJob -> RendInstGenData::generateCell
				// WORKNIG 	9CBD99 : FF 15 39 35 11 00 = logmessage_fmt(1145130828, "[BIN] tag %c%c%c%c sz %dk", &crda, 5i64, v139, v140, v141)
				// WORKNIG 	9CD313 : FF 15 BF 1F 11 00 = logmessage_fmt(1145130828, "[BIN] load_binary_dump completed in %.2f ms", v6)

				// CRASH	3CA75E : E8 8D 4B = RendInstGenData::updateVb(*(RendInstGenData **)(a1 + 24), cellRtData2, *(_DWORD *)(a1 + 32));

				// CRASH	3D5EF5 : E8 96 06 = RendInstGenData::prepareRtData(riGenData, j)
				// NOEFFECT	3CB3A3 : 41 FF D1 48 8B 93 = RendInstGenData::riGenPrepareAddPregenCB

				RendInstGenData::initRender
				"""

				log.log(f"Trying to decompress blocks @ {o} fullSz={blockSz}")
				log.addLevel()
				
				i = 0
				maxOfs = o + blockSz
				

				while o < maxOfs:
					dat = CompressedData(file)
					log.log(f"{i} found @ {o} sz={dat.cSz} cMethod={hex(dat.cMethod)}")
					
					if i == 0:
						# self.processBin("RIGzSec", BinFile(dat.decompress()), 0) # 
						dat.decompress(self.getName() + f"_sec_{i}.rigz")
						
					o = file.tell()
					i += 1
				
				log.subLevel()

				if file.tell() >= sz:
					break
		elif name == "SCN":
			header = file.readBlock(56)

			magic = readInt(header)
			sceneRevision = readInt(header)

			texNum = readInt(header)
			matNum = readInt(header)
			vdNum = readInt(header)
			mvdHdrSz = readInt(header)

			file = file.readBlock(readInt(file))

			texIDs = unpack("I" * texNum, file.read(4 * texNum))

			mvd = MatVData(self.getFilePath(), BinFile(CompressedData(file).decompress()), texNum, matNum, self.getName() + "_scn")
			rest = BinFile(zlibDecompress(file.read(file.getSize() - file.tell())))

			self.sceneMVD = mvd
			
			log.log(mvd)
		elif name == "RIGzPrim":
			idx = readByte(file)
			riGenDataSz = readInt(file)
			riGen = self.RendInstGenData(file.readBlock(riGenDataSz), riGenDataSz)

			if idx == 0:
				riGen.sweepMask = RoHugeHierBitMap2d(file)
			else:
				riGen.sweepMask = 0

			for v in riGen.landClasses:
				v.mask = RoHugeHierBitMap2d(file)
			
			return riGen
			
			
		elif name == "RIGzSec":
			pass
		elif name == "lmap_add":
			cellHdr = unpack("IIII", file.read(4 * 4))
			log.log(f"cellHdr       = {cellHdr}")
			
			file.seek(self.cellCnt, 1)

			for i in range(256):
				hdr = readEx(3, file)

				if hdr >> 8 == 0xFFFF:
					file.seek(0xC, 1)
				else:
					flag = readInt(file)
					sz = readInt(file)
					sz1 = readInt(file)
					magic = readInt(file)
					format = readInt(file)

					file.seek(sz - 8, 1)
			
			name = self.readTexName(file)
			unknown = unpack("II", file.read(4 * 2))

			log.log(f"name          = {name}")
			log.log(f"unknown       = {unknown}")

			cdata = CompressedData(file)

			log.log("Processing LandRayTracerDump:")
			log.addLevel()

			self.processBin("ltdu", BinFile(cdata.decompress(self.getName() + ".ltdu")), 0)

			log.subLevel()

		elif name == "ltdu":
			sz = readInt(file)
			magic = file.read(6)

			numCellsX = readInt(file)
			numCellsY = readInt(file)
			cellSize = unpack("f", file.read(4))[0]
			ofs = unpack("fff", file.read(4 * 3))
			box = (unpack("fff", file.read(4 * 3)), unpack("fff", file.read(4 * 3)))

			log.log("Header:")
			log.addLevel()

			log.log(f"sz             = {sz}")
			log.log(f"magic          = {magic}")
			log.log(f"numCellsX      = {numCellsX}")
			log.log(f"numCellsY      = {numCellsY}")
			log.log(f"ofs            = {ofs}")
			log.log(f"boxLim         = {box[0]}")
			log.log(f"               = {box[1]}")

			log.subLevel()

			cellsDcnt = readInt(file)
			log.log(f"cellsDcnt      = {cellsDcnt} @ {file.tell()}")
			cells = file.readBlock(cellsDcnt << 6)
			
			gridCnt = readInt(file)
			log.log(f"gridCnt        = {gridCnt} @ {file.tell()}")
			grid = file.readBlock(gridCnt * 4)
			
			griHdtdCnt = readInt(file)
			log.log(f"gridHtCnt      = {griHdtdCnt} @ {file.tell()}")
			gridHt = file.readBlock(griHdtdCnt * 4)
			
			allFacesCnt = readInt(file)
			log.log(f"allFacesCnt    = {allFacesCnt} @ {file.tell()}")
			allFaces = tuple(readShort(file) for i in range(allFacesCnt))
			
			allVertsCnt = readInt(file)
			log.log(f"allVertsCnt    = {allVertsCnt} @ {file.tell()}")
			# allVerts = file.readBlock(allVertsCnt * 8)
			allVerts = tuple(
				(-readSignedShort(file) / 256, readSignedShort(file) / 256, readSignedShort(file) / 256, readSignedShort(file) / 256)
				for i in range(allVertsCnt)
			)

			# for k, v in enumerate(allVerts):
			# 	print(f"{k}: {v}")
			
			faceIndicesCnt = readInt(file)
			log.log(f"faceIndicesCnt = {faceIndicesCnt} @ {file.tell()}")
			faceIndices = tuple(readShort(file) for i in range(faceIndicesCnt))


			



	def __readFile__(self):
		self.cdat = {}

		filePath = self.getFilePath()

		fileSz = path.getsize(filePath)
		f = open(filePath, "rb")

		file = BinFile(f.read())

		f.close()
		
		log.log("Header")
		log.addLevel()

		magic = file.read(8)
		d3dresCnt = readInt(file)
		metaSz = readInt(file)

		eVerMagic = file.read(4)
		verSz = readInt(file)
		eVer = file.read(verSz)

		file.seek(verSz % 4, 1)

		blocksCnt = readInt(file)

		log.log(f"magic      = {magic}")
		log.log(f"d3dresCnt  = {d3dresCnt}")
		log.log(f"metaSz     = {metaSz}")
		log.log(f"eVerMagic  = {eVerMagic}")
		log.log(f"eVer       = {eVer}")
		log.log(f"blocksCnt  = {blocksCnt}")

		log.addLevel()

		self.blockHeaders = tuple(Map.BlockHeader(file, i) for i in range(blocksCnt + 1))

		file.seek(metaSz + 0x10, 0)

		log.subLevel()
		
		log.subLevel()

		i = 0

		while file.tell() < fileSz:
			# if True:
			# 	break
			sz = readInt(file)
			bName = file.read(4)
			name = formatMagic(bName)
			ofs = file.tell()

			log.log(f"Block {i}: {name} (sz={sz} @ {ofs - 8}) magic={unpack('I', bName)[0]}={hex(unpack('I', bName)[0])}")
			
			dat = file.readBlock(sz - 4)

			log.addLevel()
			
			# if name == "SCN":
			self.processBin(name, dat, ofs)

			log.subLevel()

			if bName == b"\x00END":
				break
			
			i += 1

		if hasattr(self, ".lastLandMeshOfs"):
			log.log(f"Processing landmesh additionnal")
			log.addLevel()

			file.seek(self.lastLandMeshOfs, 0)
			self.processBin("lmap_add", file, self.lastLandMeshOfs)

			log.subLevel()

	def overwrite(self):
		rep = open("avg_abandoned_factory_main.rigz", "rb")
		repD = zstdCompress(rep.read())
		rep.close()

		rigzHdrOfs = 11602744
		rigzOfs = rigzHdrOfs + 8

		file.seek(0, 0)
		
		data = file.read()
		
		hdrSz = toInt(data[rigzHdrOfs:rigzHdrOfs+4])
		sz = toInt(data[rigzOfs:rigzOfs + 3])
		
		data = data[:rigzOfs] + pack("<L", len(repD))[:3] + pack("<B", 0x40)[:1] + repD + data[rigzOfs + sz + 4:]
		data = data[:rigzHdrOfs] + pack("L", (hdrSz - sz) + len(repD))[:4] + data[rigzHdrOfs + 4:]

		file = open("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\levels\\avg_abandoned_factory.bin", "wb")
		file.write(data)
		file.close()

		log.log("Overwrote")

class LandClass(Exportable): # landclasses used to automatically generated planted and tiled areas on a map : it's useless for us
	def __init__(self, filePath:str):
		self.setFilePath(filePath)
		self.setName(path.splitext(path.basename(filePath))[0])

		f = open(filePath, "rb")
		
		file = BinFile(f.read()[4:])

		f.close()

		cDat = BinFile(CompressedData(file).decompress())

		self.__readFile__(cDat)
	
	def __loadGenLand__(self, file:BinBlock):
		tiledSz = readInt(file)
		uCnt1 = readInt(file)

		file.seek(8, 1)

		plantedSz = readInt(file)
		uCnt2 = readInt(file)

		file.seek(8, 1)

		tiledNameMapOfs = readInt(file)

		file.seek(tiledNameMapOfs, 0)

		tiledNamesIndicesOfs = readInt(file)
		tiledNamesCnt = readInt(file)

		file.seek(tiledNamesIndicesOfs, 0)

		tiledNameIndices = tuple(readLong(file) for i in range(tiledNamesCnt))
		
		file.seek(tiledNameMapOfs + 0x10, 0)
		
		nameSz = lambda indices, i: (indices[i + 1] - indices[i]) if i < len(indices) - 1 else (tiledNamesIndicesOfs - indices[i])

		tiledNames = tuple(formatMagic(file.read(nameSz(tiledNameIndices, i))) for i in range(tiledNamesCnt))

		file.seek(tiledNamesIndicesOfs + 8 * tiledNamesCnt, 0)

		print(file.tell())

	
	def __readFile__(self, file:BinFile):
		# file.quickSave(self.getName() + ".lcls")
		
		sz = readInt(file)

		log.log(f"GenLand @ {file.tell()} sz={sz}")
		log.addLevel()

		self.__loadGenLand__(file.readBlock(sz))

		log.subLevel()


if __name__ == "__main__":
	from pprint import pprint

	# map = Map("D:\\OldWindows\\Users\\Gredwitch\\AppData\\Local\\Enlisted\\content\\base\\levels\\battle_of_berlin_opera - Copy.bin")
	# map = Map("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\levels\\avg_abandoned_factory - Copy.bin")
	# map = Map("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\levels\\britain.bin")
	# map = Map("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\levels\\air_afghan.bin")
	
	# mvd = map.mvd
	# mvd.computeData()
	# mvd.quickExportVDataToObj(0)
	# mvd.save()

	# mvd = map.sceneMVD
	# mvd.computeData()

	# for i in range(mvd.getVDCount()):
	# 	mvd.quickExportVDataToObj(i)
	# lc = LandClass("samples/landc_pack/avg_abadoned_factory_detailed_biome.rrd")
