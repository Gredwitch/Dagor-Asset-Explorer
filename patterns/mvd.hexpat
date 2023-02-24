
#include <std/mem.pat>
#include <std/io.pat>

namespace MVD {
	struct Material {
		padding[0x40];

		u64 flags;

		padding[8];

		u32 diffuse;
		u32 camo;
		u32 bump;
		u32 ao;
		u32 mask;
		u32 unknown1;
		u32 unknown2;
		u32 unknown3;
		u32 unknown4;
		u32 unknown5;
		u32 unknown6;
		u32 unknown7;
		u32 unknown8;
		u32 unknown9;
		u32 unknownA;
		u32 unknownB;

		u64 flags2;
		u64 flags3;
		u64 flags4;
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
	};

	Header Hdr @ 0;

	char matData[Hdr.matOffset - 0x20] @ sizeof(Hdr);
	Material materials[Hdr.matCount] @ Hdr.matOffset;
	LODInfo lodInfo[Hdr.lodCount] @ Hdr.lodOffset;
}