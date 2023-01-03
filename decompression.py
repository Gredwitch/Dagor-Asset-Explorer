from ctypes import create_string_buffer
from zstandard import ZstdCompressor, ZstdDecompressor
from os import path
from zlib import decompress as zlibdecompress
from zlib import compress as zlibcompress
from pylzma import decompress as lzmadecompress
from pylzma import compress as lzmacompress
from misc import loadDLL
from fileread import *
import log

oodle6 = loadDLL("oo2core_6_win64.dll")

if oodle6 == None:
	print("Failed to load oo2core_6_win64.dll: Oodle compressed data will not be parsed (this applies to models and textures)")

oodle3 = loadDLL("oo2core_3_win64.dll")

if oodle3 == None:
	print("Failed to load oo2core_3_win64.dll: compression to Oodle will not work")


class CompressedData:
	def __init__(self, file:BinFile):
		self.cSz = readEx(3, file)
		self.cMethod = readByte(file)
		self.cData = file.read(self.cSz)
	
	def decompress(self, outName:str = None):
		data = None

		if self.cMethod == 0x40:
			data = zstdDecompress(self.cData)
		elif self.cMethod == 0x80:
			data = oodleDecompress(self.cData)
		
		if outName is not None and not path.exists(outName):
			if data != None:
				cFile = open(outName, "wb")
				cFile.write(data)
				cFile.close()
			
				log.log(f"Wrote {len(data)} bytes to {outName}")
			else:
				log.log(f"Unknown compression method {hex(self.cMethod)}", log.LOG_ERROR)
		
		return data


def zstdDecompress(data:bytes):
	return ZstdDecompressor().decompress(data)

def zstdCompress(data:bytes):
	return ZstdCompressor().compress(data)

# def oodleDecompress(buffer:bytes,bufferSize:int = None):
#     if bufferSize == None:
#         bufferSize = toInt(buffer[:4])
#         buffer = buffer[4:]
	
#     outputBuffer = create_string_buffer(bufferSize)

#     result = oodle.OodleLZ_Decompress(buffer,bufferSize,outputBuffer,bufferSize,-1, 0, 0, 0, 0, 0, 0, 0, 0, 3) # change bufferSize to len(buffer)

#     if result == 0:
#         raise Exception("Oodle error")
		
#     return outputBuffer.raw

def oodleDecompress(data:bytes,dataLen:int = None,bufferSize:int = None):
	if bufferSize == None:
		bufferSize = toInt(data[:4])
		data = data[4:]
	
	if dataLen == None:
		dataLen = len(data)
	
	decompressed_data = create_string_buffer(bufferSize)

	res = oodle6.OodleLZ_Decompress(data,dataLen,
									   decompressed_data,
									   bufferSize, 0, 0, 0, 0, 0, 0, 0, 0, 0,
									   3)
	if res == 0:
		raise Exception("Oodle error")
		
	return decompressed_data.raw

def oodleCompress(buffer:bytes,format:int = 0x6,level:int = 0x4,bufferSize:int = None):
	# public enum OodleFormat : uint
	# {
	#     0x0,LZH,
	#     0x1,LZHLW,
	#     0x2,LZNIB,
	#     0x3,None,
	#     0x4,LZB16,
	#     0x5,LZBLW,
	#     0x6,LZA,
	#     0x7,LZNA,
	#     0x8,Kraken,
	#     0x9,Mermaid,
	#     0xA,BitKnit,
	#     0xB,Selkie,
	#     0xC,Akkorokamui
	# }
	# 
	# public enum OodleCompressionLevel : ulong
	# {
	#     0x0,None,
	#     0x1,SuperFast,
	#     0x2,VeryFast,
	#     0x3,Fast,
	#     0x4,Normal,
	#     0x5,Optimal1,
	#     0x6,Optimal2,
	#     0x7,Optimal3,
	#     0x8,Optimal4,
	#     0x9,Optimal5
	# }

	if bufferSize == None:
		bufferSize = len(buffer)
		
	outputBuffer = create_string_buffer(bufferSize)

	result = oodle3.OodleLZ_Compress(format,buffer,bufferSize,outputBuffer,level,0,0,0)

	if result == 0:
		raise Exception("Oodle error")
	
	data = outputBuffer.raw

	for i in range(len(data) - 1,-1,-1):
		if data[i] != 0:
			data = data[:i]
			
			break
	
	return data

def zlibDecompress(data:bytes):
	return zlibdecompress(data)

def zlibCompress(data:bytes):
	return zlibcompress(data)

def lzmaDecompress(data:bytes):
	return lzmadecompress(data)

def lzmaCompress(data:bytes):
	return lzmacompress(data)