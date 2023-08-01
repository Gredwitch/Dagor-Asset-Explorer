
#include <std/mem.pat>
#include <std/io.pat>

fn abs(s32 a) {
	if (a < 0)
		return -a;
	else
		return a;
	
};

namespace MVD {
	struct Material {
		float diff[4];
		float amb[4];
		float emis[4];
		float spec[4];
		
		u32 unknown;
		u32 shaderNameOfs;

		padding[8];
		
		u32 textures[16];
		
		u32 dataOfs;
		u32 dataCnt;
		
		padding[8];
		
		u64 flags;
	};

	struct Header {
		u32 matOffset;
		u32 matCount;

		padding[8];

		u32 lodOffset;
		u32 lodCount;

		padding[8];
	};

	struct VertexData {
		u32 vCnt;
		u8 vStride;
		u24 iPackedSz;
		u32 iSz;
		u16 flags;
		u16 bf_14;
		u32 iCnt;
		u32 storageFormat;

		padding[8];
	};

	Header Hdr @ 0;

	Material materials[Hdr.matCount] @ Hdr.matOffset;
	VertexData vertexData[Hdr.lodCount] @ Hdr.lodOffset;
}