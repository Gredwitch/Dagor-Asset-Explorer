
#include <std/mem.pat>
#include <std/io.pat>
#include <type/leb128.pat>
#include <type/dblk.pat>
#include <type/dagor_shared.pat>
#include <type/shadermesh.pat>
#include <type/dxp.pat>

#include <std/io.pat>

using leb128 = be type::LEB128;

/////////////////////////////////////////////
//
// HEADER
//



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
};



/////////////////////////////////////////////
//
// LMAP
//

struct LandShaderMesh {
    u32 blockSz;
	ShaderMesh mesh;
};



struct CellData {
    u32 sz;
    u32 blockSz;
    
    LandShaderMesh land[2];
    LandShaderMesh decal;
    LandShaderMesh combined;
    
    if (sz - sizeof(this) + 4 > 0) {
        LandShaderMesh patches;
    }
};

u32 CELLCNT;

struct LandMesh {
	u32 texCnt;
	u32 matCnt;
	u32 vdataCnt;
	u32 mvdHdrSz;

	u32 texMapSz;
	u32 texIndicesOfs;
	u32 texIndiciesCnt;
	
	padding[8];
	
	padding[texIndicesOfs - 0x10];
	
	u32 texMapIndicies[texIndiciesCnt];
	
	CompressedData cData;
	
	u32 shaderMeshSz;
	
	CellData cells[CELLCNT];
	
	u32 cellBoundingsSz;
	
	BBox3f cellBoundings[CELLCNT];
	float cellBoundingsRadius[CELLCNT];
};

struct DecompressedBlock {
    u32 blockSz;
    u32 blockParamsCnt;
    padding[blockSz - 4];
};

struct unknownStruct {
    s16 u1;
    s16 u2;
};

struct DDSxHolder {
	u24 unknown;
	s32 unknownVal;
	
	u32 sz1;
	u32 sz2;
	
	padding[sz1];
};

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
	
	u32 unknownHeaders[4];
	unknownStruct unknown1[CELLCNT];
	
	DDSxHolder textures[CELLCNT];
	
};

struct DetailMap {
    u32 nameSz;
    char name[nameSz];
    
    padding[4 - nameSz % 4];
};

struct LMap {
	u32 magic;
	u32 version;
	
	float gridCellSize;
	float landCellSize;
	
	u32 mapSizeX;
	u32 mapSizeY;
	
	IPoint2 origin;
	
	u32 hasTileData;
	
	u32 meshOfs;
	u32 detailOfs;
	u32 tileDataOfs;
	u32 rayTracerOfs;
	
	CELLCNT = mapSizeX * mapSizeY;
	
	LandMesh mesh;
	MetaDataBlock landClasses;
	DetailMap detail;
	
};



///////////////////////////////////////////////////////////////////////////
//
// TEX
//


struct TEX {
    FastNameEx name;
    u32 sz;
    
    DDSxHeader hdr;
};



///////////////////////////////////////////////////////////////////////////
//
// RIGz
//



struct RIGz {
    CompressedData primLayer;
    
    u32 pregenDataSz;
    CompressedData pregenData[32];
    
    u32 secLayerCellsSz;
    CompressedData secLayerCells[6];
};



///////////////////////////////////////////////////////////////////////////
//
// -MAIN-
//


struct Tag {
	u32 blockSz;
	u32 label;
	
	if (label == 1145980160) {
		char child[0];
		
		break;
	} else if (label == 1885433196) {
		LMap child;
	} else if (label == 1280471378) {
		FastLongNameMap child;
	} else if (label == 1480938496) {
	   TEX child;
	} else if (label == 2051492178) {
	   RIGz child;
	} else {
		std::print("Unknown tag {} @ {}", label, addressof(label));

		char child[0];
	}
	
	padding[blockSz - 4 - sizeof(child)];
};


Header hdr @ 0;

Tag tags[100] @ sizeof(hdr);