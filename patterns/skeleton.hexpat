
#include <std/io.pat>

struct Matrix4x4 {
	float x[4];
	float y[4];
	float z[4];
	float t[4];
};

struct Node {
	Matrix4x4 tm;
	Matrix4x4 wtm;

	u32 refOfs;
	u32 refCnt;

	padding[8];
	
	u32 pnt;
	
	padding[4];
	
	u32 nameOfs;
	
	std::print("{}", refOfs);
	
	padding[4];
	
};

struct Header {
	u32 sz;
	u32 nodeCnt;
};

Header Hdr @ 0;
Node nodes[Hdr.nodeCnt] @ sizeof(Hdr);