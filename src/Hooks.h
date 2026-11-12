#pragma once

// Hooks, rewritten from the original REL::HookVFT / REL::Hook (an AE-only CommonLib fork's helpers) onto
// CommonLibSSE-NG's write_vfunc and the SKSE trampoline, so they resolve on SE 1.5.97 and AE alike.

namespace Hooks
{
	// Installs every hook and logs one line per hook with its resolved address (rule 14).
	// Needs SKSE::AllocTrampoline to have run first (the main-update call patch uses 14 bytes).
	void Install();

	struct SprintHandlerHook
	{
		static void ProcessButton(RE::SprintHandler* a_this, RE::ButtonEvent* a_event, RE::PlayerControlsData* a_data);
		static inline REL::Relocation<decltype(&ProcessButton)> _original;
	};

	struct SneakHandlerHook
	{
		static void ProcessButton(RE::SneakHandler* a_this, RE::ButtonEvent* a_event, RE::PlayerControlsData* a_data);
		static inline REL::Relocation<decltype(&ProcessButton)> _original;
	};

	struct PlayerUpdateLoop
	{
		static void PlayerUpdate(RE::PlayerCharacter* a_this, float a_delta);
		static inline REL::Relocation<decltype(&PlayerUpdate)> _original;
	};

	// The call inside the main loop the original code hooked (AE id 36564 + 0xC26). The SE site was matched by the
	// surrounding instructions in the decrypted 1.5.97 code: id 35565 + 0x731, the same
	// "xor edx,edx / lea rcx,[global] / call / mov rcx,rax / call" sequence.
	struct MainUpdateLoop
	{
		static std::uintptr_t Thunk(std::uintptr_t a_rcx, std::uintptr_t a_rdx, std::uintptr_t a_r8, std::uintptr_t a_r9);
		static inline REL::Relocation<decltype(&Thunk)> _original;
	};
}
