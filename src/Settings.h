#pragma once

// Simple Dodge settings. The code this grew from kept them in REX::TOML (two .toml files), which
// the SE CommonLibSSE-NG does not have; they now live in Data\SKSE\Plugins\Simple Dodge.ini under the SAME
// key names, read and written with plain file I/O (never the Win32 profile API - rule 16). Each value keeps
// the original GetValue()/SetValue() shape so the dodge logic reads exactly as it did.

#include "mod-data.h"

#include <cstdint>
#include <string>
#include <vector>

namespace Config
{
	template <class T>
	struct Value
	{
		const char* section;
		const char* key;
		T           current;
		T           def;

		Value(const char* a_section, const char* a_key, T a_default) :
			section(a_section), key(a_key), current(a_default), def(a_default)
		{}

		[[nodiscard]] T GetValue() const { return current; }
		void            SetValue(T a_value) { current = a_value; }
		void            Reset() { current = def; }
	};

	struct Settings : MOD
	{
		// [Settings]
		inline static Value<bool>        enable_sneak_key_dodge{ "Settings", "bEnableSneakKeyDodge", false };
		inline static Value<bool>        enable_dodge_in_place{ "Settings", "bEnableDodgeInPlace", true };
		inline static Value<bool>        step_dodge{ "Settings", "bStepDodge", true };
		inline static Value<bool>        enable_sneak_dodge{ "Settings", "bEnableSneakDodge", false };
		inline static Value<bool>        enable_dodge_attack_cancel{ "Settings", "bEnableDodgeAttackCancel", true };
		inline static Value<bool>        only_cancel_light{ "Settings", "bOnlyCancelLightAttacks", false };
		inline static Value<float>       i_frame_duration{ "Settings", "fIFrameDuration", 0.3F };
		inline static Value<std::string> default_dodge_event{ "Settings", "sDefaultDodgeEvent", std::string("TKDodgeBack") };
		inline static Value<float>       sprinting_press_duration{ "Settings", "fSprintingPressDuration", 0.3F };
		inline static Value<float>       sneaking_press_duration{ "Settings", "fSneakingPressDuration", 0.5F };
		inline static Value<bool>        use_double_tap{ "Settings", "bUseDoubleTap", false };
		inline static Value<bool>        disable_in_third{ "Settings", "bDisableInThird", false };
		inline static Value<float>       dodge_cost{ "Settings", "fDodgeCost", 15.0F };
		// Keyboard Left Shift (DirectInput 42), the classic default. SKSE key-code space: 0-255 keyboard,
		// 256+ mouse, 266+ gamepad. 1 = unbound.
		inline static Value<std::uint32_t> dodge_key{ "Settings", "uDodgeKey", 42u };
		inline static Value<bool>        use_sprint_key{ "Settings", "bUseSprintKey", true };
		inline static Value<bool>        use_mco_recover_window{ "Settings", "bUseMCORecoverWindow", false };
		inline static Value<bool>        use_perk_lock{ "Settings", "bUsePerkLock", false };
		inline static Value<bool>        use_percentage_cost{ "Settings", "bUsePercentageCost", true };
		inline static Value<bool>        remove_forward{ "Settings", "bRemoveForwardDodge", true };
		// 8-way (the owner, 2026-11-11): diagonals get their own dodge; off = the four main directions only
		inline static Value<bool>        eight_way{ "Settings", "bEightWayDodge", true };
		// Double-tap a movement key, or flick the left stick twice, to dodge that way (1.1.0, a player's request,
		// 2026-11-12). Off by default: it changes what tapping a direction does.
		inline static Value<bool>        directional_double_tap{ "Settings", "bDirectionalDoubleTap", false };
		// Rolls play the behaviour patch's TKDodgeLongRoll clips, whose motion data travels 1.5x the step's (1.1.0, a
		// player: "for the roll dodge it makes more sense to cover more ground"). Off = the roll goes as far as the
		// step, as in 1.0.0. Needs the 1.1.0 patch generated (the graph variable iSDGLongRoll); without it, the old roll.
		inline static Value<bool>        long_roll{ "Settings", "bLongRoll", true };
		// Dodge with the weapon sheathed (1.2.0, the owner, 2026-11-12). The 1.2.0 behaviour patch adds the dodge to the
		// weapons-away graph (mt_behavior); off keeps the 1.1.0 behaviour - a sheathed dodge is refused here, before
		// stamina or the event, instead of being sent to a graph state with no dodge in it.
		inline static Value<bool>        dodge_when_sheathed{ "Settings", "bDodgeWhenSheathed", false };
		// No stamina regen while the player dodges (1.2.0, the owner, 2026-11-12): Simple Dodge.esp's
		// SDG_NoStaminaRegenSpell (0x804, StaminaRateMult -100 for 3 s) is cast on TKDR_DodgeStart and dispelled on
		// TKDR_DodgeEnd; the 3 s duration is the safety net if the end event never comes.
		inline static Value<bool>        no_stamina_regen_during_dodge{ "Settings", "bNoStaminaRegenDuringDodge", false };
		// A short whoosh when the player's dodge starts (1.2.0). The sound is sDodgeSoundID in [Forms].
		inline static Value<bool>        dodge_sound{ "Settings", "bDodgeSound", false };
		// Chain a step dodge into a roll (1.2.0, the owner 2026-11-12): a dodge press during a step dodge, once
		// fChainWindowStart of the step has played, rolls in the newly pressed direction. Once per chain.
		inline static Value<bool>        chain_step_to_roll{ "Settings", "bChainStepToRoll", false };
		// Dodge while sprinting, and out of a sprint attack (1.2.0, a Nexus request, 2026-11-13). On by default: before,
		// a dodge while sprinting was refused ("Actor is sprinting"). Off brings that back.
		inline static Value<bool>        dodge_while_sprinting{ "Settings", "bDodgeWhileSprinting", true };
		inline static Value<float>       chain_window_start{ "Settings", "fChainWindowStart", 0.40F };
		// How long after a menu CLOSES a dodge key press is ignored, in seconds.
		//
		// The menu-open check is not enough on its own: the press that closes a menu is delivered to gameplay in the
		// same breath as the close, by which point the menu is no longer open and the press reads as a plain dodge.
		// That is why exiting the journal dodged (the owner, 2026-09-16: "you dont dodge when exiting out of a menu -
		// it currently dodges when exiting the journal but not the system tab") while exiting from the System tab,
		// which closes a frame later, did not. 0 turns the guard off.
		inline static Value<float>       menu_exit_grace{ "Settings", "fMenuExitGrace", 0.25F };

