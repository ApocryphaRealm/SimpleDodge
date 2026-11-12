#include "AnimationEvents.h"
#include "dodging.h"
#include "utils/Logger.h"

constexpr uint32_t hash_djb2(const char* data, const size_t size) noexcept
{
    uint32_t hash = 5381;

    for (const char* c = data; c < data + size; ++c) {
        hash = ((hash << 5) + hash) + static_cast<unsigned char>(*c);
    }

    return hash;
}

constexpr uint32_t operator"" _h(const char* str, size_t size) noexcept
{
    return hash_djb2(str, size);
}
constexpr uint32_t hash(const char* data, const size_t size) noexcept
{
    uint32_t hash = 5381;

    for (const char* c = data; c < data + size; ++c) {
        hash = ((hash << 5) + hash) + static_cast<unsigned char>(*c);
    }

    return hash;
}

RE::BSEventNotifyControl animEventHandler::HookedProcessEvent(RE::BSAnimationGraphEvent& a_event, RE::BSTEventSource<RE::BSAnimationGraphEvent>* src)
{
    const FnProcessEvent fn = fnHash.at(*reinterpret_cast<uint64_t*>(this));

    logger::trace("Animation event {} (payload {})", a_event.tag.c_str(), a_event.payload.c_str());

    const auto player = RE::PlayerCharacter::GetSingleton();

    if (a_event.tag == "TKDR_DodgeStart") {
        if (player)
            Dodge::ApplyDodgeCostActor(player);
        // 1.2.0 additions act on the player's own dodge only (the sink also sees other actors' graph events)
        if (player && a_event.holder == player)
            Dodge::OnDodgeStart(player);
    }
    if (a_event.tag == "TKDR_DodgeEnd") {
        if (player && a_event.holder == player)
            Dodge::OnDodgeEnd(player);
    }

    if (a_event.tag == "MCO_AttackInitiate" ||a_event.tag == "MCO_PowerAttackInitiate" || a_event.tag == "MCO_attackEnterNotify")
    {
        if (player)
            player->SetGraphVariableBool("DodgeCancelEnabled", false);
    }

    if (a_event.tag == "MCO_WinOpen" || a_event.tag == "MCO_PowerWinOpen")
    {
        if (player)
            player->SetGraphVariableBool("DodgeCancelEnabled", true);
    }
    if (a_event.tag == "MCO_PowerWinClose" || a_event.tag == "MCO_WinClose")
    {
        if (player)
            player->SetGraphVariableBool("DodgeCancelEnabled", false);
    }

    // BFCO (the owner, 2026-11-11: "can you add compatability for bfco?"). BFCO marks the recovery window with its own
    // annotations - BFCO_NextWinStart (light) and BFCO_NextPowerWinStart (power), the MCO_WinOpen equivalents, read
    // from BFCO 3.100.2's clips - and has no window-close event: a new swing (BFCO_PlayerAttackStart /
    // BFCO_AttackNorStart) closes it, as MCO_AttackInitiate does.
    if (a_event.tag == "BFCO_NextWinStart" || a_event.tag == "BFCO_NextPowerWinStart")
    {
        if (player)
            player->SetGraphVariableBool("DodgeCancelEnabled", true);
    }
    if (a_event.tag == "BFCO_PlayerAttackStart" || a_event.tag == "BFCO_AttackNorStart")
    {
        if (player)
            player->SetGraphVariableBool("DodgeCancelEnabled", false);
    }


    return fn ? (this->*fn)(a_event, src) : RE::BSEventNotifyControl::kContinue;
}

std::unordered_map<uint64_t, animEventHandler::FnProcessEvent> animEventHandler::fnHash;
