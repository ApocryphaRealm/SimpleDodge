#include "ui.h"

#include "InputEvents.h"
#include "Settings.h"

#include "SKSEMenuFramework.h"
#include "PreciseSlider.h"
#include "SliderNudge.h"
#include "utils/Logger.h"
#include "utils/Strings.h"
#include "utils/Toggle.h"

#include <CLIBUtil/hotkeys.hpp>

#include <functional>

namespace Menu
{
	namespace
	{
		using S = Config::Settings;

		std::string g_status;

		constexpr const char* kEvents[] = { "TKDodgeBack", "TKDodgeForward", "TKDodgeLeft", "TKDodgeRight" };
		constexpr const char* kEventKeys[] = { "SDG_EventBack", "SDG_EventForward", "SDG_EventLeft", "SDG_EventRight" };
		constexpr const char* kEventNames[] = { "Back", "Forward", "Left", "Right" };

		constexpr const char* kLogKeys[] = { "SDG_LogTrace", "SDG_LogDebug", "SDG_LogInfo", "SDG_LogWarning", "SDG_LogError", "SDG_LogCritical", "SDG_LogOff" };
		constexpr const char* kLogNames[] = { "Trace", "Debug", "Info", "Warning", "Error", "Critical", "Off" };

		void OnMainThread(std::function<void()> a_task)
		{
			if (auto* tasks = SKSE::GetTaskInterface()) {
				tasks->AddTask(std::move(a_task));
			}
		}

		bool HasRequiredExports()
		{
			constexpr const char* required[] = {
				"AddSectionItem", "igTextV", "igTextDisabledV", "igTextWrappedV", "igSetTooltipV", "igSeparatorText",
				"igCombo_Str_arr", "igSliderFloat", "igIsKeyPressed_Bool", "igIsItemClicked", "igIsItemActive",
				"igIsItemHovered", "igButton", "igSameLine", "igSpacing", "igPushItemWidth", "igPopItemWidth",
				"igGetCursorScreenPos", "igGetWindowDrawList", "igGetFrameHeight", "igInvisibleButton", "igPushID_Str",
				"igPopID", "ImDrawList_AddRectFilled", "ImDrawList_AddCircleFilled"
			};
			for (const char* name : required) {
				if (!GetMenuFrameworkFunction<void*>(name)) {
					logger::warn("UI: the menu framework does not export \"{}\"", name);
					return false;
				}
			}
			return true;
		}

		void Help(const char* a_text)
		{
			ImGuiMCP::SameLine();
			ImGuiMCP::TextDisabled("%s", strings::TR("SDG_HelpMark", "(?)"));
			if (ImGuiMCP::IsItemHovered()) {
				ImGuiMCP::SetTooltip("%s", a_text);
			}
		}

		void Switch(const char* a_key, const char* a_label, Config::Value<bool>& a_value, const char* a_helpKey, const char* a_help)
		{
			bool v = a_value.GetValue();
			if (ImGuiMCP::Toggle(strings::TR(a_key, a_label), &v)) {
				a_value.SetValue(v);
				logger::debug("UI: {} -> {}", a_value.key, v);
			}
			Help(strings::TR(a_helpKey, a_help));
		}

		void Slider(const char* a_key, const char* a_label, Config::Value<float>& a_value, float a_min, float a_max,
			const char* a_format, float /*a_step*/, const char* a_helpKey, const char* a_help)
		{
			float v = a_value.GetValue();
			const std::string label = strings::TR(a_key, a_label);
			// rule 68 (applied at 1.1.0): precise::SliderFloat holds a keyboard / D-pad nudge to one unit of the shown digit,
			// and precise::HighlightNudge steps a highlighted slider on Left / Right; they replace the a_step arrow nudge.
			bool changed = precise::SliderFloat(label.c_str(), &v, a_min, a_max, a_format);
			if (precise::HighlightNudge(&v, a_min, a_max, a_format)) { changed = true; }
			v = std::clamp(v, a_min, a_max);
			if (changed) {
				a_value.SetValue(v);
				logger::debug("UI: {} -> {:.2f}", a_value.key, v);
			}
			Help(strings::TR(a_helpKey, a_help));
		}

