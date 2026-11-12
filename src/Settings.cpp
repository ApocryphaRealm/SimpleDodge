#include "Settings.h"

#include "Compat.h"
#include "utils/Logger.h"

#include <cctype>
#include <filesystem>
#include <fstream>
#include <map>

namespace Config
{
	namespace
	{
		std::string g_iniPath;

		std::string Lower(std::string a_s)
		{
			for (char& c : a_s) { c = static_cast<char>(std::tolower(static_cast<unsigned char>(c))); }
			return a_s;
		}

		std::string Trim(const std::string& a_s)
		{
			const auto b = a_s.find_first_not_of(" \t\r\n");
			if (b == std::string::npos) { return {}; }
			const auto e = a_s.find_last_not_of(" \t\r\n");
			return a_s.substr(b, e - b + 1);
		}

		std::string Unquote(std::string a_s)
		{
			if (a_s.size() >= 2 && a_s.front() == '"' && a_s.back() == '"') { return a_s.substr(1, a_s.size() - 2); }
			return a_s;
		}

		bool Parse(const std::string& a_text, bool& a_out)
		{
			const auto v = Lower(Trim(a_text));
			if (v == "1" || v == "true" || v == "yes") { a_out = true; return true; }
			if (v == "0" || v == "false" || v == "no") { a_out = false; return true; }
			return false;
		}
		bool Parse(const std::string& a_text, float& a_out)
		{
			try { a_out = std::stof(Trim(a_text)); return true; } catch (...) { return false; }
		}
		bool Parse(const std::string& a_text, std::uint32_t& a_out)
		{
			try { a_out = static_cast<std::uint32_t>(std::stoull(Trim(a_text), nullptr, 0)); return true; } catch (...) { return false; }
		}
		bool Parse(const std::string& a_text, std::string& a_out)
		{
			a_out = Unquote(Trim(a_text));
			return true;
		}

		std::string Format(bool a_v) { return a_v ? "true" : "false"; }
		std::string Format(float a_v) { char b[32]; std::snprintf(b, sizeof(b), "%.2f", a_v); return b; }
		std::string Format(std::uint32_t a_v) { return std::to_string(a_v); }
		std::string Format(const std::string& a_v) { return "\"" + a_v + "\""; }

		std::map<std::string, std::string> ReadKeys()
		{
			std::map<std::string, std::string> keys;
			std::ifstream in(g_iniPath);
			if (!in) { return keys; }
			std::string line, section;
			while (std::getline(in, line)) {
				const std::string t = Trim(line);
				if (t.empty() || t[0] == ';' || t[0] == '#') { continue; }
				if (t.front() == '[' && t.back() == ']') { section = Lower(t.substr(1, t.size() - 2)); continue; }
				const auto eq = t.find('=');
				if (eq == std::string::npos) { continue; }
				keys[section + "/" + Lower(Trim(t.substr(0, eq)))] = Trim(t.substr(eq + 1));
			}
			return keys;
		}

		// Every setting visited in one place, for load, save and restore alike.
		template <class Fn>
		void ForEach(Fn&& a_fn)
		{
			using S = Settings;
			a_fn(S::enable_sneak_key_dodge); a_fn(S::enable_dodge_in_place); a_fn(S::step_dodge);
			a_fn(S::enable_sneak_dodge); a_fn(S::enable_dodge_attack_cancel); a_fn(S::only_cancel_light);
			a_fn(S::i_frame_duration); a_fn(S::default_dodge_event); a_fn(S::sprinting_press_duration);
			a_fn(S::sneaking_press_duration); a_fn(S::use_double_tap); a_fn(S::disable_in_third);
			a_fn(S::dodge_cost); a_fn(S::dodge_key); a_fn(S::use_sprint_key); a_fn(S::use_mco_recover_window);
			a_fn(S::use_perk_lock); a_fn(S::use_percentage_cost); a_fn(S::remove_forward); a_fn(S::eight_way);
			a_fn(S::dodge_perk_ID); a_fn(S::on_dodge_spell_ID); a_fn(S::on_dodge_spell_perk_ID);
			a_fn(S::log_level);
		}
	}

	const std::string& Settings::IniPath() noexcept
	{
		if (g_iniPath.empty()) {
			g_iniPath = (std::filesystem::current_path() / "Data" / "SKSE" / "Plugins" / std::string(MOD::INI_FILE)).string();
		}
		return g_iniPath;
	}