		// [Forms]
		inline static Value<std::string> dodge_perk_ID{ "Forms", "sDodgeRequiredPerkID", std::string("Simple Dodge.esp|0x800") };
		inline static Value<std::string> on_dodge_spell_ID{ "Forms", "sOnDodgeSpellID", std::string("Simple Dodge.esp|0x802") };
		inline static Value<std::string> on_dodge_spell_perk_ID{ "Forms", "sOnDodgeSpellRequiredPerkID", std::string("Simple Dodge.esp|0x801") };
		// Sound descriptor (SNDR) for bDodgeSound. Default: Skyrim.esm WPNSwingUnarmed (0x0C06D1), the bare-hand swing.
		inline static Value<std::string> dodge_sound_ID{ "Forms", "sDodgeSoundID", std::string("Skyrim.esm|0xC06D1") };

		// [Debug]
		inline static Value<std::uint32_t> log_level{ "Debug", "uLogLevel", 2u };  // 2 = info (project default, rule 14)

		// Reads the INI (a missing file keeps the compiled defaults). a_save=true writes every value back instead,
		// replacing each key in place so comments and unknown keys survive. Kept as one function to match the
		// original UpdateSettings(bool) call sites.
		static bool UpdateSettings(bool a_save) noexcept;
		static void RestoreDefaults() noexcept;
		static void ApplyLogLevel() noexcept;
		static const std::string& IniPath() noexcept;
	};

	struct Forms : MOD
	{
		inline static RE::SpellItem* dummyDodgeSpell = nullptr;
		inline static RE::BGSPerk*   DodgePerkDummy = nullptr;
		inline static RE::BGSPerk*   dummySpellLockPerk = nullptr;
		inline static RE::SpellItem* onDodgeSpell = nullptr;
		inline static RE::BGSPerk*   SpellLockPerk = nullptr;
		inline static RE::BGSPerk*   ActualDodgePerk = nullptr;
		inline static RE::TESGlobal* TDMGlobal = nullptr;
		inline static RE::SpellItem* NoStaminaRegenSpell = nullptr;
		inline static RE::BGSSoundDescriptorForm* DodgeSound = nullptr;

		inline static const std::vector<std::string> MenuNames{
			std::string(RE::BarterMenu::MENU_NAME),    std::string(RE::BookMenu::MENU_NAME),     std::string(RE::Console::MENU_NAME),
			std::string(RE::ContainerMenu::MENU_NAME), std::string(RE::CraftingMenu::MENU_NAME), std::string(RE::DialogueMenu::MENU_NAME),
			std::string(RE::FavoritesMenu::MENU_NAME), std::string(RE::GiftMenu::MENU_NAME),     std::string(RE::InventoryMenu::MENU_NAME),
			std::string(RE::JournalMenu::MENU_NAME),   std::string(RE::LevelUpMenu::MENU_NAME),  std::string(RE::LockpickingMenu::MENU_NAME),
			std::string(RE::MagicMenu::MENU_NAME),     std::string(RE::MapMenu::MENU_NAME),      std::string(RE::RaceSexMenu::MENU_NAME),
			std::string(RE::SleepWaitMenu::MENU_NAME), std::string(RE::StatsMenu::MENU_NAME),    std::string(RE::TrainingMenu::MENU_NAME),
			std::string(RE::TutorialMenu::MENU_NAME),  std::string(RE::TweenMenu::MENU_NAME),
		};

		static void LoadForms() noexcept;
	};
}
