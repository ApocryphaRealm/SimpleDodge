// Offline test of src/TapDetector.h - the tap / double-tap rules behind the 1.1.0 fix for "double tap and the sprint
// button to dodge ... it will also dodge when holding the sprint button" (Nexus posts, 2026-11-12).
//
// Build and run (any C++17 compiler):  clang++ -std=c++17 -I ../src test_tap_detector.cpp -o t.exe && t.exe
// tests\run-tests.ps1 does that. Exit code 0 = every case passed.
//
// The event streams are what the dodge-key sink sees for the sprint key in game: the first down, then - while the
// key is held and the player is not yet sprinting - the sprint hook hands the game the same held press with
// heldDownSecs rewritten to 0 on every frame, which the sink (it runs after the player controls) reads as another
// down. Classic Sprinting Redone and similar mods that re-send the sprint control produce the same shape.

#include "TapDetector.h"

#include <cstdio>
#include <vector>

using namespace Tap;

static int g_fail = 0;
static int g_n = 0;
static void Check(bool a_ok, const char* a_what)
{
	++g_n;
	std::printf("%s %d %s\n", a_ok ? "PASS" : "FAIL", g_n, a_what);
	if (!a_ok) { ++g_fail; }
}

static TimePoint At(double a_s)
{
	return TimePoint{} + std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(1000.0 + a_s));
}

struct Ev { double t; bool down; float reportedHeld; };

// 1.0.0's rule: every down event is a press; two presses within 0.3 s are a double tap.
static int OldDodges(const std::vector<Ev>& a_evs)
{
	int dodges = 0;
	bool have = false;
	double last = 0.0;
	for (const auto& e : a_evs) {
		if (!e.down) { continue; }
		if (have && e.t - last <= 0.3) { ++dodges; have = false; continue; }
		have = true;
		last = e.t;
	}
	return dodges;
}

// 1.1.0's rule, as the sink and the hooks apply it.
static int NewDodges(const std::vector<Ev>& a_evs)
{
	int dodges = 0;
	Press press;
	DoubleTap dbl;
	for (const auto& e : a_evs) {
		if (e.down) {
			press.Down(At(e.t));
			continue;
		}
		const TimePoint down = press.downAt;
		const float own = press.Up(At(e.t));
		if (IsTap(own, e.reportedHeld)) {
			if (dbl.OnTap(down, At(e.t))) { ++dodges; }
		} else if (own >= 0.0F) {
			dbl.OnHold();
		}
	}
	return dodges;
}

