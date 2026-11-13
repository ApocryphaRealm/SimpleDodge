#pragma once
#include "Settings.h"
#include "TapDetector.h"

namespace Dodge
{
enum class DodgeResult : uint32_t
{
    kSuccess = 0,
    kIsDodging,
    kHasNoPerk,
    kIsAttacking,
    kIsNotInCancelState,
    kIsJumping,
    kIsSprinting,
    kIsSneaking,
    kIsSwimming,
    kIsInKillMove,
    kIsInMenu,
    kIsControlsDisabled,
    kIsInWrongState,
    kStamina,
    kOverencumbered,
    kNoDodgeBehavior,
    kWeaponSheathed,
    kUnknown = 99,
};

enum class DodgeEventResult
{
    kSuccess,
    kNoDirection,
    kForwardBlocked
};


inline const char* DodgeResultToString(const DodgeResult result)
{
    switch (result)
    {
        case DodgeResult::kSuccess:
            return "Success";

        case DodgeResult::kIsDodging:
            return "Already dodging";

        case DodgeResult::kNoDodgeBehavior:
            return "the dodge behaviour is not in this character's animation graph (no bIsDodging variable) - run Nemesis or Pandora with Simple Dodge ticked";

        case DodgeResult::kHasNoPerk:
            return "Missing required perk";

        case DodgeResult::kIsAttacking:
            return "Actor is attacking";

        case DodgeResult::kIsNotInCancelState:
            return "Attack cannot be cancelled";

        case DodgeResult::kIsJumping:
            return "Actor is jumping";

        case DodgeResult::kIsSprinting:
            return "Actor is sprinting";

        case DodgeResult::kIsSneaking:
            return "Actor is sneaking";

        case DodgeResult::kIsSwimming:
            return "Actor is swimming";

        case DodgeResult::kIsInKillMove:
            return "Actor is in killmove";

        case DodgeResult::kIsInMenu:
            return "Menu is open";

        case DodgeResult::kIsControlsDisabled:
            return "Controls are disabled";

        case DodgeResult::kIsInWrongState:
            return "Actor is in invalid state";

        case DodgeResult::kStamina:
            return "Not enough stamina";

        case DodgeResult::kOverencumbered:
            return "Actor is overencumbered";

        case DodgeResult::kWeaponSheathed:
            return "Weapon is sheathed and bDodgeWhenSheathed is off";

        default:
            return "Unknown dodge result";
    }
}


struct DodgeInputBuffer
{
    using Clock     = std::chrono::steady_clock;
    using TimePoint = Clock::time_point;

    static constexpr auto INPUT_BUFFER_TIME = std::chrono::milliseconds(400); // actual window needs testing
    TimePoint queuedAt{Clock::duration::zero()};
    bool queued      = false;
    bool checkedOnce = false;
    bool fired       = false;
    int lastRefusal  = -1;   // the refusal already logged for this press: each reason is logged once per press

    void push()
    {
        queuedAt    = Clock::now();
        queued      = true;
        fired       = false;
        lastRefusal = -1;
    }

    // seconds left before this press expires
    [[nodiscard]] float remaining() const
    {
        if (!queued)
            return 0.0f;
        return std::chrono::duration<float>(INPUT_BUFFER_TIME - (Clock::now() - queuedAt)).count();
    }

    [[nodiscard]] bool expired() const
    {
        if (!queued)
            return true;
        const bool ret = (Clock::now() - queuedAt) >= INPUT_BUFFER_TIME;
        return ret;
    }

    bool consume()
    {
        if (!queued || expired())
        {
            queued = false;
            return false;
        }
        queued = false;
        return true;
    }

    [[nodiscard]] bool can_fire() const { return queued && !fired && !expired(); }

    void mark_fired()
    {
        fired  = true;
        queued = false;
    }

    void clear()
    {
        queued   = false;
        fired    = false;
        queuedAt = TimePoint{};
    }
};

struct MenuBlocker
{
    using Clock     = std::chrono::steady_clock;
    using TimePoint = Clock::time_point;

    TimePoint blockUntil{};

