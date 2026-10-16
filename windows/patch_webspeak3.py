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
# ============================================================
# PTT CONNECT - KANAAL DASHBOARD IN LEGE RUIMTE
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)


# ============================================================
# DASHBOARD COMPONENT
# ============================================================

ptt_dashboard_component = r'''
function PttChannelDashboard({
  channel,
  clients,
  totalClientCount,
  totalChannelCount,
}: {
  channel: ChannelInfo;
  clients: ClientInfo[];
  totalClientCount: number;
  totalChannelCount: number;
}) {
  const channelClients =
    clients.filter(
      (client) =>
        client.channel === channel.id
    );

  return (
    <div className="ptt-channel-dashboard">

      <div className="ptt-dashboard-brand">
        <div className="ptt-dashboard-radio">
          <span className="ptt-dashboard-wave">
            ))) 
          </span>

          <span className="ptt-dashboard-tower">
            📡
          </span>

          <span className="ptt-dashboard-wave">
            (((
          </span>
        </div>

        <div className="ptt-dashboard-brand-text">
          <strong>
            PTT CONNECT
          </strong>

          <span>
            PRAAT • LUISTER • VERBIND
          </span>
        </div>
      </div>


      <div className="ptt-dashboard-grid">

        <section className="ptt-dashboard-card">
          <div className="ptt-dashboard-title">
            ℹ️ Kanaal info
          </div>

          <div className="ptt-dashboard-channel-name">
            {channel.name}
          </div>

          {channel.topic && (
            <div className="ptt-dashboard-description">
              {channel.topic}
            </div>
          )}

          <div className="ptt-dashboard-stats">
            <div>
              <span>
                Type
              </span>

              <strong>
                🔊 Spraakkanaal
              </strong>
            </div>

            <div>
              <span>
                Codec
              </span>

              <strong>
                {channel.codec}
              </strong>
            </div>

            <div>
              <span>
                Wachtwoord
              </span>

              <strong>
                {channel.hasPassword
                  ? "Ja"
                  : "Nee"}
              </strong>
            </div>

            <div>
              <span>
                Gebruikers
              </span>

              <strong>
                {channelClients.length}
                {" / "}
                {channel.maxClients ?? "∞"}
              </strong>
            </div>
          </div>
        </section>


        <section className="ptt-dashboard-card">
          <div className="ptt-dashboard-title">
            👥 Nu actief ({channelClients.length})
          </div>

          <div className="ptt-active-users">
            {channelClients.length === 0 ? (
              <div className="ptt-dashboard-empty">
                Niemand in dit kanaal
              </div>
            ) : (
              channelClients
                .slice(0, 8)
                .map(
                  (client) => (
                    <div
                      key={client.id}
                      className="ptt-active-user"
                    >
                      <span
                        className={
                          "ptt-active-user-dot" +
                          (
                            client.inputMuted ||
                            !client.inputHardwareEnabled
                              ? " ptt-active-user-muted"
                              : ""
                          )
                        }
                      />

                      <div className="ptt-active-user-info">
                        <strong>
                          {client.name}
                        </strong>

                        <span>
                          {client.inputMuted ||
                          !client.inputHardwareEnabled
                            ? "Microfoon gedempt"
                            : "Verbonden"}
                        </span>
                      </div>

                      <span className="ptt-active-user-signal">
                        ▂▄▆
                      </span>
                    </div>
                  )
                )
            )}

            {channelClients.length > 8 && (
              <div className="ptt-dashboard-more">
                + {channelClients.length - 8}
                {" meer"}
              </div>
            )}
          </div>
        </section>


        <section className="ptt-dashboard-card">
          <div className="ptt-dashboard-title">
            📊 Server status
          </div>

          <div className="ptt-dashboard-server-online">
            <span className="ptt-online-dot" />

            Online
          </div>

          <div className="ptt-dashboard-stats">
            <div>
              <span>
                Clients totaal
              </span>

              <strong>
                {totalClientCount}
              </strong>
            </div>

            <div>
              <span>
                Kanalen
              </span>

              <strong>
                {totalChannelCount}
              </strong>
            </div>

            <div>
              <span>
                Huidig kanaal
              </span>

              <strong>
                {channelClients.length}
              </strong>
            </div>

            <div>
              <span>
                Audio
              </span>

              <strong>
                {channel.codec}
              </strong>
            </div>
          </div>
        </section>


        <section className="ptt-dashboard-card ptt-dashboard-help">
          <div className="ptt-dashboard-title">
            🎙️ PTT Connect
          </div>

          <div className="ptt-dashboard-big-status">
            <span>
              ●
            </span>

            Klaar voor communicatie
          </div>

          <p>
            Kies je kanaal links en gebruik
            jouw ingestelde Push-To-Talk toets
            om te spreken.
          </p>

          <div className="ptt-dashboard-mini-features">
            <span>
              🎙 PTT
            </span>

            <span>
              📻 Streams
            </span>

            <span>
              🎨 Thema
            </span>
          </div>
        </section>

      </div>


      <div className="ptt-dashboard-tips">
        <div className="ptt-dashboard-title">
          💡 PTT Connect tips
        </div>

        <div className="ptt-dashboard-tip-grid">
          <span>
            • Houd je PTT-toets ingedrukt terwijl je spreekt.
          </span>

          <span>
            • Luister eerst voordat je begint met praten.
          </span>

          <span>
            • Gebruik een headset voor de beste audio.
          </span>

          <span>
            • Kies bovenaan je favoriete kleurthema.
          </span>
        </div>
      </div>

    </div>
  );
}

'''


app = replace_once(
    app,
    '''function InfoPanel({
''',
    ptt_dashboard_component +
    '''function InfoPanel({
''',
    "PTT Connect channel dashboard component"
)


# ============================================================
# DASHBOARD ONDER KANAALINFORMATIE TONEN
# ============================================================

app = replace_once(
    app,
    '''      <div className="ts-info-row">
        <span>{t("info.clients")}</span> <span>{clientCount} / {channel.maxClients ?? "∞"}</span>
      </div>
    </div>
  );
}
''',
    '''      <div className="ts-info-row">
        <span>{t("info.clients")}</span> <span>{clientCount} / {channel.maxClients ?? "∞"}</span>
      </div>

      <PttChannelDashboard
        channel={channel}
        clients={clients}
        totalClientCount={totalClientCount}
        totalChannelCount={totalChannelCount}
      />
    </div>
  );
}
''',
    "show PTT Connect dashboard in empty channel space"
)


APP_FILE.write_text(
    app,
    encoding="utf-8"
)


# ============================================================
# DASHBOARD CSS
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)


