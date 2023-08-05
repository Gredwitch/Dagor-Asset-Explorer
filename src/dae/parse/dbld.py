
import sys
from os import path, getcwd

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))


from util.fileread import *
from util.decompression import CompressedData, zlibDecompress, zstdCompress, compressBlock
# from math import * #acos, degrees
from util.terminable import Exportable, Terminable, SafeRange
from struct import unpack, pack
from util.enums import *

import util.log as log
from parse.mesh import MatVData, ShaderMesh
from parse.material import DDSx, MaterialData
from parse.datablock import loadDataBlock
from pprint import pprint

from util.misc import loadDLL, matrix_mul
import json
import ctypes

intrinsics = loadDLL("dae_intrinsics.dll")
get_v482 = intrinsics.get_v482

get_v482.argtypes = (ctypes.POINTER(ctypes.c_float), ctypes.c_float, ctypes.c_int)
get_v482.restype = None

# getPos = intrinsics.getPos
# getPos.argtypes = (
# 	ctypes.POINTER(ctypes.c_float * 4),  # dst
# 	ctypes.c_int,  # x
# 	ctypes.c_int,  # z
# 	ctypes.c_int,  # htDelta
# 	ctypes.c_float,  # grid2world
# 	ctypes.c_float,  # cell_xz_sz
# 	ctypes.c_int,  # cellSz
# 	ctypes.POINTER(ctypes.c_float * 4),  # cellOrigin
# 	ctypes.c_int,  # htMin
# 	ctypes.POINTER(ctypes.c_int * 4),  # v110
# 	ctypes.POINTER(ctypes.c_int * 4),  # v112
# 	ctypes.POINTER(ctypes.c_int * 4),  # v114
# )

