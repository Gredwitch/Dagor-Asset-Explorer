
#include <std/io.pat>

struct ShaderMeshElem {
	u64 ShaderElementPtr;
	u64 ShaderMaterialPtr;
	u64 VertexDataPtr;
	
	u32 vdOrderIndex;
	u32 startV;
	u32 numV;
	u32 startI;
	u32 numFace;
	u32 baseVertex;
};

struct ShaderMesh {
	u32 elemOfs; // actually these are u64 dptr
	u32 elemCnt;
	
	padding[8]; // u64 dcnt
	
	u16 stageEndElemIdx[8];
	s32 __deprecatedMaxMatPass;
	u32 _resv;
	
	
	if (elemCnt > 0 && elemCnt < 100) { // safeguard for debug purposes
		if (__deprecatedMaxMatPass < 0) {
		   ShaderMeshElem elem[elemCnt];
	   } else {
		   ShaderMeshElem elem[elemCnt + stageEndElemIdx[2]];
	   }
	} else if (elemCnt > 100) {
	   std::print("shadermesh error @ {}", addressof(elemOfs));
	}
};

struct ShaderMeshResource {
	ShaderMesh mesh;
	u32 resSz;
	u32 _resv;
};