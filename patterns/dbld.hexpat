
#include <std/mem.pat>
#include <std/io.pat>
#include <type/leb128.pat>
#include <type/dblk.pat>

using leb128 = be type::LEB128;

struct EditorVersion {
	u32 magic;
	u32 sz;
	char version[sz];
	
	padding[sz % 4];
};

struct MetaData {
	char Meta[24];
};

struct Header {
	u32 magic1;
	u32 magic2;
	u32 texNamesCount;
	u32 metaSz;
	
	EditorVersion eVer;

	u32 metaCnt;
	MetaData meta[metaCnt + 1];
    padding[(metaSz - (metaCnt + 1) * 24) - sizeof(eVer) - 4];
    
    u32 nameMapSz;
    u32 nameMapMagic;
};

struct NameMapIndex {
	u32 start;
	padding[4];
};

struct FastNameMap {
	u32 sz;
	u32 cnt;
	
	padding[8];
	
	char list[sz - 24];
	
	padding[8];

	NameMapIndex indices[cnt];
};
struct TexName {
	u32 sz;
	char string[sz];
	
	if (sz % 4 == 0) {
		padding[0];
	} else {
		padding[4 - sz % 4];
	}
	
};

struct DxP2 {
	u32 sz;
	u32 magic;
	u32 unknown;
	u32 texSz;
	u32 texCnt;
	TexName texNames[texCnt];
	padding[(sz - 0x10) - sizeof(texNames)];
	u32 dataSize;
	padding[dataSize];
};

struct LandTextures {
	u32 unknown;
	u32 magic;
	u32 sz;
	u32 magic2;
	u32 magic3;
	u32 count;
	
	padding[0x40];
	
	u32 texSz2;
	u32 texCnt2;
	padding[8];
	char texNames2[texSz2 - 0x10];
	u32 texIndices2[texCnt2];
};


struct CompressedData {
	u24 sz;
	u8 compressionMethod;
	padding[sz + 4];
};

struct UnknownStruct {
	u32 sz;
	padding[sz];
};

struct ListElements {
	u32 type;

	if (type == 0xC6000000) {
		u32 value;
	} else if (type == 0x40518A11) {
		u32 value;
	} else if (type == 0xC5F00000) {
		u32 value;
	} else {
		u32 value;
	}
};

struct UnknownList {
	u32 sz;
	ListElements listE[sz / 8];
};

struct StringBlock {
	u16 unknown2;
	leb128 blkSz;
	char data[blkSz];
	padding[1];
};

struct DecompressedBlock {
    u32 blockSz;
    u32 blockParamsCnt;
    padding[blockSz - 4];
};

u32 pow = 1024;

struct MetaDataBlock {
	u32 sz;
	u32 cnt;
	u32 sz2;
	u32 nameLen;
	char name[nameLen];
	padding[nameLen % 4];
	
	type::DataBlockContainer sblk;
	
	if (cnt > 1) {
	   DecompressedBlock blocks[cnt - 1];
	}
};

struct Pad {
    padding[16384 - pow];
};

struct LandRayTraceDump {
    u32 sz;
    char name[sz];
    padding[sz % 4];
    padding[6];
    
    CompressedData cdat;
    
    padding[2];
};

struct DDSThing {
    u24 hdr;
    
    if (hdr >> 8 == 0xFFFF) {
        padding[0xC];
    } else {
        u32 flag;
        u32 sz;
        u32 sz1;
        
        
        u32 magic;
        u32 format;
        
        padding[sz1 - 8];
    }
};

Header Hdr @ 0;
FastNameMap ResList @ sizeof(Hdr);
DxP2 DXP @ addressof(ResList) + sizeof(ResList);
LandTextures Landtex @ addressof(DXP) + sizeof(DXP);
CompressedData CDat @ addressof(Landtex) + sizeof(Landtex);
UnknownStruct unk[pow] @ addressof(CDat) + sizeof(CDat); // power of 2, either 256 (2^8) or 1024 (2^10)
UnknownList unk2 @ addressof(unk) + sizeof(unk);
MetaDataBlock mblk @ addressof(unk2) + sizeof(unk2);

u32 unknown[pow + 4] @ addressof(mblk) + sizeof(mblk);
Pad P @ addressof(unknown) + sizeof(unknown);

LandRayTraceDump LTD @ addressof(P) + sizeof(P);
u32 a @ sizeof(LTD) + addressof(LTD);