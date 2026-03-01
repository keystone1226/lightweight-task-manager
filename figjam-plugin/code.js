// ──────────────────────────────────────────────────────────────
// Interview Insights FigJam Plugin — code.js
// Renders interview analysis JSON onto a FigJam canvas:
//   • Section A: Key interview questions (sticky notes, yellow)
//   • Section B: User pain points (sticky notes, severity colour)
//   • Section C+: Flows (shapes + connectors, one per flow)
// ──────────────────────────────────────────────────────────────

figma.showUI(__html__, { width: 440, height: 700, title: "Interview Insights" });

figma.ui.onmessage = async (msg) => {
  if (msg.type === "CREATE_BOARD") {
    try {
      status("폰트 로딩 중…");
      await figma.loadFontAsync({ family: "Inter", style: "Regular" });
      await figma.loadFontAsync({ family: "Inter", style: "Bold" });

      status("보드 생성 중…");
      await createInterviewBoard(msg.data);

      figma.ui.postMessage({ type: "DONE" });
    } catch (err) {
      figma.ui.postMessage({ type: "ERROR", message: String(err) });
    }
  } else if (msg.type === "CLOSE") {
    figma.closePlugin();
  }
};

// ──────────────────────────────────────────────────────────────
// Layout constants
// ──────────────────────────────────────────────────────────────
const LEFT      = 200;   // canvas left margin
const STICKY_W  = 240;   // sticky width
const STICKY_H  = 240;   // sticky height
const SGAP      = 24;    // gap between stickies
const SCOLS_Q   = 4;     // stickies per row — questions
const SCOLS_PP  = 4;     // stickies per row — pain points

const NODE_W    = 200;   // flow: process node width
const NODE_H    = 72;    // flow: process node height
const DIAG_W    = 160;   // flow: decision diamond width
const DIAG_H    = 110;   // flow: decision diamond height
const OVAL_W    = 160;   // flow: start/end ellipse width
const OVAL_H    = 60;    // flow: start/end ellipse height
const FCOL_GAP  = 100;   // flow: horizontal gap between nodes
const FROW_GAP  = 80;    // flow: vertical gap between node rows
const FCOLS     = 4;     // flow: nodes per row

const SEC_LABEL_H = 56;  // height reserved for section heading text
const SEC_GAP     = 80;  // vertical gap between sections

// ──────────────────────────────────────────────────────────────
// Colours
// ──────────────────────────────────────────────────────────────
const C = {
  question:     { r: 1.00, g: 0.93, b: 0.33 },  // yellow
  painHigh:     { r: 1.00, g: 0.62, b: 0.62 },  // red
  painMedium:   { r: 1.00, g: 0.82, b: 0.55 },  // orange
  painLow:      { r: 0.72, g: 0.94, b: 0.72 },  // green
  nodeStart:    { r: 0.72, g: 0.94, b: 0.72 },
  nodeEnd:      { r: 1.00, g: 0.75, b: 0.75 },
  nodeProcess:  { r: 0.84, g: 0.92, b: 1.00 },
  nodeDecision: { r: 1.00, g: 0.92, b: 0.72 },
  nodeDefault:  { r: 0.95, g: 0.95, b: 0.95 },
  grey:         { r: 0.40, g: 0.40, b: 0.40 },
  darkGrey:     { r: 0.20, g: 0.20, b: 0.20 },
  muted:        { r: 0.55, g: 0.55, b: 0.55 },
};

