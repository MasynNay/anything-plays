/* Anything Plays — ORIGINAL GameCube hardware-GX 3D compatibility test.
 *
 * Builds only as a CI homebrew .dol with devkitPPC/libogc. No commercial
 * games, Nintendo firmware, copied meshes, or textures. Renders a rotating
 * six-face cube through the original GameCube graphics pipeline.
 * Video frames must reach the SAME hidden Dolphin GL framebuffer as the app.
 */
#include <gccore.h>
#include <malloc.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#define FIFO_BYTES (256 * 1024)
static void *fifo;
static void *framebuffers[2];
static GXRModeObj *video_mode;

static const f32 faces[6][4][3] = {
    {{-1,-1, 1},{ 1,-1, 1},{ 1, 1, 1},{-1, 1, 1}},
    {{ 1,-1,-1},{-1,-1,-1},{-1, 1,-1},{ 1, 1,-1}},
    {{-1, 1, 1},{ 1, 1, 1},{ 1, 1,-1},{-1, 1,-1}},
    {{-1,-1,-1},{ 1,-1,-1},{ 1,-1, 1},{-1,-1, 1}},
    {{ 1,-1, 1},{ 1,-1,-1},{ 1, 1,-1},{ 1, 1, 1}},
    {{-1,-1,-1},{-1,-1, 1},{-1, 1, 1},{-1, 1,-1}},
};
static const GXColor face_color[6] = {
    {255, 45, 85,255}, { 60,175,250,255}, {240,195, 40,255},
    { 80,230,115,255}, {185, 90,240,255}, {255,125, 45,255},
};

static void init_video_and_gx(void) {
    VIDEO_Init();
    PAD_Init();
    video_mode = VIDEO_GetPreferredMode(NULL);
    framebuffers[0] = MEM_K0_TO_K1(SYS_AllocateFramebuffer(video_mode));
    framebuffers[1] = MEM_K0_TO_K1(SYS_AllocateFramebuffer(video_mode));
    VIDEO_Configure(video_mode);

    fifo = memalign(32, FIFO_BYTES);
    memset(fifo, 0, FIFO_BYTES);
    GX_Init(fifo, FIFO_BYTES);
    GXColor bg = {8, 12, 32, 255};
    GX_SetCopyClear(bg, 0x00ffffff);

    GX_SetViewport(0, 0, video_mode->fbWidth, video_mode->efbHeight, 0, 1);
    f32 y_scale = GX_GetYScaleFactor(video_mode->efbHeight,
                                     video_mode->xfbHeight);
    u16 xfb_height = GX_SetDispCopyYScale(y_scale);
    GX_SetScissor(0, 0, video_mode->fbWidth, video_mode->efbHeight);
    GX_SetDispCopySrc(0, 0, video_mode->fbWidth, video_mode->efbHeight);
    GX_SetDispCopyDst(video_mode->fbWidth, xfb_height);
    GX_SetCopyFilter(video_mode->aa, video_mode->sample_pattern, GX_TRUE,
                     video_mode->vfilter);
    GX_SetFieldMode(video_mode->field_rendering,
                    video_mode->viHeight == 2 * video_mode->xfbHeight
                    ? GX_ENABLE : GX_DISABLE);
    GX_SetPixelFmt(video_mode->aa ? GX_PF_RGB565_Z16 : GX_PF_RGB8_Z24,
                   GX_ZC_LINEAR);
    GX_SetCullMode(GX_CULL_NONE);
    GX_SetDispCopyGamma(GX_GM_1_0);
    GX_SetZMode(GX_TRUE, GX_LEQUAL, GX_TRUE);
    GX_SetColorUpdate(GX_TRUE);
    GX_SetBlendMode(GX_BM_NONE, GX_BL_ONE, GX_BL_ZERO, GX_LO_CLEAR);

    GX_ClearVtxDesc();
    GX_SetVtxDesc(GX_VA_POS, GX_DIRECT);
    GX_SetVtxDesc(GX_VA_CLR0, GX_DIRECT);
    GX_SetVtxAttrFmt(GX_VTXFMT0, GX_VA_POS, GX_POS_XYZ, GX_F32, 0);
    GX_SetVtxAttrFmt(GX_VTXFMT0, GX_VA_CLR0, GX_CLR_RGBA, GX_RGBA8, 0);

    GX_SetNumChans(1);
    GX_SetChanCtrl(GX_COLOR0A0, GX_DISABLE, GX_SRC_REG, GX_SRC_VTX,
                   GX_LIGHTNULL, GX_DF_NONE, GX_AF_NONE);
    GX_SetNumTexGens(0);
    GX_SetTevOrder(GX_TEVSTAGE0, GX_TEXCOORDNULL,
                   GX_TEXMAP_NULL, GX_COLOR0A0);
    GX_SetTevOp(GX_TEVSTAGE0, GX_PASSCLR);

    Mtx44 projection;
    guPerspective(projection, 55.0f,
                  (f32)video_mode->fbWidth / video_mode->efbHeight,
                  0.1f, 100.0f);
    GX_LoadProjectionMtx(projection, GX_PERSPECTIVE);

    VIDEO_SetNextFramebuffer(framebuffers[0]);
    VIDEO_SetBlack(FALSE);
    VIDEO_Flush();
    VIDEO_WaitVSync();
}

int main(void) {
    init_video_and_gx();
    const guVector cam = {0.0f, 0.0f, 5.0f};
    const guVector up = {0.0f, 1.0f, 0.0f};
    const guVector target = {0.0f, 0.0f, 0.0f};
    const guVector axis = {1.0f, 0.8f, 0.6f};
    Mtx view, model, modelview;
    guLookAt(view, (guVector *)&cam, (guVector *)&up, (guVector *)&target);
    unsigned int frame = 0;

    while (1) {
        PAD_ScanPads();
        guMtxRotAxisDeg(model, (guVector *)&axis,
                        (f32)(frame % 360));
        guMtxConcat(view, model, modelview);
        GX_LoadPosMtxImm(modelview, GX_PNMTX0);
        GX_SetCurrentMtx(GX_PNMTX0);
        GX_Begin(GX_QUADS, GX_VTXFMT0, 24);
        for (int face = 0; face < 6; face++) {
            for (int vertex = 0; vertex < 4; vertex++) {
                GX_Position3f32(faces[face][vertex][0],
                                faces[face][vertex][1],
                                faces[face][vertex][2]);
                GX_Color4u8(face_color[face].r, face_color[face].g,
                            face_color[face].b, face_color[face].a);
            }
        }
        GX_End();
        GX_CopyDisp(framebuffers[frame & 1], GX_TRUE);
        GX_DrawDone();
        VIDEO_SetNextFramebuffer(framebuffers[frame & 1]);
        VIDEO_Flush();
        VIDEO_WaitVSync();
        frame++;
    }
    return 0;
}
