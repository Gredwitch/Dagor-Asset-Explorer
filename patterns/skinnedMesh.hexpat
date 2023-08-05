
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

struct Header {
	u32 boneOrgTmOfs;
	u32 boneOrgTmCnt;
	
	padding[8];
	
	u32 matTabOfs;
	u32 matTabCnt;
	
	padding[8];
	
	u32 boneNodeIdOfs;
	u32 boneNodeIdCnt;
	
	u32 shMatOfs;
	u32 shMatCnt;
	
	u32 workDataOfs;
	u32 workDataCnt;
};

struct TMatrix {
	float x[3];
	float y[3];
	float z[3];
	float w[3];
};

struct MatTab {
	u64 unknown1;
	u64 unknown2;
};

u32 tempVal;

struct ShaderSkinnedMesh {
	Header Hdr;
	
	ShaderMesh mesh;
	
	tempVal = sizeof(Hdr) + sizeof(mesh);
	
	if (tempVal < Hdr.boneNodeIdOfs) {
		padding[Hdr.boneNodeIdOfs - tempVal];
		tempVal = tempVal + (Hdr.boneNodeIdOfs - tempVal);
	}
	
	u16 boneNodeIds[Hdr.boneOrgTmCnt];
	
	tempVal = tempVal + sizeof(boneNodeIds);
	
	if (tempVal < Hdr.shMatOfs) {
		padding[Hdr.shMatOfs - tempVal];
		tempVal = tempVal + (Hdr.shMatOfs - tempVal);
	}
	
	u64 shMatTab[Hdr.matTabCnt];
	
	tempVal = tempVal + sizeof(shMatTab);
	
	if (tempVal < Hdr.boneOrgTmOfs) {
		padding[Hdr.boneOrgTmOfs - tempVal];
		tempVal = tempVal + (Hdr.boneOrgTmOfs - tempVal);
	}
	
	TMatrix boneOrgTm[Hdr.boneOrgTmCnt];
	
	tempVal = tempVal + sizeof(boneOrgTm);
	
	if (tempVal < Hdr.matTabOfs) {
		padding[Hdr.matTabOfs - tempVal];
		tempVal = tempVal + (Hdr.boneOrgTmOfs - matTabOfs);
	}
	
	MatTab matTab[Hdr.matTabCnt];
	
};

u32 idx = 0;
u32 SSMR_COUNT = 2;
u32 SKIN_COUNT;

struct ShaderSkinnedMeshResource {
	if (idx == 0) {
		SKIN_COUNT = 9;
	} else if (idx == 1) {
		SKIN_COUNT = 8;
	} else {
		SKIN_COUNT = -1;
	}
	
	u32 skinsNodes[SKIN_COUNT];
	u64 skinPtr[SKIN_COUNT];
	
	ShaderSkinnedMesh ssm[SKIN_COUNT];
	
	idx = idx + 1;
};

ShaderSkinnedMeshResource ssmr[SSMR_COUNT] @ 0;