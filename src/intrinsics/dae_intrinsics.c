#include <stdio.h>
#include <emmintrin.h>

/*
void printm128(char n[], __m128 a) {
	float f_a[4];
	_mm_store_ps(f_a, a);
	printf("%s: %f, %f, %f, %f\n", n, f_a[0], f_a[1], f_a[2], f_a[3]);
};
void printm128i(char n[], __m128i a) {
	float i_a[4];
	_mm_store_si128((__m128i *)i_a, a);

	printf("%s: %f, %f, %f, %f\n", n, i_a[0], i_a[1], i_a[2], i_a[3]);
};
*/
extern void get_v482(float *dst, float cell_xz_sz, int htDelta) {
	float _1div32767_0 = 1 / 32767.0f;

	__m128 VC_1div32767_0 = _mm_load_ps((float[4]) {_1div32767_0, _1div32767_0, _1div32767_0, _1div32767_0});
	__m128 VC_cell_xz_sz = _mm_load_ps((float[4]) {cell_xz_sz, 0.0f, 0.0f, 0.0f});
	__m128 VC_htDelta = _mm_load_ps((float[4]) {(float) htDelta, 0.0f, 0.0f, 0.0f});
	
	_mm_store_ps(dst, _mm_mul_ps(
		_mm_movelh_ps(
			_mm_unpacklo_ps(
				VC_cell_xz_sz,
				VC_htDelta),
			VC_cell_xz_sz),
		VC_1div32767_0));
};

/*
__m128 get_cell_coords(__m128 cellOrigin, int htMin) { // v34
	__m128 zeroF = _mm_setzero_ps();

	return _mm_movelh_ps(
          _mm_unpacklo_ps(cellOrigin, _mm_load_ps((float[4]) {(float) htMin, 0.0f, 0.0f, 0.0f})),
          _mm_unpacklo_ps(_mm_shuffle_ps(cellOrigin, cellOrigin, 170), zeroF));
}

__m128 getPosInternal(__m128i v110, __m128i v112, __m128i v114, __m128 v482, __m128 cell_coords) {
	// float zeroArray[4] = {0.0f, 0.0f, 0.0f, 0.0f};
	__m128i zeroI = _mm_setzero_si128();
	__m128 zeroF = _mm_setzero_ps();

	float _1div256_0 = 1 / 256.0f;

	__m128 VC_1div256_0 = _mm_load_ps((float[4]) {_1div256_0, _1div256_0, _1div256_0, _1div256_0});
	
	__m128 v111 = _mm_cvtepi32_ps(_mm_unpacklo_epi16(v110, _mm_cmpgt_epi16(zeroI, v110))); // -255.0        0.0          0.0 34.0 
	__m128 v113 = _mm_cvtepi32_ps(_mm_unpacklo_epi16(v112, _mm_cmpgt_epi16(zeroI, v112))); //  
	__m128 v115 = _mm_cvtepi32_ps(_mm_unpacklo_epi16(v114, _mm_cmpgt_epi16(zeroI, v114))); // 

	__m128 v116 = _mm_shuffle_ps(v111, v113, 68); //  
	__m128 v117 = _mm_shuffle_ps(v111, v113, 238); // 
	__m128 v118 = _mm_shuffle_ps(v115, zeroF, 68); // 
	__m128 v119 = _mm_shuffle_ps(v115, zeroF, 238); //
	
	__m128 v121 = _mm_mul_ps(_mm_shuffle_ps(v116, v118, 136), VC_1div256_0); //    
	__m128 v122 = _mm_mul_ps(_mm_shuffle_ps(v116, v118, 221), VC_1div256_0); //      
	__m128 v123 = _mm_mul_ps(_mm_shuffle_ps(v117, v119, 136), VC_1div256_0); //
	__m128 v124 = _mm_mul_ps(_mm_shuffle_ps(v117, v119, 221), v482); //


	// printm128i("v110", v110);
	// printm128i("v112", v112);
	// printm128i("v114", v114);

	// printm128("v111", v111);
	// printm128("v113", v113);
	// printm128("v115", v115);

	// printm128("v116", v116);
	// printm128("v117", v117);
	// printm128("v118", v118);
	// printm128("v119", v119);

	// printm128("v121", v121);
	// printm128("v122", v122);
	// printm128("v123", v123);
	// printm128("v124", v124);

	// printm128("v482", v482);
	// printm128("v34", v34);

	return _mm_add_ps(v124, cell_coords);
	// return v124;
};

extern void getPos(float *dst, int x, int z, int htDelta, float grid2world, float cell_xz_sz, int cellSz, float *cellOrigin, int htMin, int *v110_i, int *v112_i, int *v114_i) {
	__m128 v482 = get_v482(cell_xz_sz, htDelta);
	__m128 cell_coords = get_cell_coords(_mm_set_ps(cellOrigin[3], cellOrigin[2], cellOrigin[1], cellOrigin[0]), htMin);

	__m128i v110_m = _mm_set_epi32(v110_i[3], v110_i[2], v110_i[1], v110_i[0]);
	__m128i v112_m = _mm_set_epi32(v112_i[3], v112_i[2], v112_i[1], v112_i[0]);
	__m128i v114_m = _mm_set_epi32(v114_i[3], v114_i[2], v114_i[1], v114_i[0]);

	_mm_storeu_ps(dst, getPosInternal(v110_m, v112_m, v114_m, v482, cell_coords));
};
*/
int main(int argc, char *args[]) {
	// get_v482(2048.0f, 256);

	return 0;
}