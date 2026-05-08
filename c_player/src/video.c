#include "player.h"

int video_init(PlayerContext *is) {
    int width = is->video_codec_ctx->width;
    int height = is->video_codec_ctx->height;

    is->window = SDL_CreateWindow("C FFmpeg Player",
                                SDL_WINDOWPOS_UNDEFINED,
                                SDL_WINDOWPOS_UNDEFINED,
                                width, height,
                                SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE);
    if (!is->window) {
        fprintf(stderr, "SDL: could not create window - exiting\n");
        return -1;
    }

    is->renderer = SDL_CreateRenderer(is->window, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
    if (!is->renderer) {
        fprintf(stderr, "SDL: could not create renderer - exiting\n");
        return -1;
    }

    is->texture = SDL_CreateTexture(is->renderer,
                                    SDL_PIXELFORMAT_YV12,
                                    SDL_TEXTUREACCESS_STREAMING,
                                    width, height);
    if (!is->texture) {
        fprintf(stderr, "SDL: could not create texture - exiting\n");
        return -1;
    }

    return 0;
}

void video_display(PlayerContext *is, AVFrame *frame) {
    // Basic YUV420P update
    // Note: If frame format is not YUV420P, we would need SwsContext here.
    // For Phase 1, we assume common formats or add SwsContext in a later iteration.
    
    SDL_UpdateYUVTexture(is->texture, NULL,
                         frame->data[0], frame->linesize[0],
                         frame->data[1], frame->linesize[1],
                         frame->data[2], frame->linesize[2]);

    SDL_RenderClear(is->renderer);
    SDL_RenderCopy(is->renderer, is->texture, NULL, NULL);
    SDL_RenderPresent(is->renderer);
}
