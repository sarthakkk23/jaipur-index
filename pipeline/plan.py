"""The story's picture: the walled city seen from above, in flat palette colours, built up as the reader turns the story.

  stage 0 (1727)     the Amber hills to the north, the plain below, and nine plots marked out on a grid
  stage 1 (1731)     blocks rise on every plot
  stage 2 (chaupar)  the main avenues light up as markets: stalls along them, squares where they cross
  stage 3 (2019)     today: the photograph of a bazaar street takes over

A diagram, not a map: nine sectors on a grid, as UNESCO's description has it. It carries no numbers.
Every layer is in the SVG from the start; site.css shows each from its stage on, so without script the plan is shown
built and with its markets.
"""

PAPER, STONE, STONE2, BLUSH, PINK = "#f5f5f2", "#e9e8e4", "#dddcd7", "#f5e4dd", "#e3ad9f"
RED, CLAY, INK = "#b0533d", "#6c3024", "#161616"


def rect(x, y, w, h, fill, cls="", style=""):
    c = f' class="{cls}"' if cls else ""
    s = f' style="{style}"' if style else ""
    return f'<rect{c}{s} x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"/>'


def plan_svg():
    W, H = 400, 400
    gx, gy, gw, gh = 28, 112, 344, 260            # the plain the city is laid on
    av = 18                                       # avenue width
    sw, sh = (gw - 2 * av) / 3, (gh - 2 * av) / 3
    lane = 7
    out = []
    # the Amber hills, to the north
    out.append(f'<g class="hills"><path d="M0 104 L0 70 Q40 30 82 58 Q120 18 168 50 Q206 26 240 54 Q286 8 330 46 Q366 26 400 52 L400 104 Z" fill="{CLAY}"/>'
               f'<path d="M0 104 L0 84 Q52 52 104 78 Q150 50 196 76 Q246 46 292 74 Q344 52 400 72 L400 104 Z" fill="{RED}"/></g>')
    out.append(rect(0, 100, W, H - 100, STONE, "plain"))
    out.append(rect(gx - 8, gy - 8, gw + 16, gh + 16, PAPER, "ground"))
    k = 0
    blds, plots = [], []
    for j in range(3):
        for i in range(3):
            x, y = gx + i * (sw + av), gy + j * (sh + av)
            plots.append(rect(x, y, sw, sh, STONE2, "plot", f"--i:{i + j * 3}"))
            bw, bh = (sw - lane) / 2, (sh - lane) / 2
            for a in range(2):
                for b in range(2):
                    fill = [PINK, RED, PINK, CLAY][(k + a + b) % 4]
                    blds.append(rect(x + a * (bw + lane), y + b * (bh + lane), bw, bh, fill, "bld", f"--i:{k}"))
                    k += 1
    out.append(f'<g class="plots">{"".join(plots)}</g>')
    out.append(f'<g class="blds">{"".join(blds)}</g>')
    # the main avenues as markets: stalls along both sides, and the squares where they cross
    stalls, k = [], 0
    for i in range(2):
        ax = gx + (i + 1) * sw + i * av            # a north-south avenue
        for t in range(14):
            y = gy + 6 + t * (gh - 12) / 14
            stalls.append(rect(ax + 2, y, 4, 9, [RED, INK, CLAY][t % 3], "stall", f"--i:{k}")); k += 1
            stalls.append(rect(ax + av - 6, y + 4, 4, 9, [INK, RED, CLAY][t % 3], "stall", f"--i:{k}")); k += 1
    for j in range(2):
        ay = gy + (j + 1) * sh + j * av            # an east-west avenue
        for t in range(18):
            x = gx + 6 + t * (gw - 12) / 18
            stalls.append(rect(x, ay + 2, 9, 4, [RED, INK, CLAY][t % 3], "stall", f"--i:{k}")); k += 1
            stalls.append(rect(x + 4, ay + av - 6, 9, 4, [INK, RED, CLAY][t % 3], "stall", f"--i:{k}")); k += 1
    avenues = []
    for i in range(2):
        avenues.append(rect(gx + (i + 1) * sw + i * av, gy - 8, av, gh + 16, PINK, "avenue"))
        avenues.append(rect(gx - 8, gy + (i + 1) * sh + i * av, gw + 16, av, PINK, "avenue"))
    squares = []
    for i in range(2):
        for j in range(2):
            cx, cy = gx + (i + 1) * sw + i * av + av / 2, gy + (j + 1) * sh + j * av + av / 2
            squares.append(rect(cx - 15, cy - 15, 30, 30, RED, "square"))
    out.append(f'<g class="avenues">{"".join(avenues)}</g><g class="squares">{"".join(squares)}</g><g class="stalls">{"".join(stalls)}</g>')
    return (f'<svg class="plan" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" role="img" '
            f'aria-label="The walled city from above, drawn as a diagram: hills to the north, a grid of blocks, avenues lined with stalls, and squares where they cross">'
            f'{"".join(out)}</svg>')
