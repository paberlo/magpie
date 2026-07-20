# RQ4 extendido con qwen2.5:14b — conclusiones (FINAL, 2026-07-20)

Generado con `RQ4_qwen14b.ipynb` / `rq4_with_qwen14b.py` sobre `results_larger.csv` (1200 filas).
**Dataset completo**: los 700 registros de los 7 grupos (UMDA4GI + 3 modelos × 2 algoritmos) tienen
ya todos sus combos, y qwen2.5:14b (UMDA y LLM-puro) llega al 100% de patches validados — 0 filas
sin validar.

Se descubrió y corrigió por el camino un bug de magpie: en algunos runs el `.patch` nunca se
escribía en disco pese a que el entrenamiento sí encontraba un buen patch (`validar.py` fallaba con
`"El archivo .patch ... no existe"`). Afectaba a 46 filas en total, no solo a qwen2.5:14b (también
a llama3.1:8b y qwen2.5-coder:7b, ya en el borrador del paper). 44 se recuperaron reconstruyendo el
`.patch` a partir del texto `patch(BEST)=...` embebido en el propio log de entrenamiento (verificado
con `magpie.core.Patch.from_string`, sin reentrenar nada); solo 2 (ambas weka+qwen2.5:14b) no tenían
patch recuperable y se relanzaron. Detalle completo en la sección 4.1 del notebook.

## Contexto

El exploit de fitness encontrado en OptimPNG+qwen2.5:14b (`check_num_option("-o",...)` borrado,
dejando `options.optim_level` sin inicializar y desactivando de facto la optimización real, ~−99%
de "mejora" falsa) está **corregido y verificado**: `compile.sh` ahora rechaza en compilación
cualquier patch con variable usada sin inicializar, y los 50/50 `.diff` de pngOptim+qwen2.5:14b
(incluyendo los 3 recuperados) no contienen la firma del exploit.

## Validation improvement (mediana por fold+budget, luego media entre budgets)

| Grupo | MiniSAT-hack | OptimPNG | Sat4J | Weka | Suma de rangos |
|---|---:|---:|---:|---:|---:|
| UMDA+qwen7b | -66.8 | -42.8 | -1.0 | -0.6 | **11** |
| LLM-qwen14b | -33.0 | -62.8 | -2.6 | -0.9 | **11** |
| UMDA4GI | -49.3 | -47.7 | -3.3 | -0.3 | 12 |
| UMDA+qwen14b | -41.7 | -32.4 | -5.2 | -0.6 | 13 |
| UMDA+llama | -24.6 | -36.7 | -3.7 | -0.3 | 17 |
| LLM-qwen7b | -54.1 | -31.9 | 0.4 | 0.2 | 22 |
| LLM-llama | -0.4 | -9.8 | -0.3 | 0.1 | 26 |

**Conclusión 1: qwen2.5:14b no domina.** UMDA+qwen7b y LLM-qwen14b empatan en 1er puesto (suma 11),
pero UMDA+qwen14b queda a mitad de tabla (13). El modelo más grande no ofrece una ventaja clara en
mejora de validación frente a los modelos ya en el borrador del paper (llama3.1:8b, qwen2.5-coder:7b).

## Generalisation gap (validation − train; menor = generaliza mejor)

| Grupo | MiniSAT-hack | OptimPNG | Sat4J | Weka | Suma de rangos |
|---|---:|---:|---:|---:|---:|
| LLM-qwen7b | 8.9 | -1.0 | 3.8 | 1.3 | **8** |
| UMDA+llama | 25.5 | -4.5 | 10.3 | 0.8 | 13 |
| LLM-llama | 47.3 | -0.3 | 7.5 | 0.4 | 16 |
| UMDA+qwen7b | 14.2 | -1.4 | 12.8 | 1.6 | 16 |
| UMDA4GI | 9.2 | 0.2 | 5.8 | 1.7 | 17 |
| LLM-qwen14b | 40.0 | -0.0 | 4.5 | 1.7 | 19 |
| UMDA+qwen14b | 22.6 | 0.1 | 12.2 | 2.2 | **23** |

**Conclusión 2: qwen2.5:14b no mejora la generalización de UMDA — la empeora.** UMDA+qwen14b tiene
el peor gap de generalización de los 7 grupos (23), empujado por MiniSAT-hack (22.6) y Sat4J (12.2).
Un modelo más grande no corrige la conocida debilidad de generalización de UMDA4GI; en LLM-puro
LLM-qwen7b sigue siendo con diferencia el mejor generalizador.

## Patch-finding rate

| Grupo | Encontrados | % sin patch |
|---|---:|---:|
| UMDA4GI | 100/100 | 0.0% |
| UMDA+qwen14b | 100/100 | 0.0% |
| UMDA+qwen7b | 99/100 | 1.0% |
| UMDA+llama | 96/100 | 4.0% |
| LLM-qwen14b | 100/100 | 0.0% |
| LLM-qwen7b | 92/100 | 8.0% |
| LLM-llama | 85/100 | 15.0% |

**Conclusión 3: como buscador puro (LLM-puro), qwen2.5:14b encuentra patch en el 100% de los runs**,
frente al 92% de qwen2.5-coder:7b y 85% de llama3.1:8b (cifras ya depuradas del bug del `.patch`
para los 3 modelos). Esa fiabilidad no se traduce en liderazgo claro de mejora de validación (empata
1º pero con alta varianza: mejor valor de toda la tabla en OptimPNG, mediocre en MiniSAT-hack), ni
en mejor generalización.

## Resumen

Un modelo más grande (14b vs 7-8b) **no es una mejora obvia**: iguala en el mejor de los casos, y
como generador de individuos para UMDA (`UMDA+qwen14b`) empeora la generalización respecto a los
modelos ya usados en el borrador del paper. Como buscador puro sí es más fiable encontrando
patches, pero sin ventaja clara en calidad de la mejora.

**Nota aparte**: quedan 22 filas de llama3.1:8b/qwen2.5-coder:7b sin patch validado por una causa
distinta y ya preexistente ("target software crashed" en Weka, principalmente) — no relacionada con
el bug del `.patch` corregido aquí. Fuera del alcance de este documento; ver sección 4.1 del
notebook si se quiere investigar.
