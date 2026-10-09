from pathlib import Path


APP_FILE = Path("upstream/web/src/App.tsx")
VOICE_FILE = Path("upstream/web/src/voice.ts")
CSS_FILE = Path("upstream/web/src/App.css")
GATEWAY_FILE = Path("upstream/gateway/src/index.ts")


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
# ============================================================

voice = VOICE_FILE.read_text(
    encoding="utf-8"
)


# ============================================================
# PTT / TRANSMISSION MODES
# ============================================================

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


# ============================================================
# DIRECTE TEAMSpeak ONTVANGSTAUDIO
# ============================================================

voice = replace_once(
    voice,
    '''type SinkableElement = HTMLAudioElement & { setSinkId?: (id: string) => Promise<void> };
type SinkableContext = AudioContext & { setSinkId?: (id: string) => Promise<void> };
''',
    '''type SinkableContext =
  AudioContext & {
    setSinkId?: (
      id: string
    ) => Promise<void>;
  };
''',
    "direct output sink types"
)


voice = replace_once(
    voice,
    '''export class AudioPlayer {
  private nextTime = 0;
  private destination: MediaStreamAudioDestinationNode;
  private element: SinkableElement;
  private gain: GainNode;
''',
    '''export class AudioPlayer {
  private nextTime = 0;

  private scheduledSources =
    new Set<AudioBufferSourceNode>();

  private gain: GainNode;
''',
    "AudioPlayer direct fields"
)


voice = replace_once(
    voice,
    '''  constructor(context: AudioContext) {
    this.context = context;
    this.destination = context.createMediaStreamDestination();
    this.gain = context.createGain();
    this.gain.connect(this.destination);
    this.element = document.createElement("audio") as SinkableElement;
    this.element.autoplay = true;
    this.element.srcObject = this.destination.stream;
    this.element.style.display = "none";
    document.body.appendChild(this.element);
  }

  playFrame(base64Pcm: string): void {
''',
    '''  constructor(context: AudioContext) {
    this.context = context;

    this.gain =
      context.createGain();

    this.gain.connect(
      context.destination
    );
  }

  private clearScheduledAudio(): void {
    for (
      const source of
      this.scheduledSources
    ) {
      try {
        source.stop();
      } catch {
      }

      try {
        source.disconnect();
      } catch {
      }
    }

    this.scheduledSources.clear();
  }

  playFrame(base64Pcm: string): void {
''',
    "AudioPlayer direct constructor"
)


voice = replace_once(
    voice,
    '''    const source = this.context.createBufferSource();
    source.buffer = buffer;
    source.connect(this.gain);

    const now = this.context.currentTime;
    if (this.nextTime < now + 0.02) {
      // First frame, or we fell behind - restart just ahead of now instead of
      // letting a backlog build up.
      this.nextTime = now + 0.02;
    }
    source.start(this.nextTime);
    this.nextTime += frames / SAMPLE_RATE;
''',
    '''    const now =
      this.context.currentTime;

    const minimumLead =
      0.02;

    const maximumLead =
      0.12;

    if (
      this.nextTime <
      now + minimumLead
    ) {
      this.nextTime =
        now + minimumLead;
    }

    if (
      this.nextTime >
      now + maximumLead
    ) {
      this.clearScheduledAudio();

      this.nextTime =
        now + minimumLead;
    }

    const source =
      this.context.createBufferSource();

    source.buffer =
      buffer;

    source.playbackRate.value =
      1.0;

    source.connect(
      this.gain
    );

    this.scheduledSources.add(
      source
    );

    source.onended = () => {
      this.scheduledSources.delete(
        source
      );

      try {
        source.disconnect();
      } catch {
      }
    };

    source.start(
      this.nextTime
    );

    this.nextTime +=
      frames / SAMPLE_RATE;
''',
    "direct TeamSpeak live playback"
)


voice = replace_once(
    voice,
    '''  reset(): void {
    this.nextTime = 0;
  }
''',
    '''  reset(): void {
    this.clearScheduledAudio();
    this.nextTime = 0;
  }
''',
    "AudioPlayer direct reset"
)


