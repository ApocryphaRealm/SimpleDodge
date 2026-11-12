#include "Hooks.h"

#include "Compat.h"
#include "Settings.h"
#include "TapDetector.h"
#include "Utility.h"
#include "dodging.h"
#include "utils/Logger.h"

namespace Hooks
{
	// Did this press BEGIN inside a menu?
	//
	// The time grace was the wrong instrument. It assumed the press that closes a menu reaches gameplay within a
	// fixed window of the close, and that holds for the System tab but not for Quest Journal Overhaul, whose
	// journal takes longer to go (the owner, 2026-09-16: "the dodge still fires when leaving the journal menu,
	// and you should probably note that the Quest journal overhaul is different than the regular system tab
	// menu. So it still doesn't dodge when exiting the system tab").
	//
	// Whether a press started in a menu is not a guess and does not depend on how long anything takes: a tap
	// fires the dodge on RELEASE, so if the matching press went down while a menu was open, that tap belongs to
	// the menu it closed and never to a dodge - however slowly the menu got around to closing.
	// Did this hook actually SEE the press that is now being released?
	//
	// SprintHandler::ProcessButton is a player-control handler, and while a menu is open the game routes input to
	// the menu instead - so a press made IN a menu never reaches here at all. Only its release does, once the menu
	// has gone and player controls are live again, and a release on its own looks exactly like a clean tap. That is
	// why the press-began-in-a-menu flag never caught it: there was no press to flag.
	//
	// The System tab closed fast enough for the time grace to cover the gap; Quest Journal Overhaul's journal is
	// slower and slipped past it (the owner, 2026-09-16, on leaving the quest menu).
	//
	// A release with no matching press is therefore not a tap this handler can claim. It is timing-independent,
	// which is the whole point - no menu has to close within any particular window.
	//
	// 1.1.0 (a player, 2026-11-12: "I set double tap and the sprint button to dodge, but it will also dodge when
	// holding the sprint button"): the press is now counted once from its FIRST down (a down that arrives while it is
	// still held - re-sent by a sprint mod, or rewritten - is not a new press), the tap is measured on our own clock as
	// well as the game's held time, and a press that was a hold tells the double-tap detector so (TapDetector.h).
	struct TapKey
	{
		Tap::Press press;
		bool       beganInMenu = false;
		bool       stopping = false;  // this press ends a sprint / sneak rather than starting a dodge
	};
	static TapKey g_sprintKey;
	static TapKey g_sneakKey;

	// Shared by both handlers. Returns true when the event was a dodge tap and must not reach the game.
	static bool HandleTapKey(TapKey& a_key, RE::ButtonEvent* a_event, bool a_active, float a_window, const char* a_what)
	{
		const auto now = Tap::Clock::now();
		const bool up = a_event->IsUp();
		if (a_event->IsDown() && a_key.press.Down(now)) {
			a_key.beganInMenu = Utility::IsInMenu();
		}
		if (a_event->IsDown() && a_active) {
			a_key.stopping = true;
		} else if (a_event->HeldDuration() < a_window) {
			if (!up) {
				return true;  // still inside the tap window: hold it back from the game until we know
			}
			const auto down = a_key.press.downAt;
			const float own = a_key.press.Up(now);
			const bool tap = Tap::IsTap(own, a_event->HeldDuration(), a_window);
			const bool blocked = Utility::IsInMenu() || a_key.beganInMenu || own < 0.0F ||
			                     Compat::WithinMenuExitGrace(Config::Settings::menu_exit_grace.GetValue());
			// ... and not in the moment just after a menu closed. The press that LEAVES a menu is handed to gameplay
			// with the menu already shut, so IsInMenu is false by then and the tap read as a dodge (the owner,
			// 2026-09-16: "the guard against dodging out of the quest journal menu did not work").
			if (tap && !blocked) {
				logger::debug("{} key tapped ({:.2f}s) - dodge input", a_what, own);
				if (Config::Settings::use_double_tap.GetValue()) {
					Dodge::OnTap(down, now);
				} else {
					Dodge::OnInput();
				}
			} else if (own < 0.0F || a_key.beganInMenu) {
				logger::debug("{} key tap ignored: {}", a_what,
					own >= 0.0F ? "the press began while a menu was open" : "no matching press - it was made while a menu held input");
			} else if (!tap) {
				logger::debug("{} key released after {:.2f}s (game reports {:.2f}s) - a hold, not a tap", a_what, own,
					a_event->HeldDuration());
				Dodge::OnHold();
			}
			a_key.beganInMenu = false;
			a_key.stopping = false;
			if (tap) {
				return true;  // a short tap is the dodge, not a sprint / sneak
			}
		} else if (!a_active && !a_key.stopping) {
			a_event->heldDownSecs = 0.0F;  // the delayed press reaches the game now, as a fresh press
		} else if (up) {
			a_key.stopping = false;
		}
		if (up && a_key.press.held) {
			a_key.press.Up(now);
			Dodge::OnHold();
		}
		return false;
	}

