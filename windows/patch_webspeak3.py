from pathlib import Path


APP_FILE = Path("upstream/web/src/App.tsx")
VOICE_FILE = Path("upstream/web/src/voice.ts")
CSS_FILE = Path("upstream/web/src/App.css")


def replace_once(text, old, new, name):
    if old not in text:
        raise RuntimeError(
            f"PTT Connect patch mislukt: {name} niet gevonden"
        )

    count = text.count(old)

    if count != 1:
        raise RuntimeError(
            f"PTT Connect patch mislukt: {name} "
            f"komt {count} keer voor"
        )

    return text.replace(old, new, 1)


# ============================================================
# VOICE.TS
# Push-To-Talk / Continuous / Voice Activation
# ============================================================

voice = VOICE_FILE.read_text(
    encoding="utf-8"
)


voice = replace_once(
    voice,
    '''export const FRAME_SAMPLES = 960; // 20ms @ 48kHz
''',
    '''export const FRAME_SAMPLES = 960; // 20ms @ 48kHz

export type TransmissionMode =
  | "ptt"
  | "continuous"
  | "voice";
''',
    "TransmissionMode type"
)


voice = replace_once(
    voice,
    '''  hangoverSeconds?: number;
''',
    '''  hangoverSeconds?: number;

  /** Microphone transmission mode. */
  transmissionMode?: TransmissionMode;
''',
    "MicCaptureOptions transmissionMode"
)


voice = replace_once(
    voice,
    '''  private activeUntil = 0;
''',
    '''  private activeUntil = 0;

  private transmissionMode: TransmissionMode;

  private pushToTalkActive = false;
''',
    "MicCapture PTT fields"
)


voice = replace_once(
    voice,
    '''    this.hangoverSeconds = options.hangoverSeconds ?? 0.3;
''',
    '''    this.hangoverSeconds =
      options.hangoverSeconds ?? 0.3;

    this.transmissionMode =
      options.transmissionMode ?? "voice";
''',
    "MicCapture PTT constructor"
)


voice = replace_once(
    voice,
    '''      const now = this.context.currentTime;
      if (rms >= this.threshold) this.activeUntil = now + this.hangoverSeconds;
      // Shared audio (music, a video) has its own pauses; keep sending throughout.
      const shouldBeActive = this.extra !== null || now < this.activeUntil;
''',
    '''      const now = this.context.currentTime;

      if (
        this.transmissionMode === "voice" &&
        rms >= this.threshold
      ) {
        this.activeUntil =
          now + this.hangoverSeconds;
      }

      const shouldBeActive =
        this.extra !== null ||
        this.transmissionMode === "continuous" ||
        (
          this.transmissionMode === "ptt"
            ? this.pushToTalkActive
            : now < this.activeUntil
        );
''',
    "microphone activation logic"
)


voice = replace_once(
    voice,
    '''  stop(): void {
''',
    '''  setTransmissionMode(
    mode: TransmissionMode
  ): void {
    this.transmissionMode = mode;

    this.activeUntil = 0;

    this.pushToTalkActive = false;
  }

  setPushToTalk(
    active: boolean
  ): void {
    this.pushToTalkActive = active;
  }

  stop(): void {
''',
    "MicCapture PTT methods"
)


VOICE_FILE.write_text(
    voice,
    encoding="utf-8"
)


# ============================================================
# APP.TSX
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)


app = replace_once(
    app,
    '''  MicCapture,
  SAMPLE_RATE,
''',
    '''  MicCapture,
  type TransmissionMode,
  SAMPLE_RATE,
''',
    "TransmissionMode import"
)


# ============================================================
# OPSLAG
# ============================================================

app = replace_once(
    app,
    '''const VAD_HANGOVER_KEY = "webspeak3:vad-hangover";
''',
    '''const VAD_HANGOVER_KEY = "webspeak3:vad-hangover";

const VAD_THRESHOLD_KEY =
  "pttconnect:vad-threshold";

const TRANSMISSION_MODE_KEY =
  "pttconnect:transmission-mode";

const PTT_HOTKEY_KEY =
  "pttconnect:ptt-hotkey";

const PTT_HOTKEY_CUSTOMIZED_KEY =
  "pttconnect:ptt-hotkey-customized";
''',
    "PTT storage keys"
)


