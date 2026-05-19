import {
  AbsoluteFill,
  Easing,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

type TokenKind =
  | "comment"
  | "keyword"
  | "plain"
  | "operator"
  | "function"
  | "number"
  | "string"
  | "punctuation";

type Token = { kind: TokenKind; text: string };

type Palette = Record<TokenKind | "background" | "line", string>;

const tokyoLight: Palette = {
  background: "#e6e7ed",
  line: "#9da0ab",
  plain: "#343b59",
  keyword: "#65359d",
  number: "#965027",
  string: "#385f0d",
  function: "#2959aa",
  comment: "#888b94",
  operator: "#006C86",
  punctuation: "#006C86",
};

const slime: Palette = {
  background: "#1e2324",
  line: "#9ba2a0",
  plain: "#e0e0e0",
  keyword: "#9FB3C2",
  number: "#B081B9",
  string: "#8CAEC1",
  function: "#e0ba7d",
  comment: "#6e7573",
  operator: "#b4b4b4",
  punctuation: "#CCD2BE",
};

const code: Token[][] = [
  [{ kind: "comment", text: "// soft, readable, precise" }],
  [
    { kind: "keyword", text: "const" },
    { kind: "plain", text: " mood " },
    { kind: "operator", text: "=" },
    { kind: "plain", text: " " },
    { kind: "function", text: "MartelCode" },
    { kind: "punctuation", text: "({" },
  ],
  [
    { kind: "plain", text: "  tracking" },
    { kind: "punctuation", text: ":" },
    { kind: "number", text: " 0.05" },
    { kind: "punctuation", text: "," },
  ],
  [
    { kind: "plain", text: "  nums" },
    { kind: "punctuation", text: ":" },
    { kind: "string", text: ' "1.00 12.0 123."' },
    { kind: "punctuation", text: "," },
  ],
  [
    { kind: "plain", text: "  zero" },
    { kind: "punctuation", text: ":" },
    { kind: "string", text: ' "0 00 0O0O"' },
    { kind: "punctuation", text: "," },
  ],
  [{ kind: "punctuation", text: "});" }],
];

const clamp = (value: number, min: number, max: number) =>
  Math.max(min, Math.min(max, value));

const fade = (frame: number, start: number, end: number) =>
  interpolate(frame, [start, end], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

const slide = (frame: number, start: number, end: number, from: number) =>
  interpolate(frame, [start, end], [from, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

const CodeBlock: React.FC<{
  palette: Palette;
  align: "left" | "right";
  delay: number;
}> = ({ palette, align, delay }) => {
  const frame = useCurrentFrame();
  const opacity = fade(frame, delay, delay + 24);
  const x = slide(frame, delay, delay + 34, align === "left" ? -80 : 80);

  return (
    <div
      style={{
        position: "absolute",
        top: 240,
        left: align === "left" ? 90 : undefined,
        right: align === "right" ? 90 : undefined,
        width: 760,
        opacity,
        transform: `translateX(${x}px)`,
        fontFamily: "Martel Code",
        fontSize: 45,
        lineHeight: 1.32,
        letterSpacing: "0.015em",
        whiteSpace: "pre",
      }}
    >
      {code.map((line, lineIndex) => (
        <div key={lineIndex} style={{ display: "flex" }}>
          <span
            style={{
              color: palette.line,
              width: 72,
              opacity: 0.85,
              textAlign: "right",
              paddingRight: 24,
            }}
          >
            {lineIndex + 1}
          </span>
          <span>
            {line.map((token, tokenIndex) => (
              <span
                key={`${lineIndex}-${tokenIndex}`}
                style={{
                  color: palette[token.kind],
                  fontFamily:
                    token.kind === "comment"
                      ? "Martel Code Italic"
                      : "Martel Code",
                }}
              >
                {token.text}
              </span>
            ))}
          </span>
        </div>
      ))}
    </div>
  );
};

const SplitThemeReveal: React.FC = () => {
  const frame = useCurrentFrame();
  const wipe = interpolate(frame, [12, 80], [0, 50], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  return (
    <AbsoluteFill style={{ backgroundColor: tokyoLight.background }}>
      <AbsoluteFill
        style={{
          backgroundColor: slime.background,
          clipPath: `inset(0 0 0 ${100 - wipe}%)`,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: 0,
          bottom: 0,
          width: 2,
          background: "rgba(255,255,255,0.12)",
          opacity: fade(frame, 45, 70),
        }}
      />
      <CodeBlock palette={tokyoLight} align="left" delay={52} />
      <CodeBlock palette={slime} align="right" delay={70} />
    </AbsoluteFill>
  );
};

const TitleReveal: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 22, stiffness: 70 } });
  const glow = interpolate(frame, [0, 80, 140], [0, 1, 0.55], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 50% 45%, rgba(168,223,90,${
          glow * 0.26
        }) 0%, rgba(30,35,36,0.98) 48%, #111515 100%)`,
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Martel Code",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.045) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)",
          backgroundSize: "42px 42px",
          opacity: 0.45,
          transform: `translateY(${frame * -0.35}px)`,
        }}
      />
      <div
        style={{
          transform: `scale(${0.92 + scale * 0.08})`,
          color: "#f0f2ec",
          fontSize: 160,
          letterSpacing: "0.03em",
          textShadow: `0 0 ${50 * glow}px rgba(168,223,90,0.45)`,
        }}
      >
        Martel Code
      </div>
      <div
        style={{
          marginTop: 18,
          color: "#bde1df",
          fontSize: 42,
          opacity: fade(frame, 42, 88),
          letterSpacing: "0.09em",
        }}
      >
        gentle code lettering, tuned by script
      </div>
    </AbsoluteFill>
  );
};

