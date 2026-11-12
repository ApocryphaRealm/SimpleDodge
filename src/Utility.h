#pragma once
#include "Settings.h"
#include "Compat.h"

#define PI 3.14159265f
#define PI8 0.39269908f

namespace Utility
{
    inline RE::NiPoint2 Vec2Rotate(const RE::NiPoint2 &vec, float angle)
    {
        RE::NiPoint2 ret;
        ret.x = vec.x * cos(angle) - vec.y * sin(angle);
        ret.y = vec.x * sin(angle) + vec.y * cos(angle);
        return ret;
    }

    inline float Vec2Length(const RE::NiPoint2 &vec)
    {
        return std::sqrtf(vec.x * vec.x + vec.y * vec.y);
    }

    inline RE::NiPoint2 Vec2Normalize(const RE::NiPoint2 &vec)
    {
        RE::NiPoint2 ret(0.f, 0.f);
        const float vecLength = Vec2Length(vec);
        if (vecLength == 0)
        {
            return ret;
        }
        const float invlen = 1.0f / vecLength;
        ret.x = vec.x * invlen;
        ret.y = vec.y * invlen;
        return ret;
    }

    inline float DotProduct(const RE::NiPoint2 &a, const RE::NiPoint2 &b)
    {
        return a.x * b.x + a.y * b.y;
    }

    inline float CrossProduct(const RE::NiPoint2 &a, const RE::NiPoint2 &b)
    {
        return a.x * b.y - a.y * b.x;
    }

    inline float GetAngle(const RE::NiPoint2 &a, const RE::NiPoint2 &b)
    {
        return atan2(CrossProduct(a, b), DotProduct(a, b));
    }

    inline bool isJumping(const RE::Actor *a_actor)
    {
        bool result = false;
        return a_actor->GetGraphVariableBool("bInJumpState", result) && result;
    }

    inline bool IsInMenu()
    {
        return Compat::IsAnyOfMenuOpen(Config::Forms::MenuNames);
    }

};
