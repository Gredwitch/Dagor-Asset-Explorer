
struct Header {
    u32 magic;
    u32 resHdrSz;
    u32 resSz;
    u32 sz;
    
    u32 nameMapSz;
    u32 nameMapCnt;
    
    padding[8];
    
    u32 resEntrySz;
    u32 resEntryCnt;
    
    padding[8];
    
    u32 resDataSz;
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
    char nameMap[Hdr.nameMapSz - sizeof(Hdr)];
    u32 nameIndices[Hdr.nameMapCnt];
};

NameMap Nmap @ sizeof(Hdr);
RealResEntry resEntries[Hdr.resEntryCnt] @ addressof(Nmap) + sizeof(Nmap);
RealResData resData[Hdr.resDataCnt] @ sizeof(resEntries) + addressof(resEntries);