import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from util.fileread import *
from struct import unpack
import util.log as log
from util.enums import *

class DataBlock:
	def __init__(self, nameId:int, paramsCount:int, blocksCount:int, firstBlockId:int, ofs:int, sharedBlk = None, parent = None):
		self.__nameId = nameId
		self.__paramsCount = paramsCount
		self.__blocksCount = blocksCount
		self.__firstBlockId = firstBlockId
		self.__ofs = ofs
		self.__parent:DataBlock = parent
		self.__sharedBlk:SharedDataBlock = sharedBlk

		self.__dataBlocks:list[DataBlock] = []
	
	def __repr__(self):
		return f"<blk nid={self.__nameId} pcnt={self.__paramsCount} bcnt={self.__blocksCount} fblock={self.__firstBlockId} ofs={self.__ofs}>"
	
	def debug(self, indent:str = ""):
		result = f"{indent}{self.getName()}:{self}\n"

		for i in range(self.getParamsCount()):
			param = self.getParamById(i)

			result += f"{indent}\t{self.getParamNameByFlags(param[0])}: {param[1]} ({hex(param[0])})\n"
		for blk in self.getChildren():
			result += blk.debug(indent + "\t")
		
		return result

	def addDataBlock(self, blk):
		blk.__parent = self
		self.__dataBlocks.append(blk)

	def getNameId(self):
		return self.__nameId
	
	def getOfs(self):
		return self.__ofs

	def getParamsCount(self):
		return self.__paramsCount

	def getblocksCount(self):
		return self.__blocksCount

	def getFirstBlockId(self):
		return self.__firstBlockId
	
	def getParent(self):
		return self.__parent
	
	def getChildren(self):
		return self.__dataBlocks
	
	def getIsEmpty(self):
		return self.__blocksCount == 0
	
	def getIsFull(self):
		return self.__blocksCount == len(self.__dataBlocks)
	
	def setSharedBlk(self, sharedBlk):
		self.__sharedBlk = sharedBlk
	
	def getName(self):
		return self.__sharedBlk.getBlockName(self.__nameId - 1)
	
	def getBlock(self, index:int):
		return self.__dataBlocks[index]
	
	def getByName(self, index:str):
		for blk in self.__dataBlocks:
			if self.__sharedBlk.getBlockName(blk.__nameId - 1) == index:
				return blk
	
	def getParamName(self, pId:int):
		if pId < 0 or pId >= self.getParamsCount():
			raise IndexError(pId)
		

		params:BinFile = self.__sharedBlk.params
		# data:bytes = self.__sharedBlk.paramsData

		params.seek(self.getOfs() + pId * 8, 0)

		return self.__sharedBlk.sharedNameMap[(readInt(params) & 0x0FFFFFF) - 1]
	
	def getParamNameByFlags(self, flags:int):
		return self.__sharedBlk.sharedNameMap[(flags & 0x0FFFFFF) - 1]

	def getParamByName(self, name:str):
		nameMap = self.__sharedBlk.sharedNameMap

		for i in range(self.getParamsCount()):
			param = self.getParamById(i)

			if nameMap[(param[0] & 0x0FFFFFF) - 1] == name:
				return param
		
		raise IndexError(name)

	def getParamById(self, pId:int):
		if pId < 0 or pId >= self.getParamsCount():
			raise IndexError(pId)
		

		params:BinFile = self.__sharedBlk.params
		data:bytes = self.__sharedBlk.paramsData

		params.seek(self.getOfs() + pId * 8, 0)

		flags = readInt(params)
		val = readInt(params)

		blockType = flags & 0xF000000

		if blockType == 0x1000000:
			dataSlice = data[val:]

			val = ""

			for k, c in enumerate(dataSlice):
				if c == 0:
					val += dataSlice[:k].decode("ascii")

					break
			
		elif blockType == 0x2000000:
			pass # this blocktype means val = val, in gameresdesc it means val = tex[val], which implies that val is a tex idx
		elif blockType == 0x6000000:
			val = unpack("ffff", data[val:val + 0x10])
		elif blockType == 0x9000000:
			val = True
		else:
			log.log(f"{self.getName()}: Unknown flags {hex(flags)} val={val} ofs={self.getOfs()}", LOG_WARN)
			# ...
			

		return (flags, val)

