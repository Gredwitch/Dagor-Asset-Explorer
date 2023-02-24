

struct cDataHeader {
	u24 cSz;
	u8 cMethod;
};

struct CompressedData {
	cDataHeader hdr;
	padding[hdr.cSz];
};

struct Point3f {
	float x;
	float y; // z and y are inverted in dagor
	float z;
};

struct Point4f {
	float x;
	float y;
	float z;
	float w;
};

struct IPoint2 {
    s32 x;
    s32 y;
};

struct BBox3f {
	Point3f mins;
	Point3f maxs;
};

struct FastNameEx {
	u32 sz;
	char name[sz];
};

struct FastName {
	FastNameEx fname;
	
	padding[4 - fname.sz % 4];
};

struct FastLongNameMap {
	u32 namesSz;
	u32 nameCnt;
	
	padding[8];
	
	padding[namesSz - 0x10];
	
	u64 nameIndices[nameCnt];
};