int main()
{
	// A 1.5 s hold of the sprint key while standing still: real down at 0, rewritten "downs" every frame from 0.30 s.
	std::vector<Ev> hold{ { 0.0, true, 0.0F } };
	for (double t = 0.300; t < 1.5; t += 1.0 / 60.0) { hold.push_back({ t, true, 0.0F }); }
	hold.push_back({ 1.5, false, 1.5F });
	Check(OldDodges(hold) > 0, "the 1.0.0 rule dodges on a sprint hold (reproduces the report)");
	Check(NewDodges(hold) == 0, "a sprint hold never dodges");

	// The same hold where a sprint mod also rewrites the RELEASE's held time to 0.
	auto csr = hold;
	csr.back().reportedHeld = 0.0F;
	Check(NewDodges(csr) == 0, "a hold whose release reports 0 s held is still not a tap (own clock)");

	// Two quick taps.
	std::vector<Ev> two{ { 0.0, true, 0.0F }, { 0.10, false, 0.10F }, { 0.25, true, 0.0F }, { 0.35, false, 0.10F } };
	Check(NewDodges(two) == 1, "two short taps 0.15 s apart dodge once");
	Check(OldDodges(two) == 1, "(control) the old rule also dodges on two taps");

	// Tap then hold: the second press is long, so no dodge.
	std::vector<Ev> tapHold{ { 0.0, true, 0.0F }, { 0.10, false, 0.10F }, { 0.20, true, 0.0F }, { 1.20, false, 1.0F } };
	Check(NewDodges(tapHold) == 0, "a tap followed by a hold does not dodge");

	// Hold then tap: the hold cancels, the tap alone is only a first tap.
	std::vector<Ev> holdTap{ { 0.0, true, 0.0F }, { 1.0, false, 1.0F }, { 1.1, true, 0.0F }, { 1.2, false, 0.1F } };
	Check(NewDodges(holdTap) == 0, "a hold followed by one tap does not dodge");

	// Taps too far apart.
	std::vector<Ev> slow{ { 0.0, true, 0.0F }, { 0.10, false, 0.10F }, { 0.60, true, 0.0F }, { 0.70, false, 0.10F } };
	Check(NewDodges(slow) == 0, "two taps 0.5 s apart do not dodge");

	// Key repeat while tapping (keyboard auto-repeat downs) does not split one tap into two.
	std::vector<Ev> rep{ { 0.0, true, 0.0F }, { 0.05, true, 0.0F }, { 0.10, true, 0.0F }, { 0.15, false, 0.15F } };
	Check(NewDodges(rep) == 0, "one tap with repeated downs is one tap, not a double");

	// A release with no press we saw (the press went to a menu) is not a tap.
	{
		Press p;
		Check(p.Up(At(0.1)) < 0.0F && !IsTap(p.Up(At(0.1)), 0.05F), "a release with no matching press is not a tap");
	}

	// Directional double tap: fires on the second press.
	{
		DirectionalDoubleTap d;
		bool f1 = d.Down(At(0.0));
		d.Up(At(0.1));
		bool f2 = d.Down(At(0.25));
		Check(!f1 && f2, "direction tapped then pressed again within 0.3 s dodges on the second press");
		d.Up(At(2.0));  // held on to run: a long second press re-arms nothing
		Check(!d.Down(At(2.1)), "after a held second press, the next press alone does not dodge");
	}
	{
		DirectionalDoubleTap d;
		d.Down(At(0.0));
		d.Up(At(0.8));  // a hold (walking)
		Check(!d.Down(At(0.9)), "walking (a held direction) then pressing again does not dodge");
	}
	{
		DirectionalDoubleTap d;
		d.Down(At(0.0));
		d.Up(At(0.1));
		Check(!d.Down(At(0.6)), "direction taps 0.5 s apart do not dodge");
	}
	{
		DirectionalDoubleTap d;
		d.Down(At(0.0));
		d.Down(At(0.05));  // a repeat while held
		d.Up(At(0.1));
		Check(d.Down(At(0.2)), "a repeat down during the first tap does not break the double tap");
	}

	// ---- the sprint hook's per-press decision (TapKeyState), the Sprint or Sneak helper's review, 2026-11-12 ----
	// Frames of a 1.5 s sprint hold at 60 fps; a_active = the live sprint flag the hook reads each frame.
	auto runSprint = [](TapKeyState& k, bool activeAtDown, bool flipActiveMidPress, int* zeroed, int* dodges, int* swallowed) {
		*zeroed = *dodges = *swallowed = 0;
		auto count = [&](const TapKeyDecision& d) {
			*zeroed += d.zeroHeld; *swallowed += d.swallow;
			*dodges += (d.action == Action::kDodge || d.action == Action::kTap);
		};
		count(k.OnEvent(At(0.0), true, false, 0.0F, activeAtDown, false, false, 0.3F, false));
		for (double t = 1.0 / 60.0; t < 1.5; t += 1.0 / 60.0) {
			const bool active = flipActiveMidPress ? (t > 0.2) : activeAtDown;  // an outer mod writes the flag
			count(k.OnEvent(At(t), false, false, static_cast<float>(t), active, false, false, 0.3F, false));
		}
		count(k.OnEvent(At(1.5), false, true, 1.5F, false, false, false, 0.3F, false));
	};
	{
		TapKeyState k; int z, d, s;
		runSprint(k, false, false, &z, &d, &s);
		Check(z == 1 && d == 0, "sprint hold: the game gets the delayed fresh press exactly once, no dodge");
	}
	{
		TapKeyState k; int z, d, s;
		runSprint(k, false, true, &z, &d, &s);
		Check(z == 1 && d == 0, "sprint hold while another mod sets the sprint flag mid-press: fresh press still handed over once");
	}
	{
		TapKeyState k; int z, d, s;
		runSprint(k, true, false, &z, &d, &s);
		Check(z == 0 && d == 0, "a press that ends a sprint is the game's: never rewritten, a hold is no dodge");
	}
	{
		TapKeyState k;
		auto a = k.OnEvent(At(0.0), true, false, 0.0F, false, false, false, 0.3F, false);
		auto b = k.OnEvent(At(0.05), false, false, 0.05F, false, false, false, 0.3F, false);
		auto c = k.OnEvent(At(0.12), false, true, 0.12F, false, false, false, 0.3F, false);
		Check(a.swallow && b.swallow && c.swallow && c.action == Action::kDodge && !a.zeroHeld && !b.zeroHeld,
			"a quick sprint tap is held back from the game and dodges on release");
	}
	{
		TapKeyState k;
		k.OnEvent(At(0.0), true, false, 0.0F, false, false, false, 0.3F, false);
		auto c = k.OnEvent(At(0.12), false, true, 0.12F, false, false, true, 0.3F, false);
		Check(c.swallow && c.action == Action::kNone, "a sprint tap just after a menu closed is swallowed, no dodge");
	}

	// ---- the dodge-key sink (DodgeKeyState): uDodgeKey = 42 (Left Shift), NOT the sprint key ----
	{
		DodgeKeyState k; int dodges = 0;
		auto c = [&](Action a) { dodges += (a == Action::kDodge); };
		c(k.OnEvent(At(0.0), true, true, false, 0.0F, false, false));          // press
		for (double t = 0.05; t < 0.9; t += 0.05) c(k.OnEvent(At(t), true, true, false, 0.0F, false, false));  // repeats
		c(k.OnEvent(At(0.9), false, false, true, 0.9F, false, false));
		Check(dodges == 1, "double tap off: one Left Shift press (with key repeats) dodges exactly once - it is the dodge key");
	}
	{
		DodgeKeyState k; int dodges = 0;
		auto c = [&](Action a) { dodges += (a == Action::kDodge || a == Action::kTap); };
		c(k.OnEvent(At(0.0), true, true, false, 0.0F, false, true));
		c(k.OnEvent(At(0.5), true, false, false, 0.5F, false, true));
		const Action up = k.OnEvent(At(1.0), false, false, true, 1.0F, false, true);
		c(up);
		Check(dodges == 0 && up == Action::kHold, "double tap on: holding Left Shift never dodges and reports a hold");
	}
	{
		DodgeKeyState k;
		const Action a = k.OnEvent(At(0.0), true, false, false, 0.4F, false, false);  // first seen already held
		Check(a == Action::kNone, "a dodge-key press first seen already held (made in a menu) does not dodge");
	}

	std::printf(g_fail ? "%d of %d FAILED\n" : "all %d passed\n", g_fail ? g_fail : g_n, g_n);
	return g_fail ? 1 : 0;
}
