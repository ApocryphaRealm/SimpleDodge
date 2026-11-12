#pragma once

// Simple Dodge's settings page, drawn on the Apocrypha Menu Framework (the SKSE Menu Framework API it
// answers - include/SKSEMenuFramework.h). Replaces the original SKSE Menu Framework page: booleans are
// on/off switches (rule 32), every visible string goes through strings::TR (rule 66), and the dodge key
// capture refuses AMF's reserved keys (rule 28).

namespace Menu
{
	// Registers the page with the framework's Mod Control Panel. Safe with no framework installed. kDataLoaded.
	void RegisterDodgeMenu();

	namespace Settings
	{
		inline bool capture_key_input = false;  // true while the page waits for a key press to bind

		bool __stdcall OnInput(RE::InputEvent* a_event);
		void __stdcall RenderSettings();
	}
}