def formatMagic(magic:bytes):
	return magic.decode("utf-8").replace("\x00", "")


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

	
	def __init__(self, filePath:str, name:str = None, size:int = 0):
		super().__init__(filePath, name, size)
	
	def readTexName(self, file):
		sz = readInt(file)
		name = file.read(sz)

		padding = sz % 4

		if (padding != 0):
			file.seek(4 - padding, 1)
		
		return name
	
	class BlockHeader:
		def __init__(self, file:BinFile, idx:int):
			self.data = file.read(20)
			self.name = file.read(4)

			log.log(f"BlockHeader {idx}: {formatMagic(self.name)}")
			# log.log(f"BlockHeader {idx}: {formatMagic(self.name)}\t{' '.join(tuple(hex(self.data[i])[2:].upper() for i in range(20)))}")
	

	class RendInstGenData(Terminable):
		class PregEntCounter:
			structSize = 8

			def __repr__(self):
				return f"<PregEntCounter: riResIdxLow={hex(self.riResIdxLow)} riCount={hex(self.riCount)} riResIdxHigh={hex(self.riResIdxHigh)} v={self.raw}>"

			def __init__(self, file:BinFile):
				val = readInt(file)

				self.raw = val
				# self.val = pack("I", val)
				# self.val = " ".join((hex(self.val[i])[2:] for i in range(4)))

				self.riResIdxLow = val & (2**10 - 1) # val & 0x3FF

				val >>= 10

				self.riCount = val & (2**20 - 1) # (val >> 10) & 0xFFFFF

				val >>= 20

				self.riResIdxHigh = val & (2**2 - 1)
			
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

			def __init__(self, riGen, file:BinFile, id:int):
				# log.log(f"Cell #{id}:")
				# log.addLevel()

				self.ofs = file.tell()

				coverageOfs = readInt(file)
				self.coverageCnt = readInt(file)

				file.seek(coverageOfs, 0)

				self.id = id

				self.coverage = tuple(self.LandClassCoverage(file) for i in range(self.coverageCnt))
				
				# log.log("Coverage:")
				# log.addLevel()

				# for k, v in enumerate(self.coverage):
				# 	log.log(f"{k}: {v}")

				# log.subLevel()

				file.seek(self.ofs + 0x10, 0)

				self.rtData = readLong(file)

				self.htMin = readSignedShort(file)
				self.htDelta = readShort(file)
				self.riDataRelOfs = readInt(file)

				# log.log(f"rtData           = {self.rtData}")
				# log.log(f"htMin            = {self.htMin}")
				# log.log(f"htDelta          = {self.htDelta}")
				# log.log(f"riDataRelOfs     = {self.riDataRelOfs}")
				
				# self.entCnt = tuple(Map.RendInstGenData.PregEntCounter(file, entOfs + i * Map.RendInstGenData.PregEntCounter.structSize)
				# 					for i in range(65))

				# self.entCnt = [(readLong(file) - rigz.entCntOfs) // 4 for _ in range(65)]
				
				self.entCnt = [self.getEnt(riGen, readLong(file)) for _ in range(65)]
				# self.entCnt = [rigz.entCnt[(readLong(file) - rigz.entCntOfs) // 4] for _ in range(65)]
				

				if self.riDataRelOfs != 0xFFFFFFFF:
					riGen.riDataRel[self.riDataRelOfs] = self
				# log.log("entCnt:")
				# log.addLevel()

				# for k, v in enumerate(self.entCnt):
				# 	log.log(f"{k}: {v}")

				# log.subLevel()

				# log.subLevel()
			def getEnt(self, riGen, l) -> int:
				c = (l - riGen.entCntOfs) // 4

				if c == len(riGen.entCnt):
					c = 0
				
				# return rigz.entCnt[c]:DagorBinaryLevelData.RendInstGenData.PregEntCounter
				return c

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
				return f"<PregenEntPoolDesc @ {self.ofs}: colpair=({hex(self.colPair[0])}, {hex(self.colPair[1])}) posInst={self.posInst} paletteRotation={self.paletteRotation} _resv30={self._resv30} paletteRotationCount={self.paletteRotationCount} name={self.riName}>"
			
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
		
		def getCellXY(self, cell):
			return (cell.id % self.numCellW, cell.id // self.numCellW)
		
		def __init__(self, file:BinFile, size:int):
			self.rtData = readLong(file)

			cellsOfs = readInt(file)
			cellCnt = readInt(file)

			log.log(f"Size = {size}b")


			file.seek(8, 1)

			self.calculatedScale:list[float, float, float, float] = None
			self.numCellW:int = readInt(file)
			self.numCellH:int = readInt(file)
			self.cellSz:int = readShort(file)
			self.dataFlags:int = readByte(file)
			self.perInstDataDwords:int = readByte(file)
			self.sweepMaskScale:float = unpack("f", file.read(4))[0]

			self.riDataRel:dict[int, DagorBinaryLevelData.RendInstGenData.Cell] = {}
			
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

			self.world0Vxz:tuple[float, float, float, float] = unpack("ffff", file.read(4 * 4))
			self.invGridCellSzV:tuple[float, float, float, float] = unpack("ffff", file.read(4 * 4))
			self.lastCellXZXZ:tuple[float, float, float, float] = unpack("ffff", file.read(4 * 4))

			log.log(f"world0Vxz          = {self.world0Vxz}")
			log.log(f"invGridCellSzV     = {self.invGridCellSzV}")
			log.log(f"lastCellXZXZ       = {self.lastCellXZXZ}")

			self.grid2world:float = unpack("f", file.read(4))[0]
			self.densMapPivotX:float = unpack("f", file.read(4))[0]
			self.densMapPivotZ:float = unpack("f", file.read(4))[0]
			self.pregenDataBaseOfs:int = readInt(file)

			log.log(f"grid2world         = {self.grid2world}")
			log.log(f"densMapPivotX      = {self.densMapPivotX}")
			log.log(f"densMapPivotZ      = {self.densMapPivotZ}")
			log.log(f"pregenDataBaseOfs  = {self.pregenDataBaseOfs}")


			pregenEntOfs = readInt(file)
			pregenEntCnt = readInt(file)

			log.log(f"Found {pregenEntCnt} pregen ents @ {pregenEntOfs}")

			self.fpLevelBin:int = readLong(file)

			log.log(f"fpLevelBin         = {self.fpLevelBin}")

			file.seek(0x10, 1)


			file.seek(cellsOfs, 0)
			cellBlock = file.readBlock(0x228 * cellCnt)

			self.entCntOfs = file.tell()
			entCntSz = pregenEntOfs - self.entCntOfs
			entCntNum = entCntSz // 4

			log.log(f"Found {entCntNum} ent counters @ {file.tell()}")
			log.addLevel()

			self.entCnt = tuple(self.PregEntCounter(file) for i in range(entCntNum))

			for k, v in enumerate(self.entCnt):
				log.log(f"{k}: {v}")
			
			log.subLevel()
			
			log.log(f"Found {cellCnt} cells @ {cellsOfs}")
			log.addLevel()

			self.cellsOfs = cellsOfs
			self.cells = tuple(self.Cell(self, cellBlock, i) for i in range(cellCnt))
			

			for k, v in enumerate(self.cells):
				if v.riDataRelOfs != 0xFFFFFFFF and k == 87877:
					if k > 0:
						break

					log.log(f"{k}: {v}")
					log.addLevel()

					cellEntCnt = v.entCnt

					j = 1

					for i in range(0, 64):
						entIdx = cellEntCnt[i]
						oldEntIdx = entIdx
						entNextIdx = cellEntCnt[j]

						ent = self.entCnt[entIdx]
						entNext = self.entCnt[entNextIdx]
						
						if ent.raw < entNext.raw:
						# 	entIdx = i

							# while True:
						# 		# log.log("Hacking...")
								testIdx = ent.riResIdxLow

								# if ent.riResIdxLow >= pregenEntCnt:
								# 	raise Exception("Unfunny!!!")

						# 		entIdx += 1

						# 		if entIdx >= 64:
						# 			raise Exception("entIdx failure")
								
						# 		ent = cellEntCnt[entIdx]
								
						# 		if ent.raw >= entNext.raw:
						# 			break
							
						# 	cellEntCnt[i] = ent

						# log.log(f"{i} {j} {oldEnt} -> {ent} | {entNext}")
						log.log(f"{ent}")

						j += 1
					log.subLevel()

					# log.addLevel()
					# log.log("entCnt:")
					# log.addLevel()

					# for k, v in enumerate(v.entCnt):
					# 	log.log(f"{k}: {v}")

					# log.subLevel()
					# log.subLevel()

			log.subLevel()

			log.log("Land classes:")
			log.addLevel()

			self.landClasses = []

			if landClsCnt > 0:
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
			
			# for k, v in enumerate(self.landClasses):
			# 	log.log(f"{k}: {v}")

			log.subLevel()

			log.log("Pregen ents:")
			log.addLevel()

			self.pregenEnts:list[DagorBinaryLevelData.RendInstGenData.PregenEntPoolDesc] = []

			if pregenEntCnt > 0:
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

		def loadl_epi64(self, mem_addr):
			return (ctypes.c_int * 4)(*unpack("4i", mem_addr[:8] + b"\x00" * 8)) #8h
		
		def processRiDataRel(self, file:BinBlock):
			self.riDataRelFiles = {}

			for riDataRelIdx, riDataRelOfs in enumerate(self.riDataRel):
				riDataRelOfs = file.tell()

				cell:DagorBinaryLevelData.RendInstGenData.Cell = self.riDataRel[riDataRelOfs]

				log.log(f"Cell {cell.id}: RiDataRel {riDataRelIdx} @ {riDataRelOfs} [{cell}]")
				log.addLevel()

				file.seek(riDataRelOfs, 0)

				riDataRel = BinFile(CompressedData(file).decompress())

				self.riDataRelFiles[riDataRelOfs] = riDataRel


				# for k, v in enumerate(cell.entCnt):
				# 	log.log(f"{k}: idx={v} ({hex(self.entCnt[v].riResIdxHigh)}) {hex(self.entCnt[v].riCount)} x [{hex(self.entCnt[v].riResIdxLow)}]{self.pregenEnts[self.entCnt[v].riResIdxLow].riName} = {hex(self.entCnt[v].raw)}")
				
				log.subLevel()
		
		def getCellEntities(self, cellId:int, entities:dict[str, list[tuple[float, float, float, float]]] = {}, enlisted:bool = False, vegetation:bool = False, vegetationOnly:bool = False):
			cell = self.cells[cellId]

			nonVegCnt = 0
			vegCnt = 0

			log.log(f"Gathering entities for cell {cellId}")
			log.addLevel()

			riData:BinFile = self.riDataRelFiles[cell.riDataRelOfs]
			riData.seek(0, 0)
			# riData.quickSave(f"abandoned_factory_0_{cellId}.rirel")

			x = cell.id % self.numCellW
			z = cell.id // self.numCellW

			if cell.htDelta == 0:
				htDelta = 0x2000
			else:
				htDelta = cell.htDelta
			
			cellOrigin = (
				(self.grid2world * x * self.cellSz) + self.world0Vxz[0],
				cell.htMin,
				(self.grid2world * z * self.cellSz) + self.world0Vxz[1],
				1.0)
			
			dz = self.cellSz * self.grid2world * 0.125
			cell_xz_sz = self.cellSz * self.grid2world

			v482 = (ctypes.c_float * 5)()
			get_v482(v482, cell_xz_sz, htDelta)
			v482 = v482[:4]

			self.calculatedScale = v482

			scaleFix = (
				(1, 0, 0, 0),
				(0, 1, 0, 0),
				(0, 0, 1, 0),
				# (0, 0, -1, 0),
				(0, 0, 0, 1),
			)

			# for v in (cell.entCnt):
			# 	print(self.entCnt[v])
			# if True:
			# 	return

			szAdd = self.perInstDataDwords * 4
			
			for i in SafeRange(self, 65):
				j = i + 1

				entCnterIdx = cell.entCnt[i]

				if i == 64:
					nextCnterIdx = entCnterIdx
				else:
					nextCnterIdx = cell.entCnt[j]

				if entCnterIdx < nextCnterIdx:
					log.log(f"{i} {entCnterIdx=}")
					log.addLevel()

					while True:
						if self.shouldTerminate:
							break

						entCnter = self.entCnt[entCnterIdx]
						riIdx = ((entCnter.raw >> 20) & 0xC00) | (entCnter.raw & 0x3FF) # hack

						ent = self.pregenEnts[riIdx]

						if not ent.riName in entities:
							entities[ent.riName] = []
						
						entTab = entities[ent.riName]

						log.log(f"@{riData.tell():09d}\thigh={entCnter.riResIdxHigh} ({ent.paletteRotationCount}, {ent.posInst}) {entCnter.riCount:03d} x {riIdx:03d} [0x{entCnter.riCount:03x} x 0x{riIdx:03x}] val=0x{entCnter.raw:0x} {ent.riName}")

						# v49 = 3 * riIdx

						if ent.posInst == 0:
							for _ in SafeRange(self, entCnter.riCount):
								if enlisted:
									loadedData = riData.read(48 + szAdd)
									array = tuple(unpack("h", loadedData[2 + (i * 4):4 + (i * 4)])[0] for i in range(12))
								else:
									loadedData = riData.read(24 + szAdd)
									array = unpack("12h", loadedData[szAdd:szAdd + 24])
								
								nonVegCnt += 1
								
								if not vegetationOnly:
									pos = tuple(cellOrigin[i] + array[(4 * (i + 1)) - 1] * v482[i] for i in range(3))
									matrix = list(
										list(array[i + j * 4] / 256 for i in range(3)) for j in range(3)
									)

									for l in matrix:
										l.append(0)
									
									matrix.append((0, 0, 0, 1))

									matrix = matrix_mul(scaleFix, matrix)

									entTab.append(((pos[0], pos[2], pos[1]), matrix))

									# seek to (entCnter.riCount * (24 + szAdd)) - (entCnter.riCount - (2 * v49))
						else:
							for _ in SafeRange(self, entCnter.riCount):
								loadedData = riData.read(8 + szAdd)
								vegCnt += 1

								if vegetation:
									array = unpack("4h", loadedData[:8])
									
									entTab.append(((cellOrigin[0] + array[0] * v482[0], 
													cellOrigin[2] + array[2] * v482[2], 
													cellOrigin[1] + array[1] * v482[1]
												), scaleFix))
								

						entCnterIdx += 1

						if entCnterIdx >= nextCnterIdx:
							break
						
						# if entCnter.riResIdxHigh > 0:
							# entTab.pop()

							# return entities
					
					log.subLevel()
				else:
					log.log(f"{entCnterIdx}: loading from land class {self.entCnt[entCnterIdx]}")
					... # load from land class
				
			log.subLevel()
			
			return entities, nonVegCnt, vegCnt
			
	class LandMeshManager:
		class LandMesh:
			class CellData:
				def __init__(self, file:BinBlock,):
					blockSz = readInt(file)

					self.land = tuple((readInt(file), ShaderMesh(file)) for _ in range(2))
					self.decal = (readInt(file), ShaderMesh(file))
					self.combined = (readInt(file), ShaderMesh(file))

					if file.tell() < file.getSize():
						self.patches = (readInt(file), ShaderMesh(file))
					else:
						self.patches = None
			
			class LandClassManager:
				class DecompressedBlock:
					def __init__(self, file:BinBlock):
						blockSz = readInt(file)
						blockParamsCnt = readInt(file)

						file.seek(blockSz - 4, 1) # block params

				def __init__(self, file:BinBlock, cellCnt:int, name:str, filePath:str):
					self.filePath = filePath
					self.name = name

					sz = readInt(file)
					cnt = readInt(file)
					sz2 = readInt(file)

					# TODO: add simple name read function
					nameLen = readInt(file)
					name = file.read(nameLen)

					file.seek(4 - nameLen % 4, 1)

					log.log("Loading datablock")
					log.addLevel()
					self.datablock = loadDataBlock(file)
					log.subLevel()

					if cnt > 1:
						log.log(f"Loading decompresed {cnt} blocks")
						self.blocks = tuple(self.DecompressedBlock(file) for _ in range(cnt - 1))
					else:
						log.log("Landclass has no decompressed block")
						self.blocks = None
					
					unknownHeaders = unpack("IIII", file.read(4 * 4))
					unknownStruct = tuple(unpack("hh", file.read(4)) for _ in range(cellCnt))

					log.log("Loading textures")
					log.addLevel()

					self.textures = tuple(self.__loadTexture__(file, i) for i in range(cellCnt))

					log.subLevel()
				
				def __loadTexture__(self, file:BinBlock, idx:int):
					unknown1 = readEx(3, file)
					unknownVal = readEx(4, file, signed = True)

					sz1 = readInt(file)
					sz2 = readInt(file)
					

					return DDSx(self.filePath, f"{self.name}_lcls_{idx}", file = file.readBlock(sz1).read())

			def __repr__(self):
				return f"<LandMeshManager texCnt={self.texCnt} matCnt={self.matCnt} vdataCnt={self.vdataCnt}>"
			
			def __init__(self, file:BinBlock, cellCnt:int, name:str, filePath:str):
				self.texCnt = readInt(file)
				self.matCnt = readInt(file)
				self.vdataCnt = readInt(file)
				self.mvdHdrSz = readInt(file)

				log.log(self)
				
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
				
				self.matVData = MatVData(CompressedData(file).decompressToBin(), name + ".lmesh", self.texCnt, self.matCnt)
				
				smBlock = file.readBlock(readInt(file))

				log.log(f"Loading {cellCnt} cells")
				log.addLevel()

				self.cells = tuple(self.CellData(smBlock.readBlock(readInt(smBlock))) for _ in range(cellCnt))

				log.subLevel()

				cellBoundsBlock = smBlock.readBlock(readInt(smBlock))

				log.log(f"Loading {cellCnt} cell bounds")
				
				self.cellBounds = tuple((unpack("fff", cellBoundsBlock.read(4 * 3)), unpack("fff", cellBoundsBlock.read(4 * 3))) for _ in range(cellCnt))
				
				log.log(f"Loading {cellCnt} cell bounding radiuses")
				
				self.cellBoundingsRadius = tuple(unpack("f", cellBoundsBlock.read(4))[0] for _ in range(cellCnt))

				log.log(f"Loading land class manager")
				log.addLevel()

				self.landClasses = self.LandClassManager(file, cellCnt, name, filePath)

				log.subLevel()

		def __repr__(self):
			return f"<LandMeshManager {self.mapSize[0]}x{self.mapSize[1]} ({self.cellCnt})>"
		
		def __init__(self, file:BinBlock, name:str, filePath:str):
			magic = readInt(file)
			version = readInt(file)

			assert version == 4

			self.gridCellSize, self.landCellSize = unpack("ff", file.read(8))
			
			self.mapSize = (readInt(file), readInt(file))
			self.origin = unpack("ii", file.read(8))

			hasTileData = readInt(file) > 0

			meshOfs = readInt(file)
			detailOfs = readInt(file)
			tileDataOfs = readInt(file)
			rayTracerOfs = readInt(file)

			self.cellCnt = self.mapSize[0] * self.mapSize[1]

			log.log(self)

			log.log("Loading LandMesh")
			log.addLevel()

			self.lmesh = self.LandMesh(file, self.cellCnt, name, filePath)

			log.subLevel()

	def computeData(self):
		log.log(f"Loading map {self.name}")
		log.addLevel()

		self.__readFile__()

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
			self.lmap = self.LandMeshManager(file, self.name, self.filePath)
		elif name == "HM2":
			# if True:
			# 	return
			
			log.log(f"{1}: {unpack('ffff', file.read(0x4 * 4))}")
			log.log(f"{2}: {unpack('fff', file.read(0x4 * 3))}")
			log.log(f"{3}: {unpack('IIII', file.read(0x4 * 4))}")

			try:
				self.hm2CData = CompressedData(file)
				self.hm2CData.decompress(self.name + ".hm2")
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

			self.riGenLayers:list[DagorBinaryLevelData.RendInstGenData] = []
			
			for layerIdx in range(2):
				layerName = "primary" if layerIdx == 0 else "secondary"

				log.log(f"Processing {layerName} rigen layer:")
				log.addLevel()

				ofs = file.tell()

				# riGen = self.processBin("RIGzPrim", BinFile(pack("B", layerIdx) + CompressedData(file).decompress(self.name + f"_{layerName}.rigz")), ofs + absOfs) # ADD ONE BYTE TO IDENTIFY LAYER IDX
				try:
					cData = CompressedData(file).decompress()
				except:
					break
				
				if cData is None:
					break
				
				riGen = self.processBin("RIGzPrim", BinFile(pack("B", layerIdx) + cData), ofs + absOfs) # ADD ONE BYTE TO IDENTIFY LAYER IDX
				riGen.ofs = ofs + absOfs
				
				self.riGenLayers.append(riGen)
				
				riGen.processRiDataRel(file.readBlock(readInt(file)))
				# riGen.processRiDataRel(file.readBlock(readInt(file)), self.name, layerName)

				log.subLevel()

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

			mvd = MatVData(self.filePath, BinFile(CompressedData(file).decompress()), texNum, matNum, self.name + "_scn")
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

			self.processBin("ltdu", BinFile(cdata.decompress(self.name + ".ltdu")), 0)

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

		filePath = self.filePath

		fileSz = path.getsize(filePath)
		f = open(filePath, "rb")

		file = BinFile(f.read())

		f.close()
		
		log.log("Header")
		log.addLevel()

		magic = file.read(8)

		if magic != b"DBLD3x64":
			raise Exception(f"Invalid magic: {magic}. Not a map file?")

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

		self.blockHeaders = tuple(DagorBinaryLevelData.BlockHeader(file, i) for i in range(blocksCnt + 1))

		file.seek(metaSz + 0x10, 0)

		log.subLevel()
		
		log.subLevel()

		i = 0

		self.d3dresCnt = d3dresCnt

		self.tags:dict[int, int] = {}

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

			iName = toInt(bName)

			if iName in self.tags:
				raise Exception(f"Tag {bName}={hex(iName)} already present in tags dict")
			
			self.tags[iName] = ofs
			
			if name == "RIGz":
				self.processBin(name, dat, ofs)

			log.subLevel()

			if iName == TAG_END:
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

	def replacePregenCounters(self, riGenLayerIdx, data:bytes):
		log.log("replacePregenCounters")

		riGen:DagorBinaryLevelData.RendInstGenData = self.riGenLayers[riGenLayerIdx]
		

		newData = b""

		for k, v in enumerate(riGen.entCnt):
			if v.riResIdxLow == -1:
				# riResIdxLow = 0
				# riCount = 0
				# riResIdxHigh = 0
				riResIdxLow = 173 # 2**10 - 1 # v.riResIdxLow
				riCount = v.riCount
				riResIdxHigh = v.riResIdxHigh

				newRaw = riResIdxLow + (riCount << 10) + (riResIdxHigh << 20)
				
				newData += pack("I", newRaw)
			else:

				# v.raw = 0xFF_FF_FF_00
				newData += pack("I", v.raw)

		return data[:riGen.entCntOfs + 4] + newData + data[(riGen.entCntOfs + 4) + len(riGen.entCnt) * 4:]

	def replaceCellPregen(self, riGenLayerIdx, data:bytes): # replace riRelDataOfs
		log.log("replaceCellPregen")
		log.addLevel()

		riGen:DagorBinaryLevelData.RendInstGenData = self.riGenLayers[riGenLayerIdx]

		# empty = pack("65Q", *(587796 for _ in range(65)))
		
		for cell in riGen.cells:
			if not cell.riDataRelOfs in riGen.riDataRel:
				# log.log(f"Replacing pregen table for cell {cell.id}")
				# ofs = 0x20 + riGen.cellsOfs + 4 +  cell.id * 0x228
				
				# data = data[:ofs] + empty + data[ofs + 0x208:]

				continue
		
			if cell.id == 976:
			# 	log.log(f"Removing coverage count for cell {cell.id} @ {ofs}")
			# 	ofs = 4 + 4 + riGen.cellsOfs + (cell.id * 0x228)

			# 	data = data[:ofs] + pack("I", 0) + data[ofs + 4:]

				
				continue

			ofs = 4 + 28 + riGen.cellsOfs + (cell.id * 0x228)

			log.log(f"Removing riRelData offset for cell {cell.id} @ {ofs}")
			
			data = data[:ofs] + pack("I", 2**32 - 1) + data[ofs + 4:]
			
			del riGen.riDataRel[cell.riDataRelOfs]
			cell.riDataRelOfs = None

		# log.log("RiGen ent cnt")
		# log.addLevel()

		# for k, v in enumerate(riGen.entCnt):
		# 	log.log(f"{k} {hex(v.raw)} {hex(v.riResIdxLow)}\t{hex(v.riCount)}\t{hex(v.riResIdxHigh)}\t\t{riGen.pregenEnts[v.riResIdxLow].riName}")

		# log.subLevel()

		# file = open("test.dat", "wb")
		# file.write(data)
		# file.close()

		log.subLevel()

		return data

	def replaceRIGz(self, outfile:str, primData:bytes = None):
		ofs = self.riGenLayers[0].ofs - 8

		log.log(f"Replacing RIGz @ {ofs}")
		log.addLevel()

		f = open(self.filePath, "rb")
		data = f.read()
		f.close()

		sz = int.from_bytes(data[ofs:ofs + 4], "little")

		oldRigz = BinFile(data[ofs + 8: ofs + 4 + sz])

		cData = CompressedData(oldRigz)
		rest = oldRigz.readRest()

		if primData is None:
			log.log(f"Loading primary layer from {self.name}_primary.rigz")
			f = open(f"{self.name}_primary.rigz", "rb")
			primData = f.read()
			f.close()

		# primData = self.replacePregenCounters(0, primData)
		primData = self.replaceCellPregen(0, primData)
		

		# for v in self.rigz[0].cells:
		# 	if v.riDataRelOfs != 0xFFFFFFFF:
		# 		primData = primData[:v.ofs + 32] + pack("I", 0xFFFFFFFF) + primData[v.ofs + 32 + 4:]
		
		newRigz = compressBlock(primData, 0x40, 0)
		
		newRigz += rest

		data = data[:ofs] + pack("I", len(newRigz) + 4) + data[ofs + 4:ofs + 8] + newRigz + data[ofs + 4 + sz:]
		# data = data[ofs + 4 + sz:]

		f = open(outfile, "wb")
		f.write(data)
		f.close()

		log.log(f"Wrote {len(data)} to {outfile}")

		log.subLevel()

		return primData


	def readCompressedBlock(self, file:BinFile):
		sz = readEx(3, file)
		cM = readByte(file)

		file.seek(-4, 1)

		return file.read(sz + 4)
	
	def removeTerrain(self, data:bytes):
		log.log("Removing terrain")
		log.addLevel()

		lmapOfs = self.tags[TAG_LMAP] - 4	

		log.log(f"Tag lmap @ {lmapOfs}")
		data = data[:lmapOfs] + pack("I", 0x12_34_56_78) + data[lmapOfs + 4:]
		
		tags = (TAG_HM2, TAG_LNV3, TAG_LMP2)

		for tag in tags:
			ofs = self.tags[tag] - 4
			log.log(f"Tag {data[ofs:ofs + 4]} @ {ofs}")
			data = data[:ofs] + pack("I", 0x12_34_56_78) + data[ofs + 4:]

		log.subLevel()

		return data

	def replaceRIGzLayerContents(self, toReplace, primLayer):
		ofs = self.riGenLayers[0].ofs - 8

		log.log(f"Replacing RIGz Pregen @ {ofs}")

		f = open(self.filePath, "rb")
		data = f.read()
		f.close()

		sz = int.from_bytes(data[ofs:ofs + 4], "little")

		file = BinFile(data[ofs + 8: ofs + 4 + sz])
		
		if primLayer is None:
			primLayer = CompressedData(file).decompress()
		else:
			CompressedData(file)

		dataOfs = file.tell() + ofs + 8

		riRelBlock = file.readBlock(readInt(file))

		# for i in range(7, 8):
		# 	primLayer, riRelBlock = self.replaceRiRelData(riRelBlock, i, primLayer)

		# primLayer, riRelBlock = self.replaceRiRelData(riRelBlock, 5, primLayer)
		primLayer, riRelBlock = self.replaceRiRelData(riRelBlock, 3, primLayer)

		riRelBlock = BinFile(riRelBlock) if isinstance(riRelBlock, bytes) else riRelBlock

		riRelData = riRelBlock.read()

		primLayer = compressBlock(primLayer, 0x40)

		newRigz = primLayer + pack("I", len(riRelData)) + riRelData + file.readRest()

		data = data[:ofs] + pack("I", len(newRigz) + 4) + data[ofs + 4:ofs + 8] + newRigz + data[ofs + 4 + sz:]

		data = self.removeTerrain(data)
	
		f = open(toReplace, "wb")
		f.write(data)
		f.close()

		log.log(f"Wrote {len(data)} to {toReplace} @ {ofs + 8 + len(primLayer) + 4} (RIGz @ {ofs})")
	
	def replaceRiRelData(self, block:BinBlock, riRelIdx:int, primLayer:bytes):
		if isinstance(block, bytes):
			block = BinFile(block)
		
		block.seek(0, 0)

		prevData = b""

		for _ in range(riRelIdx):
			prevData += self.readCompressedBlock(block)
		
		log.log(f"Replacing riRel {riRelIdx}") # @ {block.absTell()}")
		log.addLevel()

		oldBlockSz = len(self.readCompressedBlock(block))
		ofsToCheck = block.tell()

		# block = compressedBlock + block

		f = open(f"normandy_3_976.rirel", "rb")

		# newData = compressBlock(b"\x00" * len(f.read()), 0x40)
		newData = compressBlock(f.read(), 0x40)

		f.close()

		riGen:DagorBinaryLevelData.RendInstGenData = self.riGenLayers[0]

		newRiDataRelOfs = {}

		for idx, ofs in enumerate(riGen.riDataRel):
			cell = riGen.riDataRel[ofs]

			if idx == riRelIdx:
				log.log(f"Removing coverage count for cell {cell.id} @ {ofs}")
				coverageOfs = 4 + riGen.cellsOfs + (cell.id * 0x228) + 4

				primLayer = primLayer[:coverageOfs] + pack("I", 0) + primLayer[coverageOfs + 4:]

			if ofs < ofsToCheck:
				newRiDataRelOfs[ofs] = cell

				continue
		
			riRelDefOfs = 4 + riGen.cellsOfs + (cell.id * 0x228) + 28
			newRiRelOfs = (ofs - oldBlockSz) + len(newData)

			newRiDataRelOfs[newRiRelOfs] = cell

			log.log(f"Changing riRelOfs {ofs} -> {newRiRelOfs} for cell {cell.id} @ {riRelDefOfs} ")

			primLayer = primLayer[:riRelDefOfs] + pack("I", newRiRelOfs) + primLayer[riRelDefOfs + 4:]

		log.subLevel()

		riGen.riDataRel = newRiDataRelOfs

		return primLayer, prevData + newData + block.readRest()

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
		# file.quickSave(self.name + ".lcls")
		
		sz = readInt(file)

		log.log(f"GenLand @ {file.tell()} sz={sz}")
		log.addLevel()

		self.__loadGenLand__(file.readBlock(sz))

		log.subLevel()


if __name__ == "__main__":
	# import gameres
	import os
	# from assetcacher import ASSETCACHER

	# map = DagorBinaryLevelData("D:\\OldWindows\\Users\\Gredwitch\\AppData\\Local\\Enlisted\\content\\base\\levels\\normandy_urban_area_2x2.bin")
	# map = DagorBinaryLevelData("D:\\OldWindows\\Users\\Gredwitch\\AppData\\Local\\Enlisted\\content\\base\\levels\\battle_of_berlin_opera.bin")
	map = DagorBinaryLevelData("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder\\levels\\avg_normandy.bin")

	# primData = None
	# toReplace = "D:\\OldWindows\\Users\\Gredwitch\\AppData\\Local\\Enlisted\\content\\base\\levels\\normandy_coastal_area_1x1.bin"
	# primData = map.replaceRIGz(toReplace, primData)
	# map.replaceRIGzLayerContents(toReplace, primData)

	def exportRiGen(map:DagorBinaryLevelData, write:bool = True, enlisted:bool = False, vegetation:bool = True, cells:tuple = None):
		entities = {}
		riGen = map.riGenLayers[0]

		for ofs in riGen.riDataRel:
			cell = riGen.riDataRel[ofs]
			
			if cells is not None and cell.id not in cells:
				continue

			riGen.getCellEntities(cell.id, entities, enlisted, vegetation)
			
		if write:
			file = open("samples/rigen.json", "w")
			file.write(json.dumps(entities, indent = 4))
			file.close()

			log.log("Wrote samples/rigen.json")

		return entities

	def exportEnts(map:DagorBinaryLevelData, entities):
		gameRes:list[gameres.GameResourcePack] = []
		
		path = "C:/Program Files (x86)/Steam/steamapps/common/War Thunder/content/base/res/"
		# path = "D:/OldWindows/Users/Gredwitch/AppData/Local/Enlisted/content/base/res/"

		log.log(f"Loading GRP from {path}")
		log.addLevel()

		for file in os.listdir(path):
			if os.path.splitext(file)[1] == ".grp":
				gameRes.append(gameres.GameResourcePack(path + file))

		log.subLevel()

		for ent in entities:
			if os.path.exists(f"samples/{ent}_0.obj"):
				log.log(f"Skipping already exported model {ent}", LOG_WARN)

				continue
			
			rrd = None

			for grp in gameRes:
				try:
					rrd = grp.getResourceByName(ent)
					break
				except:
					pass
			
			if rrd is None:
				log.log(f"Could not find {ent} from our loaded gamerespacks", LOG_ERROR)
				# raise Exception(f"Could not find {ent} from our loaded gamerespacks")

				continue

			level = log.curLevel
			try:
				ri = rrd.getChild()
			except:
				log.log(f"Failed to load RendInst {ent}", LOG_ERROR)
				log.curLevel = level

				continue


			if isinstance(ri, gameres.RendInst):
				try:
					ri.exportObj(0, "samples")
				except:
					log.log(f"Failed to export {ent}", LOG_ERROR)
			else:
				log.log(f"Ignoring entity {ent}: rrd child returned a {ri}")

	
	map.computeData()
	
	riGen = map.riGenLayers[0]
	# print(riGen.cellCnt)

	from pprint import pprint
	data = []
	for ofs in riGen.riDataRel:
		cell = riGen.riDataRel[ofs]

		entities = {}
		riGen.getCellEntities(cell.id, entities, False, False)
		data.append((riGen.getCellXY(cell), len(entities)))
		pprint(entities["normandy_village_shed_b"])

		break
	
	# entities = exportRiGen(map, write = True, enlisted = True, vegetation = False, cells = (528, ))
	# exportEnts(map, entities)
	
	log.log("Done")

	"""
import bpy
import bmesh
from json import loads
from mathutils import Vector, Matrix

MERGE_DISTANCE = 0.001
DECIMATE_RATIO = 0.4

def placeInstances(riGen, entities):
    for entIdx, ent in enumerate(entities):
        transformTab = riGen[ent]
        selected_object = entities[ent]
        
        for k, transform in enumerate(transformTab):
            print(f"[D] [{entIdx + 1}/{len(entities)}]: {ent} - Processing {k + 1}/{len(transformTab)}") 
            
            new_object = selected_object.copy()
            new_object.data = selected_object.data.copy()
            
            new_object.matrix_world @= Matrix(transform[1])
            new_object.location = Vector(transform[0])
            
            bpy.context.collection.objects.link(new_object)
        
        bpy.data.objects.remove(selected_object)

def optimizeObject(obj):
    print("[D] \tOptimizing")
    
    bpy.context.view_layer.objects.active = obj
    
    bpy.ops.object.mode_set(mode = "EDIT")
    
    bm = bmesh.from_edit_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts = bm.verts, dist = MERGE_DISTANCE)
    bmesh.update_edit_mesh(obj.data)
    
    bpy.ops.object.mode_set(mode = "OBJECT")
    
    decimateMod = obj.modifiers.new(name = "Decimate", type = "DECIMATE")
    decimateMod.ratio = DECIMATE_RATIO
    
    bpy.ops.object.modifier_apply(modifier = decimateMod.name)
    

def loadEntities(riGen, path:str):
    entities = {}

    for k, ent in enumerate(riGen):
        print(f"Loading entity {k + 1}/{len(riGen)}")
        
        if len(riGen[ent]) == 0:
            print(f"[D] \tSkipping {ent}")
            
            continue
        
        try:
            imported_object = bpy.ops.import_scene.obj(filepath = f"{path}/{ent}_0.obj")
            selected_object = bpy.context.selected_objects[0]
            
            entities[ent] = selected_object
        except Exception as e:
            print(f"[E] \tFailed to import {ent}: {e}")
            
            continue
        
            
        optimizeObject(entities[ent])
    
    return entities

def loadRiGen(path:str):
    file = open(f"{path}/rigen.json", "rb")
    riGen = loads(file.read())
    file.close()

    entities = loadEntities(riGen, path)
    placeInstances(riGen, entities)
    
    bpy.context.view_layer.update()


loadRiGen("C:/Users/Gredwitch/Documents/WTBS/DagorAssetExplorer/samples")
	"""