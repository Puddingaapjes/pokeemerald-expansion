EventScript_UseFlash::
	animateflash 1
	setflashlevel 1
	releaseall
	end

EventScript_UseAutoFlash::
	lockall
	checkfieldmove FIELD_MOVE_FLASH, TRUE
	goto_if_eq VAR_RESULT, PARTY_SIZE, EventScript_CantFlash
	setfieldeffectargument 0, VAR_RESULT
	bufferpartymonnick STR_VAR_1, VAR_RESULT
	buffermovename STR_VAR_2, MOVE_FLASH
	isfollowerfieldmoveuser VAR_0x8004
	setfieldeffectargument 3, VAR_0x8004 @ skip pose if so
	dofieldeffect FLDEFF_USE_FLASH
	waitstate
	setflag FLAG_SAFE_FOLLOWER_MOVEMENT
	releaseall
	end

EventScript_CantFlash::
	closemessage
	releaseall
	end