// ──────────────────────────────────────────────────────────────
// Main board builder
// ──────────────────────────────────────────────────────────────
async function createInterviewBoard(data) {
  const page = figma.currentPage;
  const all  = [];
  let   curY = 200;

  // ── Title ──────────────────────────────────────────────────
  const title = txt(data.interview_title || "인터뷰 분석 결과", 36, true);
  place(title, LEFT, curY);
  page.appendChild(title);
  all.push(title);
  curY += title.height + 12;

  const sub = txt(
    `분석일: ${data.analyzed_at || "—"}  ·  출처: ${data.source_file || "—"}`,
    14, false, C.muted
  );
  place(sub, LEFT, curY);
  page.appendChild(sub);
  all.push(sub);
  curY += sub.height + SEC_GAP;

  // ── Questions ───────────────────────────────────────────────
  if (data.questions && data.questions.length) {
    const nodes = buildQuestionsSection(page, data.questions, LEFT, curY);
    all.push(...nodes);
    curY = bottomOf(nodes) + SEC_GAP;
  }

  // ── Pain Points ─────────────────────────────────────────────
  if (data.pain_points && data.pain_points.length) {
    const nodes = buildPainPointsSection(page, data.pain_points, LEFT, curY);
    all.push(...nodes);
    curY = bottomOf(nodes) + SEC_GAP;
  }

  // ── Flows ────────────────────────────────────────────────────
  for (const flow of (data.flows || [])) {
    const nodes = buildFlowSection(page, flow, LEFT, curY);
    all.push(...nodes);
    curY = bottomOf(nodes) + SEC_GAP;
  }

  figma.viewport.scrollAndZoomIntoView(all);
}

// ──────────────────────────────────────────────────────────────
// Section builders
// ──────────────────────────────────────────────────────────────
function buildQuestionsSection(page, questions, startX, startY) {
  const created = [];

  const heading = txt("💬  주요 인터뷰 질문", 22, true);
  place(heading, startX, startY);
  page.appendChild(heading);
  created.push(heading);

  let col = 0, row = 0;
  for (const q of questions) {
    const x = startX + col * (STICKY_W + SGAP);
    const y = startY + SEC_LABEL_H + row * (STICKY_H + SGAP);

    const s = makeSticky(
      (q.category ? `[${q.category}]\n\n` : "") + q.text,
      C.question, x, y
    );
    page.appendChild(s);
    created.push(s);

    col++;
    if (col >= SCOLS_Q) { col = 0; row++; }
  }
  return created;
}

function buildPainPointsSection(page, painPoints, startX, startY) {
  const created = [];

  const heading = txt("⚠️  사용자 Pain Points", 22, true);
  place(heading, startX, startY);
  page.appendChild(heading);
  created.push(heading);

  const sorted = [...painPoints].sort((a, b) => {
    const o = { high: 0, medium: 1, low: 2 };
    const oa = o[a.severity] !== undefined ? o[a.severity] : 3;
    const ob = o[b.severity] !== undefined ? o[b.severity] : 3;
    return oa - ob;
  });

  let col = 0, row = 0;
  for (const pp of sorted) {
    const color =
      pp.severity === "high"   ? C.painHigh   :
      pp.severity === "medium" ? C.painMedium :
      C.painLow;

    const badge =
      pp.severity === "high"   ? "🔴 심각" :
      pp.severity === "medium" ? "🟡 보통" : "🟢 낮음";

    const lines = [badge, "", pp.title, "", pp.description];
    if (pp.quote) lines.push("", `"${pp.quote}"`);

    const x = startX + col * (STICKY_W + SGAP);
    const y = startY + SEC_LABEL_H + row * (STICKY_H + SGAP);

    const s = makeSticky(lines.join("\n"), color, x, y);
    page.appendChild(s);
    created.push(s);

    col++;
    if (col >= SCOLS_PP) { col = 0; row++; }
  }
  return created;
}

