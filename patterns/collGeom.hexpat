struct BSphere3 {
	float Point3[3];
	float r;
	float r2;
};

struct BBox3 {
	float bMin[3];
	float bMax[3];
};


u32 collisionFlags = 0;

struct Header {
	u32 magic;
	u32 version;
	
	u32 bSphereSz;
	BSphere3 boudingSphere;
	
	u32 sz;
	
	if (version >= 538445072) {
		u32 cFlags;
		collisionFlags = cFlags;
	} else {
		collisionFlags = 0;
	}
	
	u32 nodeCnt;
};

struct String {
	u32 sz;
	char text[sz];
	
	/*if (sz % 4 != 0) {
		padding[4 - (sz % 4)];
	}*/
	
	if (sz & 3) {
		padding[4 - (sz & 3)];
	}
};

struct Vertex {
	float v[3];
};

struct Face {
	u32 f[3];
};


Header hdr @ 0x0;


struct CollNode {
	String name;
	
	if (hdr.version >= 538247445) {
		String surfaceProp;
	} // else physMatId = -1
	
	u32 type;
	
	if (collisionFlags & 2 != 0) {
		u8 behaviorFlags;
		
		// behaviorFlags = type ^ behaviorFlags
	}
	
	
	float tm[3 * 4];
	
	if (collisionFlags & 4 != 0 ) {
	   // cb3->read(cb3, &this3->relGeomNodeTms.dptr[nodeIdx2], 48);
	   padding[48];
	}
	BSphere3 bSphere;
	BBox3 bbox;
	
	u32 vCnt;
	Vertex verts[vCnt];
	
	u32 idxCnt;
	Face faces[idxCnt / 3];
	
};


CollNode nodes[hdr.nodeCnt] @ sizeof(hdr);