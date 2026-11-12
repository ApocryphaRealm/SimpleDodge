#include "InputEvents.h"

#include "Compat.h"
#include "Settings.h"
#include "TapDetector.h"
#include "Utility.h"
#include "dodging.h"
#include "ui.h"
#include "utils/Logger.h"

#include <algorithm>
#include <cmath>

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

	namespace
	{
		// The dodge key, counted once from its first down to its release (1.1.0). This sink runs AFTER the player
		// controls on the same events, so it also sees what their hooks rewrote - the sprint hook hands the game a held
		// press with heldDownSecs 0, which 1.0.0 read here as a new press every frame (TapDetector.h).
		Tap::DodgeKeyState g_dodgeKey;  // the decision itself; tests\test_tap_detector.cpp drives it

		bool BlockedNow(std::uint32_t a_id)
		{
			if (Utility::IsInMenu()) {
				logger::trace("Dodge key {} pressed in a menu - ignored", a_id);
				return true;
			}
			// And for a moment AFTER a menu closes. The press that closes a menu reaches gameplay in the same breath
			// as the close, with the menu already shut, so the open check above cannot see it - which is why exiting
			// the journal dodged while exiting from its System tab, a frame slower, did not.
			if (Compat::WithinMenuExitGrace(Config::Settings::menu_exit_grace.GetValue())) {
				logger::trace("Dodge key {} pressed just after a menu closed - ignored", a_id);
				return true;
			}
			return false;
		}

		// A key that is ALSO the sprint (or sneak) key, with that key's tap dodge on, belongs to that hook: one
		// physical tap reached both in 1.0.0 and counted twice.
		bool OwnedByAHook(const RE::ButtonEvent* a_button)
		{
			const auto* userEvents = RE::UserEvents::GetSingleton();
			if (!userEvents) {
				return false;
			}
			const auto& ue = a_button->QUserEvent();
			return (Config::Settings::use_sprint_key.GetValue() && ue == userEvents->sprint) ||
			       (Config::Settings::enable_sneak_key_dodge.GetValue() && ue == userEvents->sneak);
		}

		void HandleDodgeKey(const RE::ButtonEvent* a_button, std::uint32_t a_id)
		{
			const auto now = Tap::Clock::now();
			const bool pressed = a_button->IsPressed();
			// Only a NEW press is checked against the menus; a press first seen already held went down in a menu.
			const bool newPress = pressed && !g_dodgeKey.press.held;
			const bool blockedNow = newPress && BlockedNow(a_id);
			const auto action = g_dodgeKey.OnEvent(now, pressed, a_button->IsDown(), a_button->IsUp(), a_button->HeldDuration(),
				blockedNow, Config::Settings::use_double_tap.GetValue());
			switch (action) {
			case Tap::Action::kDodge:
				logger::debug("Dodge key {} pressed", a_id);
				Dodge::OnInput();
				break;
			case Tap::Action::kTap:
				logger::debug("Dodge key {} tapped", a_id);
				Dodge::OnTap(g_dodgeKey.tapDown, now);
				break;
			case Tap::Action::kHold:
				logger::trace("Dodge key {} held - not a tap", a_id);
				Dodge::OnHold();
				break;
			default:
				break;
			}
		}

		// bDirectionalDoubleTap: forward, back, left, right - each its own double-tap detector.
		Tap::DirectionalDoubleTap g_dirs[4];
		const RE::NiPoint2        kDirVec[4] = { { 0.0F, 1.0F }, { 0.0F, -1.0F }, { -1.0F, 0.0F }, { 1.0F, 0.0F } };
		const char*               kDirName[4] = { "forward", "back", "left", "right" };
		int                       g_stickDir = -1;  // the direction the left stick is pushed in, -1 = centred

		void DirectionDown(int a_dir)
		{
			if (g_dirs[a_dir].Down(Tap::Clock::now())) {
				logger::debug("Direction {} double-tapped", kDirName[a_dir]);
				Dodge::OnDirectionalDoubleTap(kDirVec[a_dir]);
			}
		}

		void DirectionUp(int a_dir) { g_dirs[a_dir].Up(Tap::Clock::now()); }

		void HandleMovementKey(const RE::ButtonEvent* a_button)
		{
			const auto* ue = RE::UserEvents::GetSingleton();
			if (!ue) {
				return;
			}
			const auto& name = a_button->QUserEvent();
			int dir = -1;
			if (name == ue->forward) { dir = 0; }
			else if (name == ue->back) { dir = 1; }
			else if (name == ue->strafeLeft) { dir = 2; }
			else if (name == ue->strafeRight) { dir = 3; }
			if (dir < 0) {
				return;
			}
			if (a_button->IsPressed()) {
				DirectionDown(dir);  // Press counts it once however many downs arrive
			} else if (a_button->IsUp()) {
				DirectionUp(dir);
			}
		}

		// The left stick as four "keys": pushed past 0.75 toward the dominant axis is a press, back under 0.3 a release.
		void HandleStick(const RE::ThumbstickEvent* a_stick)
		{
			if (!a_stick->IsLeft()) {
				return;
			}
			const float x = a_stick->xValue;
			const float y = a_stick->yValue;
			const float mag = std::sqrt(x * x + y * y);
			int dir = g_stickDir;
			if (mag >= 0.75F) {
				dir = std::abs(y) >= std::abs(x) ? (y > 0.0F ? 0 : 1) : (x < 0.0F ? 2 : 3);
			} else if (mag < 0.30F) {
				dir = -1;
			}
			if (dir == g_stickDir) {
				return;
			}
			if (g_stickDir >= 0) { DirectionUp(g_stickDir); }
			g_stickDir = dir;
			if (dir >= 0) { DirectionDown(dir); }
		}
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
		const bool directional = Config::Settings::directional_double_tap.GetValue();
		for (auto e = *a_event; e; e = e->next) {
			if (directional && e->GetEventType() == RE::INPUT_EVENT_TYPE::kThumbstick) {
				HandleStick(static_cast<const RE::ThumbstickEvent*>(e));
				continue;
			}
			const auto button = e->AsButtonEvent();
			if (!button || !button->HasIDCode()) {
				continue;
			}
			if (directional) {
				HandleMovementKey(button);
			}
			const auto id = KeyCodeOf(button);
			if (bound <= 1 || id != bound || OwnedByAHook(button)) {
				continue;
			}
			HandleDodgeKey(button, id);
		}
		return EventResult::kContinue;
	}
}
