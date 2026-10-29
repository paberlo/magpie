/*
 * pngpixcmp: exit 0 if two PNG files decode to identical pixels, 1 if they
 * differ, 2 on error.
 *
 * Each image is decoded (de-interlaced by libpng) and every pixel is then
 * normalised here to 16-bit RGBA, following the PNG specification:
 * grey -> R=G=B, palette -> PLTE entry, samples of depth d scaled exactly to
 * 16 bits (x * 65535 / (2^d - 1)), alpha taken from the alpha channel, from
 * tRNS, or 65535 when the image has neither. Two encodings of the same picture
 * therefore compare equal whatever colour type, bit depth or interlacing each
 * uses, while any change in a pixel value (including the low byte of a 16-bit
 * sample) is detected.
 *
 * Linked against the libpng and zlib bundled with OptiPNG, which genetic
 * improvement never modifies (only optipng.c and optim.c are edited). That
 * build of libpng has neither read transforms nor setjmp, hence the manual
 * normalisation and an error handler that exits with status 2.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "png.h"

typedef struct {
    png_uint_32 width, height;
    uint16_t *rgba;               /* width*height*4 samples */
} image_t;

static const char *current_path = "";

static void on_error(png_structp png, png_const_charp msg)
{
    (void)png;
    fprintf(stderr, "pngpixcmp: cannot decode %s: %s\n", current_path, msg);
    exit(2);
}

static void on_warning(png_structp png, png_const_charp msg)
{
    (void)png;
    (void)msg;
}

/* Sample i of a packed row at bit depth d (1, 2, 4, 8 or 16). */
static unsigned sample(png_const_bytep row, size_t i, int d)
{
    if (d == 16) return (row[2 * i] << 8) | row[2 * i + 1];
    if (d == 8) return row[i];
    size_t bit = i * d;
    return (row[bit / 8] >> (8 - d - bit % 8)) & ((1u << d) - 1);
}

static uint16_t to16(unsigned v, int d)
{
    return (uint16_t)((unsigned long)v * 65535u / ((1u << d) - 1));
}

static void fail(const char *msg)
{
    fprintf(stderr, "pngpixcmp: %s: %s\n", current_path, msg);
    exit(2);
}

static void read_rgba16(const char *path, image_t *img)
{
    current_path = path;
    FILE *fp = fopen(path, "rb");
    if (!fp) fail("cannot open");

    png_structp png = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, on_error, on_warning);
    png_infop info = png ? png_create_info_struct(png) : NULL;
    if (!png || !info) fail("cannot initialise libpng");
    png_init_io(png, fp);
    png_read_info(png, info);
    png_set_interlace_handling(png);
    png_read_update_info(png, info);

    png_uint_32 w = png_get_image_width(png, info), h = png_get_image_height(png, info);
    int d = png_get_bit_depth(png, info);
    int ct = png_get_color_type(png, info);
    size_t rowbytes = png_get_rowbytes(png, info);

    png_colorp plte = NULL;
    int nplte = 0;
    png_bytep trns_alpha = NULL;
    int ntrns = 0;
    png_color_16p trns_col = NULL;
    if (ct == PNG_COLOR_TYPE_PALETTE) png_get_PLTE(png, info, &plte, &nplte);
    int has_trns = png_get_tRNS(png, info, &trns_alpha, &ntrns, &trns_col) != 0;

    png_bytep raw = malloc(rowbytes * h);
    png_bytepp rows = malloc(sizeof(png_bytep) * h);
    img->rgba = malloc((size_t)w * h * 4 * sizeof(uint16_t));
    if (!raw || !rows || !img->rgba) fail("out of memory");
    for (png_uint_32 y = 0; y < h; y++) rows[y] = raw + y * rowbytes;
    png_read_image(png, rows);
    png_read_end(png, NULL);

    for (png_uint_32 y = 0; y < h; y++) {
        png_const_bytep r = rows[y];
        for (png_uint_32 x = 0; x < w; x++) {
            uint16_t *p = img->rgba + ((size_t)y * w + x) * 4;
            unsigned s0, s1, s2;
            switch (ct) {
            case PNG_COLOR_TYPE_GRAY:
                s0 = sample(r, x, d);
                p[0] = p[1] = p[2] = to16(s0, d);
                p[3] = (has_trns && trns_col && s0 == trns_col->gray) ? 0 : 65535;
                break;
            case PNG_COLOR_TYPE_GRAY_ALPHA:
                p[0] = p[1] = p[2] = to16(sample(r, 2 * x, d), d);
                p[3] = to16(sample(r, 2 * x + 1, d), d);
                break;
            case PNG_COLOR_TYPE_RGB:
                s0 = sample(r, 3 * x, d);
                s1 = sample(r, 3 * x + 1, d);
                s2 = sample(r, 3 * x + 2, d);
                p[0] = to16(s0, d);
                p[1] = to16(s1, d);
                p[2] = to16(s2, d);
                p[3] = (has_trns && trns_col && s0 == trns_col->red &&
                        s1 == trns_col->green && s2 == trns_col->blue) ? 0 : 65535;
                break;
            case PNG_COLOR_TYPE_RGB_ALPHA:
                for (int c = 0; c < 4; c++) p[c] = to16(sample(r, 4 * x + c, d), d);
                break;
            case PNG_COLOR_TYPE_PALETTE:
                s0 = sample(r, x, d);
                if ((int)s0 >= nplte) fail("palette index out of range");
                p[0] = plte[s0].red * 257u;
                p[1] = plte[s0].green * 257u;
                p[2] = plte[s0].blue * 257u;
                p[3] = (has_trns && (int)s0 < ntrns) ? trns_alpha[s0] * 257u : 65535;
                break;
            default:
                fail("unknown colour type");
            }
        }
    }
    img->width = w;
    img->height = h;
    free(rows);
    free(raw);
    png_destroy_read_struct(&png, &info, NULL);
    fclose(fp);
}

int main(int argc, char **argv)
{
    if (argc != 3) {
        fprintf(stderr, "usage: pngpixcmp a.png b.png\n");
        return 2;
    }
    image_t a, b;
    read_rgba16(argv[1], &a);
    read_rgba16(argv[2], &b);
    int same = a.width == b.width && a.height == b.height &&
               memcmp(a.rgba, b.rgba, (size_t)a.width * a.height * 4 * sizeof(uint16_t)) == 0;
    if (!same)
        fprintf(stderr, "pngpixcmp: pixels differ: %s (%ux%u) vs %s (%ux%u)\n",
                argv[1], a.width, a.height, argv[2], b.width, b.height);
    free(a.rgba);
    free(b.rgba);
    return same ? 0 : 1;
}