dashboard_css = r'''

/* ==========================================================
   PTT CONNECT KANAAL DASHBOARD
   ========================================================== */

.ts-side-panel {
  overflow:
    auto;
}


.ptt-channel-dashboard {
  display:
    flex;

  flex-direction:
    column;

  gap:
    10px;

  margin-top:
    16px;

  padding-top:
    14px;

  border-top:
    1px solid
    var(--ptt-accent-soft);
}


/* ==========================================================
   PTT CONNECT LOGO / HEADER
   ========================================================== */

.ptt-dashboard-brand {
  min-height:
    92px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  gap:
    18px;

  padding:
    14px 20px;

  border:
    1px solid
    var(--ptt-accent-soft);

  border-radius:
    12px;

  background:
    radial-gradient(
      circle at 50% 50%,
      color-mix(
        in srgb,
        var(--ptt-accent) 12%,
        #081724
      ),
      #06131f 70%
    );

  box-shadow:
    inset 0 0 30px
    rgba(0,0,0,0.25);
}


.ptt-dashboard-radio {
  display:
    flex;

  align-items:
    center;

  gap:
    5px;

  color:
    var(--ptt-accent);
}


.ptt-dashboard-tower {
  font-size:
    34px;

  filter:
    drop-shadow(
      0 0 8px
      var(--ptt-glow)
    );
}


.ptt-dashboard-wave {
  font-size:
    18px;

  font-weight:
    800;

  color:
    var(--ptt-accent);
}


.ptt-dashboard-brand-text {
  display:
    flex;

  flex-direction:
    column;

  line-height:
    1.1;
}


.ptt-dashboard-brand-text strong {
  font-size:
    24px;

  letter-spacing:
    1px;

  color:
    var(--ptt-accent);

  text-shadow:
    0 0 12px
    var(--ptt-glow);
}


.ptt-dashboard-brand-text span {
  margin-top:
    5px;

  font-size:
    10px;

  letter-spacing:
    1.4px;

  color:
    #a7c1d3;
}


/* ==========================================================
   DASHBOARD GRID
   ========================================================== */

.ptt-dashboard-grid {
  display:
    grid;

  grid-template-columns:
    repeat(
      2,
      minmax(0, 1fr)
    );

  gap:
    10px;
}


.ptt-dashboard-card {
  min-width:
    0;

  padding:
    13px 14px;

  border:
    1px solid
    var(--ptt-accent-soft);

  border-radius:
    11px;

  background:
    linear-gradient(
      180deg,
      rgba(15,42,62,0.96),
      rgba(6,20,31,0.96)
    );

  box-shadow:
    0 4px 14px
    rgba(0,0,0,0.22);
}


.ptt-dashboard-title {
  margin-bottom:
    10px;

  padding-bottom:
    7px;

  border-bottom:
    1px solid
    rgba(255,255,255,0.10);

  font-size:
    14px;

  font-weight:
    800;

  color:
    var(--ptt-accent);
}


/* ==========================================================
   KANAAL INFO
   ========================================================== */

.ptt-dashboard-channel-name {
  margin-bottom:
    6px;

  font-size:
    16px;

  font-weight:
    800;

  color:
    #f1f8fc;
}


.ptt-dashboard-description {
  margin-bottom:
    12px;

  color:
    #9fb8ca;

  font-size:
    12px;

  line-height:
    1.45;
}


.ptt-dashboard-stats {
  display:
    flex;

  flex-direction:
    column;

  gap:
    6px;
}


.ptt-dashboard-stats > div {
  display:
    flex;

  align-items:
    center;

  justify-content:
    space-between;

  gap:
    12px;

  min-height:
    23px;

  padding:
    3px 0;

  border-bottom:
    1px solid
    rgba(255,255,255,0.055);
}


.ptt-dashboard-stats > div:last-child {
  border-bottom:
    none;
}


.ptt-dashboard-stats span {
  color:
    #8faabd;

  font-size:
    12px;
}


.ptt-dashboard-stats strong {
  max-width:
    60%;

  overflow:
    hidden;

  text-overflow:
    ellipsis;

  white-space:
    nowrap;

  color:
    #eaf5fc;

  font-size:
    12px;

  text-align:
    right;
}


/* ==========================================================
   ACTIEVE GEBRUIKERS
   ========================================================== */

.ptt-active-users {
  display:
    flex;

  flex-direction:
    column;

  gap:
    4px;
}


.ptt-active-user {
  display:
    flex;

  align-items:
    center;

  gap:
    9px;

  min-height:
    39px;

  padding:
    5px 7px;

  border-radius:
    8px;
}


.ptt-active-user:hover {
  background:
    rgba(255,255,255,0.045);
}


.ptt-active-user-dot {
  width:
    12px;

  height:
    12px;

  flex:
    0 0 auto;

  border-radius:
    50%;

  background:
    #2bdd6f;

  box-shadow:
    0 0 8px
    rgba(43,221,111,0.55);
}


.ptt-active-user-muted {
  background:
    #ef7d45;

  box-shadow:
    0 0 7px
    rgba(239,125,69,0.45);
}


.ptt-active-user-info {
  flex:
    1;

  min-width:
    0;

  display:
    flex;

  flex-direction:
    column;
}


.ptt-active-user-info strong {
  overflow:
    hidden;

  text-overflow:
    ellipsis;

  white-space:
    nowrap;

  color:
    #edf7fd;

  font-size:
    12px;
}


.ptt-active-user-info span {
  margin-top:
    2px;

  color:
    #7f9caf;

  font-size:
    10px;
}


.ptt-active-user-signal {
  color:
    var(--ptt-accent);

  font-size:
    13px;

  letter-spacing:
    -2px;
}


.ptt-dashboard-empty,
.ptt-dashboard-more {
  padding:
    10px;

  text-align:
    center;

  color:
    #7e9bae;

  font-size:
    11px;
}


/* ==========================================================
   SERVER STATUS
   ========================================================== */

.ptt-dashboard-server-online {
  display:
    inline-flex;

  align-items:
    center;

  gap:
    7px;

  margin-bottom:
    9px;

  padding:
    5px 9px;

  border-radius:
    999px;

  background:
    rgba(30,180,90,0.12);

  color:
    #61e68c;

  font-size:
    11px;

  font-weight:
    700;
}


.ptt-online-dot {
  width:
    9px;

  height:
    9px;

  border-radius:
    50%;

  background:
    #34dc70;

  box-shadow:
    0 0 8px
    rgba(52,220,112,0.75);
}


/* ==========================================================
   PTT STATUS
   ========================================================== */

.ptt-dashboard-big-status {
  display:
    flex;

  align-items:
    center;

  gap:
    8px;

  margin-bottom:
    9px;

  color:
    #5ae788;

  font-weight:
    800;
}


.ptt-dashboard-big-status span {
  color:
    #32dc72;

  text-shadow:
    0 0 8px
    rgba(50,220,114,0.75);
}


.ptt-dashboard-help p {
  margin:
    0 0 12px;

  color:
    #9eb6c7;

  font-size:
    12px;

  line-height:
    1.45;
}


.ptt-dashboard-mini-features {
  display:
    flex;

  flex-wrap:
    wrap;

  gap:
    6px;
}


.ptt-dashboard-mini-features span {
  padding:
    5px 8px;

  border:
    1px solid
    var(--ptt-accent-soft);

  border-radius:
    7px;

  background:
    rgba(255,255,255,0.035);

  color:
    #dceaf3;

  font-size:
    10px;
}


/* ==========================================================
   TIPS ONDERAAN
   ========================================================== */

.ptt-dashboard-tips {
  padding:
    11px 14px;

  border:
    1px solid
    var(--ptt-accent-soft);

  border-radius:
    11px;

  background:
    linear-gradient(
      90deg,
      rgba(15,42,62,0.92),
      rgba(6,20,31,0.95)
    );
}


.ptt-dashboard-tips .ptt-dashboard-title {
  margin-bottom:
    7px;
}


.ptt-dashboard-tip-grid {
  display:
    grid;

  grid-template-columns:
    repeat(
      2,
      minmax(0, 1fr)
    );

  gap:
    4px 20px;

  color:
    #9eb7c8;

  font-size:
    10px;

  line-height:
    1.35;
}


/* ==========================================================
   RESPONSIVE
   ========================================================== */

@media (max-width: 1250px) {

  .ptt-dashboard-grid {
    grid-template-columns:
      1fr;
  }


  .ptt-dashboard-tip-grid {
    grid-template-columns:
      1fr;
  }


  .ptt-dashboard-brand {
    min-height:
      75px;
  }


  .ptt-dashboard-brand-text strong {
    font-size:
      19px;
  }

}

'''


if "PTT CONNECT KANAAL DASHBOARD" not in css:
    css += dashboard_css


CSS_FILE.write_text(
    css,
    encoding="utf-8"
)


print(
    "- PTT Connect dashboard toegevoegd"
)

print(
    "- lege ruimte rechts wordt benut"
)

print(
    "- kanaalinformatie toegevoegd"
)

print(
    "- gebruikers in huidig kanaal toegevoegd"
)

print(
    "- serverstatus toegevoegd"
)

print(
    "- PTT Connect tips toegevoegd"
)

print(
    "- bestaande PTT en audio niet gewijzigd"
)
# ============================================================
# PTT CONNECT - LIVE SPREKER BIJ "NU ACTIEF"
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)


# ============================================================
# TALKERS DOORGEVEN AAN DASHBOARD
# ============================================================

app = replace_once(
    app,
    '''function PttChannelDashboard({
  channel,
  clients,
  totalClientCount,
  totalChannelCount,
}: {
  channel: ChannelInfo;
  clients: ClientInfo[];
  totalClientCount: number;
  totalChannelCount: number;
}) {
  const channelClients =
    clients.filter(
      (client) =>
        client.channel === channel.id
    );
''',
    '''function PttChannelDashboard({
  channel,
  clients,
  totalClientCount,
  totalChannelCount,
  talkers,
}: {
  channel: ChannelInfo;
  clients: ClientInfo[];
  totalClientCount: number;
  totalChannelCount: number;
  talkers: Set<number>;
}) {
  const channelClients =
    clients
      .filter(
        (client) =>
          client.channel === channel.id
      )
      .sort(
        (a, b) => {
          const aTalking =
            talkers.has(a.id)
              ? 1
              : 0;

          const bTalking =
            talkers.has(b.id)
              ? 1
              : 0;

          return (
            bTalking -
            aTalking
          );
        }
      );
''',
    "dashboard live talkers"
)


# ============================================================
# ACTIEVE GEBRUIKER LATEN OPLICHTEN
# ============================================================

app = replace_once(
    app,
    '''                    <div
                      key={client.id}
                      className="ptt-active-user"
                    >
                      <span
                        className={
                          "ptt-active-user-dot" +
                          (
                            client.inputMuted ||
                            !client.inputHardwareEnabled
                              ? " ptt-active-user-muted"
                              : ""
                          )
                        }
                      />

                      <div className="ptt-active-user-info">
                        <strong>
                          {client.name}
                        </strong>

                        <span>
                          {client.inputMuted ||
                          !client.inputHardwareEnabled
                            ? "Microfoon gedempt"
                            : "Verbonden"}
                        </span>
                      </div>

                      <span className="ptt-active-user-signal">
                        ▂▄▆
                      </span>
                    </div>
''',
    '''                    <div
                      key={client.id}
                      className={
                        "ptt-active-user" +
                        (
                          talkers.has(client.id)
                            ? " ptt-active-user-talking"
                            : ""
                        )
                      }
                    >
                      <span
                        className={
                          "ptt-active-user-dot" +
                          (
                            talkers.has(client.id)
                              ? " ptt-active-user-dot-talking"
                              : client.inputMuted ||
                                !client.inputHardwareEnabled
                                ? " ptt-active-user-muted"
                                : ""
                          )
                        }
                      />

                      <div className="ptt-active-user-info">
                        <strong>
                          {client.name}
                        </strong>

                        <span
                          className={
                            talkers.has(client.id)
                              ? "ptt-speaking-now-text"
                              : ""
                          }
                        >
                          {talkers.has(client.id)
                            ? "🎙 SPREEKT NU"
                            : client.inputMuted ||
                              !client.inputHardwareEnabled
                              ? "Microfoon gedempt"
                              : "Verbonden"}
                        </span>
                      </div>

                      <span
                        className={
                          "ptt-active-user-signal" +
                          (
                            talkers.has(client.id)
                              ? " ptt-active-user-signal-talking"
                              : ""
                          )
                        }
                      >
                        ▂▄▆
                      </span>
                    </div>
''',
    "live speaker highlight"
)


# ============================================================
# TALKERS PROP BIJ DASHBOARD
# ============================================================

app = replace_once(
    app,
    '''      <PttChannelDashboard
        channel={channel}
        clients={clients}
        totalClientCount={totalClientCount}
        totalChannelCount={totalChannelCount}
      />
''',
    '''      <PttChannelDashboard
        channel={channel}
        clients={clients}
        totalClientCount={totalClientCount}
        totalChannelCount={totalChannelCount}
        talkers={talkers}
      />
''',
    "dashboard talkers prop"
)


# ============================================================
# INFOPANEL TALKERS ARGUMENT
# ============================================================

