
struct Header {
	u32 lodHdrSz; // packedFields?
	
	u32 texCnt; // 0xFFFFFFFF if we use desc files
	u32 matCnt; // 0xFFFFFFFF if we use desc files
	u32 vdataNum;
	u32 mvdHdrSz; // & 0x3FFFFFFF
	
	if (texCnt != 0xFFFFFFFF && matCnt != 0xFFFFFFFF) {
		// retrive matt and tex data
		u32 texMapSz;
		u32 texIndicesOfs;
		u32 texIndiciesCnt;
		
		padding[8];
		
		padding[texIndicesOfs - 0x10];
		
		u32 texMapIndicies[texIndiciesCnt];
	}
	
	if (vdataNum == 0) {
	   padding[0x20];
	}
};

struct CompressedData {
	u24 cSz;
	u8 cMethod;
	padding[cSz];
};

struct Vector3f {
	float x;
	float y; // z and y are inverted in dagor
	float z;
};
struct Vector4f {
	float x;
	float y;
	float z;
	float w;
};

struct BBox3f {
	Vector3f mins;
	Vector3f maxs;
};

struct OcclusionData {
	u32 shaderMeshOfs;
	
	padding[4];
	
	float lodDistance;
	
	padding[4];
};

struct DynSceneResNameMapResource {
	u32 resNameMapSz;
	
	u32 nameMapIndicesOfs;
	u32 nameCnt;
	
	padding[8];
	
	u32 skinNodesOfs;
	u32 skinNodesCnt;
	
	padding[8];
	
	char nameMap[nameMapIndicesOfs - 0x20];
	u64 nameMapIndices[nameCnt];
};

struct RigidObject {
	u64 shaderMeshPtr;
	Vector3f sph_c;
	float sph_r;
	u32 nodeId;
	u32 _resv;
	
};


struct ModelData {
	u32 dataSz;
	u32 lodCnt;
	
	padding[8];
	
	BBox3f bbox;
	
	if (dataSz > 0x28) {
    	float bpC254[4];
    	float bpC255[4];
	}
	
	OcclusionData occ[lodCnt];
	
	DynSceneResNameMapResource names;
	
	u16 skinNodes[names.skinNodesCnt];
	
	padding[((4 - (names.skinNodesCnt % 4)) * 2) % 8];
	
};

struct ShaderSkinnedMeshResource {
	u32 cnt;
    
	if (cnt > 0) {
        u32 sz;
    	
    	u64 ptr;
    	
    	u32 texCnt;
    	u32 matCnt;
    	
    	
    	u32 unknown;
    	
    	u24 cDataSz;
    	u8 cDatMeth;
    	
    	CompressedData cdata;
    	
    	u32 t;
    }
};


Header Hdr @ 0;

u32 offset = sizeof(Hdr);

if (Hdr.vdataNum > 0) {
    CompressedData mvd @ sizeof(Hdr);
    
    offset = addressof(mvd) + sizeof(mvd);
}
ModelData modelData @ offset;

u32 lodId = 0;

struct Lod {
	u32 HdrSz;
	
	u32 rigidCnt;
	padding[8];
	
	u32 skinPtr;
	u32 skinCnt;
	padding[8];
	
	RigidObject rigids[rigidCnt];
	
	padding[modelData.occ[lodId].shaderMeshOfs - (HdrSz + sizeof(rigids))];
	lodId = lodId + 1;
	
	ShaderMesh mesh[rigidCnt];
	
};
Lod lods[modelData.lodCnt] @ addressof(modelData) + sizeof(modelData);
// ShaderSkinnedMeshResource ssm @ addressof(lods) + sizeof(lods);