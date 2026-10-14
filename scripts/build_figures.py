"""Generate journal-style figures for the profile README (light + dark variants)."""
import math
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets"
os.makedirs(OUT, exist_ok=True)

SERIF = "'Latin Modern Roman', 'CMU Serif', Charter, 'Bitstream Charter', 'Sitka Text', Cambria, Georgia, 'DejaVu Serif', serif"

THEMES = {
    "light": dict(ink="#1f2328", soft="#57606a", faint="#afb8c1", blue="#1f5fbf", blue_fill="#1f5fbf", orange="#c2410c"),
    "dark": dict(ink="#e6edf3", soft="#9198a1", faint="#4d5560", blue="#79a8ff", blue_fill="#79a8ff", orange="#f0884a"),
}


STYLE = """<style>
    .draw { stroke-dasharray: 1; stroke-dashoffset: 1; animation: draw 10s cubic-bezier(.45,0,.25,1) infinite; }
    .late { opacity: 0; animation: late 10s ease-in-out infinite; }
    .flow { stroke-dasharray: 6 6; animation: flow 1s linear infinite; }
    @keyframes draw { 0%, 5% { stroke-dashoffset: 1; } 45%, 80% { stroke-dashoffset: 0; } 100% { stroke-dashoffset: -1; } }
    @keyframes late { 0%, 40% { opacity: 0; } 50%, 78% { opacity: 1; } 88%, 100% { opacity: 0; } }
    @keyframes flow { to { stroke-dashoffset: -12; } }
    @media (prefers-reduced-motion: reduce) {
      .draw, .late, .flow { animation: none; stroke-dashoffset: 0; opacity: 1; }
    }
  </style>"""


def pdf(x, m, s):
    return math.exp(-0.5 * ((x - m) / s) ** 2) / (s * math.sqrt(2 * math.pi))


def smooth(points):
    pts = [points[0]] + list(points) + [points[-1]]
    d = [f"M{pts[1][0]:.1f},{pts[1][1]:.1f}"]
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    return " ".join(d)


def poly(points):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)


def axes(t, x0, y0, x1, y1, xticks, xlabel, ylabel=None, fs=17):
    """Left and bottom spines with outward ticks, matplotlib-style."""
    out = [
        f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="{t["ink"]}" stroke-width="1.3"/>',
        f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="{t["ink"]}" stroke-width="1.3"/>',
    ]
    for px, label in xticks:
        out.append(f'<line x1="{px:.1f}" y1="{y1}" x2="{px:.1f}" y2="{y1+6}" stroke="{t["ink"]}" stroke-width="1.3"/>')
        out.append(f'<text x="{px:.1f}" y="{y1+26}" text-anchor="middle" font-size="{fs}" fill="{t["ink"]}">{label}</text>')
    out.append(f'<text x="{(x0+x1)/2:.1f}" y="{y1+56}" text-anchor="middle" font-size="{fs+1}" fill="{t["ink"]}">{xlabel}</text>')
    if ylabel:
        cy = (y0 + y1) / 2
        out.append(f'<text x="{x0-22}" y="{cy:.1f}" text-anchor="middle" font-size="{fs+1}" fill="{t["ink"]}" transform="rotate(-90 {x0-22} {cy:.1f})">{ylabel}</text>')
    return "\n  ".join(out)


