/*
00000000 RenderableInstanceLodsResource struc ; (sizeof=0xA0, align=0x8, copyof_8533)
00000000                                         ; XREF: ?exportAssetBlk@ImpostorBaker@@AEBAXPEAVDagorAsset@@PEAVRenderableInstanceLodsResource@@AEBUImpostorExportData@1@AEAVDataBlock@@@Z/r
00000000 baseclass_0 DObject ?                   ; XREF: ImpostorBaker::exportAssetBlk(DagorAsset *,RenderableInstanceLodsResource *,ImpostorBaker::ImpostorExportData const &,DataBlock &)/w
00000010 packedFields dd ?                       ; XREF: ImpostorBaker::exportAssetBlk(DagorAsset *,RenderableInstanceLodsResource *,ImpostorBaker::ImpostorExportData const &,DataBlock &)+5/w
00000014 rotationPaletteSize db ?
00000015 qlMinAllowedLod db ?
00000016 qlReqLod dw ?
00000018 qlReqLodPrev dw ?                       ; XREF: ImpostorBaker::exportAssetBlk(DagorAsset *,RenderableInstanceLodsResource *,ImpostorBaker::ImpostorExportData const &,DataBlock &)+A/w
0000001A db ? ; undefined
0000001B db ? ; undefined
0000001C qlReqLFU dd ?
00000020 _resv dd ?                              ; XREF: ImpostorBaker::exportAssetBlk(DagorAsset *,RenderableInstanceLodsResource *,ImpostorBaker::ImpostorExportData const &,DataBlock &)+E0/r
00000024 db ? ; undefined
00000025 db ? ; undefined
00000026 db ? ; undefined
00000027 db ? ; undefined
00000028 smvd Ptr<ShaderMatVdata> ?
00000030 lods PatchableTab<RenderableInstanceLodsResource::Lod> ?
00000040 bbox BBox3 ?
00000058 bsphCenter Point3 ?
00000064 bsphRad dd ?
00000068 bound0rad dd ?
0000006C impostorDataOfs dd ?
00000070 occl dd 12 dup(?)
000000A0 RenderableInstanceLodsResource ends
*/

struct Header {
	// u32 classId; // generated by the DagorAssetExplorer : always 0x77f8232f for rendInst
	
	u24 lodHdrSz;
	u8 lodHdrflag;
	
	u32 texCnt; // 0xFFFFFFFF if we use desc files
	u32 matCnt; // 0xFFFFFFFF if we use desc files
	u32 vdataNum;
	u32 mvdHdrSz; // & 0x3FFFFFFF
	
	if (texCnt != 0xFFFFFFFF && matCnt != 0xFFFFFFFF) {
		// retrive matt and tex data
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
	u32 unknown;
	
	padding[4];
	
	float unknown1;
	
	padding[4];
};

struct ModelData {
	u32 dataSz;
	u32 lodCnt;
	
	padding[8];
	
	BBox3f bbox;
	
	Vector3f bsphCenter;
	float bsphRad;
	float bound0rad;
	
	u32 impostorDataOfs;
	
	OcclusionData occ[lodCnt];
	
	if (impostorDataOfs > 0) {
	   u64 impostorShaderMeshOfs;
	   u64 impostorSz;
	   
	   char imposterData[impostorSz - (impostorDataOfs + dataSz) + 0x30];
	}
};

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
	u32 __deprecatedMaxMatPass;
	u32 _resv;
	
	if (elemCnt > 0) {
	   ShaderMeshElem elem[elemCnt + stageEndElemIdx[2]];
	}
};


struct InstShaderMeshResource {
	u32 resSz;
	u32 _resv;
	
	ShaderMesh mesh;
};

Header Hdr @ 0;
CompressedData mvd @ sizeof(Hdr);
ModelData modelData @ addressof(mvd) + sizeof(mvd);

if (modelData.impostorDataOfs > 0) {
    if (modelData.lodCnt > 1) {
        InstShaderMeshResource instSmr[modelData.lodCnt - 1] @ addressof(modelData) + sizeof(modelData);
    }
} else {
    InstShaderMeshResource instSmr[modelData.lodCnt] @ addressof(modelData) + sizeof(modelData);
}