number_loader = '''function loadNumberPref(key: string, fallback: number): number {
  const raw = localStorage.getItem(key);
  const parsed = raw === null ? NaN : Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}
'''

number_loader_new = '''function loadNumberPref(key: string, fallback: number): number {
  const raw = localStorage.getItem(key);
  const parsed = raw === null ? NaN : Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function loadTransmissionMode(): TransmissionMode {
  const raw =
    localStorage.getItem(
      TRANSMISSION_MODE_KEY
    );

  if (
    raw === "ptt" ||
    raw === "continuous" ||
    raw === "voice"
  ) {
    return raw;
  }

  return "ptt";
}

function loadPttHotkey(): string {
  const customized =
    localStorage.getItem(
      PTT_HOTKEY_CUSTOMIZED_KEY
    ) === "1";

  if (!customized) {
    return "";
  }

  return (
    localStorage.getItem(
      PTT_HOTKEY_KEY
    ) ?? ""
  );
}

function formatPttHotkey(
  code: string
): string {
  if (!code) {
    return "Nog geen PTT-toets gekozen";
  }

  const labels: Record<string, string> = {
    Space: "Spatiebalk",

    ControlLeft: "Linker Ctrl",
    ControlRight: "Rechter Ctrl",

    ShiftLeft: "Linker Shift",
    ShiftRight: "Rechter Shift",

    AltLeft: "Linker Alt",
    AltRight: "Rechter Alt",

    MetaLeft: "Linker Windows-toets",
    MetaRight: "Rechter Windows-toets",

    Enter: "Enter",
    NumpadEnter: "Numpad Enter",

    Tab: "Tab",
    CapsLock: "Caps Lock",
    Backspace: "Backspace",
    Delete: "Delete",
    Insert: "Insert",

    Home: "Home",
    End: "End",

    PageUp: "Page Up",
    PageDown: "Page Down",

    ArrowUp: "Pijl omhoog",
    ArrowDown: "Pijl omlaag",
    ArrowLeft: "Pijl links",
    ArrowRight: "Pijl rechts",

    NumpadAdd: "Numpad +",
    NumpadSubtract: "Numpad -",
    NumpadMultiply: "Numpad *",
    NumpadDivide: "Numpad /",
    NumpadDecimal: "Numpad .",

    Pause: "Pause",
    ScrollLock: "Scroll Lock",
    NumLock: "Num Lock",
  };

  if (labels[code]) {
    return labels[code];
  }

  if (/^Key[A-Z]$/.test(code)) {
    return code.slice(3);
  }

  if (/^Digit[0-9]$/.test(code)) {
    return code.slice(5);
  }

  if (/^Numpad[0-9]$/.test(code)) {
    return "Numpad " + code.slice(6);
  }

  if (/^F[0-9]{1,2}$/.test(code)) {
    return code;
  }

  return code;
}

function makePttConnectNickname(
  value: string
): string {
  const suffix =
    " PTT Connect";

  const clean =
    value
      .trim()
      .replace(
        /\\s+PTT Connect$/i,
        ""
      )
      .trim();

  if (!clean) {
    return "";
  }

  // TeamSpeak nicknames hebben een
  // beperkte lengte. Houd ruimte vrij
  // voor " PTT Connect".
  const maxNicknameLength = 30;

  const maxBaseLength =
    Math.max(
      1,
      maxNicknameLength -
        suffix.length
    );

  const base =
    clean
      .slice(
        0,
        maxBaseLength
      )
      .trimEnd();

  return base + suffix;
}

function redPttDots(
  value: string
): string {
  return value.replace(
    /🔵/g,
    "🔴"
  );
}
'''

app = replace_once(
    app,
    number_loader,
    number_loader_new,
    "PTT preference loaders"
)


# ============================================================
# GEEN VASTE SERVER
# ============================================================

app = replace_once(
    app,
    '''      (DEMO_MODE ? DEMO_HOST : loadDesignTheme() === "nova" ? "" : "localhost")
''',
    '''      (DEMO_MODE ? DEMO_HOST : "")
''',
    "empty default server"
)