	bool Settings::UpdateSettings(bool a_save) noexcept
	{
		IniPath();
		if (!a_save) {
			if (!std::filesystem::exists(g_iniPath)) {
				logger::warn("Settings: {} not found; keeping the compiled defaults", g_iniPath);
				return false;
			}
			const auto keys = ReadKeys();
			ForEach([&](auto& a_value) {
				const auto it = keys.find(Lower(a_value.section) + "/" + Lower(a_value.key));
				if (it == keys.end()) {
					logger::debug("Settings: [{}] {} missing; keeping {}", a_value.section, a_value.key, Format(a_value.GetValue()));
					return;
				}
				auto parsed = a_value.GetValue();
				if (Parse(it->second, parsed)) {
					a_value.SetValue(parsed);
					logger::debug("Settings: [{}] {} = {}", a_value.section, a_value.key, Format(parsed));
				} else {
					logger::warn("Settings: [{}] {} = \"{}\" is not valid; keeping {}", a_value.section, a_value.key, it->second, Format(a_value.GetValue()));
				}
			});
			logger::info("Settings loaded from {}", g_iniPath);
			return true;
		}

		std::vector<std::string> lines;
		{
			std::ifstream in(g_iniPath);
			std::string line;
			while (in && std::getline(in, line)) { lines.push_back(line); }
		}
		bool ok = true;
		ForEach([&](auto& a_value) {
			const std::string wantSection = Lower(a_value.section);
			const std::string wantKey = Lower(a_value.key);
			std::string section;
			bool written = false;
			std::size_t sectionEnd = std::string::npos;
			for (std::size_t i = 0; i < lines.size(); ++i) {
				const std::string t = Trim(lines[i]);
				if (!t.empty() && t.front() == '[' && t.back() == ']') {
					section = Lower(t.substr(1, t.size() - 2));
					continue;
				}
				if (section == wantSection) { sectionEnd = i + 1; }
				const auto eq = t.find('=');
				if (eq == std::string::npos || section != wantSection) { continue; }
				if (Lower(Trim(t.substr(0, eq))) == wantKey) {
					lines[i] = std::string(a_value.key) + " = " + Format(a_value.GetValue());
					written = true;
					break;
				}
			}
			if (!written) {
				// A key the file lacks (an older INI) is appended to its section, or a new section at the end.
				const std::string entry = std::string(a_value.key) + " = " + Format(a_value.GetValue());
				if (sectionEnd != std::string::npos) {
					lines.insert(lines.begin() + static_cast<std::ptrdiff_t>(sectionEnd), entry);
				} else {
					lines.push_back("");
					lines.push_back("[" + std::string(a_value.section) + "]");
					lines.push_back(entry);
				}
				logger::debug("Settings: added missing key [{}] {}", a_value.section, a_value.key);
			}
		});
		std::ofstream out(g_iniPath, std::ios::trunc);
		if (!out) {
			logger::error("Settings: could not open {} for writing", g_iniPath);
			return false;
		}
		for (const auto& line : lines) { out << line << '\n'; }
		logger::info("Settings saved to {}", g_iniPath);
		return ok;
	}

	void Settings::RestoreDefaults() noexcept
	{
		ForEach([](auto& a_value) { a_value.Reset(); });
		ApplyLogLevel();
		logger::debug("Settings: every value restored to its compiled default (not saved yet)");
	}

	void Settings::ApplyLogLevel() noexcept
	{
		const auto lvl = static_cast<spdlog::level::level_enum>(std::clamp<std::uint32_t>(log_level.GetValue(), 0u, 6u));
		SKSE::log::set_level(lvl, lvl);
	}

	void Forms::LoadForms() noexcept
	{
		auto* dh = RE::TESDataHandler::GetSingleton();
		if (!dh) {
			logger::error("Forms: TESDataHandler is null at kDataLoaded; perk lock and on-dodge spell stay off");
			return;
		}
		if (!Compat::IsModLoaded(MOD_NAME)) {
			logger::error("Forms: {} is not active - enable it so the dodge perk and on-dodge spell forms exist. "
						  "Dodging itself still works.", MOD_NAME);
			return;
		}

		dummyDodgeSpell = dh->LookupForm<RE::SpellItem>(DUMMY_DODGE_SPELL_FORMID, MOD_NAME);
		DodgePerkDummy = dh->LookupForm<RE::BGSPerk>(DODGE_PERK_DUMMY_FORMID, MOD_NAME);
		dummySpellLockPerk = dh->LookupForm<RE::BGSPerk>(DUMMY_SPELL_LOCK_PERK_FORMID, MOD_NAME);
		logger::debug("Forms: dummy spell {}, dummy dodge perk {}, dummy spell-lock perk {}",
					  dummyDodgeSpell ? "found" : "MISSING", DodgePerkDummy ? "found" : "MISSING", dummySpellLockPerk ? "found" : "MISSING");

		auto resolve = [](const std::string& a_text, const char* a_what) -> RE::TESForm* {
			if (a_text.empty()) {
				logger::debug("Forms: {} not set", a_what);
				return nullptr;
			}
			auto* form = Compat::GetFormFromString(a_text);
			if (!form) {
				logger::error("Forms: {} \"{}\" did not resolve - check the [Forms] section of {}", a_what, a_text, INI_FILE);
			}
			return form;
		};

		if (auto* f = resolve(Settings::dodge_perk_ID.GetValue(), "dodge perk")) {
			ActualDodgePerk = f->As<RE::BGSPerk>();
			logger::info("Forms: dodge perk is {}", ActualDodgePerk ? ActualDodgePerk->GetName() : "(not a perk)");
		}
		if (auto* f = resolve(Settings::on_dodge_spell_perk_ID.GetValue(), "on-dodge spell lock perk")) {
			SpellLockPerk = f->As<RE::BGSPerk>();
			logger::info("Forms: on-dodge spell lock perk is {}", SpellLockPerk ? SpellLockPerk->GetName() : "(not a perk)");
		}
		if (auto* f = resolve(Settings::on_dodge_spell_ID.GetValue(), "on-dodge spell")) {
			onDodgeSpell = f->As<RE::SpellItem>();
			logger::info("Forms: on-dodge spell is {}", onDodgeSpell ? onDodgeSpell->GetName() : "(not a spell)");
		}
		TDMGlobal = RE::TESForm::LookupByEditorID<RE::TESGlobal>("TDM_DirectionalMovement");
		logger::debug("Forms: True Directional Movement global {}", TDMGlobal ? "found" : "not present");
	}
}