		// AMF reserved keys (rule 28): whatever the framework reports right now, asked at each capture.
		std::vector<std::int32_t> ReservedKeys()
		{
			using Fn = std::uint32_t (*)(std::int32_t*, std::uint32_t);
			std::vector<std::int32_t> out;
			if (auto fn = GetMenuFrameworkFunction<Fn>("SMF_GetReservedKeyCodes")) {
				std::int32_t buf[32]{};
				const auto n = fn(buf, 32);
				out.assign(buf, buf + std::min<std::uint32_t>(n, 32));
			}
			return out;
		}

		std::string KeyName(std::uint32_t a_key)
		{
			if (a_key <= 1) {
				return strings::TR("SDG_Unbound", "Unbound");
			}
			std::string name(clib_util::hotkeys::details::GetNameByKey(a_key));
			if (name.empty()) {
				name = std::to_string(a_key);
			}
			return name;
		}

		void DrawDodgeKeyRow()
		{
			const auto key = S::dodge_key.GetValue();
			ImGuiMCP::Text("%s: %s", strings::TR("SDG_DodgeKey", "Dodge key"), KeyName(key).c_str());
			ImGuiMCP::SameLine();
			if (!Settings::capture_key_input) {
				if (ImGuiMCP::Button(strings::TR("SDG_Rebind", "Rebind"))) {
					Settings::capture_key_input = true;
					g_status.clear();
					logger::debug("UI: waiting for a key to bind to dodge");
				}
				ImGuiMCP::SameLine();
				if (ImGuiMCP::Button(strings::TR("SDG_Unbind", "Unbind"))) {
					S::dodge_key.SetValue(1);
					logger::debug("UI: dodge key unbound");
				}
			} else {
				ImGuiMCP::Text("%s", strings::TR("SDG_PressKey", "Press a key or controller button..."));
				ImGuiMCP::SameLine();
				if (ImGuiMCP::Button(strings::TR("SDG_Cancel", "Cancel"))) {
					Settings::capture_key_input = false;
				}
			}
			Help(strings::TR("SDG_HelpDodgeKey", "The key or controller button that dodges. Keyboard, mouse and controller buttons all work."));
		}

		void RenderButtons()
		{
			ImGuiMCP::SeparatorText("");
			if (ImGuiMCP::Button(strings::TR("SDG_Save", "Save"))) {
				g_status = strings::TR("SDG_Saving", "Saving...");
				OnMainThread([]() {
					g_status = S::UpdateSettings(true) ? strings::TR("SDG_Saved", "Settings saved.")
					                                   : strings::TR("SDG_SaveFail", "Could not write the INI. See the log for why.");
				});
			}
			Help(strings::TR("SDG_HelpSave", "Writes every setting on this page to the INI so it survives a restart."));
			ImGuiMCP::SameLine();
			if (ImGuiMCP::Button(strings::TR("SDG_Reload", "Reload from INI"))) {
				OnMainThread([]() {
					g_status = S::UpdateSettings(false) ? strings::TR("SDG_Reloaded", "Settings reloaded from the INI.")
					                                    : strings::TR("SDG_ReloadFail", "Could not read the INI. See the log for why.");
					S::ApplyLogLevel();
				});
			}
			Help(strings::TR("SDG_HelpReload", "Throws away unsaved changes and re-reads the INI from disk."));
			ImGuiMCP::SameLine();
			if (ImGuiMCP::Button(strings::TR("SDG_Restore", "Restore defaults"))) {
				OnMainThread([]() { S::RestoreDefaults(); });
				g_status = strings::TR("SDG_Restored", "Defaults restored. Press Save to keep them.");
			}
			Help(strings::TR("SDG_HelpRestore", "Puts every setting back to its fresh-install value. Nothing is written until you press Save."));
			if (!g_status.empty()) {
				ImGuiMCP::TextWrapped("%s", g_status.c_str());
			}
			ImGuiMCP::Spacing();
			ImGuiMCP::Text("%s", S::IniPath().c_str());
		}
	}

