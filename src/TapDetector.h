#pragma once

// Tap and double-tap detection, kept free of game types so tests\test_tap_detector.cpp can drive it offline.
//
// Why it exists (1.1.0, 2026-11-12): a player with double-tap on and the sprint key dodging reported "it will also
// dodge when holding the sprint button". 1.0.0 counted a double tap as two "button down" events within 0.3 s. A held
// key yields more than one: the sprint hook hands the game a held press with heldDownSecs set to 0 (so the delayed
// sprint starts), the dodge-key sink runs after it on the SAME event and read that as a fresh press - and with the
// dodge key on the sprint key one physical tap also reached both the sink and the sprint hook. A sprint mod that
// re-sends the sprint control does the same. So:
//   * a press counts once from its first down until its release, however many downs arrive while it is held;
//   * a tap is a press RELEASED within the tap window, measured on our own clock from the first down we saw (and,
//     where the game also reports one, on its held time too);
//   * a double tap is two taps, the second pressed within the gap window of the first's release.
// A hold therefore never counts, whatever the input stream repeats while it is held.

#include <chrono>

namespace Tap
{
	using Clock = std::chrono::steady_clock;
	using TimePoint = Clock::time_point;

	inline float SecondsBetween(TimePoint a_from, TimePoint a_to)
	{
		return std::chrono::duration<float>(a_to - a_from).count();
	}

	// Taps shorter than this count (seconds); the double-tap gap is the same length (the original 300 ms window).
	inline constexpr float kTapWindow = 0.30F;
	inline constexpr float kGapWindow = 0.30F;

	// One physical control: a key, a button, a stick pushed one way.
	struct Press
	{
		bool      held = false;
		TimePoint downAt{};

		// True only for a NEW press. A down while already held (a repeat, a re-sent or rewritten event) is not one.
		bool Down(TimePoint a_now)
		{
			if (held) {
				return false;
			}
			held = true;
			downAt = a_now;
			return true;
		}

		// How long the press was held, or a negative number for a release with no press we saw.
		float Up(TimePoint a_now)
		{
			if (!held) {
				return -1.0F;
			}
			held = false;
			return SecondsBetween(downAt, a_now);
		}

		void Reset() { held = false; }
	};

	// A release is a tap only if BOTH our own clock and the game's held time (pass a negative a_reported when there
	// is none) say it was short - a mod that rewrites heldDownSecs cannot turn a hold into a tap.
	inline bool IsTap(float a_ownHeld, float a_reported, float a_window = kTapWindow)
	{
		if (a_ownHeld < 0.0F || a_ownHeld >= a_window) {
			return false;
		}
		return a_reported < 0.0F || a_reported < a_window;
	}

	// Two taps of one control: fires on the release that completes the second tap.
	struct DoubleTap
	{
		bool      armed = false;
		TimePoint firstUp{};

		// A completed tap (pressed at a_down, released at a_up). True when it completes a double tap.
		bool OnTap(TimePoint a_down, TimePoint a_up, float a_gap = kGapWindow)
		{
			if (armed && SecondsBetween(firstUp, a_down) <= a_gap) {
				armed = false;
				return true;
			}
			armed = true;
			firstUp = a_up;
			return false;
		}

		// A press that turned out to be a hold cancels a pending first tap.
		void OnHold() { armed = false; }
		void Reset() { armed = false; }
	};

	// Double tap of a direction (keyboard or stick), firing on the SECOND PRESS: tap once, press again to dodge, so the
	// dodge starts as the key goes down. The first press must be a tap; the second may then be held (to run on).
	struct DirectionalDoubleTap
	{
		bool      armed = false;
		TimePoint firstUp{};
		Press     press;

		// True when this down completes the double tap.
		bool Down(TimePoint a_now, float a_gap = kGapWindow)
		{
			if (!press.Down(a_now)) {
				return false;
			}
			if (armed && SecondsBetween(firstUp, a_now) <= a_gap) {
				armed = false;
				return true;
			}
			armed = false;
			return false;
		}

		void Up(TimePoint a_now, float a_window = kTapWindow)
		{
			const float held = press.Up(a_now);
			if (IsTap(held, -1.0F, a_window)) {
				armed = true;
				firstUp = a_now;
			} else {
				armed = false;
			}
		}

		void Reset()
		{
			armed = false;
			press.Reset();
		}
	};
}