class SharedDataBlock(DataBlock):
	def __init__(self, *args):
		if isinstance(args[0], int):
			super().__init__(0, 0, args[0], 1, 0)
			self.__meta = args[1]
		elif isinstance(args[0], DataBlock):
			blk:DataBlock = args[0]
			
			super().__init__(0, blk.getParamsCount(), blk.getblocksCount(), 1, 0)

		else:
			raise TypeError

		
		self.sharedNameMap:list[str] = args[1]
		self.paramsData:bytes = args[2]
		self.params:BinFile = args[3]
	
	def getBlockName(self, index:int):
		return self.sharedNameMap[index]

	def getByName(self, index:str):
		if not index in self.sharedNameMap:
			raise IndexError(index)
		else:
			i = self.sharedNameMap.index(index)

			for blk in self.getChildren():
				nid = blk.getNameId() - 1
				
				if i == nid:
					return blk
				
			raise IndexError(index)


def loadDataBlock(file:BinFile):
	magic = readByte(file)

	baseNamesNum = decodeVLQ(file, 1, 5, shift = 7)
	baseNamesSize = decodeVLQ(file, 1, 5, shift = 7)

	sharedNames = tuple(file.read(baseNamesSize)[2:].decode("utf-8").split("\x00")[:-1])
	
	blocksCount = decodeVLQ(file, 7, 0x23, lambda val: val >= 0)
	paramsCount = decodeVLQ(file, 7, 0x23, lambda val: (val & 0x80) == 0)
	dataSize = decodeVLQ(file, 7, 0x23, lambda val: val >= 0)
	offset = file.tell()

	paramsData = file.read(dataSize)
	params = file.readBlock(paramsCount * 8)
	
	dataBlocks:list[DataBlock] = []

	log.log(f"Names count:  {baseNamesNum}")
	log.log(f"Blocks count: {blocksCount}")
	log.log(f"Params count:	{paramsCount} @ {offset + dataSize}")
	log.log(f"Data size:	{dataSize}")
	log.log(f"Data offset:  {offset}")
	log.log(f"Parsing {blocksCount} blocks...")

	offset = 0
	firstBlockId = 0

	for i in range(blocksCount):
		nameId = decodeVLQ(file, 7, 0x23) - 1
		paramsCount = decodeVLQ(file, 7, 0x15)
		blocksCnt = decodeVLQ(file, 7, 0x15)
		
		
		if blocksCnt != 0:
			firstBlockId = decodeVLQ(file, 7, 0x23)
		
		blk = DataBlock(nameId, paramsCount, blocksCnt, firstBlockId, offset)
		# print(blk)
		offset += 8 * paramsCount

		dataBlocks.append(blk)

	# file.close()

	log.log(f"Building datablocks @ {file.tell()}...")

	sharedBlk = SharedDataBlock(dataBlocks[0], sharedNames, paramsData, params)
	dataBlocks[0] = sharedBlk
	
	for blk in dataBlocks:
		blk.setSharedBlk(sharedBlk)

		if blk.getIsFull():
			continue
		
		fBlock = blk.getFirstBlockId()

		for i in range(blk.getblocksCount()):
			blk.addDataBlock(dataBlocks[fBlock + i])
	
	return sharedBlk


if __name__ == "__main__":
	file = open("dynModelDes.dat", "rb")
	bf = BinFile(file.read())
	file.close()
	sblk = loadDataBlock(bf)
	
	blk = sblk.getByName("european_street_lamp_b_destr")#.getByName("matR")
	# tex = blk.getByName("matR").getChildren()[0]

	# for i in range(tex.getParamsCount()):
	# 	print(tex.getParamById(i))
		
	# for k, v in enumerate(sblk.sharedNameMap):
	# 	print(f"{k}: {v}")
	# print(blk.debug())

	for i in range(sblk.getblocksCount()):
		print(sblk.getBlockName(i))
