
from PyQt5.QtCore import QObject


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

class TerminableQObject(QObject):
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

class Exportable(Terminable):
	__name = None
	__size = None
	__filePath = None

	def getName(self):
		return self.__name
	
	def getSize(self):
		return self.__size
	
	def getFilePath(self):
		return self.__filePath

	def setName(self, name:str):
		self.__name = name
	
	def setSize(self, size:int):
		self.__size = size
	
	def setFilePath(self, filePath:str):
		self.__filePath = filePath
	
	def getExportable(self):
		return True

SafeRange = Terminable.SafeRange