from io import BufferedReader
# from terminable import Terminable


class BinFile(BufferedReader):
	def __init__(self, data:bytes):
		if type(data) == str:
			file = open(data, "rb")
			data = file.read()
			file.close()
		
		self.__data = data
		self.__size = len(data)
		self.__offset = 0
	
	def getData(self):
		return self.__data

	def read(self, bytes:int = None):
		if bytes == None:
			return self.__data
		else:
			if self.__offset + bytes > self.__size:
				raise Exception(f"Out of range: tried to read {bytes} at {self.__offset}, but file size is {self.__size}")
			
			oldOffset = self.__offset
			self.__offset += bytes

			return self.__data[oldOffset:self.__offset]
	
	def tell(self):
		return self.__offset
	
	def seek(self, bytes:int, whence:int = 0):
		if whence == 0:
			self.__offset = 0
		elif whence == 2:
			self.__offset = self.__size
		

		if self.__offset + bytes > self.__size:
			raise Exception(f"Out of range: tried to seek to {bytes} at {self.__offset}, but file size is {self.__size}")
		
		self.__offset += bytes
	
	def getSize(self):
		return self.__size

	def readBlock(self, size:int = None):
		ofs = self.tell()

		if size == None:
			size = self.getSize() - ofs

		self.seek(size, 1)

		return BinBlock(self, ofs, size)

	def readRest(self):
		return self.read(self.getSize() - self.tell())

	def quickSave(self, outName:str):
		file = open(outName, "wb")
		file.write(self.read())
		file.close()
	
	def readEx(self, start:int, end:int):
		return self.__data[start:end]

	def delete(self, size:int):
		fileSz = self.getSize()

		if (size > fileSz):
			raise ValueError("size to delete > fileSz")
		
		offset = self.tell()

		self.__data = self.__data[:offset] + self.__data[offset + size:]

		self.seek(max(offset - size, 0), 0)

		self.__size -= size
	
	def isClosed(self):
		return self.getData() is None
	
	def write(self, data:bytes):
		offset = self.tell()
		sz = len(data)

		self.__data = self.__data[:offset] + data + self.__data[offset + sz:]

		self.seek(sz, 1)
	
	def append(self, data:bytes):
		offset = self.tell()
		sz = len(data)

		self.__data = self.__data[:offset] + data + self.__data[offset:]
		self.__size += sz

		self.seek(sz, 1)

	def close(self):
		self.__data = None
		self.__size = 0
		self.__offset = 0



class BinBlock(BinFile): # guess who accidentally reinvented memoryview() :)
	def __init__(self, parent:BinFile, offset:int, size:int):
		self.__parent = parent
		# self.__data = parent.getData()
		self.__size = size
		self.__offset = 0
		self.__absOffset = offset
		self.__maxAbsOffset = offset + size
	
	def readBlock(self, size:int = None):
		ofs = self.tell()

		if size == None:
			size = self.getSize() - ofs
		
		self.seek(size, 1)

		return BinBlock(self, self.__absOffset + ofs, size)

	def getData(self):
		return self.__parent.getData()
		# return self.__data
	
	def getParentBinFile(self):
		if isinstance(self.__parent, BinFile):
			return self.__parent
		else:
			return self.__parent.getParentBinFile()
	
	def getParent(self):
		return self.__parent
	
	def read(self, bytes:int = None):
		if bytes == None:
			return self.getData()[self.__absOffset:self.__maxAbsOffset]
		else:
			if self.__offset + bytes > self.__size:
				raise Exception(f"Out of range: tried to read {bytes} at {self.__offset}, but file size is {self.__size}")
			
			oldOffset = self.__offset
			self.__offset += bytes

			return self.getData()[self.__absOffset + oldOffset:self.__absOffset + self.__offset]
	
	def tell(self):
		return self.__offset
	
	def absTell(self):
		return self.__absOffset + self.__offset
	
	def getAbsOffset(self):
		return self.__absOffset

	def seek(self, bytes:int, whence:int = 0):
		if whence == 0:
			self.__offset = 0
		elif whence == 2:
			self.__offset = self.__size
		
		if self.__offset + bytes > self.__size:
			raise Exception(f"Out of range: tried to seek to {bytes} at {self.__offset}, but file size is {self.__size}")
		

		self.__offset += bytes
	
	def getSize(self):
		return self.__size
	

def decodeVLQ(file:BinFile, step:int, end:int, breakCond = lambda val: val >= 0, shift:int = 1):
	result = 0
	val = 0

	for i in range(0, end, step):
		val = readEx(1, file, True)
		
		result |= (val & 0x7F) << (i * shift)
		
		if val >= 0:
			break
	
	return result

def toInt(data:bytes):
	return int.from_bytes(data,"little")

# TODO: move all this to the BinFile class and make the BinFile a wrapper for BufferedReaders



def readEx(bytes:int, file:BufferedReader, signed = False):
	return int.from_bytes(file.read(bytes),"little", signed=signed)


def readByte(file:BufferedReader) -> int:
	return readEx(1,file)

def readNameMap(file:BufferedReader, cnt:int, indicesOfs:int, ofs:int, parent = None, longs = False) -> list[str]:
	nameMapData = file.read(indicesOfs - file.tell())

	nameMap = []

	rangeFunc = (lambda x: parent.SafeRange(parent, x)) if parent is not None else (lambda x: range(x))
	readFunc = (lambda x: readLong(x)) if longs else (lambda x: readInt(x))

	prev = readFunc(file) - ofs

	for i in rangeFunc(cnt):
		next = -1 if cnt == i + 1 else readFunc(file) - ofs
		
		nameMap.append(nameMapData[prev:next].decode("utf-8").rstrip("\x00"),)
		
		prev = next
	
	return nameMap

def readShort(file:BufferedReader) -> int:
	return readEx(2,file)

def readSignedShort(file:BufferedReader) -> int:
	return readEx(2,file, signed = True)

def readInt(file:BufferedReader) -> int:
	return readEx(4,file)

def readLong(file:BufferedReader) -> int:
	return readEx(8,file)
