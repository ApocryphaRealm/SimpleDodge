#pragma once

#include <chrono>

#include <atomic>

// Small helpers - form-string lookup, mod-loaded check, menu check, ApplySpell - rewritten for
// CommonLibSSE-NG. The GPL-3.0 originals and their authors are credited in NOTICE.md.

#include "utils/Logger.h"

namespace Compat
{
	// "Plugin.esp|0x800" (local form ID in hex) or an EditorID (needs po3's Tweaks to resolve most types).
	inline RE::TESForm* GetFormFromString(const std::string& a_text)
	{
		if (a_text.empty()) {
			return nullptr;
		}
		if (const auto bar = a_text.find('|'); bar != std::string::npos) {
			const std::string plugin = a_text.substr(0, bar);
			const std::string id = a_text.substr(bar + 1);
			if (plugin.empty() || id.empty()) {
				logger::warn("Form string \"{}\" is missing its plugin or its form ID", a_text);
				return nullptr;
			}
			RE::FormID local = 0;
			try {
				local = static_cast<RE::FormID>(std::stoul(id, nullptr, 16));
			} catch (...) {
				logger::warn("Form string \"{}\": \"{}\" is not a hex form ID", a_text, id);
				return nullptr;
			}
			auto* dh = RE::TESDataHandler::GetSingleton();
			if (!dh) {
				logger::warn("TESDataHandler is not ready; cannot resolve \"{}\"", a_text);
				return nullptr;
			}
			return dh->LookupForm(local, plugin);
		}
		return RE::TESForm::LookupByEditorID(a_text);
	}

	inline bool IsModLoaded(std::string_view a_modName)
	{
		auto* dh = RE::TESDataHandler::GetSingleton();
		if (!dh) {
			return false;
		}
		const auto* file = dh->LookupModByName(a_modName);
		return file && file->compileIndex != 0xFF;
	}

	// The moment a watched menu last closed, and the test that goes with it.
	//
	// A menu-open check alone cannot stop a dodge on the way OUT of a menu. The press that closes the menu is handed
	// to gameplay in the same breath as the close, and by the time the dodge sink sees it the menu is already shut,
	// so it reads as an ordinary dodge press. Whether that happens at all depends on how many frames the close takes
	// - which is why the journal dodged and its System tab, one frame slower, did not.
	//
	// So the close is remembered, and presses are ignored for a short while afterwards. Steady clock: the game clock
	// stops in menus, which is exactly the span being measured.
	inline std::atomic<std::chrono::steady_clock::time_point> g_menuClosedAt{ std::chrono::steady_clock::time_point{} };

	inline void NoteMenuClosed()
	{
		g_menuClosedAt.store(std::chrono::steady_clock::now(), std::memory_order_release);
	}

	inline bool WithinMenuExitGrace(float a_seconds)
	{
		if (a_seconds <= 0.0F) {
			return false;
		}
		const auto closed = g_menuClosedAt.load(std::memory_order_acquire);
		if (closed == std::chrono::steady_clock::time_point{}) {
			return false;
		}
		return std::chrono::duration<float>(std::chrono::steady_clock::now() - closed).count() < a_seconds;
	}

	inline bool IsAnyOfMenuOpen(const std::vector<std::string>& a_menuNames)
	{
		auto* ui = RE::UI::GetSingleton();
		if (!ui) {
			return true;  // no UI yet means no gameplay either - treat as "in a menu" so nothing fires
		}
		for (const auto& name : a_menuNames) {
			if (ui->IsMenuOpen(name)) {
				return true;
			}
		}
		return false;
	}

	inline RE::ActorValue LookupActorValueByName(std::string_view a_name)
	{
		auto* list = RE::ActorValueList::GetSingleton();
#if RUNTIME_LINE == 17
		// CommonLibSSE-NG 7.2 takes a C string
		return list ? list->LookupActorValueByName(std::string(a_name).c_str()) : RE::ActorValue::kNone;
#else
		return list ? list->LookupActorValueByName(a_name) : RE::ActorValue::kNone;
#endif
	}

	inline bool IsPermanent(RE::MagicItem* a_item)
	{
		switch (a_item->GetSpellType()) {
		case RE::MagicSystem::SpellType::kDisease:
		case RE::MagicSystem::SpellType::kAbility:
		case RE::MagicSystem::SpellType::kAddiction:
			return true;
		default:
			return false;
		}
	}

	// Adds a permanent spell (ability/disease/addiction); casts anything else from the caster at the target.
	inline void ApplySpell(RE::Actor* a_caster, RE::Actor* a_target, RE::SpellItem* a_spell)
	{
		if (!a_caster || !a_target || !a_spell) {
			return;
		}
		if (IsPermanent(a_spell)) {
			a_target->AddSpell(a_spell);
			return;
		}
		if (auto* caster = a_caster->GetMagicCaster(RE::MagicSystem::CastingSource::kInstant)) {
			caster->CastSpellImmediate(a_spell, false, a_target, 1.0F, false, 0.0F, nullptr);
		} else {
			logger::warn("{} has no instant magic caster; the on-dodge spell was not cast", a_caster->GetName());
		}
	}

	// NG for SE has no Actor::IsPowerAttacking: read the current attack's data from the high process.
	inline bool IsPowerAttacking(const RE::Actor* a_actor)
	{
		if (!a_actor) {
			return false;
		}
		const auto* process = a_actor->GetActorRuntimeData().currentProcess;
		if (!process || !process->high) {
			return false;
		}
		const auto& attackData = process->high->attackData;
		return attackData && attackData->data.flags.all(RE::AttackData::AttackFlag::kPowerAttack);
	}

	inline bool IsPlayer(const RE::Actor* a_actor)
	{
		return a_actor && a_actor == RE::PlayerCharacter::GetSingleton();
	}
}