	void SprintHandlerHook::ProcessButton(RE::SprintHandler* a_this, RE::ButtonEvent* a_event, RE::PlayerControlsData* a_data)
	{
		if (a_event && Config::Settings::use_sprint_key.GetValue()) {
			const auto player = RE::PlayerCharacter::GetSingleton();
			const auto userEvents = RE::UserEvents::GetSingleton();
			if (player && userEvents && a_event->QUserEvent() == userEvents->sprint) {
				const bool sprinting = player->GetPlayerRuntimeData().playerFlags.isSprinting;
				if (HandleTapKey(g_sprintKey, a_event, sprinting, Config::Settings::sprinting_press_duration.GetValue(), "Sprint")) {
					return;
				}
			}
		}
		_original(a_this, a_event, a_data);
	}

	void SneakHandlerHook::ProcessButton(RE::SneakHandler* a_this, RE::ButtonEvent* a_event, RE::PlayerControlsData* a_data)
	{
		if (a_event && Config::Settings::enable_sneak_key_dodge.GetValue()) {
			const auto player = RE::PlayerCharacter::GetSingleton();
			const auto userEvents = RE::UserEvents::GetSingleton();
			if (player && userEvents && a_event->QUserEvent() == userEvents->sneak) {
				if (HandleTapKey(g_sneakKey, a_event, player->IsSneaking(), Config::Settings::sneaking_press_duration.GetValue(), "Sneak")) {
					return;
				}
			}
		}
		_original(a_this, a_event, a_data);
	}

	void PlayerUpdateLoop::PlayerUpdate(RE::PlayerCharacter* a_this, float a_delta)
	{
		if (a_this && !a_this->IsAttacking()) {
			a_this->SetGraphVariableBool("DodgeCancelEnabled", true);
		}
		_original(a_this, a_delta);
	}

	static bool wasInMenu = false;

	std::uintptr_t MainUpdateLoop::Thunk(std::uintptr_t a_rcx, std::uintptr_t a_rdx, std::uintptr_t a_r8, std::uintptr_t a_r9)
	{
		const bool inMenu = Utility::IsInMenu();
		if (wasInMenu != inMenu) {
			logger::debug("Menu state changed: {}", inMenu ? "a blocking menu opened" : "back to gameplay");
		}
		if (wasInMenu && !inMenu) {
			Dodge::g_menuBlocker.block();
			Dodge::ClearBuffer();
		}
		if (Dodge::g_menuBlocker.active()) {
			Dodge::ClearBuffer();
		} else if (auto* player = RE::PlayerCharacter::GetSingleton()) {
			Dodge::Update(player);
		}
		wasInMenu = inMenu;

		return _original(a_rcx, a_rdx, a_r8, a_r9);
	}

	void Install()
	{
#if RUNTIME_LINE == 17
		// Skyrim 1.7 put two new functions at slots 4 and 5 of every player input handler's vtable, so ProcessButton moved to
		// slot 6; CommonLibSSE-NG 7.2 still names slot 4 (gate rule input-handler-vfunc-slot4-wrong-on-17, 2026-11-08).
		constexpr std::size_t kProcessButtonSlot = 6;
#else
		constexpr std::size_t kProcessButtonSlot = 4;
#endif
		REL::Relocation<std::uintptr_t> sprintVtbl{ RE::VTABLE_SprintHandler[0] };
		SprintHandlerHook::_original = sprintVtbl.write_vfunc(kProcessButtonSlot, SprintHandlerHook::ProcessButton);
		logger::info("Hook: SprintHandler::ProcessButton (vtable {:X} slot {})", sprintVtbl.address(), kProcessButtonSlot);

		REL::Relocation<std::uintptr_t> sneakVtbl{ RE::VTABLE_SneakHandler[0] };
		SneakHandlerHook::_original = sneakVtbl.write_vfunc(kProcessButtonSlot, SneakHandlerHook::ProcessButton);
		logger::info("Hook: SneakHandler::ProcessButton (vtable {:X} slot {})", sneakVtbl.address(), kProcessButtonSlot);

		REL::Relocation<std::uintptr_t> playerVtbl{ RE::VTABLE_PlayerCharacter[0] };
		PlayerUpdateLoop::_original = playerVtbl.write_vfunc(0xAD, PlayerUpdateLoop::PlayerUpdate);
		logger::info("Hook: PlayerCharacter::Update (vtable {:X} slot 0xAD)", playerVtbl.address());

		REL::Relocation<std::uintptr_t> mainLoop{ RELOCATION_ID(35565, 36564), REL::Relocate(0x731, 0xC26) };
		const auto site = mainLoop.address();
		if (*reinterpret_cast<std::uint8_t*>(site) != 0xE8) {
			logger::critical("Hook: the main-loop call site {:X} is not a call (byte {:02X}) - another plugin patched it or this "
							 "game build differs. Dodging will not fire; nothing was written there.",
				site, *reinterpret_cast<std::uint8_t*>(site));
			return;
		}
		auto& trampoline = SKSE::GetTrampoline();
		MainUpdateLoop::_original = trampoline.write_call<5>(site, MainUpdateLoop::Thunk);
		logger::info("Hook: main loop update call at {:X} (original target {:X})", site, MainUpdateLoop::_original.address());
	}
}