app = replace_once(
    app,
    '''  serverGroups,
  images,
  onShowServerConnectionInfo,
''',
    '''  serverGroups,
  images,
  talkers,
  onShowServerConnectionInfo,
''',
    "InfoPanel talkers argument"
)


app = replace_once(
    app,
    '''  serverGroups: GroupEntry[] | null;
  images: Record<string, string>;
  onShowServerConnectionInfo: () => void;
''',
    '''  serverGroups: GroupEntry[] | null;
  images: Record<string, string>;
  talkers: Set<number>;
  onShowServerConnectionInfo: () => void;
''',
    "InfoPanel talkers type"
)


# ============================================================
# LIVE TALKERS VAN APP NAAR INFOPANEL
# ============================================================

app = replace_once(
    app,
    '''                serverGroups={serverGroups}
                images={serverIconImages}
                onShowServerConnectionInfo={handleShowServerConnectionInfo}
''',
    '''                serverGroups={serverGroups}
                images={serverIconImages}
                talkers={displayTalkers}
                onShowServerConnectionInfo={handleShowServerConnectionInfo}
''',
    "pass live talkers to InfoPanel"
)


APP_FILE.write_text(
    app,
    encoding="utf-8"
)


# ============================================================
# LIVE SPREKER CSS
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)


live_speaker_css = r'''

/* ==========================================================
   PTT CONNECT - LIVE SPREKER BIJ NU ACTIEF
   ========================================================== */

.ptt-active-user {
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.15s ease;
}


/* ==========================================================
   DEGENE DIE PRAAT
   ========================================================== */

.ptt-active-user-talking {
  position:
    relative;

  background:
    linear-gradient(
      90deg,
      rgba(24, 155, 82, 0.28),
      rgba(10, 70, 45, 0.16)
    ) !important;

  border:
    1px solid
    rgba(56, 235, 118, 0.75);

  box-shadow:
    0 0 13px
    rgba(45, 230, 110, 0.28),
    inset 3px 0 0
    #39ed78;

  transform:
    translateX(2px);
}


/* groene praatbol */

.ptt-active-user-dot-talking {
  background:
    #35ef78 !important;

  box-shadow:
    0 0 5px
    #35ef78,
    0 0 12px
    rgba(53,239,120,0.85) !important;

  animation:
    pttSpeakerDotPulse
    0.75s
    ease-in-out
    infinite alternate;
}


/* ==========================================================
   SPREEKT NU TEKST
   ========================================================== */

.ptt-speaking-now-text {
  color:
    #52f18b !important;

  font-weight:
    800 !important;

  letter-spacing:
    0.4px;

  text-shadow:
    0 0 7px
    rgba(75,245,135,0.42);
}


/* ==========================================================
   SIGNAAL BALKJES
   ========================================================== */

.ptt-active-user-signal-talking {
  color:
    #4df087 !important;

  font-size:
    15px !important;

  text-shadow:
    0 0 8px
    rgba(77,240,135,0.75);

  animation:
    pttSpeakerBars
    0.40s
    ease-in-out
    infinite alternate;
}


/* ==========================================================
   ANIMATIES
   ========================================================== */

@keyframes pttSpeakerDotPulse {

  from {
    transform:
      scale(0.90);

    opacity:
      0.78;
  }

  to {
    transform:
      scale(1.18);

    opacity:
      1;
  }

}


@keyframes pttSpeakerBars {

  from {
    transform:
      scaleY(0.72);

    opacity:
      0.65;
  }

  to {
    transform:
      scaleY(1.20);

    opacity:
      1;
  }

}

'''


if "PTT CONNECT - LIVE SPREKER BIJ NU ACTIEF" not in css:
    css += live_speaker_css


CSS_FILE.write_text(
    css,
    encoding="utf-8"
)


print(
    "- live spreker bij Nu actief toegevoegd"
)

print(
    "- huidige spreker komt automatisch bovenaan"
)

print(
    "- naam krijgt SPREEKT NU"
)

print(
    "- groene praatindicator toegevoegd"
)

print(
    "- bewegende signaalindicator toegevoegd"
)

print(
    "- wisselt automatisch zodra iemand anders praat"
)

print(
    "- PTT microfoon en audio niet gewijzigd"
)
# ============================================================
# PTT CONNECT - SPREKER KLEUR VAN GROEN NAAR BLAUW/CYAAN
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)


speaker_color_override_css = r'''

/* ==========================================================
   PTT CONNECT - BLAUWE SPREKER HIGHLIGHT
   ========================================================== */

.ptt-active-user-talking {
  position:
    relative;

  background:
    linear-gradient(
      90deg,
      rgba(40, 190, 255, 0.24),
      rgba(10, 70, 120, 0.14)
    ) !important;

  border:
    1px solid
    rgba(80, 220, 255, 0.78) !important;

  box-shadow:
    0 0 13px
    rgba(60, 210, 255, 0.22),
    inset 3px 0 0
    #56dfff !important;

  transform:
    translateX(2px);
}


/* blauwe praatbol */

.ptt-active-user-dot-talking {
  background:
    #59dcff !important;

  box-shadow:
    0 0 5px
    #59dcff,
    0 0 12px
    rgba(89,220,255,0.82) !important;

  animation:
    pttSpeakerDotPulse
    0.75s
    ease-in-out
    infinite alternate;
}


/* SPREEKT NU tekst blauw */

.ptt-speaking-now-text {
  color:
    #74e6ff !important;

  font-weight:
    800 !important;

  letter-spacing:
    0.4px;

  text-shadow:
    0 0 7px
    rgba(116,230,255,0.38) !important;
}


/* signaalbalkjes rechts blauw */

.ptt-active-user-signal-talking {
  color:
    #63e2ff !important;

  font-size:
    15px !important;

  text-shadow:
    0 0 8px
    rgba(99,226,255,0.68) !important;

  animation:
    pttSpeakerBars
    0.40s
    ease-in-out
    infinite alternate;
}

'''


if "PTT CONNECT - BLAUWE SPREKER HIGHLIGHT" not in css:
    css += speaker_color_override_css


CSS_FILE.write_text(
    css,
    encoding="utf-8"
)


print(
    "- spreker highlight veranderd van groen naar blauw/cyaan"
)

print(
    "- SPREEKT NU kleur aangepast"
)

print(
    "- praatbol aangepast"
)

print(
    "- signaalbalkjes aangepast"
)
# ============================================================
# PTT CONNECT - EIGEN KLEUR + PRESETS
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)


# ============================================================
# OPSLAG VOOR EIGEN KLEUREN
# ============================================================

app = replace_once(
    app,
    '''const PTT_COLOR_THEME_KEY =
  "pttconnect:color-theme";
''',
    '''const PTT_COLOR_THEME_KEY =
  "pttconnect:color-theme";

const PTT_CUSTOM_COLOR_KEY =
  "pttconnect:custom-color";

const PTT_CUSTOM_COLOR_ACTIVE_KEY =
  "pttconnect:custom-color-active";

const PTT_CUSTOM_PRESETS_KEY =
  "pttconnect:custom-color-presets";
''',
    "custom color storage keys"
)


# ============================================================
# PRESET TYPE + LADEN
# ============================================================

app = replace_once(
    app,
    '''const PTT_AUDIO_STREAMS = [
''',
    '''interface PttCustomColorPreset {
  id: string;
  name: string;
  color: string;
}

function loadPttCustomColor(): string {
  const saved =
    localStorage.getItem(
      PTT_CUSTOM_COLOR_KEY
    );

  if (
    saved &&
    /^#[0-9a-fA-F]{6}$/.test(saved)
  ) {
    return saved;
  }

  return "#18aaff";
}

function loadPttCustomColorActive(): boolean {
  return (
    localStorage.getItem(
      PTT_CUSTOM_COLOR_ACTIVE_KEY
    ) === "1"
  );
}

function loadPttCustomPresets():
  PttCustomColorPreset[] {
  try {
    const raw =
      localStorage.getItem(
        PTT_CUSTOM_PRESETS_KEY
      );

    if (!raw) {
      return [];
    }

    const parsed =
      JSON.parse(raw);

    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed
      .filter(
        (item) =>
          item &&
          typeof item.id === "string" &&
          typeof item.name === "string" &&
          typeof item.color === "string" &&
          /^#[0-9a-fA-F]{6}$/.test(
            item.color
          )
      )
      .slice(0, 12);
  } catch {
    return [];
  }
}

const PTT_AUDIO_STREAMS = [
''',
    "custom color preset loaders"
)


# ============================================================
# STATE
# ============================================================

app = replace_once(
    app,
    '''  const [
    pttThemeMenuOpen,
    setPttThemeMenuOpen
  ] = useState(false);
''',
    '''  const [
    pttThemeMenuOpen,
    setPttThemeMenuOpen
  ] = useState(false);

  const [
    pttCustomColor,
    setPttCustomColor
  ] = useState(
    loadPttCustomColor
  );

  const [
    pttCustomColorActive,
    setPttCustomColorActive
  ] = useState(
    loadPttCustomColorActive
  );

  const [
    pttCustomPresets,
    setPttCustomPresets
  ] = useState<PttCustomColorPreset[]>(
    loadPttCustomPresets
  );
''',
    "custom color state"
)


# ============================================================
# EIGEN KLEUR OPSLAAN EN TOEPASSEN
# ============================================================

