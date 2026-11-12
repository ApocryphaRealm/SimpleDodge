#pragma once

namespace Events
{
	using EventResult = RE::BSEventNotifyControl;

	struct InputEvent : RE::BSTEventSink<RE::InputEvent*>
	{
		static InputEvent* GetSingleton()
		{
			static InputEvent singleton;
			return std::addressof(singleton);
		}

		void        RegisterInput();
		EventResult ProcessEvent(RE::InputEvent* const* a_event, RE::BSTEventSource<RE::InputEvent*>*) override;

	private:
		InputEvent() = default;
	};

	// Watches menus open and close, only to remember WHEN one closed.
	//
	// The dodge sink cannot work that out for itself: it is woken by input, and the press that closes a menu arrives
	// after the menu has already gone, so "is a menu open" is false by then. Remembering the close is what lets the
	// press be recognised as the one that left the menu rather than a dodge (the owner, 2026-09-16).
	struct MenuEvent : RE::BSTEventSink<RE::MenuOpenCloseEvent>
	{
		static MenuEvent* GetSingleton()
		{
			static MenuEvent singleton;
			return std::addressof(singleton);
		}

		void        RegisterMenus();
		EventResult ProcessEvent(const RE::MenuOpenCloseEvent* a_event, RE::BSTEventSource<RE::MenuOpenCloseEvent>*) override;

	private:
		MenuEvent() = default;
	};

	// SKSE key code for a button event: 0-255 keyboard, 256+ mouse, 266+ gamepad (SKSE InputMap layout).
	std::uint32_t KeyCodeOf(const RE::ButtonEvent* a_button);
}
