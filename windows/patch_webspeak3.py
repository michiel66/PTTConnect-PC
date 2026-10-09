# ============================================================
# PTT CONNECT MODERN BLUE LOOK
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)

modern_look_css = r'''

/* ==========================================================
   PTT CONNECT - MODERN BLUE DESKTOP LOOK
   ========================================================== */

.ts-app.ts-theme-dark {
  --bg: #071421;
  --bg-toolbar-1: #0b1d2d;
  --bg-toolbar-2: #10283b;

  --border: #16486c;
  --border-soft: #123753;

  --text: #f1f7fc;
  --text-muted: #8da9be;

  --accent: #18aaff;

  --input-bg: #0a1c2b;
  --input-text: #f3f8fc;

  --button-bg-1: #102a40;
  --button-bg-2: #0b1f30;

  --button-bg-hover-1: #17405e;
  --button-bg-hover-2: #12344e;

  --row-hover: #123a57;

  --client-text: #e9f4fb;
  --self-text: #4fc3ff;

  --log-bg: #071725;
  --log-text: #a8bed0;
}


/* ==========================================================
   HELE APP
   ========================================================== */

.ts-app {
  background:
    radial-gradient(
      circle at 50% -20%,
      #123d5e 0%,
      #071421 38%,
      #040d16 100%
    ) !important;

  font-family:
    "Segoe UI",
    Arial,
    sans-serif;
}


/* ==========================================================
   BOVENSTE MENU
   ========================================================== */

.ts-menubar {
  min-height: 44px;

  padding:
    5px 12px;

  background:
    linear-gradient(
      180deg,
      #10283d,
      #091827
    ) !important;

  border-bottom:
    1px solid
    #15527b !important;

  box-shadow:
    0 2px 12px
    rgba(0,0,0,0.35);
}


.ts-menubar-item,
.ts-menubar-item-active {
  border-radius: 7px !important;

  padding:
    6px 10px !important;
}


.ts-menubar-item:hover,
.ts-menubar-item-active:hover {
  background:
    #153d59 !important;
}


/* ==========================================================
   TOOLBAR
   ========================================================== */

.ts-toolbar {
  min-height: 52px;

  padding:
    6px 12px !important;

  background:
    linear-gradient(
      180deg,
      #0e2639,
      #081a29
    ) !important;

  border-bottom:
    1px solid
    #124568 !important;
}


.ts-toolbar-icons {
  gap:
    5px !important;
}


.ts-icon-button {
  min-width: 36px;
  height: 36px;

  border-radius:
    8px !important;

  border:
    1px solid
    #174e73 !important;

  background:
    linear-gradient(
      180deg,
      #153852,
      #0d263a
    ) !important;

  box-shadow:
    inset 0 1px 0
    rgba(255,255,255,0.05);
}


.ts-icon-button:hover {
  border-color:
    #1ab3ff !important;

  background:
    #174763 !important;

  box-shadow:
    0 0 8px
    rgba(24,170,255,0.25);
}


/* ==========================================================
   GROTE HOOFDINDELING
   ========================================================== */

.ts-body {
  padding:
    8px !important;

  gap:
    8px;
}


.ts-upper {
  gap:
    8px;

  padding:
    0 !important;

  background:
    transparent !important;
}


/* ==========================================================
   KANALENLIJST EXTRA BREED
   ========================================================== */

.ts-tree-panel {
  min-width:
    410px !important;

  width:
    410px;

  background:
    linear-gradient(
      180deg,
      #0b1c2b,
      #071624
    ) !important;

  border:
    1px solid
    #155078 !important;

  border-radius:
    11px !important;

  overflow:
    auto;

  box-shadow:
    0 5px 18px
    rgba(0,0,0,0.32);
}


/* bij heel groot scherm nog iets breder */

@media (min-width: 1500px) {

  .ts-tree-panel {
    min-width:
      440px !important;
  }

}


/* ==========================================================
   SERVER BOVENAAN LINKS
   ========================================================== */

.ts-server-row {
  min-height:
    38px !important;

  margin:
    6px;

  padding:
    7px 9px !important;

  border-radius:
    8px !important;

  background:
    linear-gradient(
      180deg,
      #12334b,
      #0d273b
    );

  border:
    1px solid
    #164e73;
}


/* ==========================================================
   ZOEKVELD
   ========================================================== */

.ts-tree-search {
  margin:
    4px 8px 9px !important;

  width:
    calc(100% - 16px) !important;

  min-height:
    34px;

  padding:
    6px 10px !important;

  border-radius:
    8px !important;

  border:
    1px solid
    #174b6d !important;

  background:
    #081826 !important;

  color:
    #ffffff !important;
}


/* ==========================================================
   CHANNELS EN GEBRUIKERS
   ========================================================== */

.ts-row {
  margin:
    1px 6px;

  padding:
    5px 7px !important;

  border-radius:
    7px !important;

  transition:
    background 0.15s ease,
    border-color 0.15s ease;
}


.ts-row:hover {
  background:
    #123751 !important;
}


.ts-row-selected {
  background:
    linear-gradient(
      90deg,
      #0d4265,
      #103650
    ) !important;

  outline:
    1px solid
    #168ed0 !important;

  box-shadow:
    inset 3px 0 0
    #1ab2ff;
}


.ts-channel-row {
  min-height:
    29px !important;

  font-weight:
    600;
}


.ts-client-row {
  min-height:
    28px !important;
}


/* ==========================================================
   PRAAT INDICATOR
   ========================================================== */

.ts-talk-lamp-idle {
  background:
    radial-gradient(
      circle at 35% 30%,
      #ff8e8e,
      #ed2828 45%,
      #7d0909
    ) !important;
}


.ts-talk-lamp-talking {
  background:
    radial-gradient(
      circle at 35% 30%,
      #9affb8,
      #15d65c 45%,
      #08762e
    ) !important;

  box-shadow:
    0 0 8px
    rgba(0,255,100,0.7) !important;
}


/* ==========================================================
   RECHTER / MIDDEN PANEEL
   ========================================================== */

.ts-side-panel {
  min-width:
    0;

  display:
    flex;

  flex-direction:
    column;

  gap:
    8px;
}


/* ==========================================================
   SERVER BANNER
   ========================================================== */

.ts-banner-panel {
  min-height:
    240px !important;

  margin:
    0 !important;

  border:
    1px solid
    #15527b !important;

  border-radius:
    11px !important;

  overflow:
    hidden;

  background:
    #071522;

  box-shadow:
    0 5px 18px
    rgba(0,0,0,0.32);
}


.ts-server-banner {
  width:
    100%;

  height:
    100%;

  object-fit:
    cover;
}


/* ==========================================================
   INFO PANEEL
   ========================================================== */

.ts-info-panel {
  margin:
    0 !important;

  padding:
    14px 16px !important;

  background:
    linear-gradient(
      180deg,
      #0c2233,
      #081928
    ) !important;

  border:
    1px solid
    #144b70 !important;

  border-radius:
    11px !important;

  box-shadow:
    0 5px 18px
    rgba(0,0,0,0.28);
}


.ts-info-title {
  min-height:
    34px;

  margin-bottom:
    8px;

  padding-bottom:
    8px;

  border-bottom:
    1px solid
    #153950;

  font-size:
    17px;

  font-weight:
    700;
}


.ts-info-row {
  display:
    grid;

  grid-template-columns:
    150px 1fr;

  gap:
    10px;

  min-height:
    27px;

  align-items:
    center;
}


/* ==========================================================
   CHAT
   ========================================================== */

.ts-chat-panel {
  min-height:
    260px !important;

  margin-top:
    8px;

  background:
    linear-gradient(
      180deg,
      #091b2a,
      #06131f
    ) !important;

  border:
    1px solid
    #15527a !important;

  border-radius:
    11px !important;

  overflow:
    hidden;

  box-shadow:
    0 5px 18px
    rgba(0,0,0,0.30);
}


.ts-chat-messages {
  padding:
    14px 17px !important;

  line-height:
    1.55;
}


.ts-chat-line {
  padding:
    3px 4px;
}


.ts-chat-from {
  color:
    #35b7ff !important;

  font-weight:
    700;
}


/* ==========================================================
   CHAT TABS
   ========================================================== */

.ts-chat-tabs {
  padding:
    5px 8px !important;

  border-top:
    1px solid
    #113b58 !important;

  background:
    #081826 !important;
}


.ts-chat-tab {
  border-radius:
    7px !important;

  padding:
    6px 11px !important;
}


.ts-chat-tab-active {
  background:
    #123b58 !important;

  color:
    #4fc5ff !important;

  border:
    1px solid
    #156b99 !important;
}


/* ==========================================================
   CHAT TYPEVAK
   ========================================================== */

.ts-chat-input-row {
  padding:
    9px !important;

  gap:
    7px;

  background:
    #081725 !important;

  border-top:
    1px solid
    #123a55 !important;
}


.ts-chat-input-row textarea {
  min-height:
    42px !important;

  padding:
    10px 12px !important;

  border-radius:
    9px !important;

  border:
    1px solid
    #164d70 !important;

  background:
    #0b2031 !important;

  color:
    #ffffff !important;
}


.ts-chat-input-row textarea:focus {
  border-color:
    #1ab3ff !important;

  outline:
    none !important;

  box-shadow:
    0 0 0 2px
    rgba(26,179,255,0.12);
}


.ts-chat-input-row button {
  min-width:
    70px;

  border-radius:
    9px !important;

  border:
    1px solid
    #1599dc !important;

  background:
    linear-gradient(
      180deg,
      #159fe7,
      #0875ad
    ) !important;

  color:
    white !important;

  font-weight:
    700;
}


/* ==========================================================
   AUDIO PLAYER SNELMENU
   ========================================================== */

.ptt-stream-quick-menu {
  min-width:
    300px !important;

  padding:
    7px !important;

  border:
    1px solid
    #1671a6 !important;

  border-radius:
    10px !important;

  background:
    #081b2a !important;

  box-shadow:
    0 10px 30px
    rgba(0,0,0,0.55) !important;
}


.ptt-stream-quick-title {
  color:
    #55c8ff;

  border-bottom:
    1px solid
    #143d58;

  margin-bottom:
    5px;
}


.ptt-stream-active {
  border-color:
    #00c8ff !important;

  box-shadow:
    0 0 10px
    rgba(0,190,255,0.45) !important;
}


/* ==========================================================
   PLAYER VENSTER
   ========================================================== */

.ptt-audio-player-dialog {
  border:
    1px solid
    #1675aa !important;

  border-radius:
    12px !important;

  overflow:
    hidden;

  background:
    #081927 !important;

  box-shadow:
    0 18px 55px
    rgba(0,0,0,0.60) !important;
}


.ptt-audio-player-row {
  background:
    linear-gradient(
      180deg,
      #10283a,
      #0b1e2e
    ) !important;

  border:
    1px solid
    #164965 !important;

  border-radius:
    9px !important;
}


.ptt-audio-player-row:hover {
  border-color:
    #198fc7 !important;
}


.ptt-audio-player-row-active {
  border-color:
    #00bfff !important;

  box-shadow:
    0 0 12px
    rgba(0,190,255,0.18);
}


/* ==========================================================
   ALGEMENE KNOPPEN
   ========================================================== */

button {
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}


/* ==========================================================
   SCROLLBARS
   ========================================================== */

.ts-app ::-webkit-scrollbar {
  width:
    10px;

  height:
    10px;
}


.ts-app ::-webkit-scrollbar-track {
  background:
    #06121d;
}


.ts-app ::-webkit-scrollbar-thumb {
  background:
    #174663;

  border:
    2px solid
    #06121d;

  border-radius:
    10px;
}


.ts-app ::-webkit-scrollbar-thumb:hover {
  background:
    #1d6b94;
}


/* ==========================================================
   RESIZE HANDLES
   ========================================================== */

.ts-resize-handle-vertical {
  width:
    6px !important;

  background:
    transparent !important;
}


.ts-resize-handle-vertical:hover {
  background:
    #168ac4 !important;
}


.ts-resize-handle-horizontal {
  height:
    6px !important;

  background:
    transparent !important;
}


.ts-resize-handle-horizontal:hover {
  background:
    #168ac4 !important;
}


/* ==========================================================
   LOG ONDERAAN
   ========================================================== */

.ts-log {
  background:
    #06121c !important;

  border-top:
    1px solid
    #103a56 !important;

  color:
    #8da9bc !important;
}


/* ==========================================================
   KLEINE SCHERMEN
   ========================================================== */

@media (max-width: 1150px) {

  .ts-tree-panel {
    min-width:
      350px !important;
  }

}


@media (max-width: 850px) {

  .ts-tree-panel {
    min-width:
      300px !important;
  }

}

'''


if "PTT CONNECT - MODERN BLUE DESKTOP LOOK" not in css:
    css += modern_look_css


CSS_FILE.write_text(
    css,
    encoding="utf-8"
)


print(
    "- nieuwe PTT Connect blauwe look toegevoegd"
)

print(
    "- kanalenlijst extra breed gemaakt"
)

print(
    "- moderne ronde panelen toegevoegd"
)

print(
    "- banner en info moderner gemaakt"
)

print(
    "- chat moderner gemaakt"
)

print(
    "- audio player styling aangepast"
)