app = replace_once(
    app,
    '''  const stopPttAudioStream = () => {
''',
    '''  useEffect(() => {
    document.documentElement.style.setProperty(
      "--ptt-custom-accent",
      pttCustomColor
    );

    localStorage.setItem(
      PTT_CUSTOM_COLOR_KEY,
      pttCustomColor
    );
  }, [
    pttCustomColor
  ]);

  useEffect(() => {
    localStorage.setItem(
      PTT_CUSTOM_COLOR_ACTIVE_KEY,
      pttCustomColorActive
        ? "1"
        : "0"
    );
  }, [
    pttCustomColorActive
  ]);

  const savePttCustomPreset = () => {
    const enteredName =
      window.prompt(
        "Naam voor deze kleur:",
        "Mijn kleur"
      );

    const name =
      enteredName?.trim();

    if (!name) {
      return;
    }

    const preset:
      PttCustomColorPreset = {
        id:
          String(Date.now()),

        name:
          name.slice(0, 30),

        color:
          pttCustomColor,
      };

    const next =
      [
        ...pttCustomPresets,
        preset
      ].slice(-12);

    setPttCustomPresets(
      next
    );

    localStorage.setItem(
      PTT_CUSTOM_PRESETS_KEY,
      JSON.stringify(next)
    );

    setPttCustomColorActive(
      true
    );
  };

  const deletePttCustomPreset = (
    id: string
  ) => {
    const next =
      pttCustomPresets.filter(
        (preset) =>
          preset.id !== id
      );

    setPttCustomPresets(
      next
    );

    localStorage.setItem(
      PTT_CUSTOM_PRESETS_KEY,
      JSON.stringify(next)
    );
  };

  const stopPttAudioStream = () => {
''',
    "custom color handlers"
)


# ============================================================
# CUSTOM CLASS OP APP
# ============================================================

app = replace_once(
    app,
    '''}${novaSplash ? " ts-nova-splash" : ""} ts-ptt-color-${pttColorTheme}`}
''',
    '''}${novaSplash ? " ts-nova-splash" : ""} ts-ptt-color-${pttColorTheme}${
        pttCustomColorActive
          ? " ptt-custom-color"
          : ""
      }`}
''',
    "custom color app class"
)


# ============================================================
# VASTE KLEUR UITSCHAKELEN ALS EIGEN KLEUR ACTIEF IS
# ============================================================

app = replace_once(
    app,
    '''                    const active =
                      pttColorTheme ===
                      colorTheme.id;
''',
    '''                    const active =
                      !pttCustomColorActive &&
                      pttColorTheme ===
                      colorTheme.id;
''',
    "fixed theme active state"
)


# ============================================================
# BIJ VASTE KLEUR EIGEN KLEUR UITSCHAKELEN
# ============================================================

app = replace_once(
    app,
    '''                          setPttColorTheme(
                            colorTheme.id
                          );

                          localStorage.setItem(
''',
    '''                          setPttColorTheme(
                            colorTheme.id
                          );

                          setPttCustomColorActive(
                            false
                          );

                          localStorage.setItem(
''',
    "disable custom color when fixed theme selected"
)


# ============================================================
# EIGEN KLEUR MENU TOEVOEGEN
# ============================================================

app = replace_once(
    app,
    '''                )}

                <div className="ts-menu-separator" />

                <button
                  type="button"
                  className="ts-menu-item"
                  onClick={() => {
                    setTheme(
''',
    '''                )}

                <div className="ts-menu-separator" />

                <div className="ptt-custom-color-section">

                  <div className="ptt-custom-color-title">
                    🎨 Eigen kleur
                  </div>

                  <div className="ptt-custom-color-picker-row">

                    <input
                      type="color"
                      className="ptt-custom-color-picker"
                      value={pttCustomColor}
                      onChange={(event) => {
                        const color =
                          event.target.value;

                        setPttCustomColor(
                          color
                        );

                        setPttCustomColorActive(
                          true
                        );
                      }}
                      title="Kies eigen kleur"
                    />

                    <button
                      type="button"
                      className={
                        "ptt-custom-color-use" +
                        (
                          pttCustomColorActive
                            ? " ptt-custom-color-use-active"
                            : ""
                        )
                      }
                      onClick={() =>
                        setPttCustomColorActive(
                          true
                        )
                      }
                    >
                      <span
                        className="ptt-custom-color-preview"
                        style={{
                          background:
                            pttCustomColor
                        }}
                      />

                      {pttCustomColorActive
                        ? "Eigen kleur actief"
                        : "Gebruik eigen kleur"}
                    </button>

                  </div>


                  <button
                    type="button"
                    className="ptt-custom-save-button"
                    onClick={
                      savePttCustomPreset
                    }
                  >
                    ＋ Opslaan als preset
                  </button>


                  {pttCustomPresets.length > 0 && (
                    <div className="ptt-custom-presets">

                      <div className="ptt-custom-presets-title">
                        Mijn presets
                      </div>

                      {pttCustomPresets.map(
                        (preset) => (
                          <div
                            key={preset.id}
                            className="ptt-custom-preset-row"
                          >

                            <button
                              type="button"
                              className="ptt-custom-preset-select"
                              onClick={() => {
                                setPttCustomColor(
                                  preset.color
                                );

                                setPttCustomColorActive(
                                  true
                                );
                              }}
                            >
                              <span
                                className="ptt-theme-swatch"
                                style={{
                                  background:
                                    preset.color
                                }}
                              />

                              <span>
                                {preset.name}
                              </span>
                            </button>


                            <button
                              type="button"
                              className="ptt-custom-preset-delete"
                              title="Preset verwijderen"
                              onClick={() =>
                                deletePttCustomPreset(
                                  preset.id
                                )
                              }
                            >
                              ✕
                            </button>

                          </div>
                        )
                      )}

                    </div>
                  )}

                </div>


                <div className="ts-menu-separator" />

                <button
                  type="button"
                  className="ts-menu-item"
                  onClick={() => {
                    setTheme(
''',
    "custom color theme menu"
)


APP_FILE.write_text(
    app,
    encoding="utf-8"
)


# ============================================================
# CSS EIGEN KLEUR
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)


custom_color_css = r'''

/* ==========================================================
   PTT CONNECT - EIGEN KLEUR
   ========================================================== */

.ts-app.ptt-custom-color {
  --ptt-accent:
    var(
      --ptt-custom-accent,
      #18aaff
    );

  --ptt-accent-soft:
    color-mix(
      in srgb,
      var(
        --ptt-custom-accent,
        #18aaff
      ) 55%,
      #071421
    );

  --ptt-accent-dark:
    color-mix(
      in srgb,
      var(
        --ptt-custom-accent,
        #18aaff
      ) 36%,
      #03101a
    );

  --ptt-glow:
    color-mix(
      in srgb,
      var(
        --ptt-custom-accent,
        #18aaff
      ) 38%,
      transparent
    );
}


/* ==========================================================
   THEMA MENU IETS BREDER
   ========================================================== */

.ptt-theme-menu {
  min-width:
    270px !important;

  max-height:
    calc(100vh - 120px);

  overflow-y:
    auto;
}


/* ==========================================================
   EIGEN KLEUR GEDEELTE
   ========================================================== */

.ptt-custom-color-section {
  padding:
    6px 8px 8px;
}


.ptt-custom-color-title {
  margin-bottom:
    7px;

  color:
    var(--ptt-accent);

  font-size:
    12px;

  font-weight:
    800;
}


.ptt-custom-color-picker-row {
  display:
    flex;

  align-items:
    center;

  gap:
    7px;
}


.ptt-custom-color-picker {
  width:
    42px;

  height:
    34px;

  padding:
    2px;

  border:
    1px solid
    var(--ptt-accent-soft);

  border-radius:
    7px;

  background:
    #071521;

  cursor:
    pointer;
}


.ptt-custom-color-use {
  flex:
    1;

  min-height:
    34px;

  display:
    flex;

  align-items:
    center;

  gap:
    8px;

  padding:
    5px 8px;

  border:
    1px solid
    #21445a;

  border-radius:
    7px;

  background:
    #0b1e2c;

  color:
    #dceaf3;

  cursor:
    pointer;
}


.ptt-custom-color-use:hover {
  border-color:
    var(--ptt-accent);
}


.ptt-custom-color-use-active {
  border-color:
    var(--ptt-accent);

  box-shadow:
    0 0 8px
    var(--ptt-glow);
}


.ptt-custom-color-preview {
  width:
    15px;

  height:
    15px;

  flex:
    0 0 auto;

  border-radius:
    50%;

  border:
    1px solid
    rgba(255,255,255,0.65);
}


/* ==========================================================
   OPSLAAN
   ========================================================== */

.ptt-custom-save-button {
  width:
    100%;

  margin-top:
    7px;

  padding:
    7px 9px;

  border:
    1px solid
    var(--ptt-accent-soft);

  border-radius:
    7px;

  background:
    rgba(255,255,255,0.035);

  color:
    #dceaf3;

  cursor:
    pointer;
}


.ptt-custom-save-button:hover {
  border-color:
    var(--ptt-accent);

  color:
    #ffffff;
}


/* ==========================================================
   PRESETS
   ========================================================== */

.ptt-custom-presets {
  margin-top:
    9px;

  padding-top:
    7px;

  border-top:
    1px solid
    rgba(255,255,255,0.08);
}


.ptt-custom-presets-title {
  margin-bottom:
    5px;

  color:
    #809caf;

  font-size:
    10px;

  font-weight:
    700;

  text-transform:
    uppercase;

  letter-spacing:
    0.6px;
}


.ptt-custom-preset-row {
  display:
    flex;

  align-items:
    center;

  gap:
    4px;

  margin:
    2px 0;
}


.ptt-custom-preset-select {
  flex:
    1;

  min-width:
    0;

  display:
    flex;

  align-items:
    center;

  gap:
    2px;

  padding:
    6px 7px;

  border:
    1px solid
    transparent;

  border-radius:
    6px;

  background:
    transparent;

  color:
    #dceaf3;

  text-align:
    left;

  cursor:
    pointer;
}


.ptt-custom-preset-select:hover {
  border-color:
    var(--ptt-accent-soft);

  background:
    rgba(255,255,255,0.045);
}


.ptt-custom-preset-select > span:last-child {
  overflow:
    hidden;

  text-overflow:
    ellipsis;

  white-space:
    nowrap;
}


.ptt-custom-preset-delete {
  width:
    28px;

  height:
    28px;

  padding:
    0;

  border:
    1px solid
    transparent;

  border-radius:
    6px;

  background:
    transparent;

  color:
    #7995a7;

  cursor:
    pointer;
}


.ptt-custom-preset-delete:hover {
  border-color:
    #a4424c;

  background:
    rgba(190,50,65,0.14);

  color:
    #ff7b86;
}

'''


