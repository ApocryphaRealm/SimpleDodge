#include "dodging.h"
#include "Compat.h"
#include "utils/Logger.h"

#include "API/PerkEntryPointExtenderAPI.h"
#include "RollHeading.h"
#include "Settings.h"
#include "Utility.h"
#include "mod-data.h"

namespace Dodge
{
static DodgeInputBuffer buffer;
// 1.1.0: one detector of TAPS (press + release, each short) shared by the dodge, sprint and sneak keys, replacing the
// 1.0.0 count of "down" events, which a held sprint key could satisfy on its own (TapDetector.h says why).
static Tap::DoubleTap dodgeDoubleTap;
// Direction of a directional double tap, used only when no movement is held by the time the dodge fires.
static bool g_hasForcedDirection = false;
static RE::NiPoint2 g_forcedDirection{};
// The direction the last GetDodgeEvent read (x right, y forward, camera-relative), for turning a roll (1.2.0).
static bool g_hasInput = false;
static RE::NiPoint2 g_input{};

// The player's dodge in progress (1.2.0, step-to-roll chain): what it is, when it started and how long its clip is.
struct CurrentDodge
{
    using Clock = std::chrono::steady_clock;
    bool active = false;
    bool step = false;          // a step dodge, so a chain may follow
    bool chained = false;       // a chained roll: nothing may chain from it
    Clock::time_point start{};
    float duration = 0.8f;      // the clip's length in seconds
    Clock::time_point chargedAt{};   // a chained roll charged its own stamina here
};
static CurrentDodge g_cur;

// Clip lengths of the step dodges (third person; the motion data's durations), by event.
static float StepDuration(const std::string& a_event)
{
    if (a_event == "TKDodgeForward" || a_event == "TKDodgeForwardRight" || a_event == "TKDodgeBackLeft") return 0.866667f;
    if (a_event == "TKDodgeBack") return 0.8f;
    return 0.7f;   // Left, Right, ForwardLeft, BackRight
}

// Every roll is the forward roll, the body turned first to where the stick points (1.2.0, item 9). The input is
// camera-relative: the camera's yaw is the player's heading, plus the third-person orbit offset while free rotation is
// on (weapon sheathed). Dodge in place (no input) rolls straight ahead, no turn.
static void TurnForRoll(RE::Actor* a_actor)
{
    if (!a_actor || !g_hasInput)
        return;
    float camYaw = a_actor->data.angle.z;
    if (auto* cam = RE::PlayerCamera::GetSingleton(); cam && cam->IsInThirdPerson() && cam->currentState)
    {
        auto* tps = static_cast<RE::ThirdPersonState*>(cam->currentState.get());
        if (tps && tps->freeRotationEnabled)
            camYaw += tps->freeRotation.x;
    }
    const float from = a_actor->data.angle.z;
    const float target = RollHeading::Target(camYaw, g_input.x, g_input.y);
    a_actor->SetHeading(target);
    logger::debug("Roll: turned from {:.2f} to {:.2f} (camera {:.2f}, input {:.2f},{:.2f})", from, target, camYaw,
                  g_input.x, g_input.y);
}

static int RollStep(RE::Actor* a_actor)
{
    if (Config::Settings::long_roll.GetValue())
    {
        int ready = 0;
        if (a_actor->GetGraphVariableInt("iSDGLongRoll", ready) && ready == 1)
            return 4;
    }
    return 0;
}

// Perk Entry Point Extender is OPTIONAL. Its API header looks the DLL up on every call and logs a critical line each
// time it is missing - several per dodge press, which a player read as the reason the dodge failed (Discord report,
// 2026-11-12). Resolve it once, keep the answer either way, and say once at info level what its absence means.
static bool PerkEntryPointsAvailable()
{
    static const bool available = [] {
        if (!GetModuleHandleW(L"PerkEntryPointExtender.dll"))
        {
            logger::info("Perk Entry Point Extender is not installed (it is optional): without it, perks cannot change "
                         "the dodge cost or the invincibility time.");
            return false;
        }
        if (!PerkEntryPointExtenderAPI::RequestInterface())
        {
            logger::info("Perk Entry Point Extender is loaded but gave no interface (it is optional): perks cannot "
                         "change the dodge cost or the invincibility time.");
            return false;
        }
        logger::info("Perk Entry Point Extender found: perks can change the dodge cost and the invincibility time.");
        return true;
    }();
    return available;
}

static bool InputBlocked()
{
    return Utility::IsInMenu() || g_menuBlocker.active();
}

void OnInput()
{
    if (InputBlocked())
        return;
    g_hasForcedDirection = false;
    buffer.push();
};

void OnTap(Tap::TimePoint a_down, Tap::TimePoint a_up)
{
    if (!Config::Settings::use_double_tap.GetValue() || InputBlocked())
        return;
    if (dodgeDoubleTap.OnTap(a_down, a_up))
    {
        logger::debug("Double tap ({:.2f}s tap) - dodge input", Tap::SecondsBetween(a_down, a_up));
        OnInput();
    }
    else
    {
        logger::trace("First tap of a double tap ({:.2f}s)", Tap::SecondsBetween(a_down, a_up));
    }
}

void OnHold()
{
    dodgeDoubleTap.OnHold();
}

void OnDirectionalDoubleTap(RE::NiPoint2 a_dir)
{
    if (!Config::Settings::directional_double_tap.GetValue() || InputBlocked())
        return;
    logger::debug("Direction double-tapped ({:.0f}, {:.0f}) - dodge input", a_dir.x, a_dir.y);
    buffer.push();
    g_forcedDirection = a_dir;
    g_hasForcedDirection = true;
}

// A dodge press while the player's dodge plays (1.2.0, bChainStepToRoll): a step, once fChainWindowStart of it has
// played, becomes a roll in the newly pressed direction - turn, then the forward roll (graph event SDGChainRoll). Once per
// chain: a chained roll, or a roll, chains to nothing. A press before the window is dropped, not held for it.
static bool TryChain(RE::Actor* a_actor)
{
    using Clock = CurrentDodge::Clock;
    const float played = std::chrono::duration<float>(Clock::now() - g_cur.start).count();
    if (!g_cur.step || g_cur.chained)
    {
        logger::debug("Chain: refused - {}", g_cur.chained ? "already chained once" : "a roll does not chain");
        return false;
    }
    if (played < Config::Settings::chain_window_start.GetValue() * g_cur.duration)
    {
        logger::debug("Chain: press at {:.2f}s, before the window ({:.2f}s) - ignored", played,
                      Config::Settings::chain_window_start.GetValue() * g_cur.duration);
        return false;
    }
    if (const auto res = GetDodgeResult(a_actor, true); res != DodgeResult::kSuccess)
    {
        logger::debug("Chain failed because of: {}", DodgeResultToString(res));
        return false;
    }
    std::string ev;
    if (GetDodgeEvent(ev) == DodgeEventResult::kForwardBlocked)
        return false;
    const int iStep = RollStep(a_actor);
    a_actor->SetGraphVariableInt("iStep", iStep);
    TurnForRoll(a_actor);
    float iFrames = std::clamp(Config::Settings::i_frame_duration.GetValue(), 0.0f, 3.0f);
    a_actor->SetGraphVariableFloat("TKDR_IframeDuration", iFrames);
    if (!a_actor->NotifyAnimationGraph("SDGChainRoll"))
    {
        static bool warned = false;
        if (!warned)
        {
            warned = true;
            logger::warn("Chain: the behaviour has no SDGChainRoll - run Nemesis or Pandora again with Simple Dodge ticked");
        }
        return false;
    }
    // The chained roll stays inside the dodge state, so no new TKDR_DodgeStart comes: charge it here, through the
    // normal path (stamina was checked above), and run the start actions (no-regen spell, sound).
    ApplyDodgeCostActor(a_actor);
    OnDodgeStart(a_actor);
    g_cur.chargedAt = Clock::now();
    g_cur.step = false;
    g_cur.chained = true;
    g_cur.start = Clock::now();
    logger::debug("Chain: step -> {} (iStep {})", iStep == 4 ? "long roll" : "roll", iStep);
    return true;
}

bool ChargeOnDodgeStart()
{
    return std::chrono::duration<float>(CurrentDodge::Clock::now() - g_cur.chargedAt).count() > 0.3f;
}

void Update(RE::Actor* a_actor)
{
    if (!buffer.can_fire())
        return;

    // the dodge state is over once its clip and a margin have passed, whatever events were missed
    if (g_cur.active && std::chrono::duration<float>(CurrentDodge::Clock::now() - g_cur.start).count() > g_cur.duration + 1.0f)
        g_cur.active = false;

    if (Config::Settings::chain_step_to_roll.GetValue() && g_cur.active)
    {
        if (TryChain(a_actor))
            buffer.mark_fired();
        else
            buffer.clear();
        return;
    }

    if (!CanDodge(a_actor))
        return;

    if (DoDodge(a_actor))
    {
        buffer.mark_fired();
    };
}
bool CanDodge(RE::Actor* a_actor)
{
    if (!a_actor) // should be impossible at this point but this makes it pretty
                  // much impossible for the coming checks to fail on nullptr
    {
        return false;
    }
    const auto result = GetDodgeResult(a_actor);
    if (result == DodgeResult::kSuccess)
    {
        return true;
    }
    // once per press and reason: the buffer re-checks every frame, and the 1.2.0 round-2 test logged "Already dodging"
    // 23 times for one press during a step with the chain off
    if (buffer.lastRefusal != static_cast<int>(result))
    {
        buffer.lastRefusal = static_cast<int>(result);
        logger::debug("Dodge failed because of: {}", DodgeResultToString(result));
    }
    // A refusal that waiting out the buffer's 0.4 s will not fix drops the press instead of re-checking - and re-logging
    // - it every frame: sheathed (drawing counts as sheathed until it ends), over carry weight, not enough stamina, no
    // perk, no dodge behaviour. The 1.2.0 test logged 483 lines for about 20 presses while overencumbered.
    switch (result)
    {
        case DodgeResult::kWeaponSheathed:
        case DodgeResult::kOverencumbered:
        case DodgeResult::kStamina:
        case DodgeResult::kHasNoPerk:
        case DodgeResult::kNoDodgeBehavior:
            buffer.clear();
            break;
        case DodgeResult::kIsDodging:
            // the press is kept only while the dodge in progress will end inside the buffer's window (a press just
            // before the landing still dodges again); a dodge that outlasts the window cannot be waited out, so the
            // press is dropped here instead of being refused on every frame until it expires
            if (g_cur.active)
            {
                const float played = std::chrono::duration<float>(CurrentDodge::Clock::now() - g_cur.start).count();
                if (g_cur.duration - played > buffer.remaining())
                    buffer.clear();
            }
            break;
        default:
            break;
    }

    return false;
}

DodgeResult PerkCheck(const RE::Actor* a_actor)
{
    using namespace Config;
    if (!Settings::use_perk_lock.GetValue())
    {
        return DodgeResult::kSuccess;
    }

    if (IsInGodModeHelper(a_actor))
    {
        return DodgeResult::kSuccess;
    }

    RE::BGSPerk* perk{};
    if (Forms::ActualDodgePerk)
    {
        perk = Forms::ActualDodgePerk;
    }
    if (!perk)
    {
        perk = Forms::DodgePerkDummy;
    }
    if (perk && a_actor->HasPerk(perk))
    {
        return DodgeResult::kSuccess;
    }

    return DodgeResult::kHasNoPerk;
}

DodgeResult IsDodging(const RE::Actor* a_actor)
{
    // bIsDodging exists only in a behaviour graph Nemesis / Pandora generated with
    // the dodge behaviour patch. Without it GetGraphVariableBool returns false, which this used to report as "Already dodging" on
    // every press (the 1.7.104 test instance, 2026-11-07, which has no generated behaviours). Say what is missing instead.
    bool bIsDodging = false;
    if (!a_actor->GetGraphVariableBool("bIsDodging", bIsDodging))
    {
        static bool warned = false;
        if (!warned)
        {
            warned = true;
            logger::warn("Dodge: {}", DodgeResultToString(DodgeResult::kNoDodgeBehavior));
        }
        return DodgeResult::kNoDodgeBehavior;
    }
    return bIsDodging ? DodgeResult::kIsDodging : DodgeResult::kSuccess;
}

bool IsInMCORecovery(const RE::Actor* a_actor)
{
    if (!Config::Settings::use_mco_recover_window.GetValue())
        return true;

    bool enabled               = false;
    const bool isCancelEnabled = a_actor->GetGraphVariableBool("DodgeCancelEnabled", enabled) && enabled;
    return isCancelEnabled;
}

float CalculateDodgeCost(RE::Actor* a_actor)
{
    if (const bool is_player_god_mod = Compat::IsPlayer(a_actor) && RE::PlayerCharacter::IsGodMode(); is_player_god_mod)
    {
        return 0.0;
    }

    float dodgeCostModifier = 1.0;
    float extraDodgeCostMod = 1.0;

    const auto cost_modifierAV  = Compat::LookupActorValueByName(MOD::USED_AV);
    const auto stag_cost_mod_AV = Compat::LookupActorValueByName(MOD::EXTRA_DODGE_AV);

    // These two actor values exist only when another mod's Actor Value Generator toml defines them (TK Dodge RE Addon
    // ships DodgeCostModifier_AVG.toml). A definition whose value reads 0 or less made every dodge free, or negative.
    // Such a value is treated as 1 (no change), and said once per actor value.
    auto guarded = [a_actor](RE::ActorValue a_av, std::string_view a_name, bool& a_warned) {
        const float v = a_actor->AsActorValueOwner()->GetActorValue(a_av);
        if (v > 0.0f)
            return v;
        if (!a_warned)
        {
            a_warned = true;
            logger::warn("Dodge cost: actor value {} reads {} - another mod's Actor Value Generator toml defines it "
                         "(e.g. TK Dodge RE Addon's DodgeCostModifier_AVG.toml). Using 1 instead.", a_name, v);
        }
        return 1.0f;
    };
    static bool warnedCost = false, warnedExtra = false;
    if (cost_modifierAV != RE::ActorValue::kNone)
    {
        dodgeCostModifier = guarded(cost_modifierAV, MOD::USED_AV, warnedCost);
    }
    if (stag_cost_mod_AV != RE::ActorValue::kNone)
    {
        extraDodgeCostMod = guarded(stag_cost_mod_AV, MOD::EXTRA_DODGE_AV, warnedExtra);
    }
    float dodge_cost = Config::Settings::dodge_cost.GetValue();
    float cost       = dodge_cost;
    if (Config::Settings::use_percentage_cost.GetValue())
    {
        const auto max_stam = a_actor->AsActorValueOwner()->GetBaseActorValue(RE::ActorValue::kStamina);
        cost                = ((max_stam / 100) * dodge_cost) * dodgeCostModifier * extraDodgeCostMod;
    }
    else
    {
        cost = dodge_cost * dodgeCostModifier * extraDodgeCostMod;
    }
    RE::TESForm* armo = a_actor->GetWornArmor(RE::BGSBipedObjectForm::BipedObjectSlot::kBody, true);

    if (PerkEntryPointsAvailable())
        RE::HandleEntryPoint(RE::PerkEntryPoint::kModPowerAttackStamina, a_actor, cost, MOD::DODGE_COST_PERK, armo);
    logger::debug("Dodge Cost after is {}", cost);

    return cost;
}

void ApplyDodgeCostActor(RE::Actor* a_actor)
{
    if (Compat::IsPlayer(a_actor) && RE::PlayerCharacter::IsGodMode())
        return;

    float dodgeCost = CalculateDodgeCost(a_actor);
    logger::debug("Dodge Cost first is {}", dodgeCost);

#if RUNTIME_LINE == 17
    a_actor->AsActorValueOwner()->DamageActorValue(RE::ActorValue::kStamina, dodgeCost);  // 7.2: a positive amount
#else
    a_actor->AsActorValueOwner()->RestoreActorValue(RE::ACTOR_VALUE_MODIFIER::kDamage, RE::ActorValue::kStamina, -dodgeCost);
#endif
    logger::debug("Dodge cost {} applied to {}", dodgeCost, a_actor->GetName());
}

DodgeEventResult GetDodgeEvent(std::string& a_event)
{
    const auto* controls = RE::PlayerControls::GetSingleton();
    if (!controls)
    {
        logger::warn("Dodge: PlayerControls is null; no direction");
        return DodgeEventResult::kNoDirection;
    }
    auto normalizedInputDirection = Utility::Vec2Normalize(controls->data.prevMoveVec);
    // A directional double tap names its own direction; the held movement wins when there is one (so a second key
    // held at the same time gives the diagonal), the tapped direction otherwise.
    if (normalizedInputDirection.x == 0.f && normalizedInputDirection.y == 0.f && g_hasForcedDirection)
    {
        normalizedInputDirection = g_forcedDirection;
    }
    g_hasForcedDirection = false;
    g_hasInput = !(normalizedInputDirection.x == 0.f && normalizedInputDirection.y == 0.f);
    g_input = normalizedInputDirection;
    if (!g_hasInput)
    {
        return DodgeEventResult::kNoDirection;
    }

    if (Config::Forms::TDMGlobal && Config::Forms::TDMGlobal->Is(RE::FormType::Global) &&
        Config::Forms::TDMGlobal->value != 0)
    {
        logger::debug("TDM Free Movement, Force to Forward Dodge!");
        a_event = "TKDodgeForward";
    }
    else
    {
        constexpr RE::NiPoint2 forwardVector(0.f, 1.f);
        const float dodgeAngle = Utility::GetAngle(normalizedInputDirection, forwardVector);
        // 8-way (the owner, 2026-11-11): eight 45-degree sectors centred on the eight directions; negative angles are
        // to the left. Pure forward still honours "Block forward dodge"; the forward diagonals are not blocked.
        if (Config::Settings::eight_way.GetValue())
        {
            if (dodgeAngle >= -PI8 && dodgeAngle < PI8)
            {
                if (Config::Settings::remove_forward.GetValue())
                    return DodgeEventResult::kForwardBlocked;
                a_event = "TKDodgeForward";
            }
            else if (dodgeAngle >= PI8 && dodgeAngle < 3 * PI8)       a_event = "TKDodgeForwardRight";
            else if (dodgeAngle >= 3 * PI8 && dodgeAngle < 5 * PI8)   a_event = "TKDodgeRight";
            else if (dodgeAngle >= 5 * PI8 && dodgeAngle < 7 * PI8)   a_event = "TKDodgeBackRight";
            else if (dodgeAngle >= -3 * PI8 && dodgeAngle < -PI8)     a_event = "TKDodgeForwardLeft";
            else if (dodgeAngle >= -5 * PI8 && dodgeAngle < -3 * PI8) a_event = "TKDodgeLeft";
            else if (dodgeAngle >= -7 * PI8 && dodgeAngle < -5 * PI8) a_event = "TKDodgeBackLeft";
            else                                                      a_event = "TKDodgeBack";
            logger::debug("8-way dodge: angle {:.2f} -> {}", dodgeAngle, a_event);
            return DodgeEventResult::kSuccess;
        }
        if (dodgeAngle >= -2 * PI8 && dodgeAngle < 2 * PI8)
        {
            if (Config::Settings::remove_forward.GetValue())
                return DodgeEventResult::kForwardBlocked;
            a_event = "TKDodgeForward";
        }
        else if (dodgeAngle >= -6 * PI8 && dodgeAngle < -2 * PI8)
        {
            a_event = "TKDodgeLeft";
        }
        else if (dodgeAngle >= 6 * PI8 || dodgeAngle < -6 * PI8)
        {
            a_event = "TKDodgeBack";
        }
        else if (dodgeAngle >= 2 * PI8 && dodgeAngle < 6 * PI8)
        {
            a_event = "TKDodgeRight";
        }
        else
        {
            a_event = Config::Settings::default_dodge_event.GetValue();
        }
    }
    return DodgeEventResult::kSuccess;
}

void CastOnDodgeSpell(RE::Actor* a_actor)
{
    RE::BGSPerk* lockPerk;

    if (!Config::Forms::SpellLockPerk)
    {
        lockPerk = Config::Forms::dummySpellLockPerk;
    }
    else
        lockPerk = Config::Forms::SpellLockPerk;

    RE::SpellItem* dodgeSpell;
    if (!Config::Forms::onDodgeSpell)
    {
        dodgeSpell = Config::Forms::dummyDodgeSpell;
    }
    else
        dodgeSpell = Config::Forms::onDodgeSpell;

    if (a_actor && lockPerk && dodgeSpell && a_actor->HasPerk(lockPerk))
    {
        Compat::ApplySpell(a_actor, a_actor, dodgeSpell);
    }
}

bool CanAttackCancel(const RE::Actor* a_actor)
{
    const bool cancel_enabled    = Config::Settings::enable_dodge_attack_cancel.GetValue();
    const bool only_light_cancel = Config::Settings::only_cancel_light.GetValue();

    if (cancel_enabled)
    {
        if (only_light_cancel)
        {
            return !Compat::IsPowerAttacking(a_actor);
        }
        return IsInMCORecovery(a_actor);
    }
    return false;
}

DodgeResult IsInAttackState(const RE::Actor* a_actor)
{
    if (const auto attackState = a_actor->AsActorState()->GetAttackState();
        attackState == RE::ATTACK_STATE_ENUM::kNone || CanAttackCancel(a_actor))
    {
        return DodgeResult::kSuccess;
    }
    return DodgeResult::kIsAttacking;
}

DodgeResult IsSprinting(const RE::Actor* a_actor)
{
    if (Config::Settings::dodge_while_sprinting.GetValue() || !a_actor->AsActorState()->IsSprinting())
    {
        return DodgeResult::kSuccess;
    }
    return DodgeResult::kIsSprinting;
}

DodgeResult IsSneaking(const RE::Actor* a_actor)
{
    if (!a_actor->IsSneaking() || Config::Settings::enable_sneak_dodge.GetValue())
    {
        return DodgeResult::kSuccess;
    }
    return DodgeResult::kIsSneaking;
}
DodgeResult IsSwimming(const RE::Actor* a_actor)
{
    if (!a_actor->AsActorState()->IsSwimming())
    {
        return DodgeResult::kSuccess;
    }
    return DodgeResult::kIsSwimming;
}

DodgeResult IsInKillMove(const RE::Actor* a_actor)
{
    if (!a_actor->IsInKillMove())
    {
        return DodgeResult::kSuccess;
    }
    return DodgeResult::kIsInKillMove;
}

bool IsInGodModeHelper(const RE::Actor* a_actor)
{
    if (Compat::IsPlayer(a_actor) && RE::PlayerCharacter::IsGodMode())
    {
        return true;
    }
    return false;
}

DodgeResult IsInMenu(const RE::Actor* a_actor)
{
    if (!Compat::IsPlayer(a_actor))
    {
        return DodgeResult::kSuccess;
    }

    if (!Utility::IsInMenu())
    {
        return DodgeResult::kSuccess;
    }
    return DodgeResult::kIsInMenu;
}

DodgeResult IsControlsDisabled(const RE::Actor* a_actor)
{
    if (!Compat::IsPlayer(a_actor))
    {
        return DodgeResult::kSuccess;
    }

    if (const auto playerControls = RE::PlayerControls::GetSingleton();
        playerControls && playerControls->attackBlockHandler &&
        playerControls->attackBlockHandler->inputEventHandlingEnabled && playerControls->movementHandler &&
        playerControls->movementHandler->inputEventHandlingEnabled)
    {
        return DodgeResult::kSuccess;
    }
    return DodgeResult::kIsControlsDisabled;
}

DodgeResult IsInWrongState(const RE::Actor* a_actor)
{
    if (Config::Settings::disable_in_third.GetValue() && Compat::IsPlayer(a_actor) &&
        RE::PlayerCamera::GetSingleton()->IsInThirdPerson())
    {
        return DodgeResult::kIsInWrongState;
    }

    if (a_actor->AsActorState()->GetSitSleepState() == RE::SIT_SLEEP_STATE::kNormal &&
        a_actor->AsActorState()->GetKnockState() == RE::KNOCK_STATE_ENUM::kNormal && a_actor->AsActorState()->GetFlyState() == RE::FLY_STATE::kNone)
    {
        return DodgeResult::kSuccess;
    }
    return DodgeResult::kIsInWrongState;
}

DodgeResult HasStamina(RE::Actor* a_actor)
{
    if (IsInGodModeHelper(a_actor))
    {
        return DodgeResult::kSuccess;
    }
    if (a_actor->AsActorValueOwner()->GetActorValue(RE::ActorValue::kStamina) >= CalculateDodgeCost(a_actor))
    {
        return DodgeResult::kSuccess;
    }
    return DodgeResult::kStamina;
}

DodgeResult IsOverencumbered(const RE::Actor* a_actor)
{
    if (IsInGodModeHelper(a_actor))
    {
        return DodgeResult::kSuccess;
    }
    if (!a_actor->IsOverEncumbered())
    {
        return DodgeResult::kSuccess;
    }
    return DodgeResult::kOverencumbered;
}

DodgeResult IsJumping(const RE::Actor* a_actor)
{
    if (!Utility::isJumping(a_actor))
    {
        return DodgeResult::kSuccess;
    }
    return DodgeResult::kIsJumping;
}

DodgeResult IsWeaponSheathed(const RE::Actor* a_actor)
{
    // Sheathed, the character is in 0_master's MT_Behavior_State (mt_behavior); the dodge is there only since the
    // 1.2.0 behaviour patch. Off (the default) refuses it here, before stamina or the event - in 1.1.0 the event went
    // to a graph state with no dodge, and the input buffer re-sent it every frame for its whole window.
    if (Config::Settings::dodge_when_sheathed.GetValue())
        return DodgeResult::kSuccess;
    const auto state = a_actor->AsActorState();
    if (!state)
        return DodgeResult::kUnknown;
    return state->IsWeaponDrawn() ? DodgeResult::kSuccess : DodgeResult::kWeaponSheathed;
}

DodgeResult GetDodgeResult(RE::Actor* a_actor, bool a_allowWhileDodging)
{
    if (!a_actor)
        return DodgeResult::kUnknown;

    if (const auto res = IsInMenu(a_actor); res != DodgeResult::kSuccess)
        return res;

    if (const auto res = IsControlsDisabled(a_actor); res != DodgeResult::kSuccess)
        return res;

    if (const auto res = IsInKillMove(a_actor); res != DodgeResult::kSuccess)
        return res;

    if (const auto res = IsInWrongState(a_actor); res != DodgeResult::kSuccess)
        return res;

    if (const auto res = IsWeaponSheathed(a_actor); res != DodgeResult::kSuccess)
        return res;

    if (const auto res = IsJumping(a_actor); res != DodgeResult::kSuccess)
        return res;

    if (const auto res = IsSwimming(a_actor); res != DodgeResult::kSuccess)
        return res;

    if (const auto res = IsDodging(a_actor); res != DodgeResult::kSuccess &&
        !(a_allowWhileDodging && res == DodgeResult::kIsDodging))
        return res;

    if (const auto res = IsInAttackState(a_actor); res != DodgeResult::kSuccess)
        return res;

    if (const auto res = IsSprinting(a_actor); res != DodgeResult::kSuccess)
        return res;

    if (const auto res = IsSneaking(a_actor); res != DodgeResult::kSuccess)
        return res;

    if (const auto res = HasStamina(a_actor); res != DodgeResult::kSuccess)
    {
        RE::HUDMenu::FlashMeter(RE::ActorValue::kStamina);
        return res;
    }

    if (const auto res = IsOverencumbered(a_actor); res != DodgeResult::kSuccess)
        return res;

    if (const auto res = PerkCheck(a_actor); res != DodgeResult::kSuccess)
        return res;

    return DodgeResult::kSuccess;
}

bool DoDodge(RE::Actor* a_actor)
{
    if (!CanDodge(a_actor))
    {
        logger::debug("cannot dodge");
        return false;
    }

    std::string dodge_event = Config::Settings::default_dodge_event.GetValue();
    const auto result       = GetDodgeEvent(dodge_event);

    if (result == DodgeEventResult::kForwardBlocked)
        return false;

    if (result == DodgeEventResult::kNoDirection && !Config::Settings::enable_dodge_in_place.GetValue())
        return false;

    // iStep picks the clip through iStepSelector = iStep + iIsPlayer: 0 = roll, 2 = step, 4 = long roll (1.1.0). The
    // long-roll slots exist only in a graph generated from the 1.1.0 patch, which also declares iSDGLongRoll = 1;
    // asking for slot 4 in an older graph would point past its selector's last generator, so it falls back to 0.
    int iStep = 0;
    if (Config::Settings::step_dodge.GetValue())
    {
        iStep = 2;
    }
    if (iStep != 2)
    {
        iStep = RollStep(a_actor);
        // The first-person graphs carry no long roll (1.2.0): there the standard roll plays without a warning. The
        // warning stays for a third-person graph without it, which means the behaviour was not generated again.
        const auto* cam      = RE::PlayerCamera::GetSingleton();
        const bool firstPerson = Compat::IsPlayer(a_actor) && cam && cam->IsInFirstPerson();
        if (iStep == 0 && Config::Settings::long_roll.GetValue() && firstPerson)
        {
            logger::debug("Dodge: first person has no long roll - the standard roll plays");
        }
        else if (iStep == 0 && Config::Settings::long_roll.GetValue())
        {
            static bool warned = false;
            if (!warned)
            {
                warned = true;
                logger::warn("Dodge: Long roll is on but this character's behaviour has no long roll (iSDGLongRoll) - "
                             "run Nemesis or Pandora again with Simple Dodge ticked. Using the standard roll.");
            }
        }
        // item 9: every roll is the forward roll, the body turned to the stick direction first
        TurnForRoll(a_actor);
        dodge_event = "TKDodgeForward";
    }
    a_actor->SetGraphVariableInt("iStep", iStep);
    logger::debug("Dodge: {} (iStep {}) {}", iStep == 2 ? "step" : (iStep == 4 ? "long roll" : "roll"), iStep, dodge_event);

    CastOnDodgeSpell(a_actor);
    float iFrames = Config::Settings::i_frame_duration.GetValue();

    RE::TESForm* armo = a_actor->GetWornArmor(RE::BGSBipedObjectForm::BipedObjectSlot::kBody, true);
    if (PerkEntryPointsAvailable())
        RE::HandleEntryPoint(RE::PerkEntryPoint::kModPowerAttackStamina, a_actor, iFrames, MOD::IFRAME_DURATION_PERK, armo);

    iFrames = std::clamp(iFrames, 0.0f, 3.0f);

    a_actor->SetGraphVariableFloat("TKDR_IframeDuration",
                                   iFrames); // Set invulnerable frame duration
    const bool sprinting = a_actor->AsActorState()->IsSprinting();
    bool sent = a_actor->NotifyAnimationGraph(dodge_event);
    if (sprinting)
    {
        // bDodgeWhileSprinting (1.2.0): if the sprint state takes no dodge event, leave the sprint first and try once more
        const bool retried = !sent;
        if (retried)
        {
            a_actor->NotifyAnimationGraph("SprintStop");
            sent = a_actor->NotifyAnimationGraph(dodge_event);
        }
        logger::debug("Dodge: out of a sprint{} - {}", retried ? " (SprintStop sent first)" : "", sent ? "dodged" : "the graph took no dodge");
    }
    if (sent && Compat::IsPlayer(a_actor))
    {
        g_cur.active   = true;
        g_cur.step     = iStep == 2;
        g_cur.chained  = false;
        g_cur.start    = CurrentDodge::Clock::now();
        g_cur.duration = iStep == 2 ? StepDuration(dodge_event) : 1.0f;
    }
    return sent;
}

void OnDodgeStart(RE::Actor* a_actor)
{
    if (!a_actor)
        return;
    if (Config::Settings::no_stamina_regen_during_dodge.GetValue())
    {
        if (auto* spell = Config::Forms::NoStaminaRegenSpell)
        {
            Compat::ApplySpell(a_actor, a_actor, spell);
            logger::debug("Dodge start: stamina regen blocked (SDG_NoStaminaRegenSpell)");
        }
        else
        {
            static bool warned = false;
            if (!warned)
            {
                warned = true;
                logger::warn("No stamina regen during dodge is on, but Simple Dodge.esp has no SDG_NoStaminaRegenSpell "
                             "(0x804) - install the 1.2.0 plugin.");
            }
        }
    }
    if (Config::Settings::dodge_sound.GetValue())
    {
        auto* sound = Config::Forms::DodgeSound;
        auto* audio = RE::BSAudioManager::GetSingleton();
        if (sound && audio)
        {
            RE::BSSoundHandle handle;
#if RUNTIME_LINE == 17
            const bool built = audio->GetSoundHandle(handle, sound);
#else
            const bool built = audio->BuildSoundDataFromDescriptor(handle, sound);
#endif
            if (built)
            {
                if (auto* node = a_actor->Get3D())
                    handle.SetObjectToFollow(node);
                const bool played = handle.Play();
                logger::debug("Dodge start: sound {:08X} {}", sound->GetFormID(), played ? "played" : "did not play");
            }
            else
            {
                logger::debug("Dodge start: no sound handle for {:08X}", sound->GetFormID());
            }
        }
    }
}

void OnDodgeEnd(RE::Actor* a_actor)
{
    if (!a_actor)
        return;
    g_cur.active = false;
    // Dispelled whatever the setting says now, so a switch turned off mid-dodge leaves nothing behind.
    if (auto* spell = Config::Forms::NoStaminaRegenSpell)
    {
        if (auto* target = a_actor->AsMagicTarget())
        {
            auto handle = a_actor->GetHandle();
            if (target->DispelEffect(spell, handle))
                logger::debug("Dodge end: stamina regen restored");
        }
    }
}

void ClearBuffer()
{
    buffer.clear();
    dodgeDoubleTap.Reset();
    g_hasForcedDirection = false;
}
} // namespace Dodge
