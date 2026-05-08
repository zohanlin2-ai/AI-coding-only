#include "player.h"
#include "logger.h"

int video_thread(void *arg) {
    PlayerContext *is = (PlayerContext *)arg;
    AVFrame *frame = av_frame_alloc();
    int ret;

    for (;;) {
        if (is->quit) break;
        if (is->paused) {
            SDL_Delay(10);
            continue;
        }

        ret = decoder_decode_frame(is->video_codec_ctx, &is->video_queue, frame);
        if (ret < 0) break;
        if (ret == 0) continue; // EOF

        // A/V Sync
        double pts = frame->best_effort_timestamp;
        if (pts == AV_NOPTS_VALUE) pts = 0;
        pts *= av_q2d(is->fmt_ctx->streams[is->video_stream_idx]->time_base);
        is->video_clock = pts;

        double frame_delay = 1000.0 / av_q2d(is->video_codec_ctx->framerate);
        if (frame_delay <= 0 || frame_delay > 100) frame_delay = 40;

        double delay = compute_target_delay(frame_delay, is->video_clock, is->audio_clock);
        
        SDL_Delay((Uint32)delay);

        // Push frame to main thread for rendering
        SDL_LockMutex(is->pictq_mutex);
        while (is->display_frame_ready && !is->quit) {
            SDL_CondWait(is->pictq_cond, is->pictq_mutex);
        }
        
        av_frame_move_ref(is->display_frame, frame);
        is->display_frame_ready = 1;
        SDL_UnlockMutex(is->pictq_mutex);
    }

    av_frame_free(&frame);
    return 0;
}

int demux_thread(void *arg) {
    PlayerContext *is = (PlayerContext *)arg;
    AVPacket pkt;
    for (;;) {
        if (is->quit) break;
        if (is->paused) {
            SDL_Delay(10);
            continue;
        }

        if (is->video_queue.size > MAX_VIDEOQ_SIZE || is->audio_queue.size > MAX_AUDIOQ_SIZE) {
            SDL_Delay(10);
            continue;
        }

        if (av_read_frame(is->fmt_ctx, &pkt) < 0) {
            SDL_Delay(100);
            continue;
        }

        if (pkt.stream_index == is->video_stream_idx) {
            packet_queue_put(&is->video_queue, &pkt);
        } else if (pkt.stream_index == is->audio_stream_idx) {
            packet_queue_put(&is->audio_queue, &pkt);
        } else {
            av_packet_unref(&pkt);
        }
    }
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <filename>\n", argv[0]);
        return -1;
    }

    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_TIMER) != 0) {
        fprintf(stderr, "Could not initialize SDL - %s\n", SDL_GetError());
        return -1;
    }

    PlayerContext *is = av_mallocz(sizeof(PlayerContext));
    packet_queue_init(&is->video_queue);
    packet_queue_init(&is->audio_queue);
    
    if (avformat_open_input(&is->fmt_ctx, argv[1], NULL, NULL) != 0) {
        return -1;
    }

    if (avformat_find_stream_info(is->fmt_ctx, NULL) < 0) {
        return -1;
    }

    is->video_stream_idx = -1;
    for (int i = 0; i < is->fmt_ctx->nb_streams; i++) {
        if (is->fmt_ctx->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO && is->video_stream_idx < 0) {
            is->video_stream_idx = i;
        }
    }

    if (is->video_stream_idx == -1) return -1;

    // Get total duration in seconds
    if (is->fmt_ctx->duration != AV_NOPTS_VALUE) {
        is->duration = (double)is->fmt_ctx->duration / AV_TIME_BASE;
    }

    if (decoder_init(is, is->video_stream_idx, AVMEDIA_TYPE_VIDEO) < 0) return -1;
    if (video_init(is) < 0) return -1;
    audio_init(is); // Failure is non-fatal for video test

    is->pictq_mutex = SDL_CreateMutex();
    is->pictq_cond = SDL_CreateCond();
    is->display_frame = av_frame_alloc();

    SDL_Thread *v_tid = SDL_CreateThread(video_thread, "video_thread", is);
    SDL_Thread *d_tid = SDL_CreateThread(demux_thread, "demux_thread", is);

    SDL_Event event;

    while (!is->quit) {
        // Render pending frame
        SDL_LockMutex(is->pictq_mutex);
        if (is->display_frame_ready) {
            video_display(is, is->display_frame);
            
            // Update Timeline
            char title[128];
            int cur_sec = (int)is->video_clock;
            int tot_sec = (int)is->duration;
            sprintf(title, "C Player [%02d:%02d / %02d:%02d] %s", 
                    cur_sec / 60, cur_sec % 60, 
                    tot_sec / 60, tot_sec % 60,
                    is->paused ? "(PAUSED)" : "");
            SDL_SetWindowTitle(is->window, title);

            av_frame_unref(is->display_frame);
            is->display_frame_ready = 0;
            SDL_CondSignal(is->pictq_cond);
        }
        SDL_UnlockMutex(is->pictq_mutex);

        // Poll events, but don't block fully so we can render
        if (SDL_PollEvent(&event)) {
            switch (event.type) {
                case SDL_QUIT:
                    is->quit = 1;
                    break;
                case SDL_KEYDOWN:
                    if (event.key.keysym.sym == SDLK_ESCAPE) {
                        is->quit = 1;
                    } else if (event.key.keysym.sym == SDLK_p) {
                        is->paused = !is->paused;
                        SDL_PauseAudioDevice(is->audio_dev, is->paused);
                    }
                    break;
            }
        } else {
            SDL_Delay(5);
        }
    }

    log_m("Debug: Quitting! Setting flag.\n");
    is->quit = 1;
    log_m("Debug: Aborting queues.\n");
    packet_queue_abort(&is->video_queue);
    packet_queue_abort(&is->audio_queue);
    
    // Unlock display loop
    SDL_LockMutex(is->pictq_mutex);
    SDL_CondSignal(is->pictq_cond);
    SDL_UnlockMutex(is->pictq_mutex);

    log_m("Debug: Waiting for threads...\n");
    SDL_WaitThread(v_tid, NULL);
    SDL_WaitThread(d_tid, NULL);
    log_m("Debug: threads finished.\n");
    
    // Cleanup
    log_m("Debug: Closing avformat input.\n");
    avformat_close_input(&is->fmt_ctx);
    
    log_m("Debug: SDL_Quit().\n");
    SDL_Quit();
    
    log_m("Debug: End of main.\n");
    return 0;
}