voice = replace_once(
    voice,
    '''  /** Routes playback to a specific device (empty string = system default). */
  async setOutputDevice(deviceId: string): Promise<void> {
    if (typeof this.element.setSinkId === "function") {
      await this.element.setSinkId(deviceId);
      return;
    }
    const ctx = this.context as SinkableContext;
    if (typeof ctx.setSinkId === "function") {
      await ctx.setSinkId(deviceId);
    }
    // Neither API is available - stays on the system default output.
  }

  dispose(): void {
    this.detachAecRenderTap();
    this.element.pause();
    this.element.srcObject = null;
    this.element.remove();
    this.destination.stream.getTracks().forEach((t) => t.stop());
  }
''',
    '''  /** Routes playback to a specific device (empty string = system default). */
  async setOutputDevice(
    deviceId: string
  ): Promise<void> {
    const ctx =
      this.context as SinkableContext;

    if (
      typeof ctx.setSinkId ===
      "function"
    ) {
      await ctx.setSinkId(
        deviceId
      );
    }
  }

  dispose(): void {
    this.clearScheduledAudio();
    this.nextTime = 0;
    this.detachAecRenderTap();

    try {
      this.gain.disconnect();
    } catch {
    }
  }
''',
    "direct output device and dispose"
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
# OPSLAG + KLEUREN + STREAMS
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

const PTT_COLOR_THEME_KEY =
  "pttconnect:color-theme";
''',
    "PTT storage keys"
)


number_loader = '''function loadNumberPref(key: string, fallback: number): number {
  const raw = localStorage.getItem(key);
  const parsed = raw === null ? NaN : Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}
'''


number_loader_new = '''type PttColorTheme =
  | "blue"
  | "green"
  | "red"
  | "purple"
  | "orange"
  | "pink";

const PTT_COLOR_THEMES: Array<{
  id: PttColorTheme;
  name: string;
  swatch: string;
}> = [
  {
    id: "blue",
    name: "Blauw",
    swatch: "#18aaff",
  },
  {
    id: "green",
    name: "Groen",
    swatch: "#31c66d",
  },
  {
    id: "red",
    name: "Rood",
    swatch: "#ff4d5a",
  },
  {
    id: "purple",
    name: "Paars",
    swatch: "#a970ff",
  },
  {
    id: "orange",
    name: "Oranje",
    swatch: "#ff9b3d",
  },
  {
    id: "pink",
    name: "Roze",
    swatch: "#ff5ca8",
  },
];

const PTT_AUDIO_STREAMS = [
  {
    id: "pi2nos",
    name: "PI2NOS",
    url: "https://stream.hobbyscoop.nl/pi2nos",
  },
  {
    id: "pi3utr",
    name: "PI3UTR",
    url: "https://stream.hobbyscoop.nl/pi3utr",
  },
  {
    id: "pi3goe",
    name: "PI3GOE",
    url: "https://stream.hobbyscoop.nl/pi3goe",
  },
] as const;

function loadNumberPref(key: string, fallback: number): number {
  const raw = localStorage.getItem(key);
  const parsed = raw === null ? NaN : Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function loadPttColorTheme(): PttColorTheme {
  const saved =
    localStorage.getItem(
      PTT_COLOR_THEME_KEY
    );

  if (
    saved === "blue" ||
    saved === "green" ||
    saved === "red" ||
    saved === "purple" ||
    saved === "orange" ||
    saved === "pink"
  ) {
    return saved;
  }

  return "blue";
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

  const maxNicknameLength =
    30;

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
    "PTT preference loaders colors and streams"
)


# ============================================================
# GEEN AUTOMATISCHE SERVER
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
# NAAM PTT CONNECT
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
# RODE SERVERBOLLEN
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
# AUDIO PLAYER DIALOG
# ============================================================

audio_dialog = r'''
function PttAudioPlayersDialog({
  activeStreamId,
  errorMessage,
  onPlay,
  onStop,
  onClose,
}: {
  activeStreamId: string | null;
  errorMessage: string;
  onPlay: (
    id: string,
    url: string
  ) => Promise<void>;
  onStop: () => void;
  onClose: () => void;
}) {
  const backdrop =
    useBackdropDismiss(onClose);

  return (
    <div
      className="ts-dialog-backdrop"
      {...backdrop}
    >
      <div
        className="ts-dialog ptt-audio-player-dialog"
        onClick={(event) =>
          event.stopPropagation()
        }
      >
        <div className="ts-dialog-titlebar">
          <span>
            📻 Audio Players / Streams
          </span>

          <button
            type="button"
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        <div className="ts-dialog-body">
          <p>
            Luister naar een audiostream.
            De stream wordt alleen op jouw
            computer afgespeeld.
          </p>

          <div className="ptt-audio-player-list">
            {PTT_AUDIO_STREAMS.map(
              (stream) => {
                const active =
                  activeStreamId ===
                  stream.id;

                return (
                  <div
                    key={stream.id}
                    className={
                      "ptt-audio-player-row" +
                      (
                        active
                          ? " ptt-audio-player-row-active"
                          : ""
                      )
                    }
                  >
                    <div className="ptt-audio-player-info">
                      <strong>
                        {stream.name}
                      </strong>

                      <span>
                        {stream.url}
                      </span>
                    </div>

                    <div className="ptt-audio-player-actions">
                      <button
                        type="button"
                        disabled={active}
                        onClick={() =>
                          void onPlay(
                            stream.id,
                            stream.url
                          )
                        }
                      >
                        ▶ Aan
                      </button>

                      <button
                        type="button"
                        disabled={!active}
                        onClick={onStop}
                      >
                        ■ Uit
                      </button>
                    </div>
                  </div>
                );
              }
            )}
          </div>

          {errorMessage && (
            <div className="ptt-audio-player-error">
              ⚠️ {errorMessage}
            </div>
          )}

          <div className="ptt-audio-player-note">
            <div>
              • Er kan maar één stream tegelijk actief zijn.
            </div>
            <div>
              • Een stream start nooit automatisch.
            </div>
            <div>
              • Push-To-Talk blijft gewoon werken.
            </div>
            <div>
              • Sluiten van dit venster stopt de stream niet.
            </div>
          </div>
        </div>

        <div className="ts-dialog-buttons">
          <button
            type="button"
            onClick={onStop}
            disabled={!activeStreamId}
          >
            ■ Alles uit
          </button>

          <div className="ts-dialog-buttons-right">
            <button
              type="button"
              onClick={onClose}
            >
              Sluiten
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

'''


app = replace_once(
    app,
    '''function AnwendungPanel({
''',
    audio_dialog +
    '''function AnwendungPanel({
''',
    "PTT audio player dialog"
)


# ============================================================
# HOTKEY PANEL
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

      if (event.code === "Escape") {
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

        <div className="ts-options-field-row">
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

        <p className="ts-options-hint">
          Iedere gebruiker kan hier
          zijn eigen Push-To-Talk toets
          kiezen.
        </p>
      </fieldset>
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
# PLAYER + THEMA STATE
# ============================================================

app = replace_once(
    app,
    '''  const [extrasMenuOpen, setExtrasMenuOpen] = useState(false);
''',
    '''  const [extrasMenuOpen, setExtrasMenuOpen] = useState(false);

  const [
    audioPlayersOpen,
    setAudioPlayersOpen
  ] = useState(false);

  const [
    audioPlayersQuickOpen,
    setAudioPlayersQuickOpen
  ] = useState(false);

  const [
    activeAudioStreamId,
    setActiveAudioStreamId
  ] = useState<string | null>(null);

  const [
    audioStreamError,
    setAudioStreamError
  ] = useState("");

  const audioStreamElementRef =
    useRef<HTMLAudioElement | null>(
      null
    );

  const [
    pttColorTheme,
    setPttColorTheme
  ] = useState<PttColorTheme>(
    loadPttColorTheme
  );

  const [
    pttThemeMenuOpen,
    setPttThemeMenuOpen
  ] = useState(false);
''',
    "PTT player and theme state"
)


# ============================================================
# OPSLAAN
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
# PLAYER START / STOP
# ============================================================

player_handlers = r'''  const stopPttAudioStream = () => {
    const current =
      audioStreamElementRef.current;

    if (current) {
      try {
        current.pause();
      } catch {
      }

      current.removeAttribute(
        "src"
      );

      try {
        current.load();
      } catch {
      }
    }

    audioStreamElementRef.current =
      null;

    setActiveAudioStreamId(
      null
    );

    setAudioStreamError("");
  };

  const startPttAudioStream = async (
    id: string,
    url: string
  ) => {
    stopPttAudioStream();

    setAudioStreamError("");

    const audio =
      document.createElement(
        "audio"
      );

    audio.preload =
      "none";

    audio.autoplay =
      false;

    audio.src =
      url;

    audio.volume =
      1;

    audioStreamElementRef.current =
      audio;

    setActiveAudioStreamId(
      id
    );

    audio.addEventListener(
      "error",
      () => {
        if (
          audioStreamElementRef.current !==
          audio
        ) {
          return;
        }

        setAudioStreamError(
          "Deze stream kon niet worden afgespeeld."
        );

        setActiveAudioStreamId(
          null
        );

        audioStreamElementRef.current =
          null;
      },
      {
        once: true
      }
    );

    try {
      await audio.play();
    } catch {
      if (
        audioStreamElementRef.current ===
        audio
      ) {
        setAudioStreamError(
          "Deze stream kon niet worden gestart."
        );

        setActiveAudioStreamId(
          null
        );

        audioStreamElementRef.current =
          null;
      }
    }
  };

'''


app = replace_once(
    app,
    '''  const handleInputDeviceChange = (deviceId: string) => {
''',
    player_handlers +
    '''  const handleInputDeviceChange = (deviceId: string) => {
''',
    "PTT audio player handlers"
)


# ============================================================
# HOTKEY CHANGE
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
# MICROFOON TRANSMISSION MODE
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
# PTT TOETS
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
# AUDIO SETTINGS DOORGEVEN
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


# ============================================================
# APP KLEURKLASSE
# ============================================================

app = replace_once(
    app,
    '''      className={`ts-app ts-theme-${theme}${designThemeClassName(designTheme)}${
        activeCustomTheme ? " ts-design-custom" : ""
      }${demoForceMobile ? " ts-force-mobile" : ""}${novaSplash ? " ts-nova-splash" : ""}`}
''',
    '''      className={`ts-app ts-theme-${theme}${designThemeClassName(designTheme)}${
        activeCustomTheme ? " ts-design-custom" : ""
      }${demoForceMobile ? " ts-force-mobile" : ""}${novaSplash ? " ts-nova-splash" : ""} ts-ptt-color-${pttColorTheme}`}
''',
    "PTT color theme app class"
)


# ============================================================
# TOOLS MENU
# ============================================================

app = replace_once(
    app,
    '''              <div className="ts-menu-separator" />
              <button
                className="ts-menu-item"
                onClick={() => {
                  setOptionsDialogOpen(true);
                  setExtrasMenuOpen(false);
                }}
              >
                <span className="ts-menu-item-icon">⚙️</span>
                <span className="ts-menu-item-label">{t("menu.extras.options")}</span>
              </button>
''',
    '''              <div className="ts-menu-separator" />

              <button
                className="ts-menu-item"
                onClick={() => {
                  setAudioPlayersOpen(true);
                  setAudioPlayersQuickOpen(false);
                  setExtrasMenuOpen(false);
                }}
              >
                <span className="ts-menu-item-icon">
                  📻
                </span>

                <span className="ts-menu-item-label">
                  Audio Players / Streams
                </span>
              </button>

              <div className="ts-menu-separator" />

              <button
                className="ts-menu-item"
                onClick={() => {
                  setOptionsDialogOpen(true);
                  setExtrasMenuOpen(false);
                }}
              >
                <span className="ts-menu-item-icon">⚙️</span>
                <span className="ts-menu-item-label">{t("menu.extras.options")}</span>
              </button>
''',
    "Audio Players under Tools"
)


# ============================================================
# THEMA KNOP + PLAYER KNOP
# ============================================================

app = replace_once(
    app,
    '''          <button
            className="ts-icon-button"
            onClick={() => setTheme((mode) => (mode === "dark" ? "light" : "dark"))}
            title={t("toolbar.toggleTheme")}
            aria-label={t("toolbar.toggleTheme")}
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
          <img src={`${import.meta.env.BASE_URL}logo.png`} alt="" className="ts-app-logo" />
''',
    '''          <div className="ptt-theme-quick">
            <button
              type="button"
              className="ts-icon-button"
              onClick={() =>
                setPttThemeMenuOpen(
                  (open) => !open
                )
              }
              title="Kleurthema"
              aria-label="Kleurthema"
              aria-expanded={pttThemeMenuOpen}
            >
              {theme === "dark" ? "☀️" : "🌙"}
            </button>

            {pttThemeMenuOpen && (
              <div className="ts-menu ptt-theme-menu">
                <div className="ptt-theme-menu-title">
                  🎨 Kleurthema
                </div>

                {PTT_COLOR_THEMES.map(
                  (colorTheme) => {
                    const active =
                      pttColorTheme ===
                      colorTheme.id;

                    return (
                      <button
                        key={colorTheme.id}
                        type="button"
                        className={
                          "ts-menu-item" +
                          (
                            active
                              ? " ptt-theme-menu-active"
                              : ""
                          )
                        }
                        onClick={() => {
                          setPttColorTheme(
                            colorTheme.id
                          );

                          localStorage.setItem(
                            PTT_COLOR_THEME_KEY,
                            colorTheme.id
                          );

                          setPttThemeMenuOpen(
                            false
                          );
                        }}
                      >
                        <span
                          className="ptt-theme-swatch"
                          style={{
                            background:
                              colorTheme.swatch
                          }}
                        />

                        <span className="ts-menu-item-label">
                          {colorTheme.name}
                        </span>

                        {active && (
                          <span className="ptt-theme-check">
                            ✓
                          </span>
                        )}
                      </button>
                    );
                  }
                )}

                <div className="ts-menu-separator" />

                <button
                  type="button"
                  className="ts-menu-item"
                  onClick={() => {
                    setTheme(
                      (mode) =>
                        mode === "dark"
                          ? "light"
                          : "dark"
                    );

                    setPttThemeMenuOpen(
                      false
                    );
                  }}
                >
                  <span className="ts-menu-item-icon">
                    {theme === "dark"
                      ? "☀️"
                      : "🌙"}
                  </span>

                  <span className="ts-menu-item-label">
                    {theme === "dark"
                      ? "Lichte modus"
                      : "Donkere modus"}
                  </span>
                </button>
              </div>
            )}
          </div>

          <div className="ptt-stream-quick">
            <button
              type="button"
              className={
                "ts-icon-button" +
                (
                  activeAudioStreamId
                    ? " ptt-stream-active"
                    : ""
                )
              }
              onClick={() =>
                setAudioPlayersQuickOpen(
                  (open) => !open
                )
              }
              title="Audio Players / Streams"
            >
              📻
            </button>

            {audioPlayersQuickOpen && (
              <div className="ts-menu ptt-stream-quick-menu">
                <div className="ptt-stream-quick-title">
                  📻 Audio Players / Streams
                </div>

                {PTT_AUDIO_STREAMS.map(
                  (stream) => {
                    const active =
                      activeAudioStreamId ===
                      stream.id;

                    return (
                      <button
                        key={stream.id}
                        type="button"
                        className="ts-menu-item"
                        onClick={() => {
                          if (active) {
                            stopPttAudioStream();
                          } else {
                            void startPttAudioStream(
                              stream.id,
                              stream.url
                            );
                          }
                        }}
                      >
                        <span className="ts-menu-item-icon">
                          {active ? "■" : "▶"}
                        </span>

                        <span className="ts-menu-item-label">
                          {stream.name}
                        </span>

                        <span className="ptt-stream-status">
                          {active ? "AAN" : ""}
                        </span>
                      </button>
                    );
                  }
                )}

                <div className="ts-menu-separator" />

                <button
                  type="button"
                  className="ts-menu-item"
                  onClick={() => {
                    setAudioPlayersOpen(true);
                    setAudioPlayersQuickOpen(false);
                  }}
                >
                  <span className="ts-menu-item-icon">
                    ⚙️
                  </span>

                  <span className="ts-menu-item-label">
                    Player openen
                  </span>
                </button>

                {activeAudioStreamId && (
                  <button
                    type="button"
                    className="ts-menu-item"
                    onClick={() => {
                      stopPttAudioStream();
                      setAudioPlayersQuickOpen(false);
                    }}
                  >
                    <span className="ts-menu-item-icon">
                      ■
                    </span>

                    <span className="ts-menu-item-label">
                      Stream uit
                    </span>
                  </button>
                )}
              </div>
            )}
          </div>

          <img src={`${import.meta.env.BASE_URL}logo.png`} alt="" className="ts-app-logo" />
''',
    "theme and audio player toolbar buttons"
)


# ============================================================
# PLAYER DIALOG
# ============================================================

app = replace_once(
    app,
    '''      {restartNotice && <RestartNoticeDialog message={restartNotice} onAck={() => setRestartNotice(null)} />}
''',
    '''      {audioPlayersOpen && (
        <PttAudioPlayersDialog
          activeStreamId={
            activeAudioStreamId
          }
          errorMessage={
            audioStreamError
          }
          onPlay={
            startPttAudioStream
          }
          onStop={
            stopPttAudioStream
          }
          onClose={() =>
            setAudioPlayersOpen(false)
          }
        />
      )}

      {restartNotice && <RestartNoticeDialog message={restartNotice} onAck={() => setRestartNotice(null)} />}
''',
    "Audio player dialog render"
)


APP_FILE.write_text(
    app,
    encoding="utf-8"
)


# ============================================================
# GATEWAY - EXTERNE AUDIO TOESTAAN
# ============================================================

gateway = GATEWAY_FILE.read_text(
    encoding="utf-8"
)


gateway = replace_once(
    gateway,
    '''  "media-src 'self' data: blob:",
''',
    '''  "media-src 'self' data: blob: https:",
''',
    "allow HTTPS audio streams in CSP"
)


GATEWAY_FILE.write_text(
    gateway,
    encoding="utf-8"
)


# ============================================================
# CSS
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)


ptt_css = r'''

/* ==========================================================
   PTT CONNECT MODERN LOOK
   ========================================================== */

.ts-app {
  --ptt-accent: #18aaff;
  --ptt-accent-soft: #15527b;
  --ptt-accent-dark: #0d4265;
  --ptt-glow: rgba(24,170,255,0.35);

  height: 100vh;
  min-height: 100vh;
  box-sizing: border-box;

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

.ts-app *,
.ts-app *::before,
.ts-app *::after {
  box-sizing: border-box;
}


/* ==========================================================
   KLEURTHEMA'S
   ========================================================== */

.ts-app.ts-ptt-color-blue {
  --ptt-accent: #18aaff;
  --ptt-accent-soft: #15527b;
  --ptt-accent-dark: #0d4265;
  --ptt-glow: rgba(24,170,255,0.35);
}

.ts-app.ts-ptt-color-green {
  --ptt-accent: #31c66d;
  --ptt-accent-soft: #287548;
  --ptt-accent-dark: #17492c;
  --ptt-glow: rgba(49,198,109,0.35);
}

.ts-app.ts-ptt-color-red {
  --ptt-accent: #ff4d5a;
  --ptt-accent-soft: #8e3440;
  --ptt-accent-dark: #58242c;
  --ptt-glow: rgba(255,77,90,0.35);
}

.ts-app.ts-ptt-color-purple {
  --ptt-accent: #a970ff;
  --ptt-accent-soft: #65459b;
  --ptt-accent-dark: #3e2a65;
  --ptt-glow: rgba(169,112,255,0.35);
}

.ts-app.ts-ptt-color-orange {
  --ptt-accent: #ff9b3d;
  --ptt-accent-soft: #945b2e;
  --ptt-accent-dark: #5e391f;
  --ptt-glow: rgba(255,155,61,0.35);
}

.ts-app.ts-ptt-color-pink {
  --ptt-accent: #ff5ca8;
  --ptt-accent-soft: #944069;
  --ptt-accent-dark: #5d2944;
  --ptt-glow: rgba(255,92,168,0.35);
}


/* ==========================================================
   DONKERE BASIS
   ========================================================== */

.ts-app.ts-theme-dark {
  --bg: #071421;
  --bg-toolbar-1: #0b1d2d;
  --bg-toolbar-2: #10283b;
  --border: var(--ptt-accent-soft);
  --border-soft: #123753;
  --text: #f1f7fc;
  --text-muted: #8da9be;
  --accent: var(--ptt-accent);
  --input-bg: #0a1c2b;
  --input-text: #f3f8fc;
  --button-bg-1: #102a40;
  --button-bg-2: #0b1f30;
  --button-bg-hover-1: #17405e;
  --button-bg-hover-2: #12344e;
  --row-hover: #123a57;
  --client-text: #e9f4fb;
  --self-text: var(--ptt-accent);
  --log-bg: #071725;
  --log-text: #a8bed0;
}


/* ==========================================================
   BOVENMENU
   ========================================================== */

.ts-menubar {
  min-height: 44px;

  padding:
    5px 12px !important;

  background:
    linear-gradient(
      180deg,
      #10283d,
      #091827
    ) !important;

  border-bottom:
    1px solid
    var(--ptt-accent-soft) !important;

  box-shadow:
    0 2px 12px
    rgba(0,0,0,0.35);
}

.ts-menubar-item,
.ts-menubar-item-active {
  border-radius:
    7px !important;

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
  min-height:
    52px;

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
    var(--ptt-accent-soft) !important;
}

.ts-toolbar-icons {
  gap:
    5px !important;
}

.ts-icon-button {
  min-width:
    36px;

  height:
    36px;

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
}

.ts-icon-button:hover {
  border-color:
    var(--ptt-accent) !important;

  background:
    #174763 !important;

  box-shadow:
    0 0 9px
    var(--ptt-glow) !important;
}


/* ==========================================================
   HOOFDINDELING
   ========================================================== */

.ts-body {
  padding:
    8px !important;
}

.ts-upper {
  align-items:
    stretch;

  gap:
    8px;

  background:
    transparent !important;
}


/* ==========================================================
   BREDE KANALENLIJST
   ========================================================== */

.ts-tree-panel {
  min-width:
    440px !important;

  flex-basis:
    440px;

  background:
    linear-gradient(
      180deg,
      #0b1c2b,
      #071624
    ) !important;

  border:
    1px solid
    var(--ptt-accent-soft) !important;

  border-radius:
    11px !important;

  overflow:
    auto;

  box-shadow:
    0 5px 18px
    rgba(0,0,0,0.32);
}

@media (min-width: 1500px) {
  .ts-tree-panel {
    min-width:
      480px !important;
  }
}


/* ==========================================================
   SERVER RIJ
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
    ) !important;

  border:
    1px solid
    var(--ptt-accent-soft) !important;
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

.ts-tree-search:focus {
  border-color:
    var(--ptt-accent) !important;

  outline:
    none;
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
}

.ts-row:hover {
  background:
    #123751 !important;
}

.ts-row-selected {
  background:
    linear-gradient(
      90deg,
      var(--ptt-accent-dark),
      #102c3e
    ) !important;

  outline:
    1px solid
    var(--ptt-accent) !important;

  box-shadow:
    inset 3px 0 0
    var(--ptt-accent) !important;
}

.ts-channel-row {
  min-height:
    29px !important;

  font-weight:
    600;
}

.ts-client-row {
  min-height:
    29px !important;
}


/* ==========================================================
   PRAATINDICATOR
   ========================================================== */

.ts-talk-lamp-idle {
  background:
    radial-gradient(
      circle at 35% 30%,
      #ff8e8e,
      #ed2828 45%,
      #7d0909
    ) !important;

  box-shadow:
    inset 0 1px 1px
      rgba(255,255,255,0.55),
    0 0 0 1px
      rgba(0,0,0,0.35) !important;
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
    rgba(0,255,100,0.70) !important;
}


/* ==========================================================
   RECHTER PANEEL
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
   TEAMSpeak 3 ACHTIGE BANNER
   ========================================================== */

.ts-banner-panel {
  min-height:
    0 !important;

  height:
    150px !important;

  max-height:
    150px !important;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  padding:
    6px !important;

  margin:
    0 !important;

  border:
    1px solid
    var(--ptt-accent-soft) !important;

  border-radius:
    11px !important;

  overflow:
    hidden;

  background:
    #06121c !important;

  box-shadow:
    0 5px 18px
    rgba(0,0,0,0.32);
}

.ts-server-banner {
  display:
    block;

  width:
    100% !important;

  height:
    100% !important;

  max-width:
    100% !important;

  max-height:
    138px !important;

  object-fit:
    contain !important;

  object-position:
    center center !important;
}

@media (max-height: 800px) {
  .ts-banner-panel {
    height:
      120px !important;

    max-height:
      120px !important;
  }

  .ts-server-banner {
    max-height:
      108px !important;
  }
}


/* ==========================================================
   INFO PANEEL
   ========================================================== */

.ts-info-panel {
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
    var(--ptt-accent-soft) !important;

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
  min-height:
    27px;
}


/* ==========================================================
   CHAT
   ========================================================== */

.ts-chat-panel {
  min-height:
    250px !important;

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
    var(--ptt-accent-soft) !important;

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
    var(--ptt-accent) !important;

  font-weight:
    700;
}


/* ==========================================================
   CHAT TABS
   ========================================================== */

.ts-chat-tabs {
  padding:
    5px 8px !important;

  background:
    #081826 !important;

  border-top:
    1px solid
    #113b58 !important;
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
    var(--ptt-accent) !important;

  border-color:
    var(--ptt-accent-soft) !important;
}


/* ==========================================================
   CHAT INVOER
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
    var(--ptt-accent) !important;

  outline:
    none !important;

  box-shadow:
    0 0 0 2px
    var(--ptt-glow) !important;
}

.ts-chat-input-row button {
  min-width:
    70px;

  border-radius:
    9px !important;

  border:
    1px solid
    var(--ptt-accent) !important;

  background:
    linear-gradient(
      180deg,
      var(--ptt-accent),
      var(--ptt-accent-dark)
    ) !important;

  color:
    white !important;

  font-weight:
    700;
}


/* ==========================================================
   THEMA MENU
   ========================================================== */

.ptt-theme-quick {
  position:
    relative;

  display:
    inline-flex;

  align-items:
    center;
}

.ptt-theme-menu {
  position:
    absolute !important;

  top:
    calc(100% + 5px);

  right:
    0;

  left:
    auto !important;

  min-width:
    220px;

  z-index:
    10020;

  padding:
    7px !important;

  border:
    1px solid
    var(--ptt-accent-soft) !important;

  border-radius:
    10px !important;

  background:
    #081b2a !important;

  box-shadow:
    0 12px 32px
    rgba(0,0,0,0.60) !important;
}

.ptt-theme-menu-title {
  padding:
    7px 10px 9px;

  margin-bottom:
    4px;

  border-bottom:
    1px solid
    rgba(255,255,255,0.10);

  font-weight:
    700;

  color:
    var(--ptt-accent);
}

.ptt-theme-swatch {
  width:
    16px;

  height:
    16px;

  border-radius:
    50%;

  margin-right:
    8px;

  border:
    1px solid
    rgba(255,255,255,0.55);

  box-shadow:
    0 0 5px
    rgba(0,0,0,0.45);

  flex-shrink:
    0;
}

.ptt-theme-menu-active {
  background:
    rgba(255,255,255,0.08) !important;

  font-weight:
    700;
}

.ptt-theme-check {
  margin-left:
    auto;

  padding-left:
    10px;

  color:
    var(--ptt-accent);

  font-weight:
    800;
}


/* ==========================================================
   AUDIO PLAYER SNELMENU
   ========================================================== */

.ptt-stream-quick {
  position:
    relative;

  display:
    inline-flex;

  align-items:
    center;
}

.ptt-stream-quick-menu {
  position:
    absolute !important;

  top:
    calc(100% + 5px);

  right:
    0;

  left:
    auto !important;

  min-width:
    300px !important;

  z-index:
    10000;

  padding:
    7px !important;

  border:
    1px solid
    var(--ptt-accent-soft) !important;

  border-radius:
    10px !important;

  background:
    #081b2a !important;

  box-shadow:
    0 10px 30px
    rgba(0,0,0,0.55) !important;
}

.ptt-stream-quick-title {
  padding:
    8px 12px;

  font-weight:
    700;

  color:
    var(--ptt-accent);
}

.ptt-stream-active {
  border-color:
    var(--ptt-accent) !important;

  box-shadow:
    0 0 10px
    var(--ptt-glow) !important;
}

.ptt-stream-status {
  margin-left:
    auto;

  padding-left:
    12px;

  font-size:
    0.75rem;

  font-weight:
    700;

  color:
    var(--ptt-accent);
}


/* ==========================================================
   PLAYER VENSTER
   ========================================================== */

.ptt-audio-player-dialog {
  width:
    min(
      720px,
      calc(100vw - 50px)
    );

  border:
    1px solid
    var(--ptt-accent-soft) !important;

  border-radius:
    12px !important;

  overflow:
    hidden;

  background:
    #081927 !important;
}

.ptt-audio-player-list {
  display:
    flex;

  flex-direction:
    column;

  gap:
    8px;
}

.ptt-audio-player-row {
  display:
    flex;

  align-items:
    center;

  gap:
    16px;

  padding:
    12px;

  border:
    1px solid
    #164965 !important;

  border-radius:
    9px !important;

  background:
    linear-gradient(
      180deg,
      #10283a,
      #0b1e2e
    ) !important;
}

.ptt-audio-player-row-active {
  border-color:
    var(--ptt-accent) !important;

  box-shadow:
    0 0 10px
    var(--ptt-glow) !important;
}

.ptt-audio-player-info {
  flex:
    1;

  min-width:
    0;

  display:
    flex;

  flex-direction:
    column;

  gap:
    4px;
}

.ptt-audio-player-info span {
  overflow:
    hidden;

  text-overflow:
    ellipsis;

  white-space:
    nowrap;

  font-size:
    0.82rem;

  opacity:
    0.72;
}

.ptt-audio-player-actions {
  display:
    flex;

  gap:
    8px;
}

.ptt-audio-player-note {
  margin-top:
    14px;

  padding:
    10px 12px;

  border:
    1px solid
    rgba(255,255,255,0.10);

  border-radius:
    6px;

  line-height:
    1.6;
}

.ptt-audio-player-error {
  margin-top:
    12px;

  padding:
    10px 12px;

  border:
    1px solid
    rgba(255,90,90,0.55);

  border-radius:
    6px;

  color:
    #ffb0b0;
}


/* ==========================================================
   RESIZE
   ========================================================== */

.ts-resize-handle-vertical {
  width:
    6px !important;
}

.ts-resize-handle-vertical:hover {
  background:
    var(--ptt-accent) !important;
}

.ts-resize-handle-horizontal {
  height:
    6px !important;
}

.ts-resize-handle-horizontal:hover {
  background:
    var(--ptt-accent) !important;
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
    var(--ptt-accent-soft);

  border:
    2px solid
    #06121d;

  border-radius:
    10px;
}

.ts-app ::-webkit-scrollbar-thumb:hover {
  background:
    var(--ptt-accent);
}


/* ==========================================================
   LOG
   ========================================================== */

.ts-log {
  background:
    #06121c !important;

  border-top:
    1px solid
    var(--ptt-accent-soft) !important;

  color:
    #8da9bc !important;
}


/* ==========================================================
   KLEINERE SCHERMEN
   ========================================================== */

@media (max-width: 1150px) {
  .ts-tree-panel {
    min-width:
      380px !important;
  }
}

@media (max-width: 850px) {
  .ts-tree-panel {
    min-width:
      310px !important;
  }

  .ptt-audio-player-row {
    flex-direction:
      column;

    align-items:
      stretch;
  }

  .ptt-audio-player-actions button {
    flex:
      1;
  }
}

'''


if "PTT CONNECT MODERN LOOK" not in css:
    css += ptt_css


CSS_FILE.write_text(
    css,
    encoding="utf-8"
)


print(
    "PTT Connect patch succesvol toegepast"
)

print(
    "- Push-To-Talk behouden"
)

print(
    "- microfoon zendkant niet gewijzigd"
)

print(
    "- TeamSpeak ontvangstaudio behouden"
)

print(
    "- PI2NOS toegevoegd"
)

print(
    "- PI3UTR toegevoegd"
)

print(
    "- PI3GOE toegevoegd"
)

print(
    "- externe HTTPS audiostreams toegestaan"
)

print(
    "- maximaal 1 stream tegelijk"
)

print(
    "- streams starten nooit automatisch"
)

print(
    "- snelknop naast zonnetje"
)

print(
    "- players ook onder Tools"
)

print(
    "- brede kanalenlijst behouden"
)

print(
    "- 6 kleurthema's toegevoegd"
)

print(
    "- blauw groen rood paars oranje roze"
)

print(
    "- kleurkeuze wordt opgeslagen"
)

print(
    "- kleinere TeamSpeak 3 banner"
)

print(
    "- banner volledig passend in beeld"
)
