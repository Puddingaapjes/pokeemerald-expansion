#include "global.h"
#include "constants/species.h"

#define MAX_VARIANTS 5

struct PaletteRange
{
    u8 start : 4;        // Start index of palette customisation range
    u8 length : 4;       // Length of customisation range
};

struct PaletteShift
{
    s8 hueAmount;   // Hue shift amount [-128...127]
    s8 chrAmount;   // Chr shift amount [-128...127]
    s8 lumAmount;   // Lum shift amount [-128...127]
};

struct PaletteVariant
{
    struct PaletteRange paletteRange;
    struct PaletteShift paletteShift[MAX_VARIANTS];
};

struct SpeciesVariant
{
    u8 numVariants;
    struct PaletteVariant base;
    struct PaletteVariant accent;
};

// return variant data or return default if species has no variants.
const struct SpeciesVariant *GetSpeciesVariants(enum Species species);
const struct SpeciesVariant *GetSpeciesShinyVariants(enum Species species);

void ApplyPaletteVariantToPaletteBuffer(u16 pal16[16], const struct PaletteVariant *pv, u8 varIdx);
void ApplyCustomRestrictionToPaletteBuffer(u8 hMin, u8 hMax, u8 cMin, u8 cMax, u8 lMin, u8 lMax, u16 pal16[16]);
void ApplyMonSpeciesVariantToPaletteBuffer(enum Species species, bool8 shiny, u32 personality, u16 pal16[16]);
u8 GetMonVariantIdx(enum Species species, bool32 isShiny, u32 personality);

// Species data helpers
#define BASE(s, l, ...)                             \
    .base.paletteRange = { .start = (s), .length = (l) },   \
    .base.paletteShift = { __VA_ARGS__ },                   \
    .numVariants = sizeof((struct PaletteShift[]){__VA_ARGS__}) / sizeof(struct PaletteShift)

#define ACCENT(s, l, ...)                           \
    .accent.paletteRange = { .start = (s), .length = (l) }, \
    .accent.paletteShift = { __VA_ARGS__ }

#define DEFAULT_SPECIES_VARIANT \
{                               \
    BASE(1, 15,  {0, 0, 0}),   \
}

static const struct SpeciesVariant gSpeciesVariants[NUM_SPECIES] = 
{
    [SPECIES_BULBASAUR] = {
        BASE(1, 5, {0, 0, 0}, {-35, 0, 0}, {30, 0, -20}),
        ACCENT(6, 3, {0, 0, 0}, {-10, 0, 0}, {10, 0, 0})
    },
    [SPECIES_IVYSAUR] = {
        BASE(1, 4, {0, 0, 0}, {-35, 0, 0}, {30, 0, -20}),
        ACCENT(5, 3, {0, 0, 0}, {-10, 0, 0}, {10, 0, 0})
    },
    [SPECIES_VENUSAUR] = {
        BASE(1, 4, {0, 0, 0}, {-35, 0, -20}, {30, 0, -20}),
        ACCENT(5, 3, {0, 0, 0}, {-10, 0, 0}, {10, 0, 0})
    },
    [SPECIES_CHARMANDER] = {
        BASE(1, 4, {0, 0, 0}, {-20, 10, 0}, {12, 20, -20}),
    },
    [SPECIES_CHARMELEON] = {
        BASE(1, 4, {-12, -10, 20}, {-30, -15, 25}, {0, 0, 0}),
    },
    [SPECIES_CHARIZARD] = {
        BASE(3, 3, {0, 0, 0}, {-20, 10, 10}, {15, 20, -20}),
    },
    [SPECIES_SQUIRTLE] = {
        BASE(5, 4, {0, 0, 0}, {25, 20, -10}, {50, 20, 0}, {-60, 10, -20}),
    },
    [SPECIES_WARTORTLE] = {
        BASE(3, 4, {0, 0, 0}, {50, 0, 0}, {85, 0, 0}, {-30, 0, 0}),
    },
    [SPECIES_BLASTOISE] = {
        BASE(5, 5, {0, 0, 0}, {50, 0, 0}, {80, 0, 0}, {-30, 0, 0}),
    },
    [SPECIES_EEVEE] = {
        BASE(1, 15, {0, 0, 0}, {-30, 0, 20}, {0, 0, 0}),
    },
    [SPECIES_WURMPLE] = {
        BASE(1, 15, {0, 0, 0}, {128, 0, -25}, {40, 0, 0}),
    },
};
static const struct SpeciesVariant gSpeciesShinyVariants[NUM_SPECIES] = 
{
  [SPECIES_BULBASAUR] = {
      BASE(10, 3, {0, 0, 0}, {25, 0, 20}, {-30, 0, -20}),
  },
  [SPECIES_IVYSAUR] = {
      BASE(9, 4, {0, 0, 0}, {25, 0, 20}, {-30, 0, -20}),
  },
  [SPECIES_VENUSAUR] = {
      BASE(9, 4, {0, 0, 0}, {25, 0, 20}, {-30, 0, -20}),
  },
  [SPECIES_CHARMANDER] = {
    BASE(7, 6, {0, 0, 0}, {128, 0, 0}, {64, 0, 0}, {32, 0, 0}),
  },
  [SPECIES_CHARMELEON] = {
    BASE(7, 4, {0, 0, 0}, {128, 0, 0}, {64, 0, 0}, {32, 0, 0}),
  },
  [SPECIES_CHARIZARD] = {
    BASE(6, 5, {0, 0, 0}, {128, 0, 0}, {64, 0, 0}, {32, 0, 0}),
  },
  [SPECIES_SQUIRTLE] = {
    BASE(5, 4, {0, 0, 0}, {0, -65, 20}),
    ACCENT(11, 3, {0, 0, 0}, {0, -40, 20}),
  },
  [SPECIES_WARTORTLE] = {
    BASE(3, 4, {0, 0, 0}, {0, -65, 20}),
    ACCENT(9, 3, {0, 0, 0}, {0, -40, 20}),  
  },
  [SPECIES_BLASTOISE] = {
    BASE(5, 5, {0, 0, 0}, {0, -75, 20}),
    ACCENT(14, 2, {0, 0, 0}, {0, -40, 20}),
  },
};