	void RegisterDodgeMenu()
	{
		if (!SKSEMenuFramework::IsInstalled()) {
			logger::info("UI: no menu framework installed; settings come from the INI only");
			return;
		}
		if (!HasRequiredExports()) {
			logger::warn("UI: the installed menu framework is too old for this page; update the Apocrypha Menu Framework");
			return;
		}
		SKSEMenuFramework::SetSection("Simple Dodge");  // the menu shows this name (owner, 2026-11-11: the mod is "Simple Dodge")
		SKSEMenuFramework::AddSectionItem("Settings", Settings::RenderSettings);
		SKSEMenuFramework::AddInputEvent(Settings::OnInput);
		logger::info("UI: settings page registered with the menu framework");
	}

	bool __stdcall Settings::OnInput(RE::InputEvent* a_event)
	{
		if (!capture_key_input) {
			return false;
		}
		for (auto e = a_event; e; e = e->next) {
			const auto button = e->AsButtonEvent();
			if (!button || !button->HasIDCode() || !button->IsDown()) {
				continue;
			}
			const auto key = Events::KeyCodeOf(button);
			if (key == 256) {  // left mouse clicks the page itself; never capture it
				continue;
			}
			const auto reserved = ReservedKeys();
			if (key < 256 && std::find(reserved.begin(), reserved.end(), static_cast<std::int32_t>(key)) != reserved.end()) {
				g_status = std::string(strings::TR("SDG_Reserved", "That key is reserved by the menu framework. Pick another.")) +
				           " (" + KeyName(key) + ")";
				logger::debug("UI: capture refused key {} - reserved by the framework", key);
				return true;
			}
			S::dodge_key.SetValue(key);
			capture_key_input = false;
			g_status = std::string(strings::TR("SDG_Bound", "Dodge bound to")) + " " + KeyName(key) + ". " +
			           strings::TR("SDG_RememberSave", "Press Save to keep it.");
			logger::debug("UI: dodge key captured {}", key);
			return true;
		}
		return false;
	}

