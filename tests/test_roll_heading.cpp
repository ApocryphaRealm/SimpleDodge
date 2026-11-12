// Offline test of src/RollHeading.h - every roll is the forward roll, the body first turned to the stick direction
// relative to the camera (1.2.0). Eight input directions at four camera yaws: the body must face where the stick points.
//
// Build and run (any C++17 compiler): clang++ -std=c++17 -I ../src test_roll_heading.cpp -o t.exe && t.exe
// tests\run-tests.ps1 does that. Exit code 0 = every case passed.

#include "RollHeading.h"

#include <cmath>
#include <cstdio>

static int g_fail = 0, g_n = 0;
static void Check(bool a_ok, const char* a_what, float a_got, float a_want)
{
	++g_n;
	std::printf("%s %d %s (got %.4f want %.4f)\n", a_ok ? "PASS" : "FAIL", g_n, a_what, a_got, a_want);
	if (!a_ok) { ++g_fail; }
}

static bool Near(float a, float b) { return std::fabs(RollHeading::Wrap(a - b)) < 1e-4f; }

int main()
{
	using namespace RollHeading;
	const float d = kPi / 4.0f;
	const float s = 0.70710678f;
	struct In { const char* name; float x, y, angle; } dirs[] = {
		{ "forward", 0, 1, 0 },         { "forward-right", s, s, d },   { "right", 1, 0, 2 * d },
		{ "back-right", s, -s, 3 * d }, { "back", 0, -1, kPi },          { "back-left", -s, -s, -3 * d },
		{ "left", -1, 0, -2 * d },      { "forward-left", -s, s, -d },
	};
	const float cams[] = { 0.0f, kPi / 2.0f, -2.5f, 3.0f };
	for (float cam : cams) {
		for (const auto& in : dirs) {
			char what[96];
			std::snprintf(what, sizeof(what), "camera %.2f, stick %s", cam, in.name);
			const float got = Target(cam, in.x, in.y);
			Check(Near(got, cam + in.angle) && got > -kPi - 1e-5f && got <= kPi + 1e-5f, what, got, Wrap(cam + in.angle));
		}
	}
	// the facing direction from the heading (sin, cos) points where the stick points in world space
	{
		const float cam = 0.6f;
		const float h = Target(cam, 1.0f, 0.0f);   // stick right
		// world right of the camera: the camera forward (sin cam, cos cam) turned 90 degrees clockwise
		const float wx = std::sin(cam + kPi / 2), wy = std::cos(cam + kPi / 2);
		Check(std::fabs(std::sin(h) - wx) < 1e-4f && std::fabs(std::cos(h) - wy) < 1e-4f, "stick right faces the camera's right", h, cam + kPi / 2);
	}
	Check(Near(Wrap(3.5f * kPi), -0.5f * kPi), "wrap 3.5 pi", Wrap(3.5f * kPi), -0.5f * kPi);
	std::printf(g_fail ? "%d of %d FAILED\n" : "all %d passed\n", g_fail ? g_fail : g_n, g_n);
	return g_fail ? 1 : 0;
}