app = replace_once(
    app,
    '''  const [connectDialogOpen, setConnectDialogOpen] = useState(false);
''',
    '''  const [connectDialogOpen, setConnectDialogOpen] = useState(true);
''',
    "connection dialog startup"
)


# ============================================================
# AUTOMATISCH "PTT Connect" ACHTER DE NAAM
# Dit werkt voor normaal verbinden EN bookmarks.
# ============================================================

app = replace_once(
    app,
    '''      nickname: overrides?.nickname ?? nickname,
''',
    '''      nickname:
        makePttConnectNickname(
          overrides?.nickname ??
          nickname
        ),
''',
    "automatic PTT Connect nickname"
)


# ============================================================
# BLAUWE SERVERBOLLEN -> RODE BOLLEN
# Ook als 🔵 onderdeel van de servernaam is.
# ============================================================

app = replace_once(
    app,
    '''            label: String(data.serverName || connectHost),
''',
    '''            label:
              redPttDots(
                String(
                  data.serverName ||
                  connectHost
                )
              ),
''',
    "red server tab dots"
)


app = replace_once(
    app,
    '''          setServerName(data.serverName);
''',
    '''          setServerName(
            redPttDots(
              String(data.serverName)
            )
          );
''',
    "red displayed server name"
)


# ============================================================
# AUDIO SETTINGS
# ============================================================

app = replace_once(
    app,
    '''  vadHangover: number;
  onVadHangoverChange: (v: number) => void;
  noiseSuppressionEnabled: boolean;
''',
    '''  vadHangover: number;

  onVadHangoverChange:
    (v: number) => void;

  transmissionMode:
    TransmissionMode;

  onTransmissionModeChange:
    (mode: TransmissionMode) => void;

  pttHotkey: string;

  onPttHotkeyChange:
    (code: string) => void;

  noiseSuppressionEnabled: boolean;
''',
    "AudioSettings PTT fields"
)


# ============================================================
# PUSH TO TALK / CONTINUOUS / VOICE ACTIVATION
# ============================================================

old_modes = '''            <label className="ts-options-radio">
              <input type="radio" name="activation" disabled readOnly />
              {t("recording.pushToTalk")}
            </label>
            <label className="ts-options-radio">
              <input type="radio" name="activation" disabled readOnly />
              {t("recording.continuous")}
            </label>
            <label className="ts-options-radio">
              <input type="radio" name="activation" checked readOnly />
              {t("recording.voiceActivation")}
            </label>
'''

new_modes = '''            <label className="ts-options-radio">
              <input
                type="radio"
                name="activation"
                checked={
                  audio.transmissionMode ===
                  "ptt"
                }
                onChange={() =>
                  audio.onTransmissionModeChange(
                    "ptt"
                  )
                }
              />

              {t("recording.pushToTalk")}
            </label>

            <label className="ts-options-radio">
              <input
                type="radio"
                name="activation"
                checked={
                  audio.transmissionMode ===
                  "continuous"
                }
                onChange={() =>
                  audio.onTransmissionModeChange(
                    "continuous"
                  )
                }
              />

              {t("recording.continuous")}
            </label>

            <label className="ts-options-radio">
              <input
                type="radio"
                name="activation"
                checked={
                  audio.transmissionMode ===
                  "voice"
                }
                onChange={() =>
                  audio.onTransmissionModeChange(
                    "voice"
                  )
                }
              />

              {t("recording.voiceActivation")}
            </label>
'''

app = replace_once(
    app,
    old_modes,
    new_modes,
    "recording transmission modes"
)


# ============================================================
# HOTKEY SCHERM
# GEBRUIKER DRUKT ZELF OP GEWENSTE TOETS
# ============================================================

