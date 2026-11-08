/* Anything Plays 3.0: test-only MinGW C portability helper for pinned bsnes.
 * Original upstream Git source stays bit-for-bit unchanged. This header is
 * supplied only as a compiler -include in MSYS2 Windows source-build tests.
 * It does NOT certify GPL redistribution, replace shipped cores, or patch ROMs.
 */
#ifndef AP_V30_BSNES_MINGW_VASPRINTF_COMPAT_H
#define AP_V30_BSNES_MINGW_VASPRINTF_COMPAT_H
#if defined(_WIN32) && !defined(__cplusplus)
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <errno.h>
static inline int ap_v30_bsnes_mingw_vasprintf(char **result,
                                                const char *fmt,
                                                va_list original) {
    if (!result || !fmt) { errno = EINVAL; return -1; }
    *result = NULL;
    va_list measure;
    va_copy(measure, original);
    int required = vsnprintf(NULL, 0, fmt, measure);
    va_end(measure);
    if (required < 0) { return -1; }
    if ((unsigned long long)required + 1ULL > (unsigned long long)SIZE_MAX) {
        errno = ENOMEM;
        return -1;
    }
    char *buffer = (char *)malloc((size_t)required + 1U);
    if (!buffer) { errno = ENOMEM; return -1; }
    va_list render;
    va_copy(render, original);
    int written = vsnprintf(buffer, (size_t)required + 1U, fmt, render);
    va_end(render);
    if (written < 0 || written > required) { free(buffer); return -1; }
    *result = buffer;
    return written;
}
#define vasprintf ap_v30_bsnes_mingw_vasprintf
#endif
#endif
