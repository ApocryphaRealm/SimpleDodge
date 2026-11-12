#pragma once

class animEventHandler
{
private:
    template <class Ty>
    static Ty SafeWrite64Function(const uintptr_t addr, Ty data)
    {
        DWORD oldProtect;
        void* _d[2];
        memcpy(_d, &data, sizeof(data));
        constexpr size_t len = sizeof(_d[0]);

        VirtualProtect(reinterpret_cast<void*>(addr), len, PAGE_EXECUTE_READWRITE, &oldProtect);
        Ty olddata;
        memset(&olddata, 0, sizeof(Ty));
        memcpy(&olddata, reinterpret_cast<void*>(addr), len);
        memcpy(reinterpret_cast<void*>(addr), &_d[0], len);
        VirtualProtect(reinterpret_cast<void*>(addr), len, oldProtect, &oldProtect);
        return olddata;
    }

    typedef RE::BSEventNotifyControl(animEventHandler::* FnProcessEvent)(RE::BSAnimationGraphEvent& a_event, RE::BSTEventSource<RE::BSAnimationGraphEvent>* dispatcher);

    RE::BSEventNotifyControl HookedProcessEvent(RE::BSAnimationGraphEvent& a_event, RE::BSTEventSource<RE::BSAnimationGraphEvent>* src);

    static void HookSink(uintptr_t ptr)
    {
        FnProcessEvent fn = SafeWrite64Function(ptr + 0x8, &animEventHandler::HookedProcessEvent);
        fnHash.insert(std::pair(ptr, fn));
    }

public:
    /*Hook anim event sink*/
    static void Register(const bool player, const bool NPC)
    {
        if (player) {
            logger::debug("Sinking animation event hook for player");
            const REL::Relocation pcPtr{ RE::VTABLE_PlayerCharacter[2] };
            HookSink(pcPtr.address());
        }
        if (NPC) {
            logger::debug("Sinking animation event hook for NPC");
            const REL::Relocation npcPtr{ RE::VTABLE_Character[2] };
            HookSink(npcPtr.address());
        }
        logger::debug("Sinking complete.");
    }

    static void RegisterForPlayer() { Register(true, false); }

protected:
    static std::unordered_map<uint64_t, FnProcessEvent> fnHash;
};