hotkey_panel = '''function HotkeysPanel({
  audio,
}: {
  audio: AudioSettings;
}) {
  const t = useT();

  const [
    learningPtt,
    setLearningPtt
  ] = useState(false);

  useEffect(() => {
    if (!learningPtt) {
      return;
    }

    const captureKey = (
      event: KeyboardEvent
    ) => {
      event.preventDefault();

      event.stopPropagation();

      event.stopImmediatePropagation();

      if (event.repeat) {
        return;
      }

      if (
        event.code === "Escape"
      ) {
        setLearningPtt(false);
        return;
      }

      if (!event.code) {
        return;
      }

      audio.onPttHotkeyChange(
        event.code
      );

      setLearningPtt(false);
    };

    window.addEventListener(
      "keydown",
      captureKey,
      true
    );

    return () => {
      window.removeEventListener(
        "keydown",
        captureKey,
        true
      );
    };
  }, [
    learningPtt,
    audio
  ]);

  return (
    <>
      <h3>
        {t("options.section.hotkeys")}
      </h3>

      <p className="ts-options-subtitle">
        PTT Connect Push-To-Talk
      </p>

      <fieldset className="ts-options-fieldset">
        <legend>
          Push-To-Talk
        </legend>

        <div
          className="ts-options-field-row"
        >
          <strong>
            Gekozen toets:
          </strong>

          <span>
            {formatPttHotkey(
              audio.pttHotkey
            )}
          </span>
        </div>

        <div
          className="ts-options-field-row"
          style={{
            marginTop: "0.75rem"
          }}
        >
          <button
            type="button"
            onClick={() =>
              setLearningPtt(true)
            }
          >
            {learningPtt
              ? "Druk nu op een toets..."
              : audio.pttHotkey
                ? "Wijzig PTT-toets"
                : "Kies PTT-toets"}
          </button>

          {audio.pttHotkey && (
            <button
              type="button"
              onClick={() =>
                audio.onPttHotkeyChange("")
              }
            >
              Wissen
            </button>
          )}
        </div>

        {learningPtt ? (
          <p className="ts-options-hint">
            Druk nu op de toets die je
            wilt gebruiken om te praten.
            Druk op Escape om te annuleren.
          </p>
        ) : (
          <p className="ts-options-hint">
            Iedere gebruiker kan hier
            zijn eigen Push-To-Talk toets
            kiezen.
          </p>
        )}
      </fieldset>

      <p className="ts-options-hint">
        Houd de gekozen toets ingedrukt
        om te praten en laat de toets los
        om te stoppen.
      </p>

      <p className="ts-options-hint">
        De gekozen toets wordt
        automatisch opgeslagen.
      </p>
    </>
  );
}

'''

app = replace_once(
    app,
    '''function AnwendungPanel({
''',
    hotkey_panel +
    '''function AnwendungPanel({
''',
    "HotkeysPanel"
)


app = replace_once(
    app,
    '''            ) : active.id === "nachrichten" ? (
              <NachrichtenPanel />
''',
    '''            ) : active.id === "hotkeys" ? (
              <HotkeysPanel audio={audio} />
            ) : active.id === "nachrichten" ? (
              <NachrichtenPanel />
''',
    "Hotkeys options route"
)


# ============================================================
# PTT STATE
# ============================================================

app = replace_once(
    app,
    '''  const [vadThreshold, setVadThreshold] = useState(0.02);
  const [vadHangover, setVadHangover] = useState(() => loadNumberPref(VAD_HANGOVER_KEY, 0.3));
''',
    '''  const [
    vadThreshold,
    setVadThreshold
  ] = useState(() =>
    loadNumberPref(
      VAD_THRESHOLD_KEY,
      0.02
    )
  );

  const [
    vadHangover,
    setVadHangover
  ] = useState(() =>
    loadNumberPref(
      VAD_HANGOVER_KEY,
      0.3
    )
  );

  const [
    transmissionMode,
    setTransmissionMode
  ] = useState<TransmissionMode>(
    loadTransmissionMode
  );

  const [
    pttHotkey,
    setPttHotkey
  ] = useState(
    loadPttHotkey
  );
''',
    "PTT React state"
)


# ============================================================
# INSTELLINGEN OPSLAAN
# ============================================================

