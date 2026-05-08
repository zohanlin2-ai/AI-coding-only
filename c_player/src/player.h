#ifndef PLAYER_H
#define PLAYER_H

#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libswscale/swscale.h>
#include <libswresample/swresample.h>
#include <libavutil/time.h>
#include <libavutil/avutil.h>
#include <libavutil/imgutils.h>

#include <SDL2/SDL.h>
#include <SDL2/SDL_thread.h>

#define MAX_VIDEOQ_SIZE (15 * 1024 * 1024)
#define MAX_AUDIOQ_SIZE (5 * 1024 * 1024)

#define FF_QUIT_EVENT (SDL_USEREVENT + 2)

typedef struct MyPacketList {
    AVPacket pkt;
    struct MyPacketList *next;
} MyPacketList;

typedef struct PacketQueue {
    MyPacketList *first_pkt, *last_pkt;
    int nb_packets;
    int size;
    int abort_request;
    SDL_mutex *mutex;
    SDL_cond *cond;
} PacketQueue;

typedef struct PlayerContext {
    AVFormatContext *fmt_ctx;
    
    int video_stream_idx;
    int audio_stream_idx;

    AVCodecContext *video_codec_ctx;
    AVCodecContext *audio_codec_ctx;

    PacketQueue video_queue;
    PacketQueue audio_queue;

    SDL_Window *window;
    SDL_Renderer *renderer;
    SDL_Texture *texture;

    struct SwrContext *swr_ctx;
    double audio_clock;
    double video_clock;
    double duration;
    SDL_AudioDeviceID audio_dev;
    int paused;
    volatile int quit;
    
    // Decoupled Video Rendering
    AVFrame *display_frame;
    SDL_mutex *pictq_mutex;
    SDL_cond *pictq_cond;
    int display_frame_ready;
} PlayerContext;

// Function prototypes
void packet_queue_init(PacketQueue *q);
int packet_queue_put(PacketQueue *q, AVPacket *pkt);
int packet_queue_get(PacketQueue *q, AVPacket *pkt, int block);
void packet_queue_abort(PacketQueue *q);

int decoder_init(PlayerContext *is, int stream_idx, enum AVMediaType type);
int decoder_decode_frame(AVCodecContext *dec_ctx, PacketQueue *q, AVFrame *frame);

int video_init(PlayerContext *is);
void video_display(PlayerContext *is, AVFrame *frame);

int audio_init(PlayerContext *is);

// Sync Logic
double compute_target_delay(double frame_delay, double video_clock, double audio_clock);

#endif // PLAYER_H