    void block()
    {
        // tie the dodge blocking when a menu closes to the sprint delay instead of hard-coding a value.
        auto time  = static_cast<int>(Config::Settings::sprinting_press_duration.GetValue() * 1000);
        blockUntil = Clock::now() + std::chrono::milliseconds(time);
    }

    [[nodiscard]] bool active() const { return Clock::now() < blockUntil; }
};
static MenuBlocker g_menuBlocker;
void OnInput();                                        // A dodge request (single-press mode, or a completed double tap)
// Double-tap mode (bUseDoubleTap): a completed short tap of the dodge, sprint or sneak key - pressed at a_down and
// released at a_up, already checked short by the caller. Two in a row within the gap window dodge (TapDetector.h).
void OnTap(Tap::TimePoint a_down, Tap::TimePoint a_up);
void OnHold();                                         // a press of one of those keys that was a hold: no double tap
// bDirectionalDoubleTap: a movement key or the left stick was double-tapped toward a_dir (x right, y forward).
void OnDirectionalDoubleTap(RE::NiPoint2 a_dir);
void Update(RE::Actor* a_actor);                       // Called in the player update loop
bool CanDodge(RE::Actor* a_actor);                     // main decider if dodge is allowed
bool DoDodge(RE::Actor* a_actor);                      // do dodge
void InitTDM();                                        // True Directional Movement's API, if it is loaded
void ClearBuffer();                                    // clear input buffer. used if a menu is open
DodgeResult PerkCheck(const RE::Actor* a_actor);       // check if perk exists and the actor has the perk
DodgeResult IsDodging(const RE::Actor* a_actor);       // check if actor is already dodging
DodgeResult IsInAttackState(const RE::Actor* a_actor); // check the attack state of the actor (should be a simple build
                                                       // in function but i want to return the result
DodgeResult IsSprinting(
    const RE::Actor* a_actor); // check if actor is sprinting. returns the dodge result on top of the built in check
DodgeResult IsSneaking(const RE::Actor* a_actor);         // check if actor is sneaking. again, with dodge result
DodgeResult IsSwimming(const RE::Actor* a_actor);         // IsSwimming Check with dodge result
DodgeResult IsInKillMove(const RE::Actor* a_actor);       // Killmove check with DodgeResult
DodgeResult IsInMenu(const RE::Actor* a_actor);           // Check if a menu is open. Returns kSuccess if not
DodgeResult IsControlsDisabled(const RE::Actor* a_actor); // Success if controls are enabled
DodgeResult IsInWrongState(const RE::Actor* a_actor);     // Success if actor is in a state that allows for dodging
DodgeResult HasStamina(RE::Actor* a_actor); // success if actor has enough stamina or actor is player in god mode
DodgeResult IsOverencumbered(const RE::Actor* a_actor); // success if not overencumbered
DodgeResult IsJumping(const RE::Actor* a_actor);        // kSuccess if actor is not jumping
DodgeResult IsWeaponSheathed(const RE::Actor* a_actor); // kSuccess if drawn, or sheathed with bDodgeWhenSheathed on
DodgeResult GetDodgeResult(RE::Actor* a_actor, bool a_allowWhileDodging = false); // total result; true skips IsDodging (chain)
bool IsInGodModeHelper(const RE::Actor* a_actor);
bool CanAttackCancel(const RE::Actor* a_actor);
bool IsInMCORecovery(const RE::Actor* a_actor);
float CalculateDodgeCost(RE::Actor* a_actor);
void ApplyDodgeCostActor(RE::Actor* a_actor);
DodgeEventResult GetDodgeEvent(std::string& a_event);
void CastOnDodgeSpell(RE::Actor* a_actor);
void OnDodgeStart(RE::Actor* a_actor); // the player's TKDR_DodgeStart: no-regen spell, dodge sound
void OnDodgeEnd(RE::Actor* a_actor);   // the player's TKDR_DodgeEnd: dispel the no-regen spell
bool ChargeOnDodgeStart();             // false right after a chained roll charged itself (no double charge)


} // namespace Dodge