app = replace_once(
    app,
    '''  useEffect(() => {
    if (micCaptureRef.current) micCaptureRef.current.threshold = vadThreshold;
  }, [vadThreshold]);

  useEffect(() => {
''',
    '''  useEffect(() => {
    if (micCaptureRef.current) {
      micCaptureRef.current.threshold =
        vadThreshold;
    }

    localStorage.setItem(
      VAD_THRESHOLD_KEY,
      String(vadThreshold)
    );
  }, [vadThreshold]);

  useEffect(() => {
    localStorage.setItem(
      TRANSMISSION_MODE_KEY,
      transmissionMode
    );

    micCaptureRef.current
      ?.setTransmissionMode(
        transmissionMode
      );
  }, [transmissionMode]);

  useEffect(() => {
    if (pttHotkey) {
      localStorage.setItem(
        PTT_HOTKEY_KEY,
        pttHotkey
      );
    } else {
      localStorage.removeItem(
        PTT_HOTKEY_KEY
      );
    }
  }, [pttHotkey]);

  useEffect(() => {
''',
    "save PTT settings"
)


# ============================================================
# HANDLER VOOR NIEUWE PTT TOETS
# ============================================================

ptt_hotkey_handler = '''  const handlePttHotkeyChange = (
    code: string
  ) => {
    setPttHotkey(code);

    if (code) {
      localStorage.setItem(
        PTT_HOTKEY_CUSTOMIZED_KEY,
        "1"
      );
    } else {
      localStorage.removeItem(
        PTT_HOTKEY_CUSTOMIZED_KEY
      );
    }
  };

'''

app = replace_once(
    app,
    '''  const handleInputDeviceChange = (deviceId: string) => {
''',
    ptt_hotkey_handler +
    '''  const handleInputDeviceChange = (deviceId: string) => {
''',
    "PTT hotkey change handler"
)


# ============================================================
# TRANSMISSION MODE NAAR MICROFOON
# ============================================================

app = replace_once(
    app,
    '''        threshold: vadThreshold,
        hangoverSeconds: vadHangover,
        deviceId: overrides?.deviceId ?? (inputDeviceId || undefined),
''',
    '''        threshold: vadThreshold,

        hangoverSeconds:
          vadHangover,

        transmissionMode,

        deviceId:
          overrides?.deviceId ??
          (
            inputDeviceId ||
            undefined
          ),
''',
    "MicCapture transmissionMode"
)


# ============================================================
# PTT TOETS INGEDRUKT / LOSGELATEN
# ============================================================

ptt_keyboard = '''  useEffect(() => {
    const isTextField = (
      target: EventTarget | null
    ) => {
      const element =
        target as HTMLElement | null;

      if (!element) {
        return false;
      }

      return (
        element.isContentEditable ||
        /^(INPUT|TEXTAREA|SELECT)$/.test(
          element.tagName
        )
      );
    };

    const onKeyDown = (
      event: KeyboardEvent
    ) => {
      if (
        transmissionMode !== "ptt" ||
        !pttHotkey ||
        event.code !== pttHotkey ||
        event.repeat ||
        isTextField(event.target)
      ) {
        return;
      }

      event.preventDefault();

      micCaptureRef.current
        ?.setPushToTalk(true);
    };

    const onKeyUp = (
      event: KeyboardEvent
    ) => {
      if (
        !pttHotkey ||
        event.code !== pttHotkey
      ) {
        return;
      }

      event.preventDefault();

      micCaptureRef.current
        ?.setPushToTalk(false);
    };

    const releasePtt = () => {
      micCaptureRef.current
        ?.setPushToTalk(false);
    };

    window.addEventListener(
      "keydown",
      onKeyDown
    );

    window.addEventListener(
      "keyup",
      onKeyUp
    );

    window.addEventListener(
      "blur",
      releasePtt
    );

    return () => {
      window.removeEventListener(
        "keydown",
        onKeyDown
      );

      window.removeEventListener(
        "keyup",
        onKeyUp
      );

      window.removeEventListener(
        "blur",
        releasePtt
      );

      releasePtt();
    };
  }, [
    transmissionMode,
    pttHotkey
  ]);

'''

app = replace_once(
    app,
    '''  const handleToggleNoiseSuppression = () => {
''',
    ptt_keyboard +
    '''  const handleToggleNoiseSuppression = () => {
''',
    "PTT keyboard handling"
)


