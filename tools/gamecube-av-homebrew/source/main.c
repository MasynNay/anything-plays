/* Anything Plays — original continuous GameCube video and PCM test.
 * This homebrew is only a CI test and is never included in the app installer.
 * No Nintendo files, BIOS, game assets or commercial audio are used.
 */
#include <gccore.h>
#include <asndlib.h>
#include <stdio.h>
#include <string.h>

#define BUFFER_FRAMES 4800
static s16 tone[BUFFER_FRAMES * 2] __attribute__((aligned(32)));

static void prepare_tone(void) {
    /* Original 440-ish Hz square wave at 48kHz, big-endian stereo PCM.
       Period approximated to 109 samples (440.37Hz), 0.1-second loop. */
    for (int i = 0; i < BUFFER_FRAMES; i++) {
        s16 sample = (i % 109 < 54) ? 6200 : -6200;
        tone[i * 2] = sample;
        tone[i * 2 + 1] = sample;
    }
    DCFlushRange(tone, sizeof(tone));
}

int main(void) {
    VIDEO_Init();
    PAD_Init();
    GXRModeObj *mode = VIDEO_GetPreferredMode(NULL);
    void *framebuffer = MEM_K0_TO_K1(SYS_AllocateFramebuffer(mode));
    console_init(framebuffer, 22, 24, mode->fbWidth, mode->xfbHeight,
                 mode->fbWidth * VI_DISPLAY_PIX_SZ);
    VIDEO_Configure(mode);
    VIDEO_SetNextFramebuffer(framebuffer);
    VIDEO_SetBlack(FALSE);
    VIDEO_Flush();
    VIDEO_WaitVSync();
    if (mode->viTVMode & VI_NON_INTERLACE)
        VIDEO_WaitVSync();

    prepare_tone();
    ASND_Init();
    ASND_SetInfiniteVoice(0, VOICE_STEREO_16BIT_BE, 48000, 0,
                          tone, sizeof(tone), 180, 180);
    ASND_Pause(0);

    unsigned int frames = 0;
    while (1) {
        PAD_ScanPads();
        unsigned int pressed = PAD_ButtonsHeld(0);
        /* Change the actual GameCube VI framebuffer every emulated frame.
           A real moving counter, rather than a static homebrew menu. */
        printf("\x1b[2J\x1b[H");
        printf(" Anything Plays - ORIGINAL GameCube AV test\n\n");
        printf(" Frame: %08u   Tick: %08u\n\n", frames, frames * 3);
        printf(" Generated stereo tone ~440Hz @ 48kHz\n");
        printf(" A: %s   B: %s\n", pressed & PAD_BUTTON_A ? "DOWN" : "UP",
               pressed & PAD_BUTTON_B ? "DOWN" : "UP");
        printf("\n\n\n");
        for (int i = 0; i < 12; i++)
            printf("%s\n", (frames + i) % 24 < 12
                          ? " [####>                          ]"
                          : " [                          <####]");
        printf("\n Framebuffer, video, controller and DSP audio are all\n");
        printf(" generated entirely inside this original homebrew.\n");
        VIDEO_SetNextFramebuffer(framebuffer);
        VIDEO_Flush();
        VIDEO_WaitVSync();
        frames++;
    }
    ASND_End();
    return 0;
}