if "PTT CONNECT - EIGEN KLEUR" not in css:
    css += custom_color_css


CSS_FILE.write_text(
    css,
    encoding="utf-8"
)


print(
    "- eigen kleurkiezer toegevoegd"
)

print(
    "- gekozen eigen kleur wordt onthouden"
)

print(
    "- eigen kleuren kunnen als preset worden opgeslagen"
)

print(
    "- maximaal 12 eigen presets"
)

print(
    "- presets kunnen verwijderd worden"
)

print(
    "- vaste kleuren blijven bestaan"
)

print(
    "- PTT microfoon TeamSpeak audio en streams niet gewijzigd"
)# ============================================================
# PTT CONNECT - SLIM AUTOMATISCH CONTRAST
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)


# ============================================================
# HULPFUNCTIES VOOR LICHT/DONKER KLEUR
# ============================================================

app = replace_once(
    app,
    '''function loadPttCustomColor(): string {
''',
    '''function hexToRgb(
  hex: string
): {
  r: number;
  g: number;
  b: number;
} | null {
  const match =
    /^#([0-9a-fA-F]{6})$/.exec(
      hex
    );

  if (!match) {
    return null;
  }

  const value =
    match[1];

  return {
    r:
      parseInt(
        value.slice(0, 2),
        16
      ),

    g:
      parseInt(
        value.slice(2, 4),
        16
      ),

    b:
      parseInt(
        value.slice(4, 6),
        16
      ),
  };
}

function isLightPttColor(
  hex: string
): boolean {
  const rgb =
    hexToRgb(hex);

  if (!rgb) {
    return false;
  }

  const luminance =
    (
      0.299 * rgb.r +
      0.587 * rgb.g +
      0.114 * rgb.b
    );

  return luminance >= 170;
}

function loadPttCustomColor(): string {
''',
    "smart contrast helpers"
)


# ============================================================
# BEREKENEN OF CUSTOM KLEUR LICHT IS
# ============================================================

app = replace_once(
    app,
    '''  const [
    pttThemeMenuOpen,
    setPttThemeMenuOpen
  ] = useState(false);
''',
    '''  const [
    pttThemeMenuOpen,
    setPttThemeMenuOpen
  ] = useState(false);

  const pttCustomColorIsLight =
    isLightPttColor(
      pttCustomColor
    );
''',
    "custom color brightness"
)


# ============================================================
# EXTRA CLASS OP DE APP
# ============================================================

app = replace_once(
    app,
    '''}${novaSplash ? " ts-nova-splash" : ""} ts-ptt-color-${pttColorTheme}${
        pttCustomColorActive
          ? " ptt-custom-color"
          : ""
      }`}
''',
    '''}${novaSplash ? " ts-nova-splash" : ""} ts-ptt-color-${pttColorTheme}${
        pttCustomColorActive
          ? " ptt-custom-color"
          : ""
      }${
        pttCustomColorActive &&
        pttCustomColorIsLight
          ? " ptt-custom-color-light"
          : ""
      }`}
''',
    "smart custom color contrast class"
)


APP_FILE.write_text(
    app,
    encoding="utf-8"
)


# ============================================================
# CSS SLIM CONTRAST
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)


smart_contrast_css = r'''

/* ==========================================================
   PTT CONNECT - SLIM AUTOMATISCH CONTRAST
   ========================================================== */


/* ==========================================================
   STANDAARD: DONKERE / NORMALE ACCENTKLEUR
   ========================================================== */

.ts-app.ptt-custom-color {
  --ptt-text-main:
    #f4fbff;

  --ptt-text-soft:
    #b8d1e2;

  --ptt-text-muted:
    #89a7ba;

  --ptt-accent-text:
    #ffffff;

  --ptt-selected-text:
    #ffffff;
}


/* ==========================================================
   LICHTE CUSTOM KLEUR
   Bijvoorbeeld geel, lichtgroen, lichtroze
   ========================================================== */

.ts-app.ptt-custom-color-light {
  --ptt-text-main:
    #f4fbff;

  --ptt-text-soft:
    #c2d7e5;

  --ptt-text-muted:
    #91aabd;

  --ptt-accent-text:
    #07131d;

  --ptt-selected-text:
    #07131d;
}


/* ==========================================================
   SELECTIES
   ========================================================== */

.ts-app.ptt-custom-color-light
.ts-row-selected {
  background:
    linear-gradient(
      90deg,
      color-mix(
        in srgb,
        var(--ptt-accent) 82%,
        #ffffff
      ),
      color-mix(
        in srgb,
        var(--ptt-accent) 46%,
        #0b1e2c
      )
    ) !important;

  outline:
    1px solid
    var(--ptt-accent) !important;

  box-shadow:
    inset 3px 0 0
    color-mix(
      in srgb,
      var(--ptt-accent) 65%,
      #07131d
    ) !important;
}


.ts-app.ptt-custom-color-light
.ts-row-selected,
.ts-app.ptt-custom-color-light
.ts-row-selected * {
  color:
    var(--ptt-selected-text)
    !important;

  text-shadow:
    none !important;
}


/* ==========================================================
   THEMA TITELS
   ========================================================== */

.ts-app.ptt-custom-color-light
.ptt-dashboard-title,
.ts-app.ptt-custom-color-light
.ptt-theme-menu-title,
.ts-app.ptt-custom-color-light
.ptt-stream-quick-title,
.ts-app.ptt-custom-color-light
.ptt-custom-color-title {
  color:
    color-mix(
      in srgb,
      var(--ptt-accent) 62%,
      #ffffff
    ) !important;

  text-shadow:
    0 1px 2px
    rgba(
      0,
      0,
      0,
      0.55
    ) !important;
}


/* ==========================================================
   KNOPPEN
   ========================================================== */

.ts-app.ptt-custom-color-light
.ts-icon-button {
  color:
    #ffffff !important;
}


.ts-app.ptt-custom-color-light
.ts-icon-button:hover {
  background:
    color-mix(
      in srgb,
      var(--ptt-accent) 24%,
      #0b1e2c
    ) !important;
}


/* ==========================================================
   MENU ACTIEF ITEM
   ========================================================== */

.ts-app.ptt-custom-color-light
.ptt-theme-menu-active {
  background:
    color-mix(
      in srgb,
      var(--ptt-accent) 72%,
      #ffffff
    ) !important;
}


.ts-app.ptt-custom-color-light
.ptt-theme-menu-active,
.ts-app.ptt-custom-color-light
.ptt-theme-menu-active * {
  color:
    #07131d !important;

  text-shadow:
    none !important;
}


/* ==========================================================
   DASHBOARD KAARTEN
   ========================================================== */

.ts-app.ptt-custom-color-light
.ptt-dashboard-card {
  border-color:
    color-mix(
      in srgb,
      var(--ptt-accent) 44%,
      #102637
    ) !important;
}


.ts-app.ptt-custom-color-light
.ptt-dashboard-brand {
  border-color:
    color-mix(
      in srgb,
      var(--ptt-accent) 48%,
      #102637
    ) !important;
}


/* ==========================================================
   INPUTS
   ========================================================== */

.ts-app.ptt-custom-color-light
input,
.ts-app.ptt-custom-color-light
select,
.ts-app.ptt-custom-color-light
textarea {
  color:
    #ffffff !important;

  background:
    #0a1b29 !important;

  border-color:
    color-mix(
      in srgb,
      var(--ptt-accent) 46%,
      #173347
    ) !important;
}


/* ==========================================================
   LINKS / INFO
   ========================================================== */

.ts-app.ptt-custom-color-light
.ts-info-connection-link {
  color:
    #eaf7ff !important;
}


.ts-app.ptt-custom-color-light
.ts-info-connection-link:hover {
  color:
    #ffffff !important;

  background:
    color-mix(
      in srgb,
      var(--ptt-accent) 18%,
      #0b1e2c
    ) !important;
}


/* ==========================================================
   SPREKER HIGHLIGHT
   Houdt goede leesbaarheid bij lichte kleuren
   ========================================================== */

.ts-app.ptt-custom-color-light
.ptt-active-user-talking {
  background:
    linear-gradient(
      90deg,
      color-mix(
        in srgb,
        var(--ptt-accent) 28%,
        #0b1e2c
      ),
      #0b1e2c
    ) !important;

  border-color:
    var(--ptt-accent)
    !important;
}


.ts-app.ptt-custom-color-light
.ptt-active-user-talking,
.ts-app.ptt-custom-color-light
.ptt-active-user-talking * {
  color:
    #ffffff !important;
}


.ts-app.ptt-custom-color-light
.ptt-speaking-now-text {
  color:
    color-mix(
      in srgb,
      var(--ptt-accent) 50%,
      #ffffff
    ) !important;
}


/* ==========================================================
   SERVER / KANAAL TEKST ALTIJD LEESBAAR
   ========================================================== */

.ts-app.ptt-custom-color-light
.ts-server-row,
.ts-app.ptt-custom-color-light
.ts-server-row *,
.ts-app.ptt-custom-color-light
.ts-channel-row,
.ts-app.ptt-custom-color-light
.ts-channel-row *,
.ts-app.ptt-custom-color-light
.ts-client-row,
.ts-app.ptt-custom-color-light
.ts-client-row * {
  color:
    #edf7ff !important;
}


/* behalve geselecteerde regel */
.ts-app.ptt-custom-color-light
.ts-row-selected,
.ts-app.ptt-custom-color-light
.ts-row-selected * {
  color:
    #07131d !important;
}


/* ==========================================================
   ALGEMENE TITELS
   ========================================================== */

.ts-app.ptt-custom-color-light
.ts-info-title,
.ts-app.ptt-custom-color-light
.ptt-dashboard-channel-name,
.ts-app.ptt-custom-color-light
.ptt-active-user-info strong {
  color:
    #ffffff !important;
}

'''


