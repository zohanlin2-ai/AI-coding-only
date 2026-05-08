#include "player.h"
#include "logger.h"

int decoder_init(PlayerContext *is, int stream_idx, enum AVMediaType type) {
    AVCodecParameters *codecpar = is->fmt_ctx->streams[stream_idx]->codecpar;
    const AVCodec *codec = avcodec_find_decoder(codecpar->codec_id);
    if (!codec) {
        fprintf(stderr, "Failed to find decoder\n");
        return -1;
    }

    AVCodecContext *codec_ctx = avcodec_alloc_context3(codec);
    if (!codec_ctx) {
        fprintf(stderr, "Failed to allocate codec context\n");
        return -1;
    }

    if (avcodec_parameters_to_context(codec_ctx, codecpar) < 0) {
        fprintf(stderr, "Failed to copy codec parameters\n");
        avcodec_free_context(&codec_ctx);
        return -1;
    }

    if (avcodec_open2(codec_ctx, codec, NULL) < 0) {
        fprintf(stderr, "Failed to open codec\n");
        avcodec_free_context(&codec_ctx);
        return -1;
    }

    if (type == AVMEDIA_TYPE_VIDEO) {
        is->video_codec_ctx = codec_ctx;
        is->video_stream_idx = stream_idx;
    } else if (type == AVMEDIA_TYPE_AUDIO) {
        is->audio_codec_ctx = codec_ctx;
        is->audio_stream_idx = stream_idx;
    }

    return 0;
}

int decoder_decode_frame(AVCodecContext *dec_ctx, PacketQueue *q, AVFrame *frame) {
    int ret;
    AVPacket pkt;

    for (;;) {
        ret = avcodec_receive_frame(dec_ctx, frame);
        if (ret >= 0)
            return 1;
        if (ret == AVERROR_EOF)
            return 0;
        if (ret != AVERROR(EAGAIN)) {
            log_m("Error receiving frame: %d\n", ret);
            return -1;
        }

        // Need more data
        if (packet_queue_get(q, &pkt, 1) < 0)
            return -1;

        ret = avcodec_send_packet(dec_ctx, &pkt);
        av_packet_unref(&pkt);

        if (ret < 0 && ret != AVERROR(EAGAIN) && ret != AVERROR_EOF) {
            log_m("Error sending packet: %d\n", ret);
            return -1;
        }
    }
}
