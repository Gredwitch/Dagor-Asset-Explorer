
struct Header {
	u32 magic;
	u32 unknown;
	
	u32 fileCnt;
	u32 filesOfs;
	
	u32 nameMapIndicesOfs;
	u32 nameMapIndicesCnt;
	
	padding[8];
	
	u32 ddsxHeadersOfs;
	u32 ddsxHeadersCnt;
	
	padding[8];
	
	u32 ddsxRecordsOfs;
	u32 ddsxRecordsCnt;
};

struct DDSxHeader {
	u32 label;
	u32 d3dformat;

	u24 flags;
	u8 compressionMethod;
	
	u16 w;
	u16 h;
	
	u8 levels;
	u8 hqPartLevels;
	
	u16 depth;
	u16 bitsPerPixel;
	
	u8 lQmip;
	u8 dxtShift;
	
	/*
	
	u4 lQmip;
	u4 mQmip;
	u4 dxtShift;
	u4 uQmip;
	
	*/
	
	u32 memSz;
	u32 packedSz;
};

struct DDSxRec {
	u64 baseTexture;
	u32 D3DRESID;
	u32 ofs;
	u32 packedDataSize;
	u32 _resv;
};

Header Hdr @ 0;
char nameMap[Hdr.nameMapIndicesOfs - 0x38] @ 0x48;
u64 nameMapIndices[Hdr.nameMapIndicesCnt] @ Hdr.nameMapIndicesOfs + 0x10;
DDSxHeader ddsxHeaders[Hdr.ddsxHeadersCnt] @ Hdr.ddsxHeadersOfs + 0x10;
DDSxRec ddsxRecs[Hdr.ddsxRecordsCnt] @ Hdr.ddsxRecordsOfs + 0x10;