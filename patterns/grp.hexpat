
/*
00000000 gamerespackbin::GrpData struc ; (sizeof=0x30, align=0x8, copyof_11934)
00000000 nameMap PatchableTab<int> ?
00000010 realResTable PatchableTab<gamerespackbin::RealResEntry> ?
00000020 resData PatchableTab<gamerespackbin::ResData> ?
00000030 gamerespackbin::GrpData ends

00000000 gamerespackbin::RealResEntry struc ; (sizeof=0xC, align=0x4, copyof_11928)
00000000 classId dd ?
00000004 offset dd ?
00000008 realResId dw ?
0000000A _resv dw ?
0000000C gamerespackbin::RealResEntry ends

00000000 dag::Span<gamerespackbin::ResData> struc ; (sizeof=0x10, align=0x8, copyof_11932)
00000000                                         ; XREF: PatchableTab<gamerespackbin::ResData>/r
00000000 dptr dq ?                               ; offset
00000008 dcnt dq ?
00000010 dag::Span<gamerespackbin::ResData> ends

*/

struct Header {
	u32 magic;
	u32 grpDataSz;
	u32 realResTableSz;
	u32 sz;
	
	u32 nameMapOfs;
	u32 nameMapCnt;
	
	padding[8];
	
	u32 resEntryOfs;
	u32 resEntryCnt;
	
	padding[8];
	
	u32 resDataOfs;
	u32 resDataCnt;
	
	padding[8];
};

struct RealResEntry {
	u32 classId;
	u32 offset;
	u16 realResId;
	u16 _resv;
};

struct RealResData {
	u32 classId;
	u16 resId;
	u16 realResId;
	   
	u32 parentOffset; // note: parents do not work yet
	u32 parentCnt;
	padding[0x8];
};


Header Hdr @ 0;

struct NameMap {
	char nameMap[Hdr.nameMapOfs - sizeof(Hdr)];
	u32 nameIndices[Hdr.nameMapCnt];
};

NameMap Nmap @ sizeof(Hdr);
RealResEntry resEntries[Hdr.resEntryCnt] @ Hdr.resEntryOfs;
RealResData resData[Hdr.resDataCnt] @ Hdr.resDataOfs;