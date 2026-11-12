#include "InputEvents.h"

#include "Settings.h"
#include "Utility.h"
#include "dodging.h"
#include "ui.h"
#include "utils/Logger.h"

#include <algorithm>

namespace Events
{
	std::uint32_t KeyCodeOf(const RE::ButtonEvent* a_button)
	{
		std::uint32_t id = a_button->GetIDCode();
		switch (a_button->GetDevice()) {
		case RE::INPUT_DEVICE::kMouse:
			id += SKSE::InputMap::kMacro_MouseButtonOffset;
			break;
		case RE::INPUT_DEVICE::kGamepad:
			id = SKSE::InputMap::GamepadMaskToKeycode(id);
			break;
		default:
			break;
		}
		return id;
	}

	void InputEvent::RegisterInput()
	{
		if (const auto manager = RE::BSInputDeviceManager::GetSingleton()) {
			manager->AddEventSink(this);
			logger::info("Input: listening for the dodge key (key code {})", Config::Settings::dodge_key.GetValue());
		} else {
			logger::error("Input: BSInputDeviceManager is null; the dodge key cannot be read (sprint/sneak-key dodge still can)");
		}
	}

	void MenuEvent::RegisterMenus()
	{
		if (const auto ui = RE::UI::GetSingleton()) {
			ui->AddEventSink<RE::MenuOpenCloseEvent>(this);
			logger::info("Input: watching menu closes, so the press that leaves a menu is not taken for a dodge");
		} else {
			logger::error("Input: the UI singleton is null; a dodge can still fire on the press that closes a menu");
		}
	}

	EventResult MenuEvent::ProcessEvent(const RE::MenuOpenCloseEvent* a_event, RE::BSTEventSource<RE::MenuOpenCloseEvent>*)
	{
		if (!a_event || a_event->opening) {
			return EventResult::kContinue;
		}
		// Only the menus a dodge is already blocked inside - closing an unrelated HUD-ish menu should not eat a dodge.
		const auto& watched = Config::Forms::MenuNames;
		const std::string name(a_event->menuName.c_str() ? a_event->menuName.c_str() : "");
		if (std::find(watched.begin(), watched.end(), name) == watched.end()) {
			return EventResult::kContinue;
		}
		Compat::NoteMenuClosed();
		logger::trace("Menu \"{}\" closed; dodge presses ignored for {:.2f}s", name, Config::Settings::menu_exit_grace.GetValue());
		return EventResult::kContinue;
	}

	EventResult InputEvent::ProcessEvent(RE::InputEvent* const* a_event, RE::BSTEventSource<RE::InputEvent*>*)
	{
		if (!a_event) {
			return EventResult::kContinue;
		}
		// While the settings page is capturing a new key, the press belongs to the page, not to a dodge.
		if (Menu::Settings::capture_key_input) {
			return EventResult::kContinue;
		}

		const auto bound = Config::Settings::dodge_key.GetValue();
		for (auto e = *a_event; e; e = e->next) {
			const auto button = e->AsButtonEvent();
			if (!button || !button->IsDown() || !button->HasIDCode()) {
				continue;
			}
			const auto id = KeyCodeOf(button);
			if (bound <= 1 || id != bound) {
				continue;
			}
			if (Utility::IsInMenu()) {
				logger::trace("Dodge key {} pressed in a menu - ignored", id);
				continue;
			}
			// And for a moment AFTER a menu closes. The press that closes a menu reaches gameplay in the same breath
			// as the close, with the menu already shut, so the open check above cannot see it - which is why exiting
			// the journal dodged while exiting from its System tab, a frame slower, did not.
			if (Compat::WithinMenuExitGrace(Config::Settings::menu_exit_grace.GetValue())) {
				logger::trace("Dodge key {} pressed just after a menu closed - ignored", id);
				continue;
			}
			logger::debug("Dodge key {} pressed", id);
			Dodge::OnInput();
		}
		return EventResult::kContinue;
	}
}
