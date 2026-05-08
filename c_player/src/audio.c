#include "player.h"
#include "logger.h"

// Define a buffer size for decoded audio
#define MAX_AUDIO_FRAME_SIZE 192000

void audio_callback(void *userdata, Uint8 *stream, int len) {
    PlayerContext *is = (PlayerContext *)userdata;
    int len1;
    static uint8_t audio_buf[(MAX_AUDIO_FRAME_SIZE * 3) / 2];
    static unsigned int audio_buf_size = 0;
    static unsigned int audio_buf_index = 0;

    AVFrame *frame = av_frame_alloc();
    
    while (len > 0) {
        if (is->quit) break;
        if (is->paused) {
            memset(stream, 0, len);
            break;
        }

        if (audio_buf_index >= audio_buf_size) {
            int ret = decoder_decode_frame(is->audio_codec_ctx, &is->audio_queue, frame);
            if (ret < 0) {
                audio_buf_size = 1024;
                memset(audio_buf, 0, audio_buf_size);
            } else if (ret == 0) {
                audio_buf_size = 1024;
                memset(audio_buf, 0, audio_buf_size);
            } else {
                if (!is->swr_ctx) {
                    log_m("Audio: Initializing SwrContext\n");
                    AVChannelLayout out_layout = AV_CHANNEL_LAYOUT_STEREO;
                    swr_alloc_set_opts2(&is->swr_ctx,
                                        &out_layout, AV_SAMPLE_FMT_S16, 44100,
                                        &frame->ch_layout, frame->format, frame->sample_rate,
                                        0, NULL);
                    swr_init(is->swr_ctx);
                }

                int out_samples = swr_get_out_samples(is->swr_ctx, frame->nb_samples);
                uint8_t *out[] = { audio_buf };
                int converted = swr_convert(is->swr_ctx, out, out_samples,
                                            (const uint8_t **)frame->data, frame->nb_samples);
                
                if (converted < 0) {
                    log_m("Audio: swr_convert failed, converting to silence\n");
                    audio_buf_size = 1024;
                    memset(audio_buf, 0, audio_buf_size);
                } else {
                    audio_buf_size = converted * 2 * 2; 
                    if (frame->pts != AV_NOPTS_VALUE) {
                        AVRational tb = is->fmt_ctx->streams[is->audio_stream_idx]->time_base;
                        is->audio_clock = av_q2d(tb) * frame->pts;
                    }
                }
            }
            audio_buf_index = 0;
        }

        len1 = audio_buf_size - audio_buf_index;
        if (len1 <= 0) { // Guard against negative or zero size causing infinite loop
            memset(stream, 0, len);
            break;
        }
        if (len1 > len) len1 = len;
        
        memcpy(stream, (uint8_t *)audio_buf + audio_buf_index, len1);
        len -= len1;
        stream += len1;
        audio_buf_index += len1;
    }
    
    av_frame_free(&frame);
}

int audio_init(PlayerContext *is) {
    is->audio_stream_idx = -1;
    for (int i = 0; i < is->fmt_ctx->nb_streams; i++) {
        if (is->fmt_ctx->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_AUDIO && is->audio_stream_idx < 0) {
            is->audio_stream_idx = i;
        }
    }

    if (is->audio_stream_idx < 0) {
        log_m("Audio: No audio stream found\n");
        return -1;
    }

    log_m("Audio: Found stream at index %d\n", is->audio_stream_idx);

    if (decoder_init(is, is->audio_stream_idx, AVMEDIA_TYPE_AUDIO) < 0) {
        log_m("Audio: Failed to initialize decoder\n");
        return -1;
    }

    SDL_AudioSpec wanted_spec;
    wanted_spec.freq = 44100;
    wanted_spec.format = AUDIO_S16SYS;
    wanted_spec.channels = 2;
    wanted_spec.silence = 0;
    wanted_spec.samples = 1024;
    wanted_spec.callback = audio_callback;
    wanted_spec.userdata = is;

    is->audio_dev = SDL_OpenAudioDevice(NULL, 0, &wanted_spec, NULL, 0);
    if (is->audio_dev == 0) {
        log_m("SDL_OpenAudioDevice: %s\n", SDL_GetError());
        return -1;
    }

    log_m("Audio: Device opened successfully\n");
    SDL_PauseAudioDevice(is->audio_dev, 0);
    return 0;
}