# ---------------------------------------------------------------- Figure 1
def figure1(t):
    W, H = 1000, 440
    x0, x1, y0, y1 = 90, 960, 40, 350
    lo, hi = 0.0, 2.0

    def X(v):
        return x0 + (v - lo) / (hi - lo) * (x1 - x0)

    pm, ps = 0.9, 0.45          # model prior on ROI
    lm, ls = 1.35, 0.08         # lift test estimate and standard error
    qm = (pm / ps**2 + lm / ls**2) / (1 / ps**2 + 1 / ls**2)
    qs = (1 / (1 / ps**2 + 1 / ls**2)) ** 0.5
    peak = pdf(qm, qm, qs)
    ys = lambda d: y1 - 18 - d / peak * (y1 - y0 - 40)

    xs = [lo + i * (hi - lo) / 160 for i in range(161)]
    prior = poly([(X(v), ys(pdf(v, pm, ps))) for v in xs])
    post_pts = [(X(v), ys(pdf(v, qm, qs))) for v in xs]
    post = poly(post_pts)
    post_area = post + f" L{X(hi):.1f},{y1-18:.1f} L{X(lo):.1f},{y1-18:.1f} Z"
    prior_area = prior + f" L{X(hi):.1f},{y1-18:.1f} L{X(lo):.1f},{y1-18:.1f} Z"
    # Morph through true intermediate Gaussians (mean and log-sd interpolated), so every frame
    # is a proper distribution rather than a point-wise blend of two curves.
    dur = "10s"
    ease = lambda u: u * u * (3 - 2 * u)
    steps = 16
    xs_c = [lo + i * (hi - lo) / 64 for i in range(65)]
    curve = lambda m, sd: smooth([(X(v), ys(pdf(v, m, sd))) for v in xs_c])
    area = lambda c: c + f" L{X(hi):.1f},{y1-18:.1f} L{X(lo):.1f},{y1-18:.1f} Z"
    frames = []
    for i in range(steps + 1):
        k = ease(i / steps)
        frames.append((pm + (qm - pm) * k, math.exp(math.log(ps) + (math.log(qs) - math.log(ps)) * k)))
    times, seq = [0.0], [frames[0]]
    for i, f in enumerate(frames):        # forward: 20% -> 50%
        times.append(0.2 + 0.3 * i / steps); seq.append(f)
    for i, f in enumerate(reversed(frames)):  # back: 80% -> 97%
        times.append(0.8 + 0.17 * i / steps); seq.append(f)
    times.append(1.0); seq.append(frames[0])
    kt = ";".join(f"{x:.4f}" for x in times)

    def morph(kind):
        vals = ";".join((area(curve(m, sd)) if kind == "area" else curve(m, sd)) for m, sd in seq)
        return f'<animate attributeName="d" dur="{dur}" repeatCount="indefinite" keyTimes="{kt}" values="{vals}"/>'

    ty = y1 - 9
    ticks = [(X(v), f"{v:.1f}") for v in (0, 0.5, 1.0, 1.5, 2.0)]
    lx, ly = 120, 62
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SERIF}" role="img" aria-labelledby="t d">
  <title id="t">Figure 1. Calibrating a marketing model with a lift test</title>
  <desc id="d">A wide prior on channel ROI from a marketing mix model, a lift test estimate with its 95% interval, and the narrower calibrated posterior that combines them.</desc>
  {STYLE}
  {axes(t, x0, y0, x1, y1, ticks, "Return on ad spend (ROI)", "Density")}
  <path d="{prior_area}" fill="{t['blue_fill']}" fill-opacity=".12">{morph("area")}</path>
  <path d="{prior}" fill="none" stroke="{t['soft']}" stroke-width="2" stroke-dasharray="7 5"/>
  <path d="{prior}" fill="none" stroke="{t['blue']}" stroke-width="2.6">{morph("line")}</path>
  <g opacity="0">
  <animate attributeName="opacity" dur="{dur}" repeatCount="indefinite" keyTimes="0;0.06;0.18;0.82;0.95;1" values="0;0;1;1;0;0"/>
  <line x1="{X(lm-1.96*ls):.1f}" y1="{ty}" x2="{X(lm+1.96*ls):.1f}" y2="{ty}" stroke="{t['orange']}" stroke-width="2.2"/>
  <line x1="{X(lm-1.96*ls):.1f}" y1="{ty-7}" x2="{X(lm-1.96*ls):.1f}" y2="{ty+7}" stroke="{t['orange']}" stroke-width="2.2"/>
  <line x1="{X(lm+1.96*ls):.1f}" y1="{ty-7}" x2="{X(lm+1.96*ls):.1f}" y2="{ty+7}" stroke="{t['orange']}" stroke-width="2.2"/>
  <circle cx="{X(lm):.1f}" cy="{ty}" r="5.5" fill="{t['orange']}"/>
  </g>
  <g font-size="18" fill="{t['ink']}">
    <line x1="{lx}" y1="{ly}" x2="{lx+40}" y2="{ly}" stroke="{t['soft']}" stroke-width="2" stroke-dasharray="7 5"/>
    <text x="{lx+52}" y="{ly+6}">Model prior (MMM)</text>
    <line x1="{lx}" y1="{ly+32}" x2="{lx+40}" y2="{ly+32}" stroke="{t['orange']}" stroke-width="2.2"/>
    <circle cx="{lx+20}" cy="{ly+32}" r="5.5" fill="{t['orange']}"/>
    <text x="{lx+52}" y="{ly+38}">Lift test, 95% interval</text>
    <line x1="{lx}" y1="{ly+64}" x2="{lx+40}" y2="{ly+64}" stroke="{t['blue']}" stroke-width="2.6"/>
    <text x="{lx+52}" y="{ly+70}">Calibrated posterior</text>
  </g>