if "PTT CONNECT - SLIM AUTOMATISCH CONTRAST" not in css:
    css += smart_contrast_css


CSS_FILE.write_text(
    css,
    encoding="utf-8"
)


print(
    "- slim automatisch contrast toegevoegd"
)

print(
    "- lichte eigen kleuren worden automatisch herkend"
)

print(
    "- geselecteerde regels blijven leesbaar"
)

print(
    "- donkere kleuren houden lichte tekst"
)

print(
    "- lichte kleuren krijgen donkere tekst waar nodig"
)
# ============================================================
# FIX - SLIM CONTRAST STATE VOLGORDE
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)

app = replace_once(
    app,
    '''  const [
    pttThemeMenuOpen,
    setPttThemeMenuOpen
  ] = useState(false);

  const pttCustomColorIsLight =
    isLightPttColor(
      pttCustomColor
    );

  const [
    pttCustomColor,
    setPttCustomColor
  ] = useState(
    loadPttCustomColor
  );

  const [
    pttCustomColorActive,
    setPttCustomColorActive
  ] = useState(
    loadPttCustomColorActive
  );

  const [
    pttCustomPresets,
    setPttCustomPresets
  ] = useState<PttCustomColorPreset[]>(
    loadPttCustomPresets
  );
''',
    '''  const [
    pttThemeMenuOpen,
    setPttThemeMenuOpen
  ] = useState(false);

  const [
    pttCustomColor,
    setPttCustomColor
  ] = useState(
    loadPttCustomColor
  );

  const [
    pttCustomColorActive,
    setPttCustomColorActive
  ] = useState(
    loadPttCustomColorActive
  );

  const [
    pttCustomPresets,
    setPttCustomPresets
  ] = useState<PttCustomColorPreset[]>(
    loadPttCustomPresets
  );

  const pttCustomColorIsLight =
    isLightPttColor(
      pttCustomColor
    );
''',
    "fix smart contrast state order"
)

APP_FILE.write_text(
    app,
    encoding="utf-8"
)

print(
    "- slimme kleurcontrast state-volgorde hersteld"
)

print(
    "- PTT audio microfoon streams en icoon niet gewijzigd"
)
# ============================================================
# PTT CONNECT - WEBCAM NAAST STREAMPLAYER
# ============================================================

PUBLISH_FILE = Path(
    "upstream/web/src/publish.ts"
)


# ============================================================
# PUBLISH.TS - CAMERA ALS BRON TOESTAAN
# ============================================================

publish = PUBLISH_FILE.read_text(
    encoding="utf-8"
)


publish = replace_once(
    publish,
    '''export interface StreamPublishOptions {
  name: string;
''',
    '''export interface StreamPublishOptions {
  name: string;

  /** PTT Connect: scherm of webcam. */
  source?: "screen" | "camera";
''',
    "webcam stream source option"
)


publish = replace_once(
    publish,
    '''  async start(options: StreamPublishOptions): Promise<void> {
    if (this.state === "live" || this.state === "starting") return;
    if (!navigator.mediaDevices?.getDisplayMedia) {
      this.fail("Screen sharing requires HTTPS (or localhost) - the site is not a secure context.");
      return;
    }

    this.setState("starting");
    this.options = options;

    const video: MediaTrackConstraints = {};
    if (options.height > 0) video.height = { ideal: options.height };
    if (options.fps > 0) video.frameRate = { ideal: options.fps };

    try {
      this.media = await navigator.mediaDevices.getDisplayMedia({
        video: Object.keys(video).length > 0 ? video : true,
        audio: options.audio,
      });
    } catch (err) {
      this.setState("idle");
      this.fail(`Could not capture the screen: ${describe(err)}`);
      return;
    }
''',
    '''  async start(options: StreamPublishOptions): Promise<void> {
    if (
      this.state === "live" ||
      this.state === "starting"
    ) {
      return;
    }

    const source =
      options.source ?? "screen";

    if (
      !navigator.mediaDevices
    ) {
      this.fail(
        "Media-apparaten zijn niet beschikbaar."
      );

      return;
    }

    if (
      source === "screen" &&
      !navigator.mediaDevices.getDisplayMedia
    ) {
      this.fail(
        "Scherm delen is niet beschikbaar."
      );

      return;
    }

    if (
      source === "camera" &&
      !navigator.mediaDevices.getUserMedia
    ) {
      this.fail(
        "Webcam is niet beschikbaar."
      );

      return;
    }

    this.setState(
      "starting"
    );

    this.options =
      options;

    const video:
      MediaTrackConstraints = {};

    if (
      options.height > 0
    ) {
      video.height = {
        ideal:
          options.height
      };
    }

    if (
      options.fps > 0
    ) {
      video.frameRate = {
        ideal:
          options.fps
      };
    }

    try {

      if (
        source === "camera"
      ) {

        this.media =
          await navigator.mediaDevices
            .getUserMedia({
              video:
                Object.keys(video).length > 0
                  ? video
                  : true,

              /*
               * Webcam-audio staat bewust uit.
               * PTT Connect gebruikt de bestaande
               * TeamSpeak/PTT microfoon voor spraak.
               */
              audio:
                false,
            });

      } else {

        this.media =
          await navigator.mediaDevices
            .getDisplayMedia({
              video:
                Object.keys(video).length > 0
                  ? video
                  : true,

              audio:
                options.audio,
            });

      }

    } catch (err) {

      this.setState(
        "idle"
      );

      this.fail(
        source === "camera"
          ? `Webcam kon niet worden gestart: ${describe(err)}`
          : `Scherm kon niet worden gedeeld: ${describe(err)}`
      );

      return;
    }
''',
    "webcam media capture"
)


publish = replace_once(
    publish,
    '''      streamType: this.detectSourceType(),
''',
    '''      streamType:
        options.source === "camera"
          ? StreamSource.CAMERA
          : this.detectSourceType(),
''',
    "webcam stream type"
)


PUBLISH_FILE.write_text(
    publish,
    encoding="utf-8"
)


# ============================================================
# APP.TSX
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)


# ============================================================
# WEBCAM START / STOP FUNCTIE
# ============================================================

app = replace_once(
    app,
    '''  const publishClientName = (clid: number) =>
''',
    '''  const handleWebcamButton = () => {

    /*
     * Als er al een webcam of andere
     * videostream actief is:
     * stoppen.
     */
    if (
      publisherRef.current
    ) {
      handleStopPublishing();
      return;
    }

    if (
      ownClientId === null
    ) {
      return;
    }

    /*
     * Webcam gebruikt de bestaande
     * StreamPublisher / WebRTC verbinding.
     *
     * Webcam-microfoon staat UIT zodat
     * de bestaande PTT-audio niet wordt
     * aangeraakt of dubbel verzonden.
     */
    handleStartPublishing({
      name:
        `${
          ownClient?.name ??
          "PTT Connect"
        } - Webcam`,

      source:
        "camera",

      audio:
        false,

      accessibility:
        StreamAccess.PUBLIC,

      mode:
        StreamMode.P2P,

      viewerLimit:
        0,

      height:
        720,

      fps:
        30,

      videoBitrateKbps:
        2500,

      audioBitrateKbps:
        128,

      contentHint:
        "motion",
    });
  };


  const publishClientName = (clid: number) =>
''',
    "PTT Connect webcam handler"
)


# ============================================================
# WEBCAM KNOP NAAST STREAMPLAYER
# ============================================================

app = replace_once(
    app,
    '''          </div>

          <img src={`${import.meta.env.BASE_URL}logo.png`} alt="" className="ts-app-logo" />
''',
    '''          </div>


          <div className="ptt-webcam-quick">

            <button
              type="button"
              className={
                "ts-icon-button ptt-webcam-button" +
                (
                  publishState === "live"
                    ? " ptt-webcam-active"
                    : ""
                )
              }
              onClick={
                handleWebcamButton
              }
              disabled={
                !connected ||
                ownClientId === null ||
                DEMO_MODE
              }
              title={
                publishState === "live"
                  ? "Webcam / video stoppen"
                  : "Webcam starten"
              }
              aria-label={
                publishState === "live"
                  ? "Webcam / video stoppen"
                  : "Webcam starten"
              }
            >
              {publishState === "live"
                ? "⏹️"
                : "📷"}
            </button>

          </div>


          <img src={`${import.meta.env.BASE_URL}logo.png`} alt="" className="ts-app-logo" />
''',
    "webcam button beside stream player"
)


APP_FILE.write_text(
    app,
    encoding="utf-8"
)


# ============================================================
# CSS WEBCAM KNOP
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)


webcam_css = r'''

/* ==========================================================
   PTT CONNECT - WEBCAM KNOP
   ========================================================== */

.ptt-webcam-quick {
  position:
    relative;

  display:
    inline-flex;

  align-items:
    center;

  justify-content:
    center;
}


.ptt-webcam-button {
  transition:
    border-color 0.16s ease,
    background 0.16s ease,
    box-shadow 0.16s ease,
    transform 0.16s ease;
}


.ptt-webcam-button:hover:not(:disabled) {
  border-color:
    var(--ptt-accent) !important;

  box-shadow:
    0 0 10px
    var(--ptt-glow);

  transform:
    translateY(-1px);
}


/* ==========================================================
   WEBCAM / VIDEO ACTIEF
   ========================================================== */

.ptt-webcam-active {
  border-color:
    #39dfff !important;

  background:
    rgba(
      40,
      190,
      255,
      0.18
    ) !important;

  box-shadow:
    0 0 7px
    rgba(
      60,
      215,
      255,
      0.60
    ),
    inset 0 0 8px
    rgba(
      60,
      215,
      255,
      0.12
    ) !important;
}


/* klein actief lampje */

.ptt-webcam-active::after {
  content:
    "";

  position:
    absolute;

  top:
    4px;

  right:
    4px;

  width:
    7px;

  height:
    7px;

  border-radius:
    50%;

  background:
    #45e8ff;

  box-shadow:
    0 0 8px
    #45e8ff;
}

'''


