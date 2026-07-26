# Puerta de legibilidad — organic-chemistry


**PASA**


## 1 · Miniatura 83×128

| carta | contraste | veredicto |
|---|---|---|
| 01 | 0.319 | ok |
| 02 | 0.312 | ok |
| 03 | 0.314 | ok |
| 04 | 0.313 | ok |
| 05 | 0.315 | ok |
| 06 | 0.317 | ok |
| 07 | 0.317 | ok |
| 10 | 0.312 | ok |
| 11 | 0.314 | ok |
| 12 | 0.318 | ok |

Contraste = desviación típica de la luminancia sobre el tapete. Es un detector de humo — dice si la carta se ha convertido en una mancha — no una prueba de legibilidad. Un tema muy despejado (líneas finas sobre mucho blanco) puntúa bajo por diseño y aun así se lee: para eso está la lámina de la prueba 3.

## 2 · Siluetas 10 / 11 / 12

| par | distancia | veredicto |
|---|---|---|
| 10 vs 11 | 0.767 | ok |
| 10 vs 12 | 0.942 | ok |
| 11 vs 12 | 0.949 | ok |

Distancia de Jaccard entre las dos siluetas, normalizada por lo que ocupan. Es el fallo más común del spec (§4.2): por debajo de 0.55 las dos figuras se pisan tanto que son la misma carta con otro dibujo. `qa/silueta_NN.png` enseña qué recortó el test de cada una.

## 3 · Mesa mixta

`qa/mesa_mixta.png` — el as de este tema junto a los de otros. **A ojo:** ¿los sigue atando el marco? ¿hay alguna que grite más que las demás? Eso no lo puede medir una máquina.

## 4 · Daltonismo

`qa/deuteranopia.png` y `qa/protanopia.png` — **a ojo:** el recuento de pintas no puede depender de un rojo contra un verde, porque contar es la única señal real que hay.

## 5 · Tapete

| fondo | definición del borde | veredicto |
|---|---|---|
| verde | 0.335 | ok |
| oscuro | 0.329 | ok |

---

Las pruebas 3 y 4 son de ojo: el informe sólo prepara las láminas. Míralas antes de dar el tema por bueno.
