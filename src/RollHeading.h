#pragma once

// Rolls are always the forward roll, turned to the stick direction (1.2.0, the owner 2026-11-12: "for roll dodges, lets
// use only the front roll dodge and have it play in the direction they point with the stick so the whole body moves to
// that direction and then dodges forward in that direction"). Kept free of game types so tests\test_roll_heading.cpp
// can check the turn math offline.
//
// Skyrim's heading: radians about +Z, 0 = facing +Y, increasing clockwise seen from above (toward +X). The stick /
// WASD input (x right, y forward) is relative to the CAMERA's yaw, so the roll faces cameraYaw + atan2(x, y).

#include <cmath>

namespace RollHeading
{
	constexpr float kPi = 3.14159265358979f;

	// angle in (-pi, pi]
	inline float Wrap(float a_angle)
	{
		while (a_angle > kPi) { a_angle -= 2.0f * kPi; }
		while (a_angle <= -kPi) { a_angle += 2.0f * kPi; }
		return a_angle;
	}

	// The input's angle from straight ahead: + to the right, - to the left, pi straight back.
	inline float InputAngle(float a_x, float a_y) { return std::atan2(a_x, a_y); }

	// Heading the body takes before a roll: the camera's yaw turned by the input's angle.
	inline float Target(float a_cameraYaw, float a_x, float a_y) { return Wrap(a_cameraYaw + InputAngle(a_x, a_y)); }
}