	void __stdcall Settings::RenderSettings()
	{
		strings::Tick();

		ImGuiMCP::TextWrapped("%s", strings::TR("SDG_Intro", "Changes apply immediately. Press Save to keep them. After changing the dodge animation patch, run Pandora again."));
		ImGuiMCP::Spacing();
		ImGuiMCP::PushItemWidth(260.0F);

		ImGuiMCP::SeparatorText(strings::TR("SDG_SecDodge", "Dodging"));
		Switch("SDG_StepDodge", "Step dodge instead of roll", S::step_dodge, "SDG_HelpStepDodge", "Short sidesteps instead of rolls.");
		Switch("SDG_InPlace", "Dodge while standing still", S::enable_dodge_in_place, "SDG_HelpInPlace", "Dodging with no direction held uses the default direction below.");
		{
			int current = 0;
			for (int i = 0; i < 4; ++i) {
				if (S::default_dodge_event.GetValue() == kEvents[i]) { current = i; }
			}
			std::vector<std::string> store;
			std::vector<const char*> labels;
			for (int i = 0; i < 4; ++i) { store.emplace_back(strings::TR(kEventKeys[i], kEventNames[i])); }
			for (auto& s : store) { labels.push_back(s.c_str()); }
			if (ImGuiMCP::Combo(strings::TR("SDG_DefaultDir", "Default direction"), &current, labels.data(), 4)) {
				S::default_dodge_event.SetValue(kEvents[current]);
			}
			Help(strings::TR("SDG_HelpDefaultDir", "The direction used when dodging without holding a direction."));
		}
		Switch("SDG_NoForward", "Block forward dodge", S::remove_forward, "SDG_HelpNoForward", "Holding forward does not dodge.");
		Switch("SDG_EightWay", "Eight-way dodging", S::eight_way, "SDG_HelpEightWay", "Diagonal directions get their own dodge. Off: the four main directions only. Needs Pandora run again.");
		Switch("SDG_NoThird", "Only in first person", S::disable_in_third, "SDG_HelpNoThird", "Turns dodging off in third person.");
		Slider("SDG_IFrames", "Invincibility time", S::i_frame_duration, 0.0F, 3.0F, "%.2f s", 0.05F, "SDG_HelpIFrames",
			"How long you cannot be hit after a dodge starts. Needs IFrame Generator RE. Animations with their own i-frame annotations ignore this.");

		ImGuiMCP::SeparatorText(strings::TR("SDG_SecKeys", "Keys"));
		DrawDodgeKeyRow();
		Switch("SDG_DoubleTap", "Double-tap to dodge", S::use_double_tap, "SDG_HelpDoubleTap", "Dodge only when the dodge, sprint or sneak key is pressed twice quickly.");
		Switch("SDG_SprintKey", "Dodge with a tap of Sprint", S::use_sprint_key, "SDG_HelpSprintKey", "A quick tap of the sprint key dodges; holding it sprints.");
		Slider("SDG_SprintTap", "Sprint tap length", S::sprinting_press_duration, 0.05F, 2.0F, "%.2f s", 0.05F, "SDG_HelpSprintTap", "A sprint press shorter than this dodges.");
		Switch("SDG_SneakKey", "Dodge with a tap of Sneak", S::enable_sneak_key_dodge, "SDG_HelpSneakKey", "A quick tap of the sneak key dodges; holding it sneaks.");
		Slider("SDG_SneakTap", "Sneak tap length", S::sneaking_press_duration, 0.05F, 2.0F, "%.2f s", 0.05F, "SDG_HelpSneakTap", "A sneak press shorter than this dodges.");

		ImGuiMCP::SeparatorText(strings::TR("SDG_SecStamina", "Stamina"));
		Slider("SDG_Cost", "Dodge cost", S::dodge_cost, 0.0F, 100.0F, "%.1f", 1.0F, "SDG_HelpCost", "Stamina each dodge uses (or percent of max stamina, below).");
		Switch("SDG_Percent", "Cost is a percentage of max stamina", S::use_percentage_cost, "SDG_HelpPercent", "Treats the dodge cost as a percentage instead of a flat amount.");

		ImGuiMCP::SeparatorText(strings::TR("SDG_SecAttacks", "Attacks and sneaking"));
		Switch("SDG_Cancel", "Dodge cancels attacks", S::enable_dodge_attack_cancel, "SDG_HelpCancel", "A dodge can interrupt your attack.");
		Switch("SDG_LightOnly", "Only cancel light attacks", S::only_cancel_light, "SDG_HelpLightOnly", "Power attacks cannot be cancelled by a dodge.");
		Switch("SDG_MCO", "Only in the MCO/BFCO recovery window", S::use_mco_recover_window, "SDG_HelpMCO", "With MCO or BFCO, an attack can only be cancelled into a dodge once its recovery window opens.");
		Switch("SDG_Sneak", "Dodge while sneaking", S::enable_sneak_dodge, "SDG_HelpSneak", "Allows dodging from sneak.");

		ImGuiMCP::SeparatorText(strings::TR("SDG_SecPerks", "Perks and spells"));
		Switch("SDG_PerkLock", "Dodging needs a perk", S::use_perk_lock, "SDG_HelpPerkLock", "Only characters with the dodge perk (set in the INI's [Forms] section) can dodge.");
		ImGuiMCP::TextWrapped("%s %s", strings::TR("SDG_PerkIs", "Dodge perk:"), S::dodge_perk_ID.GetValue().c_str());
		ImGuiMCP::TextWrapped("%s %s", strings::TR("SDG_SpellIs", "On-dodge spell:"), S::on_dodge_spell_ID.GetValue().c_str());
		Help(strings::TR("SDG_HelpForms", "Perk and spell IDs are edited in the INI (Plugin.esp|0x800 or an EditorID), then Reload from INI."));

		ImGuiMCP::SeparatorText(strings::TR("SDG_SecDebug", "Debug"));
		{
			int level = static_cast<int>(std::clamp<std::uint32_t>(S::log_level.GetValue(), 0u, 6u));
			std::vector<std::string> store;
			std::vector<const char*> labels;
			for (int i = 0; i < 7; ++i) { store.emplace_back(strings::TR(kLogKeys[i], kLogNames[i])); }
			for (auto& s : store) { labels.push_back(s.c_str()); }
			if (ImGuiMCP::Combo(strings::TR("SDG_LogLevel", "Log level"), &level, labels.data(), 7)) {
				S::log_level.SetValue(static_cast<std::uint32_t>(level));
				S::ApplyLogLevel();
			}
			Help(strings::TR("SDG_HelpLog", "Applies immediately. The log is Documents\\My Games\\Skyrim Special Edition\\SKSE\\Simple Dodge.log."));
		}

		ImGuiMCP::PopItemWidth();
		RenderButtons();
	}
}
