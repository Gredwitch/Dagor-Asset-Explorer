
struct PregenEntPoolDesc {
	u64 riResOfs;
	u64 riNameOfs;
	u32 colPair[2];

	u32 flags;

	// posInst = flags & 1;
	// paletteRotation = (flags >> 1) & 1;
	// _resv30 = flags & 0xFFFFFF00;

	u32 paletteRotationCount;
};

struct LandClassRec {
	u64 landClassNameOfs;
	u64 asset;
	u64 mask;
	u64 riResMap;
};

struct Header {
	u32 sz;
	u64 rtDataPtr; // null
	
	u32 cellsOfs;
	u32 cellCnt;

	padding[8];

	u32 numCellW;
	u32 numCellH;
	u16 cellSz;
	u8 dataFlags;
	u8 perInstDataDwords;
	float sweepMaskScale;

	padding[8];

	u32 landClsOfs;
	u32 landClsCnt;

	padding[8];

	float world0Vxz[4];
	float invGridCellSzV[4];
	float lastCellXZXZ[4];

	float grid2world;
	float densMapPivotX;
	float densMapPivotZ;

	u32 pregenDataBaseOfs;

	u32 pregenEntOfs;
	u32 pregenEntCnt;

	u64 fpLevelBin;

	padding[0x10];
	
	padding[landClsOfs - 0xA0];
};
#pragma pattern_limit 231072;
u32 TOTAL_COVERAGE = 0;

struct PregenEntCounterPtr {
    u32 ofs;
    u32 cnt;
};

struct Cell {
	u32 coverageOfs;
	u32 coverageCnt;
	
	TOTAL_COVERAGE = TOTAL_COVERAGE + coverageCnt;
	
	padding[8];
	
	u64 rtDataPtr;
	
	s16 htMin;
	u16 htDelta;
	u32 riDataRelOfs;
	
	u64 pregenEntCounterCnt[65];
	// PregenEntCounterPtr pregenEntCounter[65];
};

struct LandClassCoverage {
	u32 landClsIdx;
	u32 msq;
};

struct PregenEntCounter {
    
};

struct UnknownData {
    u32 u1;
    u32 u2;
    u32 sz;
    
    padding[sz];
};

Header Hdr @ 0;
LandClassRec landCls[Hdr.landClsCnt] @ Hdr.landClsOfs + 4;
Cell cells[Hdr.cellCnt] @ Hdr.cellsOfs + 4;
LandClassCoverage landClsCoverage[TOTAL_COVERAGE] @ addressof(landCls) + sizeof(landCls);
PregenEntPoolDesc pregenEnt[Hdr.pregenEntCnt] @ Hdr.pregenEntOfs + 4;

UnknownData unknown[10] @ Hdr.sz + 4;


// u32 END @ pregenEnt[Hdr.pregenEntCnt - 1].riNameOfs + 0x20;


// #include <std/io.pat>

// PregenEntCounterWrapper pregenEntCounterWrapper[Hdr.cellCnt] @ addressof(cells) + sizeof(cells);