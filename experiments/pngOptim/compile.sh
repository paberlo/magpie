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

make CFLAGS="-O -Wall -Werror=uninitialized" > /dev/null 2>&1        # Silenciar la salida de make
# -Werror=uninitialized: rechaza en compilacion cualquier patch que deje una
# variable usada sin inicializar (p.ej. borrar la unica asignacion previa a su
# uso), como el exploit encontrado en qwen2.5:14b/OptimPNG (delete de la linea
# "val = check_num_option(...)" que dejaba options.optim_level con basura y
# desactivaba de facto la optimizacion real).
#make test > /dev/null 2>&1



