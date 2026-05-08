#include "player.h"

// compute_target_delay receives the base frame delay, the current video clock, and audio clock,
// and returns the target delay in milliseconds for the current video frame to catch up or stall.
double compute_target_delay(double frame_delay, double video_clock, double audio_clock) {
    double diff = video_clock - audio_clock;
    double delay = frame_delay;

    if (diff > 0.01) {
        // Video is ahead of audio, stall the video
        delay = frame_delay + diff * 1000;
    } else if (diff < -0.01) {
        // Video is behind audio, catch up
        delay = frame_delay + diff * 1000;
        if (delay < 0) {
            delay = 0;
        }
    }
    
    // Prevent the delay from causing a freezing UI (max 100ms)
    if (delay > 100) {
        delay = 100;
    }

    return delay;
}
