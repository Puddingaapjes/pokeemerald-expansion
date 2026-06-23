#include "global.h"
#include "constants/species.h"

struct PaletteVariant
{
  u8 start : 4;        // Start index of palette customisation range
  u8 length : 4;       // Length of customisation range
  u8 hue_amount : 4;   // Index into hue table [0,10,20,30,40,50,60,70,80,90,100,110,125,140,160,180]
  u8 chr_amount : 2;   // Index into chroma table [0,10,20,30]
  u8 lum_amount : 2;   // Index into luma table [0,10,20,30]
  u8 hue_direction : 2;
  u8 chr_direction : 2;
  u8 lum_direction : 2;
};

enum shift_direction
{    
    CENTER  = 0,   // down, center, up  
    UP      = 1,   // shift up 
    DOWN    = 2,   // shift down
    INVERSE = 3,   // up, center, down
};


struct SpeciesVariant
{
  struct PaletteVariant pv1;
  struct PaletteVariant pv2;
};

// Precomputed hue-amount table
// Code uses hue in [0..255] instead of [0..360]
// {0,10,20,30,40,50,60,70,80,90,100,110,125,140,160,180} -> {0,7,14,21,28,35,42,49,56,63,70,77,88,98,112,128}
static const u16 sHueTable[16] = {0, 7, 14, 21, 28, 35, 42, 49, 56, 63, 70, 77, 88, 98, 112, 128};
static const u8 sCLTable[4] = {0, 10, 20, 30};

// return variant data or return default if species has no variants.
const struct SpeciesVariant *GetSpeciesVariants(u32 species);
const struct SpeciesVariant *GetSpeciesShinyVariants(u32 species);

void ApplyPaletteVariantToPaletteBuffer(u16 pal16[16], const struct PaletteVariant *pv, u16 prn16);
void ApplyCustomRestrictionToPaletteBuffer(u8 hMin, u8 hMax, u8 cMin, u8 cMax, u8 lMin, u8 lMax, u16 pal16[16]);
void ApplyMonSpeciesVariantToPaletteBuffer(u32 species, bool8 shiny, u32 personality, u16 pal16[16]);

// Species data helpers


#define NUM_VARIANTS 3

#define HUE_INDEX(h) (            \
    ((h) == 0 ? 0 : (h) <= 10 ? 1 \
                : (h) <= 20   ? 2 \
                : (h) <= 30   ? 3 \
                : (h) <= 40   ? 4 \
                : (h) <= 50   ? 5 \
                : (h) <= 60   ? 6 \
                : (h) <= 70   ? 7 \
                : (h) <= 80   ? 8 \
                : (h) <= 90   ? 9 \
                : (h) <= 100  ? 10 \
                : (h) <= 110  ? 11 \
                : (h) <= 125  ? 12 \
                : (h) <= 140  ? 13 \
                : (h) <= 160  ? 14 \
                : /*(h)==180*/ 15))

#define CHR_INDEX(s) (           \
    ((s) == 0 ? 0 : (s) <= 10 ? 1 \
                : (s) <= 20  ? 2 \
                : /*(s)==30*/ 3))

#define LUM_INDEX(v) ( \
    ((v) == 0 ? 0      \
    : (v) <= 10 ? 1     \
    : (v) <= 20  ? 2   \
    : /*(v)==30*/ 3))



#define PAL1(s, l)  \
  .pv1.start = (s), \
  .pv1.length = (l)

#define PAL2(s, l)  \
  .pv2.start = (s), \
  .pv2.length = (l)

#define HCL1(h, hd, s, sd, v, vd)       \
  .pv1.hue_amount = HUE_INDEX(h),       \
  .pv1.hue_direction = (hd),            \
  .pv1.chr_amount = CHR_INDEX(s),       \
  .pv1.chr_direction = (sd),            \
  .pv1.lum_amount = LUM_INDEX(v),       \
  .pv1.lum_direction = (vd)

#define HCL2(h, hd, s, sd, v, vd)       \
  .pv2.hue_amount = HUE_INDEX(h),       \
  .pv2.hue_direction = (hd),            \
  .pv2.chr_amount = CHR_INDEX(s),       \
  .pv2.chr_direction = (sd),            \
  .pv2.lum_amount = LUM_INDEX(v),       \
  .pv2.lum_direction = (vd)

#define DEFAULT_SPECIES_VARIANT \
  {                             \
      PAL1(1, 15),              \
      HCL1(0, CENTER, 0, CENTER, 0, CENTER),    \
  }

static const struct SpeciesVariant gSpeciesVariants[NUM_SPECIES] = 
{
    [SPECIES_BULBASAUR] = {
        PAL1(2, 5),
        HCL1(30, CENTER, 0, CENTER, 0, CENTER),
    },
    [SPECIES_IVYSAUR] = {
        PAL1(6, 4),
        HCL1(30, CENTER, 0, CENTER, 0, CENTER),
    },
    [SPECIES_VENUSAUR] = {
        PAL1(1, 4),
        HCL1(30, CENTER, 0, CENTER, 0, CENTER),
    },
    [SPECIES_CHARMANDER] = {
        PAL1(5, 4),
        HCL1(20, CENTER, 30, CENTER, 30, CENTER),
    },
    [SPECIES_CHARMELEON] = {
        PAL1(4, 4),
        HCL1(60, UP, 30, UP, 30, DOWN),
    },
    [SPECIES_CHARIZARD] = {
        PAL1(5, 5),
        HCL1(20, CENTER, 30, CENTER, 30, CENTER),
        PAL2(5, 3),
        HCL2(30, CENTER, 10, CENTER, 10, CENTER),
    },
    [SPECIES_SQUIRTLE] = {
        PAL1(11, 5),
        HCL1(60, DOWN, 0, CENTER, 0, CENTER),
    },
    [SPECIES_WARTORTLE] = {
        PAL1(6, 4),
        HCL1(60, UP, 0, CENTER, 0, CENTER),
    },
    [SPECIES_BLASTOISE] = {
        PAL1(1, 4),
        HCL1(60, DOWN, 0, CENTER, 0, CENTER),
    },
};
static const struct SpeciesVariant gSpeciesShinyVariants[NUM_SPECIES] = 
{
  [SPECIES_BULBASAUR] = {
      PAL1(2, 5),
      HCL1(45, CENTER, 0, CENTER, 0, CENTER),
  },
  [SPECIES_IVYSAUR] = {
      PAL1(6, 4),
      HCL1(45, CENTER, 0, CENTER, 0, CENTER),
  },
  [SPECIES_VENUSAUR] = {
      PAL1(1, 4),
      HCL1(45, CENTER, 0, CENTER, 0, CENTER),
  },
  [SPECIES_CHARMANDER] = {
    PAL1(9, 6),
    HCL1(180, CENTER, 0, CENTER, 0, CENTER),
  },
  [SPECIES_CHARMELEON] = {
    PAL1(13, 3),
    HCL1(180, CENTER, 0, CENTER, 0, CENTER),
  },
  [SPECIES_CHARIZARD] = {
    PAL1(11, 5),
    HCL1(180, CENTER, 0, CENTER, 0, CENTER),
  },
};