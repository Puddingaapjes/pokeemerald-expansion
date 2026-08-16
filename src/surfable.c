#include "global.h"
#include "event_data.h"
#include "event_object_movement.h"
#include "field_effect.h"
#include "field_effect_helpers.h"
#include "field_player_avatar.h"
#include "main.h"
#include "party_menu.h"
#include "pokemon.h"
#include "sprite.h"
#include "surfable.h"
#include "constants/event_object_movement.h"
#include "constants/event_objects.h"
#include "constants/field_effects.h"
#include "constants/moves.h"
#include "constants/species.h"

static const struct SpriteTemplate sFieldEffectObjectTemplate_SurfMon = {
    .tileTag = TAG_NONE,
    .paletteTag = OBJ_EVENT_PAL_TAG_DYNAMIC,
    .oam = &gObjectEventBaseOam_32x32,
    .anims = sAnimTable_OverworldSurfing,
    .images = NULL,
    .affineAnims = gDummySpriteAffineAnimTable,
    .callback = UpdateSurfBlobFieldEffect,
};

extern const struct OamData gObjectEventBaseOam_32x32;
extern const struct OamData gObjectEventBaseOam_64x64;
extern const struct SpriteTemplate *const gFieldEffectObjectTemplatePointers[];

extern void SynchronizeSurfAnim(struct ObjectEvent *playerObj, struct Sprite *sprite);
extern void SynchronizeSurfPosition(struct ObjectEvent *playerObj, struct Sprite *sprite);
extern void UpdateBobbingEffect(struct ObjectEvent *playerObj, struct Sprite *playerSprite, struct Sprite *sprite);

static void CreateOverlaySprite(enum Species species, bool32 isShiny, bool32 isFemale);
static void UpdateSurfMonOverlay(struct Sprite *sprite);

u32 CreateSurfablePokemonSprite(void)
{
    u8 spriteId;
    struct Sprite *sprite;
    struct SpriteTemplate spriteTemplate;
    u8 i;
    enum Species species;
    bool32 isShiny;
    bool32 isFemale;

    i = VarGet(VAR_SURF_MON_SLOT);
    species = GetMonData(&gParties[B_TRAINER_PLAYER][i], MON_DATA_SPECIES, NULL);
    isShiny = IsMonShiny(&gParties[B_TRAINER_PLAYER][i]);
    isFemale = GetMonGender(&gParties[B_TRAINER_PLAYER][i]) == MON_FEMALE;

    SetSpritePosToOffsetMapCoords((s16 *)&gFieldEffectArguments[0], (s16 *)&gFieldEffectArguments[1], 8, 8);

      if (gSpeciesInfo[species].overworldDataSurfing.images != NULL)
    {
        spriteTemplate = sFieldEffectObjectTemplate_SurfMon;
        spriteTemplate.images = gSpeciesInfo[species].overworldDataSurfing.images;
        spriteTemplate.anims = gSpeciesInfo[species].overworldDataSurfing.anims;
        LoadDynamicFollowerPalette(species, isShiny, isFemale, TRUE);
        spriteId = CreateSpriteAtEnd(&spriteTemplate, gFieldEffectArguments[0], gFieldEffectArguments[1], 0x96);
        if (spriteId != MAX_SPRITES)
        {
            gSprites[spriteId].oam.paletteNum = IndexOfSpritePaletteTag(species + OBJ_EVENT_MON + (isShiny ? OBJ_EVENT_MON_SHINY : 0));
        }
        if (gSpeciesInfo[species].overworldDataSurfingOverlay.images != NULL)
        { 
            CreateOverlaySprite(species, isShiny, isFemale);
        }
    }
    else
    { // Create surf blob
        LoadObjectEventPalette(FLDEFFOBJ_SURF_BLOB);
        spriteId = CreateSpriteAtEnd(gFieldEffectObjectTemplatePointers[FLDEFFOBJ_SURF_BLOB], gFieldEffectArguments[0], gFieldEffectArguments[1], 0x96);
    }

    if (spriteId != MAX_SPRITES)
    {
        sprite = &gSprites[spriteId];
        sprite->coordOffsetEnabled = TRUE;
        sprite->data[2] = gFieldEffectArguments[2];
        sprite->data[3] = -1;
        sprite->data[6] = -1;
        sprite->data[7] = -1;
    }
    FieldEffectActiveListRemove(FLDEFF_SURF_BLOB);
    return spriteId;
}

static void CreateOverlaySprite(enum Species species, bool32 isShiny, bool32 isFemale)
{
    u8 overlaySprite;
    u8 subpriority;
    struct Sprite *sprite;
    struct SpriteTemplate spriteTemplate;

    subpriority = gSprites[gPlayerAvatar.spriteId].subpriority - 1;
    spriteTemplate = sFieldEffectObjectTemplate_SurfMon;
    spriteTemplate.images = gSpeciesInfo[species].overworldDataSurfingOverlay.images;
    spriteTemplate.anims = gSpeciesInfo[species].overworldDataSurfingOverlay.anims;
    spriteTemplate.callback = UpdateSurfMonOverlay;
    overlaySprite = CreateSpriteAtEnd(&spriteTemplate, gFieldEffectArguments[0], gFieldEffectArguments[1], subpriority);

    if (overlaySprite != MAX_SPRITES)
    {
        gSprites[overlaySprite].oam.paletteNum = IndexOfSpritePaletteTag(species + OBJ_EVENT_MON + (isShiny ? OBJ_EVENT_MON_SHINY : 0));
        sprite = &gSprites[overlaySprite];
        sprite->coordOffsetEnabled = TRUE;
        sprite->data[2] = gFieldEffectArguments[2];
        sprite->data[3] = -1;
        sprite->data[6] = -1;
        sprite->data[7] = -1;
        sprite->oam.priority = 2;
    }
    SetSurfBlob_BobState(overlaySprite, BOB_PLAYER_AND_MON);
}

static void UpdateSurfMonOverlay(struct Sprite *sprite)
{
    struct ObjectEvent *playerObj;
    struct Sprite *linkedSprite;
    u8 subpriority;
	
    playerObj = &gObjectEvents[gPlayerAvatar.objectEventId];
    linkedSprite = &gSprites[playerObj->spriteId];
	
    // Fix for Fishing whilst surfing having overlay sprite "bob" up and down appropriately, unfortunately breaks proper "jump" onto Surfing Pokemon - Needs further investigation to fix.
	if (VarGet(VAR_FREEZESURFBLOB) == 1)
	{
		SynchronizeSurfAnim(playerObj, sprite);
		SynchronizeSurfPosition(playerObj, sprite);
	}
	else
	{
    SynchronizeSurfAnim(playerObj, sprite);
    SynchronizeSurfPosition(playerObj, sprite);
	UpdateBobbingEffect(playerObj, linkedSprite, sprite);
	}

    // Reset the subpriority for the overlay sprite so it shows on top of the player
    // We need this here so the subprio is correct after a screen transition (e.g. after exiting a battle)
    subpriority = gSprites[gPlayerAvatar.spriteId].subpriority - 1;
    sprite->subpriority = subpriority;

    if (linkedSprite->animNum < MOVEMENT_ACTION_DELAY_16)
    {
        sprite->x = linkedSprite->x;
        sprite->y = linkedSprite->y + 8;
        sprite->y2 = linkedSprite->y2;
    }
    if (!(gPlayerAvatar.flags & PLAYER_AVATAR_FLAG_SURFING))
        DestroySprite(sprite);
}