if "PTT CONNECT - WEBCAM KNOP" not in css:
    css += webcam_css


CSS_FILE.write_text(
    css,
    encoding="utf-8"
)


print(
    "- webcam knop naast streamplayer toegevoegd"
)

print(
    "- webcam gebruikt bestaande WebRTC stream"
)

print(
    "- andere gebruikers kunnen webcamstream bekijken"
)

print(
    "- webcam staat standaard uit"
)

print(
    "- webcam gebruikt 720p 30fps"
)

print(
    "- webcam-microfoon staat uit"
)

print(
    "- bestaande PTT microfoon niet gewijzigd"
)

print(
    "- TeamSpeak ontvangstaudio niet gewijzigd"
)

print(
    "- radiostreams niet gewijzigd"
)

print(
    "- PTT audio streams en microfoon niet gewijzigd"
)
# ============================================================
# PTT CONNECT - MIROTALK ACHTIGE VIDEO GALERIJ
# Alleen video - audio blijft via TeamSpeak / Push-To-Talk
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)


# ============================================================
# STREAM EVENT NAAR ALLE VIDEO TEGELS STUREN
# ============================================================

app = replace_once(
    app,
    '''          streamViewerRef.current?.handleEvent(streamEvent);
          publisherRef.current?.handleEvent(streamEvent);
          break;
''',
    '''          streamViewerRef.current?.handleEvent(streamEvent);
          publisherRef.current?.handleEvent(streamEvent);

          /*
           * PTT Connect videogalerij.
           *
           * Iedere videotegeI heeft zijn eigen
           * StreamViewer/WebRTC verbinding.
           *
           * Alle stream-events worden daarom ook
           * naar de galerij doorgestuurd.
           */
          window.dispatchEvent(
            new CustomEvent<StreamEvent>(
              "pttconnect-stream-event",
              {
                detail:
                  streamEvent
              }
            )
          );

          break;
''',
    "video gallery stream events"
)


# ============================================================
# VIDEO TILE COMPONENT
# ============================================================

app = replace_once(
    app,
    '''function AlphaBadge() {
''',
    '''function PttVideoGalleryTile({
  info,
  clientName,
  send,
  iceServers,
}: {
  info: StreamInfo;
  clientName: string;
  send: (
    message:
      Record<string, unknown>
  ) => void;
  iceServers:
    RTCIceServer[];
}) {

  const videoRef =
    useRef<HTMLVideoElement | null>(
      null
    );

  const sendRef =
    useRef(send);

  const [
    media,
    setMedia
  ] =
    useState<MediaStream | null>(
      null
    );

  const [
    connectionState,
    setConnectionState
  ] =
    useState<
      RTCPeerConnectionState |
      "waiting"
    >(
      "waiting"
    );

  const [
    error,
    setError
  ] =
    useState<string | null>(
      null
    );


  /*
   * Houd de nieuwste send-functie vast
   * zonder de WebRTC verbinding bij iedere
   * render opnieuw op te bouwen.
   */
  useEffect(
    () => {
      sendRef.current =
        send;
    },
    [
      send
    ]
  );


  /*
   * Eén StreamViewer per webcam/schermstream.
   */
  useEffect(
    () => {

      let mounted =
        true;

      setMedia(
        null
      );

      setError(
        null
      );

      setConnectionState(
        "waiting"
      );


      const viewer =
        new StreamViewer(
          info.id,
          info.clientId,
          {
            send:
              (
                message
              ) => {
                sendRef.current(
                  message
                );
              },

            onTrack:
              (
                stream
              ) => {

                if (
                  !mounted
                ) {
                  return;
                }

                setMedia(
                  stream
                );
              },

            onStateChange:
              (
                state
              ) => {

                if (
                  !mounted
                ) {
                  return;
                }

                setConnectionState(
                  state
                );
              },

            onError:
              (
                message
              ) => {

                if (
                  !mounted
                ) {
                  return;
                }

                setError(
                  message
                );
              },

            iceServers,
          }
        );


      /*
       * Stream events van de centrale
       * TeamSpeak verbinding ontvangen.
       */
      const handleStreamEvent =
        (
          event:
            Event
        ) => {

          const customEvent =
            event as
              CustomEvent<StreamEvent>;

          if (
            customEvent.detail
          ) {
            viewer.handleEvent(
              customEvent.detail
            );
          }
        };


      window.addEventListener(
        "pttconnect-stream-event",
        handleStreamEvent
      );


      /*
       * Automatisch aansluiten.
       *
       * Bij een PUBLIC stream gaat dit
       * automatisch.
       *
       * Bij PRIVATE wacht hij op toestemming
       * van de gebruiker die de webcam deelt.
       */
      viewer.join(
        "PTT Connect videogalerij"
      );


      return () => {

        mounted =
          false;

        window.removeEventListener(
          "pttconnect-stream-event",
          handleStreamEvent
        );

        viewer.close();
      };

    },
    [
      info.id,
      info.clientId
    ]
  );


  /*
   * MediaStream aan video-element koppelen.
   */
  useEffect(
    () => {

      const video =
        videoRef.current;

      if (
        !video
      ) {
        return;
      }

      if (
        video.srcObject !==
        media
      ) {
        video.srcObject =
          media;
      }

    },
    [
      media
    ]
  );


  const connected =
    connectionState ===
      "connected";


  return (
    <div
      className={
        "ptt-video-tile" +
        (
          connected
            ? " ptt-video-tile-connected"
            : ""
        )
      }
    >

      <div className="ptt-video-tile-video">

        <video
          ref={
            videoRef
          }
          autoPlay
          playsInline

          /*
           * ZEER BELANGRIJK:
           *
           * videostream-audio wordt hier
           * altijd gedempt.
           *
           * Alle stem/audio blijft via
           * TeamSpeak Push-To-Talk lopen.
           */
          muted
        />

        {!media && (
          <div className="ptt-video-waiting">

            <div className="ptt-video-avatar">
              📷
            </div>

            <strong>
              {clientName}
            </strong>

            <span>
              {error
                ? "Video niet beschikbaar"
                : "Webcam verbinden…"}
            </span>

          </div>
        )}


        <div className="ptt-video-name">

          <span className="ptt-video-live-dot" />

          <span>
            {clientName}
          </span>

          {connected && (
            <span className="ptt-video-live-text">
              LIVE
            </span>
          )}

        </div>

      </div>


      {error && (
        <div className="ptt-video-error">
          {error}
        </div>
      )}

    </div>
  );
}


function AlphaBadge() {
''',
    "PTT video gallery tile component"
)


# ============================================================
# VIDEO GALERIJ IN DE APP
# ============================================================

app = replace_once(
    app,
    '''      {(watchedStream || (publishState !== "idle" && publishState !== "stopped")) && (
''',
    '''      {(() => {

        /*
         * Bepaal het TeamSpeak-kanaal
         * waarin wij zelf zitten.
         */
        const ownChannelId =
          clients.find(
            (
              client
            ) =>
              client.id ===
              ownClientId
          )?.channel;


        if (
          ownChannelId ===
          undefined
        ) {
          return null;
        }


        /*
         * Alleen streams van gebruikers
         * in hetzelfde kanaal.
         *
         * Eigen stream wordt niet opnieuw
         * geopend: daarvoor bestaat al
         * de lokale preview.
         */
        const channelStreams =
          Object.values(
            streamInfos
          ).filter(
            (
              info
            ) => {

              if (
                info.clientId ===
                ownClientId
              ) {
                return false;
              }

              const client =
                clients.find(
                  (
                    candidate
                  ) =>
                    candidate.id ===
                    info.clientId
                );

              return (
                client?.channel ===
                ownChannelId
              );
            }
          );


        if (
          channelStreams.length ===
          0
        ) {
          return null;
        }


        return (
          <section className="ptt-video-gallery">

            <div className="ptt-video-gallery-header">

              <div className="ptt-video-gallery-title">

                <span className="ptt-video-gallery-icon">
                  📹
                </span>

                <div>
                  <strong>
                    PTT Connect Video
                  </strong>

                  <span>
                    Webcamgalerij • zelfde kanaal
                  </span>
                </div>

              </div>


              <div className="ptt-video-gallery-status">

                <span className="ptt-video-gallery-online-dot" />

                {
                  channelStreams.length
                }

                {
                  channelStreams.length ===
                  1
                    ? " video"
                    : " video's"
                }

              </div>

            </div>


            <div
              className={
                "ptt-video-grid " +
                (
                  channelStreams.length === 1
                    ? "ptt-video-grid-1"
                    :
                  channelStreams.length === 2
                    ? "ptt-video-grid-2"
                    :
                  channelStreams.length <= 4
                    ? "ptt-video-grid-4"
                    :
                  channelStreams.length <= 6
                    ? "ptt-video-grid-6"
                    :
                    "ptt-video-grid-many"
                )
              }
            >

              {
                channelStreams.map(
                  (
                    info
                  ) => {

                    const client =
                      clients.find(
                        (
                          candidate
                        ) =>
                          candidate.id ===
                          info.clientId
                      );


                    return (
                      <PttVideoGalleryTile
                        key={
                          info.id
                        }

                        info={
                          info
                        }

                        clientName={
                          client?.name ??
                          `Gebruiker ${info.clientId}`
                        }

                        send={
                          (
                            message
                          ) => {
                            socketRef.current
                              ?.send(
                                JSON.stringify(
                                  message
                                )
                              );
                          }
                        }

                        iceServers={
                          [
                            ...DEFAULT_ICE_SERVERS,
                            ...turnServers
                          ]
                        }
                      />
                    );
                  }
                )
              }

            </div>


            <div className="ptt-video-gallery-footer">

              <span>
                🎙️ Audio blijft via Push-To-Talk
              </span>

              <span>
                🔒 Alleen gebruikers in dit kanaal
              </span>

            </div>

          </section>
        );

      })()}


      {(watchedStream || (publishState !== "idle" && publishState !== "stopped")) && (
''',
    "PTT Connect MiroTalk video gallery"
)


