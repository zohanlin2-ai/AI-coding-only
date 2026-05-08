#include <stdio.h>
#include <assert.h>
#include <SDL2/SDL.h>
#include <libavcodec/avcodec.h>

#include "../src/player.h"

PacketQueue q;

int writer_thread(void *arg) {
    for (int i = 0; i < 100; i++) {
        AVPacket *pkt = av_packet_alloc();
        // We use a dummy payload size of 10
        av_new_packet(pkt, 10); 
        int ret = packet_queue_put(&q, pkt);
        av_packet_free(&pkt);
        assert(ret == 0);
    }
    return 0;
}

int reader_thread(void *arg) {
    for (int i = 0; i < 100; i++) {
        AVPacket pkt;
        int ret = packet_queue_get(&q, &pkt, 1);
        if (ret >= 0) {
            av_packet_unref(&pkt);
        } else {
            // Aborted
        }
    }
    return 0;
}

int blocked_reader_thread(void *arg) {
    AVPacket pkt;
    // Should block because queue is empty
    int ret = packet_queue_get(&q, &pkt, 1);
    // When packet_queue_abort is called, it should wake up and return -1
    assert(ret == -1);
    return 0;
}

void test_queue_concurrency() {
    packet_queue_init(&q);
    q.abort_request = 0;

    SDL_Thread *writers[4];
    SDL_Thread *readers[4];

    for (int i = 0; i < 4; i++) {
        writers[i] = SDL_CreateThread(writer_thread, "writer", NULL);
        readers[i] = SDL_CreateThread(reader_thread, "reader", NULL);
    }

    for (int i = 0; i < 4; i++) {
        SDL_WaitThread(writers[i], NULL);
        SDL_WaitThread(readers[i], NULL);
    }

    // After 400 writes and 400 reads, the queue should be exactly empty.
    assert(q.nb_packets == 0);
    assert(q.size == 0);
    printf("test_queue_concurrency PASSED\n");
}

void test_queue_abort() {
    packet_queue_init(&q);
    q.abort_request = 0;

    SDL_Thread *reader = SDL_CreateThread(blocked_reader_thread, "blocked_reader", NULL);

    // Sleep to allow the reader to enter the blocked SDL_CondWait state
    SDL_Delay(50);
    
    // Fire the abort
    packet_queue_abort(&q);

    // Wait for the blocked thread to gracefully exit
    SDL_WaitThread(reader, NULL);
    
    printf("test_queue_abort PASSED\n");
}

int main(int argc, char *argv[]) {
    // SDL initialization is required for SDL_CreateMutex etc.
    if (SDL_Init(SDL_INIT_TIMER | SDL_INIT_VIDEO) < 0) {
        fprintf(stderr, "Failed to initialize SDL: %s\n", SDL_GetError());
        return -1;
    }

    printf("Running PacketQueue Tests...\n");
    test_queue_concurrency();
    test_queue_abort();
    printf("All PacketQueue tests passed!\n\n");

    SDL_Quit();
    return 0;
}