# ============================================================
# PTT INSTELLINGEN NAAR OPTIONS SCHERM
# ============================================================

app = replace_once(
    app,
    '''            vadHangover,
            onVadHangoverChange: setVadHangover,
            noiseSuppressionEnabled,
''',
    '''            vadHangover,

            onVadHangoverChange:
              setVadHangover,

            transmissionMode,

            onTransmissionModeChange:
              setTransmissionMode,

            pttHotkey,

            onPttHotkeyChange:
              handlePttHotkeyChange,

            noiseSuppressionEnabled,
''',
    "Options PTT properties"
)


APP_FILE.write_text(
    app,
    encoding="utf-8"
)


# ============================================================
# APP.CSS
# PTT CONNECT RODE BOLLEN + NETTERE UITLIJNING
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)


ptt_css = r'''

/* ==========================================================
   PTT Connect desktop styling
   ========================================================== */

.ts-app {
  height: 100vh;
  min-height: 100vh;
  box-sizing: border-box;
}

.ts-app *,
.ts-app *::before,
.ts-app *::after {
  box-sizing: border-box;
}

/* Hoofdscherm rustiger en rechter uitlijnen */
.ts-upper {
  align-items: stretch;
}

.ts-tree-panel {
  min-width: 300px;
}

.ts-side-panel {
  min-width: 0;
}

.ts-banner-panel {
  min-height: 220px;
}

.ts-info-panel {
  padding: 0.75rem 1rem;
}

.ts-chat-panel {
  min-height: 180px;
}

/* Blauwe idle praatbol wordt PTT Connect rood */
.ts-talk-lamp-idle {
  background:
    radial-gradient(
      circle at 32% 28%,
      #ffb3b3 0%,
      #e53935 44%,
      #8b1111 100%
    ) !important;

  box-shadow:
    inset 0 1px 1px
      rgba(255, 255, 255, 0.55),
    inset 0 -1px 2px
      rgba(0, 0, 0, 0.35),
    0 0 0 1px
      rgba(0, 0, 0, 0.30) !important;
}

/* Pratende gebruiker blijft groen zodat direct
   zichtbaar blijft wie daadwerkelijk spreekt. */
.ts-talk-lamp-talking {
  box-shadow:
    inset 0 1px 1px
      rgba(255, 255, 255, 0.6),
    inset 0 -1px 2px
      rgba(0, 0, 0, 0.3),
    0 0 5px
      rgba(76, 175, 80, 0.65),
    0 0 0 1px
      rgba(0, 0, 0, 0.2);
}

/* Serverregel en gebruikerregels gelijk uitlijnen */
.ts-server-row,
.ts-client-row,
.ts-channel-row {
  min-height: 20px;
  align-items: center;
}

/* Iets meer ruimte in de serverboom */
.ts-tree-list-root {
  padding-top: 0.2rem;
}

/* Informatieblok netjes op één lijn houden */
.ts-info-title {
  align-items: center;
}

.ts-info-row {
  align-items: baseline;
}

/* Bij groot Windows-scherm iets ruimere rechterkant */
@media (min-width: 1300px) {
  .ts-tree-panel {
    min-width: 320px;
  }

  .ts-info-panel {
    padding-left: 1.1rem;
    padding-right: 1.1rem;
  }
}

'''

if "PTT Connect desktop styling" not in css:
    css += ptt_css


CSS_FILE.write_text(
    css,
    encoding="utf-8"
)


print(
    "PTT Connect patch succesvol toegepast"
)

print(
    "- gebruiker kiest zelf server"
)

print(
    "- bookmarks blijven werken"
)

print(
    "- echte Push-To-Talk"
)

print(
    "- gebruiker kiest zelf PTT-toets"
)

print(
    "- PTT-toets wordt opgeslagen"
)

print(
    "- naam krijgt automatisch PTT Connect"
)

print(
    "- blauwe bollen zijn rood"
)

print(
    "- server blauwe emoji worden rood"
)

print(
    "- desktop layout netjes uitgelijnd"
)
