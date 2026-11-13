// Simple Dodge - a dodge for Skyrim SE / AE / 1.7 on CommonLibSSE-NG, with its settings page on the Apocrypha
// Menu Framework. GPL-3.0-or-later; see NOTICE.md for the projects it is based on.
#include "AnimationEvents.h"
#include "Hooks.h"
#include "InputEvents.h"
#include "Settings.h"
#include "ui.h"
#include "dodging.h"

#include "utils/AddressLibraryGuard.h"
#include "utils/Logger.h"
#include "utils/Strings.h"

namespace
{
	void Listener(SKSE::MessagingInterface::Message* a_msg)
	{
		switch (a_msg->type) {
		case SKSE::MessagingInterface::kInputLoaded:
			logger::debug("kInputLoaded: registering the dodge key listener");
			Events::InputEvent::GetSingleton()->RegisterInput();
			Events::MenuEvent::GetSingleton()->RegisterMenus();
			break;
		case SKSE::MessagingInterface::kPostLoad:
			Dodge::InitTDM();
			break;
		case SKSE::MessagingInterface::kDataLoaded:
			logger::debug("kDataLoaded: animation-event sink, forms, strings, settings page");
			animEventHandler::RegisterForPlayer();
			Config::Forms::LoadForms();
			strings::Configure("Simple Dodge");
			Menu::RegisterDodgeMenu();
			break;
		default:
			break;
		}
	}
}

SKSEPluginLoad(const SKSE::LoadInterface* a_skse)
{
	// The log first, then the Address Library guard, then SKSE::Init - in that order. CommonLibSSE-NG's
	// Init opens the Address Library itself, so a guard placed after it never ran when the file was
	// missing (oproso's wheeler.log, 2026-09-18); and the guard's own line has to land in a log that exists.
	// When the file for this game is missing the plugin loads inert with a message that names it.
	SKSE::log::init(std::string(MOD::LOG_NAME));
	if (!AddressLibraryGuard::Guard("Simple Dodge")) {
		return true;
	}
#if RUNTIME_LINE == 17
	// CommonLibSSE-NG 7.2's Init(a_skse, a_log = true) starts its own logger, which recreates this plugin's log
	// and wipes what was written above. Ours is already running.
	SKSE::Init(a_skse, false);
#else
	SKSE::Init(a_skse);
#endif

	Config::Settings::UpdateSettings(false);
	Config::Settings::ApplyLogLevel();
	SKSE::log::describe_level(std::string(MOD::INI_FILE));

	logger::info("Simple Dodge {} loading on Skyrim {}", SKSE::PluginDeclaration::GetSingleton()->GetVersion().string("."),
		REL::Module::get().version().string("."));

	SKSE::AllocTrampoline(64);
	Hooks::Install();

	const auto messaging = SKSE::GetMessagingInterface();
	if (!messaging || !messaging->RegisterListener(Listener)) {
		logger::critical("Could not register for SKSE messages; Simple Dodge cannot start");
		return false;
	}
	return true;
}