function buildFlowSection(page, flow, startX, startY) {
  const created  = [];
  const nodeMap  = {};   // node id → SceneNode

  const heading = txt(`🔀  플로우: ${flow.title}`, 22, true);
  place(heading, startX, startY);
  page.appendChild(heading);
  created.push(heading);

  const contentY = startY + SEC_LABEL_H;
  const nodes    = flow.nodes || [];
  const edges    = flow.edges || [];

  // ── Draw nodes ──────────────────────────────────────────────
  for (let i = 0; i < nodes.length; i++) {
    const n   = nodes[i];
    const col = i % FCOLS;
    const row = Math.floor(i / FCOLS);

    const { w, h, shape } = nodeGeometry(n.type);
    const x = startX + col * (NODE_W + FCOL_GAP);
    const y = contentY + row * (NODE_H + FROW_GAP);
    // Centre non-standard sizes within the column
    const cx = x + (NODE_W - w) / 2;
    const cy = y + (NODE_H - h) / 2;

    const shp = figma.createShapeWithText();
    shp.shapeType = shape;
    shp.resize(w, h);
    shp.fills = [{ type: "SOLID", color: nodeColor(n.type) }];
    // Font must be loaded before setting characters
    shp.text.fontName = { family: "Inter", style: "Regular" };
    shp.text.fontSize = 13;
    shp.text.characters = n.label || "";
    place(shp, cx, cy);
    page.appendChild(shp);

    nodeMap[n.id] = shp;
    created.push(shp);
  }

  // ── Draw connectors ─────────────────────────────────────────
  for (const e of edges) {
    const src = nodeMap[e.source];
    const tgt = nodeMap[e.target];
    if (!src || !tgt) continue;

    const conn = figma.createConnector();
    conn.connectorStart = { endpointNodeId: src.id, magnet: "AUTO" };
    conn.connectorEnd   = { endpointNodeId: tgt.id, magnet: "AUTO" };
    conn.strokeWeight   = 2;
    conn.strokes        = [{ type: "SOLID", color: C.darkGrey }];
    page.appendChild(conn);
    created.push(conn);

    // Edge label
    if (e.label) {
      const lbl = txt(e.label, 11, false, C.grey);
      // Place roughly at midpoint between the two nodes
      const mx = (src.x + src.width / 2 + tgt.x + tgt.width / 2) / 2 - 40;
      const my = (src.y + src.height / 2 + tgt.y + tgt.height / 2) / 2 - 10;
      place(lbl, mx, my);
      page.appendChild(lbl);
      created.push(lbl);
    }
  }

  return created;
}

// ──────────────────────────────────────────────────────────────
// Node helpers
// ──────────────────────────────────────────────────────────────
function nodeGeometry(type) {
  if (type === "Decision") return { w: DIAG_W, h: DIAG_H, shape: "DIAMOND" };
  if (type === "Start" || type === "End") return { w: OVAL_W, h: OVAL_H, shape: "ELLIPSE" };
  return { w: NODE_W, h: NODE_H, shape: "ROUNDED_RECTANGLE" };
}

function nodeColor(type) {
  if (type === "Start")    return C.nodeStart;
  if (type === "End")      return C.nodeEnd;
  if (type === "Decision") return C.nodeDecision;
  if (type === "Process")  return C.nodeProcess;
  return C.nodeDefault;
}

// ──────────────────────────────────────────────────────────────
// Factory helpers
// ──────────────────────────────────────────────────────────────
function makeSticky(content, color, x, y) {
  const s = figma.createSticky();
  s.fills = [{ type: "SOLID", color }];
  s.text.fontName  = { family: "Inter", style: "Regular" };
  s.text.fontSize  = 14;
  s.text.characters = content;
  place(s, x, y);
  return s;
}

function txt(content, size, bold, color) {
  const t = figma.createText();
  t.fontName   = { family: "Inter", style: bold ? "Bold" : "Regular" };
  t.fontSize   = size;
  t.characters = content;
  if (color) t.fills = [{ type: "SOLID", color }];
  return t;
}

function place(node, x, y) {
  node.x = x;
  node.y = y;
}

// ──────────────────────────────────────────────────────────────
// Layout util
// ──────────────────────────────────────────────────────────────
function bottomOf(nodes) {
  let max = 0;
  for (const n of nodes) {
    if (typeof n.y === "number" && typeof n.height === "number") {
      max = Math.max(max, n.y + n.height);
    }
  }
  return max;
}

// ──────────────────────────────────────────────────────────────
// Status helper
// ──────────────────────────────────────────────────────────────
function status(msg) {
  figma.ui.postMessage({ type: "STATUS", message: msg });
}