APP_FILE.write_text(
    app,
    encoding="utf-8"
)


# ============================================================
# CSS - MIROTALK ACHTIGE VIDEO GALERIJ
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)


video_gallery_css = r'''

/* ==========================================================
   PTT CONNECT VIDEO GALERIJ
   ========================================================== */

.ptt-video-gallery {
  position:
    fixed;

  z-index:
    115;

  left:
    470px;

  right:
    24px;

  bottom:
    22px;

  max-height:
    58vh;

  display:
    flex;

  flex-direction:
    column;

  overflow:
    hidden;

  border:
    1px solid
    rgba(
      70,
      190,
      255,
      0.30
    );

  border-radius:
    18px;

  background:
    rgba(
      5,
      15,
      27,
      0.96
    );

  backdrop-filter:
    blur(18px);

  box-shadow:
    0 24px 60px
    rgba(
      0,
      0,
      0,
      0.46
    ),
    0 0 26px
    rgba(
      20,
      170,
      255,
      0.08
    );
}


/* ==========================================================
   HEADER
   ========================================================== */

.ptt-video-gallery-header {
  min-height:
    62px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    space-between;

  gap:
    16px;

  padding:
    10px 16px;

  border-bottom:
    1px solid
    rgba(
      255,
      255,
      255,
      0.08
    );

  background:
    linear-gradient(
      90deg,
      rgba(
        10,
        40,
        63,
        0.94
      ),
      rgba(
        5,
        19,
        33,
        0.94
      )
    );
}


.ptt-video-gallery-title {
  display:
    flex;

  align-items:
    center;

  gap:
    11px;
}


.ptt-video-gallery-icon {
  width:
    38px;

  height:
    38px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  border:
    1px solid
    rgba(
      65,
      205,
      255,
      0.42
    );

  border-radius:
    11px;

  background:
    rgba(
      40,
      175,
      255,
      0.12
    );

  font-size:
    20px;
}


.ptt-video-gallery-title div {
  display:
    flex;

  flex-direction:
    column;

  gap:
    2px;
}


.ptt-video-gallery-title strong {
  color:
    #f4fbff;

  font-size:
    14px;
}


.ptt-video-gallery-title div > span {
  color:
    #8ca9ba;

  font-size:
    11px;
}


.ptt-video-gallery-status {
  display:
    flex;

  align-items:
    center;

  gap:
    7px;

  padding:
    7px 10px;

  border-radius:
    999px;

  background:
    rgba(
      42,
      196,
      255,
      0.09
    );

  color:
    #aeeaff;

  font-size:
    11px;

  font-weight:
    700;
}


.ptt-video-gallery-online-dot {
  width:
    7px;

  height:
    7px;

  border-radius:
    50%;

  background:
    #58e5ff;

  box-shadow:
    0 0 8px
    rgba(
      88,
      229,
      255,
      0.9
    );
}


/* ==========================================================
   VIDEO GRID
   ========================================================== */

.ptt-video-grid {
  display:
    grid;

  gap:
    9px;

  padding:
    11px;

  overflow:
    auto;

  min-height:
    0;
}


.ptt-video-grid-1 {
  grid-template-columns:
    minmax(
      0,
      1fr
    );
}


.ptt-video-grid-2 {
  grid-template-columns:
    repeat(
      2,
      minmax(
        0,
        1fr
      )
    );
}


.ptt-video-grid-4 {
  grid-template-columns:
    repeat(
      2,
      minmax(
        0,
        1fr
      )
    );
}


.ptt-video-grid-6 {
  grid-template-columns:
    repeat(
      3,
      minmax(
        0,
        1fr
      )
    );
}


.ptt-video-grid-many {
  grid-template-columns:
    repeat(
      3,
      minmax(
        0,
        1fr
      )
    );
}


/* ==========================================================
   VIDEO TEGEL
   ========================================================== */

.ptt-video-tile {
  position:
    relative;

  overflow:
    hidden;

  min-width:
    0;

  border:
    1px solid
    rgba(
      255,
      255,
      255,
      0.11
    );

  border-radius:
    13px;

  background:
    #02080e;

  box-shadow:
    0 10px 24px
    rgba(
      0,
      0,
      0,
      0.28
    );

  transition:
    border-color
    0.16s ease,
    box-shadow
    0.16s ease;
}


.ptt-video-tile-connected {
  border-color:
    rgba(
      60,
      210,
      255,
      0.30
    );
}


.ptt-video-tile-video {
  position:
    relative;

  width:
    100%;

  aspect-ratio:
    16 / 9;

  overflow:
    hidden;

  background:
    radial-gradient(
      circle at center,
      #0d2638,
      #02080e
    );
}


.ptt-video-tile video {
  width:
    100%;

  height:
    100%;

  display:
    block;

  object-fit:
    cover;

  background:
    #02080e;
}


/* ==========================================================
   WACHTSCHERM
   ========================================================== */

.ptt-video-waiting {
  position:
    absolute;

  inset:
    0;

  display:
    flex;

  flex-direction:
    column;

  align-items:
    center;

  justify-content:
    center;

  gap:
    5px;

  color:
    #edfaff;

  text-align:
    center;

  background:
    radial-gradient(
      circle at center,
      rgba(
        21,
        74,
        108,
        0.56
      ),
      rgba(
        2,
        8,
        14,
        0.95
      )
    );
}


.ptt-video-waiting strong {
  font-size:
    13px;
}


.ptt-video-waiting span {
  color:
    #8caabd;

  font-size:
    10px;
}


.ptt-video-avatar {
  width:
    48px;

  height:
    48px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  margin-bottom:
    4px;

  border:
    1px solid
    rgba(
      66,
      206,
      255,
      0.30
    );

  border-radius:
    50%;

  background:
    rgba(
      32,
      171,
      255,
      0.11
    );

  font-size:
    23px;
}


/* ==========================================================
   NAAM OVER VIDEO
   ========================================================== */

.ptt-video-name {
  position:
    absolute;

  left:
    8px;

  right:
    8px;

  bottom:
    8px;

  display:
    flex;

  align-items:
    center;

  gap:
    6px;

  min-width:
    0;

  padding:
    6px 8px;

  border:
    1px solid
    rgba(
      255,
      255,
      255,
      0.10
    );

  border-radius:
    8px;

  background:
    rgba(
      0,
      7,
      12,
      0.76
    );

  backdrop-filter:
    blur(8px);

  color:
    #f5fbff;

  font-size:
    11px;

  font-weight:
    700;
}


.ptt-video-name > span:nth-child(2) {
  overflow:
    hidden;

  text-overflow:
    ellipsis;

  white-space:
    nowrap;
}


.ptt-video-live-dot {
  flex:
    0 0 auto;

  width:
    7px;

  height:
    7px;

  border-radius:
    50%;

  background:
    #50ddff;

  box-shadow:
    0 0 7px
    #50ddff;
}


.ptt-video-live-text {
  margin-left:
    auto;

  color:
    #66e4ff;

  font-size:
    9px;

  letter-spacing:
    0.07em;
}


/* ==========================================================
   FOUTMELDING
   ========================================================== */

.ptt-video-error {
  padding:
    7px 9px;

  border-top:
    1px solid
    rgba(
      255,
      90,
      90,
      0.20
    );

  background:
    rgba(
      90,
      15,
      18,
      0.55
    );

  color:
    #ffb9bd;

  font-size:
    10px;
}


/* ==========================================================
   FOOTER
   ========================================================== */

.ptt-video-gallery-footer {
  min-height:
    36px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    space-between;

  gap:
    12px;

  padding:
    7px 13px;

  border-top:
    1px solid
    rgba(
      255,
      255,
      255,
      0.07
    );

  color:
    #82a1b4;

  background:
    rgba(
      2,
      10,
      17,
      0.94
    );

  font-size:
    10px;
}


/* ==========================================================
   RESPONSIVE
   ========================================================== */

@media (
  max-width:
    1200px
) {

  .ptt-video-gallery {
    left:
      390px;
  }

  .ptt-video-grid-6,
  .ptt-video-grid-many {
    grid-template-columns:
      repeat(
        2,
        minmax(
          0,
          1fr
        )
      );
  }

}


@media (
  max-width:
    850px
) {

  .ptt-video-gallery {
    left:
      12px;

    right:
      12px;

    bottom:
      12px;

    max-height:
      70vh;
  }


  .ptt-video-grid,
  .ptt-video-grid-2,
  .ptt-video-grid-4,
  .ptt-video-grid-6,
  .ptt-video-grid-many {
    grid-template-columns:
      1fr;
  }


  .ptt-video-gallery-footer {
    flex-direction:
      column;

    align-items:
      flex-start;
  }

}

'''


if (
  "PTT CONNECT VIDEO GALERIJ"
  not in css
):
    css += (
        video_gallery_css
    )


CSS_FILE.write_text(
    css,
    encoding="utf-8"
)


print(
    "- MiroTalk-achtige videogalerij toegevoegd"
)

print(
    "- meerdere webcams tegelijk mogelijk"
)

print(
    "- alleen gebruikers uit hetzelfde TeamSpeak-kanaal"
)

print(
    "- elke webcam heeft eigen WebRTC verbinding"
)

print(
    "- video-audio altijd gedempt"
)

print(
    "- spraak blijft uitsluitend via Push-To-Talk"
)

print(
    "- bestaande PTT microfoon NIET gewijzigd"
)

print(
    "- TeamSpeak ontvangstaudio NIET gewijzigd"
)

print(
    "- radiostreamplayer NIET gewijzigd"
)
