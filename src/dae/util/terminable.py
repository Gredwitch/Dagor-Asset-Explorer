
import sys
from os import path, getcwd

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import util.log as log
from PyQt5.QtCore import QObject
from abc import ABC, abstractmethod
from util.fileread import BinFile

class Terminable:
	class SafeRange:
		def __init__(self, parent, start:int , stop:int = None, step:int = None): # ugly but fuck u
			self.parent = parent

			if stop == None and step == None:
				self.stop = start
				self.start = 0
				self.step = 1
			elif step == None:
				self.start = start
				self.stop = stop
				self.step = 1
			else:
				self.start = start
				self.stop = stop
				self.step = step
			
			if self.step == 0:
				raise ValueError("SafeRange() arg 3 must not be zero")
			
			self.cur = self.start - self.step

			if self.step < 0:
				self.val1 =  self.start - self.step
				self.val2 =  self.stop - self.step
			else:
				self.val1 = self.stop
				self.val2 = self.start
		
		def __iter__(self):
			return self
		
		def __next__(self):
			return self.next()
		
		def next(self):
			self.cur += self.step

			if self.cur >= self.val1 or self.cur < self.val2 or self.parent.shouldTerminate() == True:
				raise StopIteration()
			else:
				return self.cur

	__shouldTerminate = False
	__subTask = None
	__subProcess = None

	def terminate(self):
		self.__shouldTerminate = True

		if self.__subTask != None:
			self.__subTask.terminate()
		
		if self.__subProcess != None:
			self.__subProcess.kill()
	
	def setSubTask(self, var):
		self.__subTask = var
	
	def setSubProcess(self, subProcess):
		self.__subProcess = subProcess
	
	def shouldTerminate(self):
		return self.__shouldTerminate

class TerminableQObject(QObject, Terminable):
	def __init__(self, *args, **kwargs):
		super().__init__(args, kwargs)


class FilePathable:
	def __init__(self, filePath:str = None, name:str = None, size:int = 0):
		if filePath is not None and name is None:
			name = path.splitext(path.basename(filePath))[0]
		
		self.__filePath = filePath
		self.__name = name
		self.__size = size

	@property
	def name(self):
		return self.__name
	
	@property
	def filePath(self):
		return self.__filePath

	@property
	def size(self):
		return self.__size
	
	def _setSize(self, size:int):
		self.__size = size
	
	def _setName(self, name:str):
		self.__name = name
	
	def _setFilePath(self, filePath:str):
		self.__filePath = filePath


class Exportable(Terminable, FilePathable, ABC):
	def __init__(self, filePath:str, name:str = None, size:int = 0):
		FilePathable.__init__(self, filePath, name, path.getsize(filePath) if size == 0 else size)
		
		self.__isValid:bool = False
	
	def _setValid(self):
		self.__isValid = True

	@property
	def exportable(self):
		return True

	@property
	def valid(self):
		return self.__isValid
	
	@classmethod
	@property
	@abstractmethod
	def classIconName(self) -> str:
		...
	
	@property
	def iconName(self):
		return self.classIconName

	@classmethod
	@property
	@abstractmethod
	def classNiceName(cls) -> str:
		...
	
	@classmethod
	@property
	@abstractmethod
	def fileExtension(cls) -> str:
		...
	
	@property
	def niceName(self) -> str:
		return self.classNiceName

class Packed(Exportable):
	def __init__(self, filePath:str, name:str = None, size:int = 0, offset:int = 0):
		FilePathable.__init__(self, filePath, name, size)

		self.__offset = offset
		self.__cachedBin = None
	
	@property
	def offset(self):
		return self.__offset

	def setCachedBinFile(self, file:BinFile):
		if file is None:
			self.__cachedBin = None
		else:
			file.seek(self.__offset)

			self.__cachedBin = file.readBlock(self.size)

	def getBin(self) -> BinFile:
		if self.__cachedBin is None or self.__cachedBin.isClosed():
			file = open(self.filePath, "rb")

			file.seek(self.offset, 1)

			bin = BinFile(file.read(self.size))

			file.close()

			return bin
		else:
			return self.__cachedBin

	def _save(self, output:str, binData:bytes):
		output = path.normpath(f"{output}/{self.name}.{self.fileExtension}")

		file = open(output, "wb")

		file.write(binData)

		file.close()

		log.log(f"Wrote {len(binData)} bytes to {output}")
	
	def save(self, output:str = getcwd()):
		self._save(output, self.getBin().read())

class Pack(Exportable):
	def __init__(self, filePath:str, name:str = None, size:int = 0):
		super().__init__(filePath, name, size)

		self.__cachedBin = None
	
	def enableCaching(self):
		f = open(self.filePath, "rb")
		file = BinFile(f.read())
		f.close()

		self.__cachedBin = file
	
	def clearCache(self):
		self.__cachedBin.close()
		self.__cachedBin = None
	
	@property
	def cachedBinFile(self):
		return self.__cachedBin
	
	@abstractmethod
	def getPackedFiles(self) -> list[Packed]:
		...


SafeRange = Terminable.SafeRange