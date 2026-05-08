#include <stdio.h>
#include <assert.h>
#include <math.h>

// We declare the compute_target_delay prototype manually here 
// to avoid including the massive player.h which requires ffmpeg headers.
// We will compile this alongside src/sync.o.
double compute_target_delay(double frame_delay, double video_clock, double audio_clock);

void test_video_ahead() {
    // Video is at 10.0s, Audio is at 9.8s
    // Diff = 0.2s = 200ms
    // Video is too fast, so delay should increase to slow it down.
    double delay = compute_target_delay(40.0, 10.0, 9.8);
    // target = 40.0 + 0.2 * 1000 = 240, but capped at 100.
    assert(fabs(delay - 100.0) < 0.001);
    printf("test_video_ahead PASSED\n");
}

void test_video_behind() {
    // Video is at 9.8s, Audio is at 10.0s
    // Diff = -0.2s = -200ms
    // Video is too slow, needs to catch up (delay should be 0).
    double delay = compute_target_delay(40.0, 9.8, 10.0);
    // target = 40.0 - 200 = -160, capped to 0.
    assert(fabs(delay - 0.0) < 0.001);
    printf("test_video_behind PASSED\n");
}

void test_video_in_sync() {
    // Diff is 0.005, which is within the 0.01 threshold.
    // Should return base frame_delay.
    double delay = compute_target_delay(40.0, 10.005, 10.0);
    assert(fabs(delay - 40.0) < 0.001);
    printf("test_video_in_sync PASSED\n");
}

int main() {
    printf("Running Sync Logic Tests...\n");
    test_video_ahead();
    test_video_behind();
    test_video_in_sync();
    printf("All sync tests passed!\n\n");
    return 0;
}
