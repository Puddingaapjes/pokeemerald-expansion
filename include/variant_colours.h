#include "global.h"
#include "constants/species.h"

#define MAX_VARIANTS 4

struct PaletteRange
{
    u8 start : 4;  // Start index of palette customisation range
    u8 length : 4; // Length of customisation range
};

struct PaletteShift
{
    s8 hueAmount;   
    s8 chrAmount;  
    s8 lumAmount;
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
const struct SpeciesVariant *GetSpeciesVariants(enum Species species, bool32 isShiny);

void ApplyPaletteVariantToPaletteBuffer(u16 pal16[16], const struct PaletteVariant *pv, u8 varIdx);
void ApplyCustomRestrictionToPaletteBuffer(u8 hMin, u8 hMax, u8 cMin, u8 cMax, u8 lMin, u8 lMax, u16 pal16[16]);
void ApplyMonSpeciesVariantToPaletteBuffer(enum Species species, bool32 isShiny, u32 personality, u16 pal16[16]);
u8 GetMonVariantIndex(enum Species species, bool32 isShiny, u32 personality);

// Species data helpers
#define BASE(s, l, ...)                             \
    .base.paletteRange = { .start = (s), .length = (l) },   \
    .base.paletteShift = { __VA_ARGS__ },                   \
    .numVariants = sizeof((struct PaletteShift[]){__VA_ARGS__}) / sizeof(struct PaletteShift)

#define ACCENT(s, l, ...)                           \
    .accent.paletteRange = { .start = (s), .length = (l) }, \
    .accent.paletteShift = { __VA_ARGS__ }

static const struct SpeciesVariant gSpeciesVariants[NUM_SPECIES] = {
    [SPECIES_BULBASAUR] = {
        BASE(2, 5, {0, 0, 0}, {-55, 0, -10}, {40, 0, 0}),
        ACCENT(7, 5, {0, 0, 0}, {-8, 0, 0}, {12, 0, 0})
    },
    [SPECIES_IVYSAUR] = {
        BASE(2, 4, {0, 0, 0}, {-52, 0, -10}, {40, 0, 0}),
        ACCENT(6, 4, {0, 0, 0}, {-8, 0, 0}, {12, 0, 0})
    },
    [SPECIES_VENUSAUR] = {
        BASE(2, 4, {0, 0, 0}, {-52, 0, -10}, {40, 0, 0}),
        ACCENT(6, 2, {0, 0, 0}, {-8, 0, 0}, {12, 0, 0})
    },
    [SPECIES_CHARMANDER] = {
        BASE(2, 4, {0, 0, 0}, {-30, -5, 10}, {7, 12, -16}),
        ACCENT(4, 1, {0, 0, 0}, {0, 0, 0}, {8, 0, 0})
    },
    [SPECIES_CHARMELEON] = {
        BASE(2, 5, {-22, -18, 10}, {-38, -20, 20}, {0, 0, 0}),
    },
    [SPECIES_CHARIZARD] = {
        BASE(2, 3, {0, 0, 0}, {-30, -3, 14}, {12, 20, -16}),
        ACCENT(4, 3, {0, 0, 0}, {0, 0, 0}, {10, 10, 0})
    },
    [SPECIES_SQUIRTLE] = {
        BASE(2, 4, {-66, 40, -10}, {0, 0, 0}, {35, 10, 5}),
    },
    [SPECIES_WARTORTLE] = {
        BASE(2, 4, {0, 0, 0}, {-50, 0, -20}, {40, -10, 0}),
    },
    [SPECIES_BLASTOISE] = {
        BASE(2, 4, {0, 0, 0}, {-50, 0, 0}, {40, -10, 0}),
    },
    [SPECIES_EEVEE] = {
        BASE(1, 15, {0, 0, 0}, {-30, 0, 20}, {0, 0, 0}),
    },
    [SPECIES_WURMPLE] = {
        BASE(1, 15, {0, 0, 0}, {127, 0, -25}, {40, 0, 0}),
    },
};

static const struct SpeciesVariant gSpeciesShinyVariants[NUM_SPECIES] = 
{
    [SPECIES_BULBASAUR] = {
        BASE(11, 3, {0, 0, 0}, {40, 0, 0}, {-30, 0, 0}),
    },
    [SPECIES_IVYSAUR] = {
        BASE(10, 4, {0, 0, 0}, {40, 0, 0}, {-20, 0, 0}),
    },
    [SPECIES_VENUSAUR] = {
        BASE(8, 4, {0, 0, 0}, {40, 0, 0}, {-30, 0, 0}),
    },
    [SPECIES_CHARMANDER] = {
        BASE(8, 6, {0, 0, 0}, {127, 0, 0}, {20, 0, 20}),
        ACCENT(9, 2, {0, 0, 0}, {0, 0, 0}, {40, 0, 0})
    },
    [SPECIES_CHARMELEON] = {
        BASE(9, 4, {0, 0, 0}, {127, 0, 0}, {20, 0, 20}),
        ACCENT(10, 2, {0, 0, 0}, {0, 0, 0}, {40, 0, 0})
    },
    [SPECIES_CHARIZARD] = {
        BASE(7, 5, {0, 0, 0}, {127, 0, 0}, {20, 0, 20}),
        ACCENT(10, 2, {0, 0, 0}, {0, 0, 0}, {40, 0, 0})
    },
    [SPECIES_SQUIRTLE] = {
        BASE(2, 5, {0, 0, 0}, {0, -70, 20}),
        ACCENT(7, 5, {0, 0, 0}, {0, -30, 0})
    },
    [SPECIES_WARTORTLE] = {
        BASE(2, 4, {0, 0, 0}, {0, -70, 30}),
        ACCENT(7, 4, {0, 0, 0}, {0, -30, 0})
    },
    [SPECIES_BLASTOISE] = {
        BASE(2, 4, {0, 0, 0}, {0, -70, 30}),
        ACCENT(7, 4, {0, 0, 0}, {0, -30, 0})
    },
};