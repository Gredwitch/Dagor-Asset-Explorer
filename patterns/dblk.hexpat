#pragma pattern_limit 2000000
#pragma array_limit 200000
#include <type/leb128.pat>

namespace type {
	struct DataBlock {
		type::LEB128 nameId;
		type::LEB128 paramsCount;
		type::LEB128 blocksCnt;
		
		if (blocksCnt != 0) {
			type::LEB128 firstBlockId;
		}
	};

	struct DataBlockContainer {
		u8 magic;
		
		type::LEB128 baseNamesNum;
		type::LEB128 baseNamesSize;

		padding[2];

		char sharedName[baseNamesSize - 2];
		
		type::LEB128 blocksCount;
		type::LEB128 paramsCount;
		type::LEB128 dataSize;
		
		char paramsData[dataSize];
		char params[paramsCount * 8];
		
		DataBlock blocks[blocksCount];

	};

	// Container MainBlock @ 0x0;
}