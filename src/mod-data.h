#pragma once

#include <string_view>

struct MOD
{
	inline static constexpr std::string_view INI_FILE = "Simple Dodge.ini";
	inline static constexpr std::string_view LOG_NAME = "Simple Dodge";

	// Our own light plugin (the owner, 2026-11-11: our own assets in place of the earlier addon plugin):
	// 0x800 SDG_DodgePerk, 0x801 SDG_DodgeSpellPerk, 0x802 SDG_OnDodgeSpell "Dodge Guard".
	inline static constexpr std::string_view MOD_NAME = "Simple Dodge.esp";

	inline static constexpr RE::FormID DUMMY_SPELL_LOCK_PERK_FORMID = 0x801;
	inline static constexpr RE::FormID DUMMY_DODGE_SPELL_FORMID = 0x802;
	inline static constexpr RE::FormID DODGE_PERK_DUMMY_FORMID = 0x800;

	inline static constexpr std::string_view USED_AV = "DodgeCostModifier";
	inline static constexpr std::string_view EXTRA_DODGE_AV = "ExtraDodgeCostModifier";

	inline static constexpr std::string_view DODGE_COST_PERK = "ModDodgeCost";
	inline static constexpr std::string_view IFRAME_DURATION_PERK = "ModiFrameDuration";
};
