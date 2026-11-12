#include "dodging.h"
#include "Compat.h"
#include "utils/Logger.h"

#include "API/PerkEntryPointExtenderAPI.h"
#include "Settings.h"
#include "Utility.h"
#include "mod-data.h"

namespace Dodge
{
static DodgeInputBuffer buffer;
static DoublePress dodgeDoublePress;

void OnInput()
{
    if (Utility::IsInMenu())
        return;
    if (g_menuBlocker.active())
        return;

    if (Config::Settings::use_double_tap.GetValue())
    {
        if (dodgeDoublePress.on_key_pressed())
        {
            dodgeDoublePress.last_press = {};
            buffer.push();
        }
    }
    else
    {
        dodgeDoublePress.last_press = {};
        buffer.push();
    }
};

void Update(RE::Actor* a_actor)
{
    if (!buffer.can_fire())
        return;

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
    logger::debug("Dodge failed because of: {}", DodgeResultToString(result));

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

    if (cost_modifierAV != RE::ActorValue::kNone)
    {
        dodgeCostModifier = a_actor->AsActorValueOwner()->GetActorValue(cost_modifierAV);
    }
    if (stag_cost_mod_AV != RE::ActorValue::kNone)
    {
        extraDodgeCostMod = a_actor->AsActorValueOwner()->GetActorValue(stag_cost_mod_AV);
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
    const auto normalizedInputDirection = Utility::Vec2Normalize(RE::PlayerControls::GetSingleton()->data.prevMoveVec);
    if (normalizedInputDirection.x == 0.f && normalizedInputDirection.y == 0.f)
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
    if (!a_actor->AsActorState()->IsSprinting())
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

DodgeResult GetDodgeResult(RE::Actor* a_actor)
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

    if (const auto res = IsJumping(a_actor); res != DodgeResult::kSuccess)
        return res;

    if (const auto res = IsSwimming(a_actor); res != DodgeResult::kSuccess)
        return res;

    if (const auto res = IsDodging(a_actor); res != DodgeResult::kSuccess)
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

    if (Config::Settings::step_dodge.GetValue())
    {
        logger::debug("step dodge bool is {}", Config::Settings::step_dodge.GetValue());
        logger::debug("step dodge active");
        a_actor->SetGraphVariableInt("iStep", 2);
    }
    else
        a_actor->SetGraphVariableInt("iStep", 0);
    logger::debug("step dodge bool is {}", Config::Settings::step_dodge.GetValue());

    CastOnDodgeSpell(a_actor);
    float iFrames = Config::Settings::i_frame_duration.GetValue();

    RE::TESForm* armo = a_actor->GetWornArmor(RE::BGSBipedObjectForm::BipedObjectSlot::kBody, true);
    RE::HandleEntryPoint(RE::PerkEntryPoint::kModPowerAttackStamina, a_actor, iFrames, MOD::IFRAME_DURATION_PERK, armo);

    iFrames = std::clamp(iFrames, 0.0f, 3.0f);

    a_actor->SetGraphVariableFloat("TKDR_IframeDuration",
                                   iFrames); // Set invulnerable frame duration
    return a_actor->NotifyAnimationGraph(dodge_event);
}

void ClearBuffer()
{
    buffer.clear();
    dodgeDoublePress.reset_last_press();
}
} // namespace Dodge