</svg>
"""


# ---------------------------------------------------------------- Figure 2
def figure2(t):
    W, H = 1200, 430
    pw, gap = 320, 60
    px = [60, 60 + pw + gap, 60 + 2 * (pw + gap)]
    top, bot = 30, 300
    parts = []

    # (a) selection diagram: S marks the factor that differs between source and target.
    ax = px[0]
    nodes = {"Z": (ax + 60, 210), "X": (ax + 170, 110), "Y": (ax + 290, 210)}
    edges = [("Z", "X"), ("X", "Y"), ("Z", "Y")]
    a = []
    a.append(f'<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{t["ink"]}"/></marker>'
             f'<marker id="arrS" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{t["orange"]}"/></marker></defs>')
    r = 24
    for u, v in edges:
        (x1_, y1_), (x2_, y2_) = nodes[u], nodes[v]
        d = math.hypot(x2_ - x1_, y2_ - y1_)
        ux, uy = (x2_ - x1_) / d, (y2_ - y1_) / d
        a.append(f'<line x1="{x1_+ux*r:.1f}" y1="{y1_+uy*r:.1f}" x2="{x2_-ux*(r+3):.1f}" y2="{y2_-uy*(r+3):.1f}" stroke="{t["ink"]}" stroke-width="1.8" marker-end="url(#arr)"/>')
    for name, (cx, cy) in nodes.items():
        pulse = (f'<animate attributeName="stroke" dur="2s" repeatCount="indefinite" values="{t["ink"]};{t["orange"]};{t["ink"]}" keyTimes="0;0.5;1"/>'
                 if name == "Z" else "")
        a.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{t["ink"]}" stroke-width="1.8">{pulse}</circle>')
        a.append(f'<text x="{cx}" y="{cy+7}" text-anchor="middle" font-size="22" font-style="italic" fill="{t["ink"]}">{name}</text>')
    sx, sy = nodes["Z"][0], 70
    a.append(f'<rect x="{sx-18}" y="{sy-18}" width="36" height="36" fill="none" stroke="{t["orange"]}" stroke-width="2"/>')
    a.append(f'<text x="{sx}" y="{sy+7}" text-anchor="middle" font-size="22" font-style="italic" fill="{t["orange"]}">S</text>')
    a.append(f'<line x1="{sx}" y1="{sy+20}" x2="{sx}" y2="{nodes["Z"][1]-r-3}" stroke="{t["orange"]}" stroke-width="1.8" marker-end="url(#arrS)" class="flow"/>')
    parts.append("\n  ".join(a))

    # (b) adaptive allocation: share of traffic per arm across rounds.
    bx0, bx1 = px[1] + 40, px[1] + pw
    rounds = 10

    def BX(i):
        return bx0 + i / (rounds - 1) * (bx1 - bx0)

    def BY(v):
        return bot - v * (bot - top - 20)

    ts = [i * 9 / 60 for i in range(61)]
    sc = lambda u: (1 - math.exp(-u / 3)) / (1 - math.exp(-3))
    sa = lambda u: (1 - math.exp(-u / 4.5)) / (1 - math.exp(-2))
    C = [1/3 + (0.89 - 1/3) * sc(u) for u in ts]
    A = [1/3 - (1/3 - 0.11) * sa(u) for u in ts]
    shares = {"A": A, "B": [1 - a - c for a, c in zip(A, C)], "C": C}
    cols = {"A": t["soft"], "B": t["faint"], "C": t["blue"]}
    b = [axes(t, bx0, top, bx1, bot, [(BX(0), "1"), (BX(4.5), "5"), (BX(9), "10")], "Round", "Share of traffic")]
    for arm, vals in shares.items():
        pts = [(BX(u), BY(v)) for u, v in zip(ts, vals)]
        b.append(f'<path d="{smooth(pts)}" fill="none" stroke="{cols[arm]}" stroke-width="{2.6 if arm == "C" else 2}" pathLength="1" class="draw"/>')
        b.append(f'<text x="{pts[-1][0]+8:.1f}" y="{pts[-1][1]+6:.1f}" font-size="18" font-style="italic" fill="{cols[arm]}" class="late">{arm}</text>')
    parts.append("\n  ".join(b))

    # (c) return distribution with the lower tail (CVaR) shaded.
    cx0, cx1 = px[2] + 40, px[2] + pw
    m, s = 0.55, 0.17
    q = m - 1.2816 * s

    def CX(u):
        return cx0 + u * (cx1 - cx0)

    pk = pdf(m, m, s)

    def CY(d):
        return bot - d / pk * (bot - top - 40)

    us = [i / 200 for i in range(201)]
    curve = poly([(CX(u), CY(pdf(u, m, s))) for u in us])
    tail = poly([(CX(u), CY(pdf(u, m, s))) for u in us if u <= q] + [(CX(q), CY(pdf(q, m, s)))])
    tail += f" L{CX(q):.1f},{bot} L{CX(0):.1f},{bot} Z"
    c = [axes(t, cx0, top, cx1, bot, [(CX(q), "VaR"), (CX(m), "E[R]")], "Return")]
    tw = CX(q) - CX(0)
    c.append(f'<clipPath id="tailclip"><rect x="{CX(0):.1f}" y="{top}" width="0" height="{bot-top}">'
             f'<animate attributeName="width" dur="10s" repeatCount="indefinite" keyTimes="0;0.05;0.45;0.8;1" values="0;0;{tw:.1f};{tw:.1f};0" calcMode="spline" keySplines="0 0 1 1;.45 0 .25 1;0 0 1 1;.45 0 .25 1"/></rect></clipPath>')
    c.append(f'<path d="{tail}" fill="{t["orange"]}" fill-opacity=".35" clip-path="url(#tailclip)"/>')
    c.append(f'<path d="{curve}" fill="none" stroke="{t["ink"]}" stroke-width="2.2"/>')
    c.append(f'<line x1="{CX(m):.1f}" y1="{bot}" x2="{CX(m):.1f}" y2="{top+14}" stroke="{t["soft"]}" stroke-width="1.6" stroke-dasharray="5 4"/>')
    c.append(f'<text x="{CX(q)-46:.1f}" y="{bot-58}" text-anchor="middle" font-size="18" fill="{t["orange"]}" class="late">CVaR</text>')
    parts.append("\n  ".join(c))

    caps = ["(a) Transportability", "(b) Adaptive experimentation", "(c) Risk-aware allocation"]
    cap_x = [px[0] + pw / 2, px[1] + 40 + (pw - 40) / 2, px[2] + 40 + (pw - 40) / 2]
    captions = "\n  ".join(
        f'<text x="{x:.1f}" y="{H-14}" text-anchor="middle" font-size="20" fill="{t["ink"]}">{c_}</text>' for x, c_ in zip(cap_x, caps)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SERIF}" role="img" aria-labelledby="t d">
  <title id="t">Figure 2. Research questions</title>
  <desc id="d">(a) A selection diagram where node S marks the factor that differs between the source and target markets. (b) Share of traffic per arm across rounds of an adaptive experiment, concentrating on the best arm. (c) A distribution of returns with the lower tail shaded, showing value at risk and conditional value at risk.</desc>
  {STYLE}
  {parts[0]}
  {parts[1]}
  {parts[2]}
  {captions}
</svg>
"""


for name, t in THEMES.items():
    for stem, fn in [("figure1", figure1), ("figure2", figure2)]:
        with open(os.path.join(OUT, f"{stem}-{name}.svg"), "w") as f:
            f.write(fn(t))
print("ok", sorted(os.listdir(OUT)))
