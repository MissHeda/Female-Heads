// COMPONENT is defined in each addon's script_component.hpp, which includes this file first.

#define MAINPREFIX z
#define PREFIX mhfh

#include "script_version.hpp"

#define VERSION_CONFIG version = MAJOR.MINOR; versionStr = QUOTE(MAJOR.MINOR.PATCHLVL); versionAr[] = {MAJOR,MINOR,PATCHLVL}

// Minimum Arma version the mod is built against (SlotItemChanged needs 2.14).
#define REQUIRED_VERSION 2.18

#define COMPONENT_NAME QUOTE(MH Female Heads - COMPONENT_BEAUTIFIED)
