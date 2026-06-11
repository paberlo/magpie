#!/usr/bin/env bash

# write_variant writes the patched optipng.c/optim.c (only if changed) to the
# work dir root; copy them into the build tree before make, otherwise make
# always rebuilds the unmodified originals and the patch never reaches the binary
for FILE in optipng.c optim.c; do
    if [ -f "$FILE" ]; then
        cp "$FILE" "optipng-7.9.1/src/optipng/$FILE"
    fi
done

cd optipng-7.9.1

make > /dev/null 2>&1        # Silenciar la salida de make
#make test > /dev/null 2>&1