const NumeralScene: React.FC = () => {
  const frame = useCurrentFrame();
  const enter = fade(frame, 0, 34);
  const scan = interpolate(frame, [20, 140], [-120, 980], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const rows = ["1.00", "12.0", "123.", "0000", "0O0O"];

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#e6e7ed",
        fontFamily: "Martel Code",
        color: "#343b59",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          opacity: enter,
          transform: `translateY(${slide(frame, 0, 32, 60)}px)`,
          fontSize: 108,
          lineHeight: 1.08,
          fontVariantNumeric: "tabular-nums",
          position: "relative",
        }}
      >
        {rows.map((row) => (
          <div key={row}>{row}</div>
        ))}
        <div
          style={{
            position: "absolute",
            left: scan,
            top: -30,
            width: 4,
            height: "calc(100% + 60px)",
            backgroundColor: "#2959aa",
            opacity: 0.45,
            boxShadow: "0 0 42px #2959aa",
          }}
        />
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 92,
          fontSize: 42,
          color: "#006C86",
          opacity: fade(frame, 48, 88),
        }}
      >
        dotted zero · tabular decimals · wide breathing space
      </div>
    </AbsoluteFill>
  );
};

const FinalCard: React.FC = () => {
  const frame = useCurrentFrame();
  const lift = slide(frame, 0, 36, 80);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#1e2324",
        justifyContent: "center",
        alignItems: "center",
        fontFamily: "Martel Code",
        color: "#e0e0e0",
      }}
    >
      <Img
        src={staticFile("images/martel-code-cover.png")}
        style={{
          position: "absolute",
          width: 1220,
          borderRadius: 18,
          opacity: 0.18,
          filter: "blur(1px)",
          transform: "scale(1.08)",
        }}
      />
      <div
        style={{
          transform: `translateY(${lift}px)`,
          opacity: fade(frame, 0, 30),
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 128, letterSpacing: "0.04em" }}>v0.2.0</div>
        <div
          style={{
            marginTop: 22,
            fontSize: 44,
            color: "#a8df5a",
            fontFamily: "Martel Code Italic",
          }}
        >
          upright + italic · ttf · otf · woff2
        </div>
        <div style={{ marginTop: 64, fontSize: 34, color: "#8CAEC1" }}>
          github.com/colelawrence/martel-code
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const MartelCodeTrailer: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const exitFade = 1 - fade(frame, durationInFrames - 24, durationInFrames - 1);

  return (
    <AbsoluteFill
      style={{
        fontFamily: "Martel Code",
        opacity: clamp(exitFade, 0, 1),
      }}
    >
      <Sequence durationInFrames={110}>
        <TitleReveal />
      </Sequence>
      <Sequence from={88} durationInFrames={128}>
        <SplitThemeReveal />
      </Sequence>
      <Sequence from={198} durationInFrames={108}>
        <NumeralScene />
      </Sequence>
      <Sequence from={292} durationInFrames={96}>
        <FinalCard />
      </Sequence>
    </AbsoluteFill>
  );
};
