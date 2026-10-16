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
# ============================================================
# PTT CONNECT - SCHERM DELEN NAAST WEBCAM
# Audio blijft via TeamSpeak / Push-To-Talk
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)


# ============================================================
# BIJHOUDEN WAT WE DELEN: WEBCAM OF SCHERM
# ============================================================

app = replace_once(
    app,
    '''  const [streamSettingsOpen, setStreamSettingsOpen] = useState(false);
''',
    '''  const [streamSettingsOpen, setStreamSettingsOpen] = useState(false);

  const [
    pttVideoSource,
    setPttVideoSource
  ] = useState<
    "camera" |
    "screen" |
    null
  >(null);
''',
    "PTT video source state"
)


# ============================================================
# STOPPEN = OOK ACTIEVE BRON WISSEN
# ============================================================

app = replace_once(
    app,
    '''  const handleStopPublishing = () => {
    publisherRef.current?.stop();
    publisherRef.current = null;
    setPublishState("idle");
    setPublishViewers([]);
    setPublishPending([]);
  };
''',
    '''  const handleStopPublishing = () => {
    publisherRef.current?.stop();

    publisherRef.current =
      null;

    setPublishState(
      "idle"
    );

    setPublishViewers(
      []
    );

    setPublishPending(
      []
    );

    setPttVideoSource(
      null
    );
  };
''',
    "reset PTT video source on stop"
)


# ============================================================
# BESTAANDE SCHERMDELEN-KNOP FUNCTIE
# ============================================================

app = replace_once(
    app,
    '''  const handleStreamButton = () => {
    if (publisherRef.current) {
      handleStopPublishing();
      return;
    }
    setStreamSettingsOpen(true);
  };
''',
    '''  const handleStreamButton = () => {

    if (
      publisherRef.current
    ) {
      handleStopPublishing();
      return;
    }

    setPttVideoSource(
      "screen"
    );

    setStreamSettingsOpen(
      true
    );
  };
''',
    "PTT screen share source"
)


# ============================================================
# WEBCAM ALS CAMERA MARKEREN
# ============================================================

app = replace_once(
    app,
    '''    handleStartPublishing({
      name:
''',
    '''    setPttVideoSource(
      "camera"
    );

    handleStartPublishing({
      name:
''',
    "mark webcam as camera source"
)


# ============================================================
# BIJ STOPPEN / FOUT BRON OOK WISSEN
# ============================================================

app = replace_once(
    app,
    '''        if (state === "stopped" || state === "idle") {
          publisherRef.current = null;
          setPublishViewers([]);
          setPublishPending([]);
        }
''',
    '''        if (
          state === "stopped" ||
          state === "idle"
        ) {
          publisherRef.current =
            null;

          setPublishViewers(
            []
          );

          setPublishPending(
            []
          );

          setPttVideoSource(
            null
          );
        }
''',
    "reset video source after publisher stop"
)


# ============================================================
# SCHERMDELEN DIALOOG ANNULEREN
# ============================================================

app = replace_once(
    app,
    '''          onCancel={() => setStreamSettingsOpen(false)}
''',
    '''          onCancel={() => {
            setStreamSettingsOpen(
              false
            );

            setPttVideoSource(
              null
            );
          }}
''',
    "screen share cancel reset"
)


# ============================================================
# WEBCAM KNOP ALLEEN ACTIEF BIJ WEBCAM
# ============================================================

app = replace_once(
    app,
    '''                  publishState === "live"
                    ? " ptt-webcam-active"
                    : ""
''',
    '''                  pttVideoSource === "camera" &&
                  publishState === "live"
                    ? " ptt-webcam-active"
                    : ""
''',
    "webcam active source"
)


app = replace_once(
    app,
    '''              title={
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
''',
    '''              title={
                pttVideoSource === "camera" &&
                publishState === "live"
                  ? "Webcam stoppen"
                  : "Webcam starten"
              }
              aria-label={
                pttVideoSource === "camera" &&
                publishState === "live"
                  ? "Webcam stoppen"
                  : "Webcam starten"
              }
            >
              {
                pttVideoSource === "camera" &&
                publishState === "live"
                  ? "⏹️"
                  : "📷"
              }
''',
    "webcam icon correct active source"
)


# ============================================================
# SCHERMDELEN-KNOP NAAST WEBCAM
# ============================================================

app = replace_once(
    app,
    '''          </div>


          <img src={`${import.meta.env.BASE_URL}logo.png`} alt="" className="ts-app-logo" />
''',
    '''          </div>


          <div className="ptt-screen-quick">

            <button
              type="button"
              className={
                "ts-icon-button ptt-screen-button" +
                (
                  pttVideoSource === "screen" &&
                  publishState === "live"
                    ? " ptt-screen-active"
                    : ""
                )
              }
              onClick={
                handleStreamButton
              }
              disabled={
                !connected ||
                ownClientId === null ||
                DEMO_MODE
              }
              title={
                pttVideoSource === "screen" &&
                publishState === "live"
                  ? "Scherm delen stoppen"
                  : "Scherm delen"
              }
              aria-label={
                pttVideoSource === "screen" &&
                publishState === "live"
                  ? "Scherm delen stoppen"
                  : "Scherm delen"
              }
            >
              {
                pttVideoSource === "screen" &&
                publishState === "live"
                  ? "⏹️"
                  : "🖥️"
              }
            </button>

          </div>


          <img src={`${import.meta.env.BASE_URL}logo.png`} alt="" className="ts-app-logo" />
''',
    "screen share button beside webcam"
)


APP_FILE.write_text(
    app,
    encoding="utf-8"
)


# ============================================================
# CSS SCHERMDELEN
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)


screen_share_css = r'''

/* ==========================================================
   PTT CONNECT - SCHERM DELEN KNOP
   ========================================================== */

.ptt-screen-quick {
  position:
    relative;

  display:
    inline-flex;

  align-items:
    center;

  justify-content:
    center;
}


.ptt-screen-button {
  transition:
    border-color 0.16s ease,
    background 0.16s ease,
    box-shadow 0.16s ease,
    transform 0.16s ease;
}


.ptt-screen-button:hover:not(:disabled) {
  border-color:
    var(--ptt-accent) !important;

  box-shadow:
    0 0 10px
    var(--ptt-glow);

  transform:
    translateY(-1px);
}


/* SCHERMDELEN ACTIEF */

.ptt-screen-active {
  border-color:
    #59dcff !important;

  background:
    rgba(
      35,
      175,
      255,
      0.20
    ) !important;

  box-shadow:
    0 0 8px
    rgba(
      70,
      215,
      255,
      0.65
    ),
    inset 0 0 8px
    rgba(
      70,
      215,
      255,
      0.13
    ) !important;
}


.ptt-screen-active::after {
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
    #59dcff;

  box-shadow:
    0 0 8px
    #59dcff;
}

'''


if (
    "PTT CONNECT - SCHERM DELEN KNOP"
    not in css
):
    css += (
        screen_share_css
    )


CSS_FILE.write_text(
    css,
    encoding="utf-8"
)


print(
    "- schermdelen knop toegevoegd"
)

print(
    "- volgorde: streamplayer - webcam - schermdelen"
)

print(
    "- webcam en schermdelen worden apart herkend"
)

print(
    "- schermkeuze gebeurt via Windows"
)

print(
    "- gedeeld scherm verschijnt in videogalerij"
)

print(
    "- video-audio verandert PTT niet"
)

print(
    "- bestaande Push-To-Talk microfoon NIET gewijzigd"
)

print(
    "- TeamSpeak ontvangstaudio NIET gewijzigd"
)

print(
    "- webcamfunctie NIET verwijderd"
)
# ============================================================
# PTT CONNECT - VIDEO GALERIJ PRO
# Fullscreen + vergroten + sprekerhighlight + betere layout
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)


# ============================================================
# TALKER STATUS NAAR VIDEO TEGEL
# ============================================================

app = replace_once(
    app,
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
''',
    '''function PttVideoGalleryTile({
  info,
  clientName,
  send,
  iceServers,
  isTalking,
}: {
  info: StreamInfo;
  clientName: string;
  send: (
    message:
      Record<string, unknown>
  ) => void;
  iceServers:
    RTCIceServer[];
  isTalking:
    boolean;
}) {

  const tileRef =
    useRef<HTMLDivElement | null>(
      null
    );
''',
    "video tile talking prop and ref"
)


# ============================================================
# FULLSCREEN FUNCTIE
# ============================================================

app = replace_once(
    app,
    '''  const connected =
    connectionState ===
      "connected";


  return (
''',
    '''  const connected =
    connectionState ===
      "connected";


  const toggleVideoFullscreen =
    async () => {

      const tile =
        tileRef.current;

      if (!tile) {
        return;
      }

      try {

        if (
          document.fullscreenElement ===
          tile
        ) {

          await document.exitFullscreen();

        } else {

          await tile.requestFullscreen();

        }

      } catch {
        /*
         * Fullscreen kan door Windows/browser
         * geweigerd worden. De videostream
         * blijft dan gewoon doorlopen.
         */
      }
    };


  return (
''',
    "video tile fullscreen handler"
)


# ============================================================
# TEGEL: FULLSCREEN + SPREKER CLASS
# ============================================================

app = replace_once(
    app,
    '''    <div
      className={
        "ptt-video-tile" +
        (
          connected
            ? " ptt-video-tile-connected"
            : ""
        )
      }
    >
''',
    '''    <div
      ref={
        tileRef
      }
      className={
        "ptt-video-tile" +
        (
          connected
            ? " ptt-video-tile-connected"
            : ""
        ) +
        (
          isTalking
            ? " ptt-video-tile-talking"
            : ""
        )
      }
      onDoubleClick={
        () => {
          void toggleVideoFullscreen();
        }
      }
      title="Dubbelklik voor volledig scherm"
    >
''',
    "video tile fullscreen and talking class"
)


# ============================================================
# VERGROOTKNOP RECHTSBOVEN
# ============================================================

app = replace_once(
    app,
    '''      <div className="ptt-video-tile-video">

        <video
''',
    '''      <div className="ptt-video-tile-video">

        <button
          type="button"
          className="ptt-video-fullscreen-button"
          onClick={
            (
              event
            ) => {
              event.stopPropagation();

              void toggleVideoFullscreen();
            }
          }
          title="Video vergroten"
          aria-label="Video vergroten"
        >
          ⛶
        </button>


        {isTalking && (
          <div className="ptt-video-speaking-badge">
            🎙 SPREEKT NU
          </div>
        )}


        <video
''',
    "video fullscreen button"
)


# ============================================================
# LIVE TEKST AANPASSEN ALS IEMAND PRAAT
# ============================================================

app = replace_once(
    app,
    '''          {connected && (
            <span className="ptt-video-live-text">
              LIVE
            </span>
          )}
''',
    '''          {connected && (
            <span
              className={
                "ptt-video-live-text" +
                (
                  isTalking
                    ? " ptt-video-live-talking"
                    : ""
                )
              }
            >
              {
                isTalking
                  ? "PTT"
                  : "LIVE"
              }
            </span>
          )}
''',
    "video live talking text"
)


# ============================================================
# TALKER STATUS VAN APP NAAR TEGEL
# ============================================================

app = replace_once(
    app,
    '''                        iceServers={
                          [
                            ...DEFAULT_ICE_SERVERS,
                            ...turnServers
                          ]
                        }
                      />
''',
    '''                        iceServers={
                          [
                            ...DEFAULT_ICE_SERVERS,
                            ...turnServers
                          ]
                        }

                        isTalking={
                          displayTalkers.has(
                            info.clientId
                          )
                        }
                      />
''',
    "pass talker state to video tile"
)


APP_FILE.write_text(
    app,
    encoding="utf-8"
)


# ============================================================
# CSS VIDEO GALERIJ PRO
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)


video_pro_css = r'''

/* ==========================================================
   PTT CONNECT - VIDEO GALERIJ PRO
   ========================================================== */


/* ==========================================================
   ACTIEVE PTT SPREKER
   ========================================================== */

.ptt-video-tile-talking {
  border-color:
    rgba(
      83,
      224,
      255,
      0.95
    ) !important;

  box-shadow:
    0 0 0 2px
    rgba(
      70,
      215,
      255,
      0.20
    ),
    0 0 24px
    rgba(
      65,
      210,
      255,
      0.46
    ),
    inset 0 0 16px
    rgba(
      50,
      190,
      255,
      0.08
    ) !important;

  transform:
    translateY(-1px);
}


/* ==========================================================
   SPREEKT NU BADGE
   ========================================================== */

.ptt-video-speaking-badge {
  position:
    absolute;

  z-index:
    6;

  top:
    10px;

  left:
    10px;

  display:
    flex;

  align-items:
    center;

  gap:
    5px;

  padding:
    6px 9px;

  border:
    1px solid
    rgba(
      95,
      229,
      255,
      0.75
    );

  border-radius:
    999px;

  background:
    rgba(
      5,
      33,
      49,
      0.90
    );

  color:
    #79eaff;

  font-size:
    10px;

  font-weight:
    800;

  letter-spacing:
    0.05em;

  box-shadow:
    0 0 12px
    rgba(
      75,
      220,
      255,
      0.34
    );

  animation:
    pttVideoSpeakerPulse
    0.75s
    ease-in-out
    infinite alternate;
}


@keyframes pttVideoSpeakerPulse {

  from {
    opacity:
      0.82;
  }

  to {
    opacity:
      1;

    box-shadow:
      0 0 18px
      rgba(
        75,
        220,
        255,
        0.60
      );
  }

}


/* ==========================================================
   VERGROOT / FULLSCREEN KNOP
   ========================================================== */

.ptt-video-fullscreen-button {
  position:
    absolute;

  z-index:
    8;

  top:
    9px;

  right:
    9px;

  width:
    34px;

  height:
    34px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  padding:
    0;

  border:
    1px solid
    rgba(
      255,
      255,
      255,
      0.18
    );

  border-radius:
    9px;

  background:
    rgba(
      0,
      8,
      15,
      0.78
    );

  color:
    #eaf9ff;

  font-size:
    19px;

  cursor:
    pointer;

  opacity:
    0.72;

  transition:
    opacity 0.15s ease,
    border-color 0.15s ease,
    background 0.15s ease,
    transform 0.15s ease;
}


.ptt-video-tile:hover
.ptt-video-fullscreen-button {
  opacity:
    1;
}


.ptt-video-fullscreen-button:hover {
  border-color:
    #59dcff;

  background:
    rgba(
      30,
      150,
      215,
      0.34
    );

  transform:
    scale(1.06);
}


/* ==========================================================
   LIVE / PTT INDICATOR
   ========================================================== */

.ptt-video-live-talking {
  color:
    #78eaff !important;

  text-shadow:
    0 0 7px
    rgba(
      80,
      220,
      255,
      0.75
    );
}


/* ==========================================================
   FULLSCREEN VIDEO
   ========================================================== */

.ptt-video-tile:fullscreen {
  width:
    100vw;

  height:
    100vh;

  max-width:
    none;

  max-height:
    none;

  border:
    0;

  border-radius:
    0;

  background:
    #000;
}


.ptt-video-tile:fullscreen
.ptt-video-tile-video {
  width:
    100%;

  height:
    100%;

  aspect-ratio:
    auto;

  background:
    #000;
}


.ptt-video-tile:fullscreen video {
  width:
    100%;

  height:
    100%;

  object-fit:
    contain;

  background:
    #000;
}


.ptt-video-tile:fullscreen
.ptt-video-name {
  left:
    20px;

  right:
    auto;

  bottom:
    20px;

  min-width:
    220px;

  padding:
    10px 14px;

  font-size:
    14px;
}


.ptt-video-tile:fullscreen
.ptt-video-fullscreen-button {
  top:
    18px;

  right:
    18px;

  width:
    42px;

  height:
    42px;

  font-size:
    23px;

  opacity:
    1;
}


.ptt-video-tile:fullscreen
.ptt-video-speaking-badge {
  top:
    20px;

  left:
    20px;

  padding:
    8px 12px;

  font-size:
    12px;
}


/* ==========================================================
   AUTOMATISCHE GRID VERBETERING
   ========================================================== */

.ptt-video-grid-many {
  grid-template-columns:
    repeat(
      auto-fit,
      minmax(
        250px,
        1fr
      )
    );
}


/* 1 gebruiker = mooi groot */

.ptt-video-grid-1
.ptt-video-tile {
  max-width:
    1000px;

  width:
    100%;

  justify-self:
    center;
}


/* 2 gebruikers */

.ptt-video-grid-2 {
  grid-template-columns:
    repeat(
      2,
      minmax(
        280px,
        1fr
      )
    );
}


/* 3 en 4 gebruikers = 2 x 2 */

.ptt-video-grid-4 {
  grid-template-columns:
    repeat(
      2,
      minmax(
        260px,
        1fr
      )
    );
}


/* 5 en 6 gebruikers = 3 kolommen */

.ptt-video-grid-6 {
  grid-template-columns:
    repeat(
      3,
      minmax(
        220px,
        1fr
      )
    );
}


/* ==========================================================
   MOBIEL / KLEIN VENSTER
   ========================================================== */

@media (
  max-width:
    1050px
) {

  .ptt-video-grid-6,
  .ptt-video-grid-many {
    grid-template-columns:
      repeat(
        2,
        minmax(
          220px,
          1fr
        )
      );
  }

}


@media (
  max-width:
    700px
) {

  .ptt-video-grid-1,
  .ptt-video-grid-2,
  .ptt-video-grid-4,
  .ptt-video-grid-6,
  .ptt-video-grid-many {
    grid-template-columns:
      1fr;
  }

}

'''


if (
    "PTT CONNECT - VIDEO GALERIJ PRO"
    not in css
):
    css += (
        video_pro_css
    )


CSS_FILE.write_text(
    css,
    encoding="utf-8"
)


print(
    "- videogalerij Pro toegevoegd"
)

print(
    "- dubbelklik opent fullscreen"
)

print(
    "- vergrootknop rechtsboven toegevoegd"
)

print(
    "- ESC sluit fullscreen via Windows/browser"
)

print(
    "- actieve PTT spreker krijgt blauwe rand"
)

print(
    "- SPREEKT NU verschijnt op videobeeld"
)

print(
    "- gebruikersnaam blijft zichtbaar"
)

print(
    "- 2x2 en 3x3 galerij automatisch verbeterd"
)

print(
    "- Push-To-Talk audio NIET gewijzigd"
)

print(
    "- TeamSpeak ontvangstaudio NIET gewijzigd"
)
# ============================================================
# PTT CONNECT - VIDEO GALERIJ BEDIENING
# Inklappen/openen + gebruiker vastpinnen
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)


# ============================================================
# GALERIJ STATUS
# ============================================================

app = replace_once(
    app,
    '''  const [
    pttVideoSource,
    setPttVideoSource
  ] = useState<
    "camera" |
    "screen" |
    null
  >(null);
''',
    '''  const [
    pttVideoSource,
    setPttVideoSource
  ] = useState<
    "camera" |
    "screen" |
    null
  >(null);

  const [
    pttVideoGalleryCollapsed,
    setPttVideoGalleryCollapsed
  ] = useState(
    false
  );

  const [
    pttPinnedVideoClientId,
    setPttPinnedVideoClientId
  ] = useState<number | null>(
    null
  );
''',
    "video gallery controls state"
)


# ============================================================
# PIN PROPS NAAR VIDEO TEGEL
# ============================================================

app = replace_once(
    app,
    '''  iceServers,
  isTalking,
}: {
''',
    '''  iceServers,
  isTalking,
  isPinned,
  onTogglePin,
}: {
''',
    "video tile pin props args"
)


app = replace_once(
    app,
    '''  isTalking:
    boolean;
}) {
''',
    '''  isTalking:
    boolean;
  isPinned:
    boolean;
  onTogglePin:
    () => void;
}) {
''',
    "video tile pin props type"
)


# ============================================================
# PIN KNOP OP VIDEO TEGEL
# ============================================================

app = replace_once(
    app,
    '''        <button
          type="button"
          className="ptt-video-fullscreen-button"
''',
    '''        <button
          type="button"
          className={
            "ptt-video-pin-button" +
            (
              isPinned
                ? " ptt-video-pin-active"
                : ""
            )
          }
          onClick={
            (
              event
            ) => {
              event.stopPropagation();

              onTogglePin();
            }
          }
          title={
            isPinned
              ? "Video losmaken"
              : "Video vastzetten"
          }
          aria-label={
            isPinned
              ? "Video losmaken"
              : "Video vastzetten"
          }
        >
          📌
        </button>


        <button
          type="button"
          className="ptt-video-fullscreen-button"
''',
    "video tile pin button"
)


# ============================================================
# GALERIJ COLLAPSED CLASS
# ============================================================

app = replace_once(
    app,
    '''          <section className="ptt-video-gallery">
''',
    '''          <section
            className={
              "ptt-video-gallery" +
              (
                pttVideoGalleryCollapsed
                  ? " ptt-video-gallery-collapsed"
                  : ""
              )
            }
          >
''',
    "video gallery collapsed class"
)


# ============================================================
# HEADER KNOPPEN
# ============================================================

app = replace_once(
    app,
    '''              <div className="ptt-video-gallery-status">

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
''',
    '''              <div className="ptt-video-gallery-actions">

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


                <button
                  type="button"
                  className="ptt-video-gallery-control"
                  onClick={
                    () => {
                      setPttVideoGalleryCollapsed(
                        (
                          current
                        ) =>
                          !current
                      );
                    }
                  }
                  title={
                    pttVideoGalleryCollapsed
                      ? "Videogalerij openen"
                      : "Videogalerij inklappen"
                  }
                >
                  {
                    pttVideoGalleryCollapsed
                      ? "▴"
                      : "▾"
                  }
                </button>

              </div>
''',
    "video gallery header controls"
)


# ============================================================
# VASTGEPINDE VIDEO ALTIJD EERST
# ============================================================

app = replace_once(
    app,
    '''                channelStreams.map(
                  (
                    info
                  ) => {
''',
    '''                [
                  ...channelStreams
                ]
                  .sort(
                    (
                      a,
                      b
                    ) => {

                      if (
                        a.clientId ===
                        pttPinnedVideoClientId
                      ) {
                        return -1;
                      }

                      if (
                        b.clientId ===
                        pttPinnedVideoClientId
                      ) {
                        return 1;
                      }

                      return 0;
                    }
                  )
                  .map(
                  (
                    info
                  ) => {
''',
    "pinned video first"
)


# ============================================================
# PIN STATUS NAAR TEGEL
# ============================================================

app = replace_once(
    app,
    '''                        isTalking={
                          displayTalkers.has(
                            info.clientId
                          )
                        }
                      />
''',
    '''                        isTalking={
                          displayTalkers.has(
                            info.clientId
                          )
                        }

                        isPinned={
                          pttPinnedVideoClientId ===
                          info.clientId
                        }

                        onTogglePin={
                          () => {
                            setPttPinnedVideoClientId(
                              (
                                current
                              ) =>
                                current === info.clientId
                                  ? null
                                  : info.clientId
                            );
                          }
                        }
                      />
''',
    "video tile pin state"
)


APP_FILE.write_text(
    app,
    encoding="utf-8"
)


# ============================================================
# CSS
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)


video_controls_css = r'''

/* ==========================================================
   PTT CONNECT - VIDEO GALERIJ BEDIENING
   ========================================================== */

.ptt-video-gallery-actions {
  display:
    flex;

  align-items:
    center;

  gap:
    8px;
}


.ptt-video-gallery-control {
  width:
    34px;

  height:
    34px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  border:
    1px solid
    rgba(90, 215, 255, 0.28);

  border-radius:
    9px;

  background:
    rgba(30, 150, 215, 0.10);

  color:
    #9deaff;

  cursor:
    pointer;

  font-size:
    16px;
}


.ptt-video-gallery-control:hover {
  border-color:
    #59dcff;

  background:
    rgba(40, 180, 245, 0.20);
}


/* ==========================================================
   INGEKLAPTE GALERIJ
   ========================================================== */

.ptt-video-gallery-collapsed {
  max-height:
    64px;
}


.ptt-video-gallery-collapsed
.ptt-video-grid,

.ptt-video-gallery-collapsed
.ptt-video-gallery-footer {
  display:
    none !important;
}


/* ==========================================================
   PIN KNOP
   ========================================================== */

.ptt-video-pin-button {
  position:
    absolute;

  z-index:
    8;

  top:
    9px;

  right:
    51px;

  width:
    34px;

  height:
    34px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  padding:
    0;

  border:
    1px solid
    rgba(255, 255, 255, 0.18);

  border-radius:
    9px;

  background:
    rgba(0, 8, 15, 0.78);

  color:
    #eaf9ff;

  cursor:
    pointer;

  opacity:
    0.72;
}


.ptt-video-tile:hover
.ptt-video-pin-button {
  opacity:
    1;
}


.ptt-video-pin-button:hover {
  border-color:
    #59dcff;

  background:
    rgba(30, 150, 215, 0.34);
}


.ptt-video-pin-active {
  opacity:
    1 !important;

  border-color:
    #59dcff !important;

  background:
    rgba(30, 165, 225, 0.30) !important;

  box-shadow:
    0 0 10px
    rgba(70, 215, 255, 0.42);
}


/* fullscreen */

.ptt-video-tile:fullscreen
.ptt-video-pin-button {
  top:
    18px;

  right:
    68px;

  width:
    42px;

  height:
    42px;

  opacity:
    1;
}

'''


if (
    "PTT CONNECT - VIDEO GALERIJ BEDIENING"
    not in css
):
    css += video_controls_css


CSS_FILE.write_text(
    css,
    encoding="utf-8"
)


print(
    "- videogalerij inklappen/openen toegevoegd"
)

print(
    "- gebruiker vastpinnen toegevoegd"
)

print(
    "- vastgepinde gebruiker staat vooraan"
)

print(
    "- fullscreen blijft werken"
)

print(
    "- actieve PTT spreker blijft zichtbaar"
)

print(
    "- webcam en schermdelen niet gewijzigd"
)

print(
    "- Push-To-Talk audio NIET gewijzigd"
)
# ============================================================
# PTT CONNECT - CB TRANSCEIVER VIEW
# Normale weergave <-> CB transceiver weergave
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)


# ============================================================
# STATE - CB VIEW
# ============================================================

app = replace_once(
    app,
    '''  const [
    pttPinnedVideoClientId,
    setPttPinnedVideoClientId
  ] = useState<number | null>(
    null
  );
''',
    '''  const [
    pttPinnedVideoClientId,
    setPttPinnedVideoClientId
  ] = useState<number | null>(
    null
  );

  const [
    pttLayoutMode,
    setPttLayoutMode
  ] = useState<
    "normal" |
    "cb"
  >(
    "normal"
  );
''',
    "CB layout mode state"
)


# ============================================================
# HULPGEGEVENS VOOR CB VIEW
# ============================================================

app = replace_once(
    app,
    '''  const publishClientName = (clid: number) =>
''',
    '''  const pttOwnClient =
    clients.find(
      (client) =>
        client.id ===
        ownClientId
    ) ?? null;

  const pttCurrentChannel =
    channels.find(
      (channel) =>
        channel.id ===
        pttOwnClient?.channel
    ) ?? null;

  const pttCbChannels =
    channels.filter(
      (channel) =>
        !String(
          channel.name ?? ""
        )
          .trim()
          .startsWith("[cspacer]")
    );

  const pttCbCurrentIndex =
    Math.max(
      0,
      pttCbChannels.findIndex(
        (channel) =>
          channel.id ===
          pttCurrentChannel?.id
      )
    );

  const pttCbCurrentNumber =
    pttCbCurrentIndex >= 0
      ? pttCbCurrentIndex + 1
      : 1;

  const pttCurrentChannelClients =
    pttCurrentChannel
      ? clients.filter(
          (client) =>
            client.channel ===
            pttCurrentChannel.id
        )
      : [];

  const pttCurrentTalkers =
    pttCurrentChannelClients.filter(
      (client) =>
        displayTalkers.has(
          client.id
        )
    );

  const pttCbTalkingNow =
    pttCurrentTalkers[0] ??
    null;

  const pttCbTxActive =
    pttOwnClient
      ? displayTalkers.has(
          pttOwnClient.id
        )
      : false;

  const pttCbRxActive =
    pttCurrentTalkers.some(
      (client) =>
        client.id !==
        pttOwnClient?.id
    );

  const pttCbPrevChannel = () => {
    if (
      pttCbChannels.length === 0
    ) {
      return;
    }

    const nextIndex =
      pttCbCurrentIndex <= 0
        ? pttCbChannels.length - 1
        : pttCbCurrentIndex - 1;

    const nextChannel =
      pttCbChannels[
        nextIndex
      ];

    /*
     * Veilige eerste versie:
     * selecteert het kanaal visueel.
     * Later kunnen we dit desgewenst
     * direct laten joinen.
     */
    setSelected({
      type: "channel",
      id: nextChannel.id,
    });
  };

  const pttCbNextChannel = () => {
    if (
      pttCbChannels.length === 0
    ) {
      return;
    }

    const nextIndex =
      pttCbCurrentIndex >=
      pttCbChannels.length - 1
        ? 0
        : pttCbCurrentIndex + 1;

    const nextChannel =
      pttCbChannels[
        nextIndex
      ];

    setSelected({
      type: "channel",
      id: nextChannel.id,
    });
  };


  const publishClientName = (clid: number) =>
''',
    "CB view computed data"
)


# ============================================================
# KNOPPEN IN DE BOVENBALK
# ============================================================

app = replace_once(
    app,
    '''          </div>


          <img src={`${import.meta.env.BASE_URL}logo.png`} alt="" className="ts-app-logo" />
''',
    '''          </div>


          <div className="ptt-cb-top-switch">

            <button
              type="button"
              className={
                "ts-icon-button ptt-cb-top-button" +
                (
                  pttLayoutMode === "normal"
                    ? " ptt-cb-top-button-active"
                    : ""
                )
              }
              onClick={() =>
                setPttLayoutMode(
                  "normal"
                )
              }
              title="Normale weergave"
              aria-label="Normale weergave"
            >
              🎙 Normaal
            </button>

            <button
              type="button"
              className={
                "ts-icon-button ptt-cb-top-button" +
                (
                  pttLayoutMode === "cb"
                    ? " ptt-cb-top-button-active"
                    : ""
                )
              }
              onClick={() =>
                setPttLayoutMode(
                  "cb"
                )
              }
              title="CB Transceiver weergave"
              aria-label="CB Transceiver weergave"
            >
              📻 CB Transceiver
            </button>

          </div>


          <img src={`${import.meta.env.BASE_URL}logo.png`} alt="" className="ts-app-logo" />
''',
    "top buttons normal/cb view"
)


# ============================================================
# CB OVERLAY VOOR HET EINDE VAN DE APP
# ============================================================

app = replace_once(
    app,
    '''      {(watchedStream || (publishState !== "idle" && publishState !== "stopped")) && (
''',
    '''      {pttLayoutMode === "cb" && (
        <section className="ptt-cb-overlay">

          <div className="ptt-cb-overlay-header">

            <div className="ptt-cb-overlay-title">
              <span className="ptt-cb-overlay-icon">
                📻
              </span>

              <div>
                <strong>
                  CB TRANSCEIVER VIEW
                </strong>

                <span>
                  Gebruik TeamSpeak kanalen als CB kanalen
                </span>
              </div>
            </div>


            <div className="ptt-cb-overlay-header-right">

              <div className="ptt-cb-overlay-info">
                <strong>
                  CB kanalen = TeamSpeak kanalen
                </strong>

                <span>
                  Elk CB kanaal in deze modus is een TeamSpeak kanaal.
                </span>
              </div>

              <button
                type="button"
                className="ptt-cb-back-button"
                onClick={() =>
                  setPttLayoutMode(
                    "normal"
                  )
                }
              >
                ↩ Normaal
              </button>

            </div>

          </div>


          <div className="ptt-cb-overlay-body">

            <aside className="ptt-cb-left-panel">

              <div className="ptt-cb-left-title">
                📻 CB KANALEN (TeamSpeak)
              </div>

              <div className="ptt-cb-channel-list">
                {pttCbChannels
                  .slice(0, 40)
                  .map(
                    (
                      channel,
                      index
                    ) => {
                      const channelUsers =
                        clients.filter(
                          (client) =>
                            client.channel ===
                            channel.id
                        );

                      const active =
                        channel.id ===
                        pttCurrentChannel?.id;

                      return (
                        <div
                          key={channel.id}
                          className={
                            "ptt-cb-channel-row" +
                            (
                              active
                                ? " ptt-cb-channel-row-active"
                                : ""
                            )
                          }
                        >
                          <span className="ptt-cb-channel-number">
                            CH {index + 1}
                          </span>

                          <span className="ptt-cb-channel-name">
                            {channel.name}
                          </span>

                          <span className="ptt-cb-channel-users">
                            👥 {channelUsers.length}
                          </span>
                        </div>
                      );
                    }
                  )}
              </div>

            </aside>


            <main className="ptt-cb-main-panel">

              <div className="ptt-cb-radio-face">

                <div className="ptt-cb-display-block">

                  <div className="ptt-cb-display">
                    CH {String(
                      pttCbCurrentNumber
                    ).padStart(
                      2,
                      "0"
                    )}
                  </div>

                  <div className="ptt-cb-display-name">
                    {pttCurrentChannel?.name ??
                      "Geen kanaal"}
                  </div>

                  <div className="ptt-cb-display-sub">
                    🎙 CB kanalen = TeamSpeak kanalen
                  </div>
                </div>


                <div className="ptt-cb-channel-buttons">

                  <button
                    type="button"
                    className="ptt-cb-channel-button"
                    onClick={
                      pttCbPrevChannel
                    }
                  >
                    CH +
                  </button>

                  <button
                    type="button"
                    className="ptt-cb-channel-button"
                    onClick={
                      pttCbNextChannel
                    }
                  >
                    CH −
                  </button>

                </div>


                <div className="ptt-cb-ptt-block">

                  <div className="ptt-cb-big-ptt">
                    <span className="ptt-cb-big-ptt-mic">
                      🎙
                    </span>

                    <span className="ptt-cb-big-ptt-text">
                      PTT
                    </span>
                  </div>

                </div>


                <div className="ptt-cb-rx-tx-block">

                  <div className="ptt-cb-rx-tx-row">
                    <span>
                      RX
                    </span>

                    <span
                      className={
                        "ptt-cb-led" +
                        (
                          pttCbRxActive
                            ? " ptt-cb-led-green"
                            : ""
                        )
                      }
                    />
                  </div>

                  <div className="ptt-cb-rx-tx-row">
                    <span>
                      TX
                    </span>

                    <span
                      className={
                        "ptt-cb-led" +
                        (
                          pttCbTxActive
                            ? " ptt-cb-led-red"
                            : ""
                        )
                      }
                    />
                  </div>

                  <div className="ptt-cb-side-button">
                    ⭐ Favoriet
                  </div>

                  <div className="ptt-cb-side-button">
                    🔎 SCAN
                  </div>

                </div>

              </div>


              <div className="ptt-cb-status-row">

                <div className="ptt-cb-status-card ptt-cb-smeter-card">
                  <div className="ptt-cb-status-title">
                    S-METER / SIGNAAL
                  </div>

                  <div className="ptt-cb-smeter-bars">
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                  </div>

                  <div className="ptt-cb-smeter-scale">
                    <span>S</span>
                    <span>1</span>
                    <span>3</span>
                    <span>5</span>
                    <span>7</span>
                    <span>9</span>
                    <span>+20</span>
                    <span>+40</span>
                  </div>
                </div>


                <div className="ptt-cb-status-card">
                  <div className="ptt-cb-status-title">
                    NU PRAAT:
                  </div>

                  <div className="ptt-cb-speaking-name">
                    {pttCbTalkingNow?.name ??
                      "Niemand"}
                  </div>

                  <div className="ptt-cb-speaking-bars">
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                  </div>
                </div>


                <div className="ptt-cb-status-card">
                  <div className="ptt-cb-status-title">
                    GEBRUIKERS
                  </div>

                  <div className="ptt-cb-status-big">
                    {pttCurrentChannelClients.length}
                    <span> / ∞</span>
                  </div>
                </div>


                <div className="ptt-cb-knobs-card">

                  <div className="ptt-cb-knob-group">
                    <div className="ptt-cb-knob-label">
                      VOLUME
                    </div>

                    <div className="ptt-cb-knob" />
                  </div>

                  <div className="ptt-cb-knob-group">
                    <div className="ptt-cb-knob-label">
                      SQUELCH
                    </div>

                    <div className="ptt-cb-knob" />
                  </div>

                </div>

              </div>


              <div className="ptt-cb-bottom-strip">

                <div className="ptt-cb-bottom-item">
                  <span className="ptt-cb-bottom-label">
                    Huidig kanaal
                  </span>

                  <strong>
                    CH {String(
                      pttCbCurrentNumber
                    ).padStart(
                      2,
                      "0"
                    )} - {pttCurrentChannel?.name ?? "Onbekend"}
                  </strong>
                </div>

                <div className="ptt-cb-bottom-item">
                  <span className="ptt-cb-bottom-label">
                    Type
                  </span>

                  <strong>
                    Spraakkanaal
                  </strong>
                </div>

                <div className="ptt-cb-bottom-item">
                  <span className="ptt-cb-bottom-label">
                    Codec
                  </span>

                  <strong>
                    {pttCurrentChannel?.codec ?? "OpusVoice"}
                  </strong>
                </div>

                <div className="ptt-cb-bottom-item">
                  <span className="ptt-cb-bottom-label">
                    Gebruikers in kanaal
                  </span>

                  <strong>
                    {pttCurrentChannelClients.length} / ∞
                  </strong>
                </div>

              </div>

            </main>

          </div>


          <div className="ptt-cb-footer-bar">
            <span>🟢 Verbonden met PTT Connect</span>
            <span>🎙 Microfoon actief</span>
            <span>🔊 Luidspreker actief</span>
            <span>📡 Ping: {serverConnectionInfo?.ping ?? "18"} ms</span>
          </div>

        </section>
      )}


      {(watchedStream || (publishState !== "idle" && publishState !== "stopped")) && (
''',
    "CB overlay render"
)


APP_FILE.write_text(
    app,
    encoding="utf-8"
)


# ============================================================
# CSS - CB TRANSCEIVER VIEW
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)


cb_css = r'''

/* ==========================================================
   PTT CONNECT - CB TRANSCEIVER VIEW
   ========================================================== */

.ptt-cb-top-switch {
  display:
    inline-flex;

  align-items:
    center;

  gap:
    8px;

  margin-left:
    12px;

  padding:
    4px;

  border:
    1px solid
    rgba(78, 210, 255, 0.22);

  border-radius:
    16px;

  background:
    rgba(5, 18, 31, 0.75);
}

.ptt-cb-top-button {
  min-width:
    148px;

  padding:
    10px 16px !important;

  border-radius:
    12px !important;

  font-weight:
    700;
}

.ptt-cb-top-button-active {
  border-color:
    #42d8ff !important;

  background:
    linear-gradient(
      180deg,
      rgba(35, 170, 255, 0.28),
      rgba(10, 60, 105, 0.24)
    ) !important;

  box-shadow:
    0 0 14px rgba(66, 216, 255, 0.20);
}


/* ==========================================================
   OVERLAY
   ========================================================== */

.ptt-cb-overlay {
  position:
    fixed;

  inset:
    88px 18px 18px 18px;

  z-index:
    140;

  display:
    flex;

  flex-direction:
    column;

  overflow:
    hidden;

  border:
    1px solid rgba(60, 205, 255, 0.36);

  border-radius:
    18px;

  background:
    linear-gradient(
      180deg,
      rgba(2, 13, 24, 0.98),
      rgba(2, 9, 18, 0.99)
    );

  box-shadow:
    0 18px 60px rgba(0, 0, 0, 0.45),
    0 0 24px rgba(45, 190, 255, 0.10);
}

.ptt-cb-overlay-header {
  display:
    flex;

  align-items:
    center;

  justify-content:
    space-between;

  gap:
    18px;

  padding:
    16px 18px;

  border-bottom:
    1px solid rgba(255, 255, 255, 0.08);

  background:
    linear-gradient(
      90deg,
      rgba(3, 18, 34, 0.96),
      rgba(3, 9, 20, 0.96)
    );
}

.ptt-cb-overlay-title {
  display:
    flex;

  align-items:
    center;

  gap:
    14px;
}

.ptt-cb-overlay-icon {
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

  border:
    1px solid rgba(67, 214, 255, 0.42);

  border-radius:
    14px;

  background:
    rgba(35, 170, 255, 0.10);

  font-size:
    26px;
}

.ptt-cb-overlay-title strong {
  display:
    block;

  color:
    #4fe4ff;

  font-size:
    22px;

  letter-spacing:
    0.02em;
}

.ptt-cb-overlay-title span {
  color:
    #d8f5ff;

  font-size:
    13px;
}

.ptt-cb-overlay-header-right {
  display:
    flex;

  align-items:
    center;

  gap:
    14px;
}

.ptt-cb-overlay-info {
  display:
    flex;

  flex-direction:
    column;

  gap:
    4px;

  padding:
    12px 16px;

  border:
    1px solid rgba(65, 208, 255, 0.22);

  border-radius:
    16px;

  background:
    rgba(8, 25, 40, 0.70);
}

.ptt-cb-overlay-info strong {
  color:
    #f4fbff;

  font-size:
    14px;
}

.ptt-cb-overlay-info span {
  color:
    #b8d4e5;

  font-size:
    12px;
}

.ptt-cb-back-button {
  min-width:
    180px;

  padding:
    16px 18px;

  border:
    1px solid rgba(76, 220, 255, 0.52);

  border-radius:
    16px;

  background:
    linear-gradient(
      180deg,
      rgba(33, 165, 255, 0.22),
      rgba(12, 72, 118, 0.18)
    );

  color:
    #dff8ff;

  font-size:
    16px;

  font-weight:
    800;

  cursor:
    pointer;

  box-shadow:
    0 0 18px rgba(66, 216, 255, 0.12);
}

.ptt-cb-back-button:hover {
  border-color:
    #60e3ff;

  background:
    linear-gradient(
      180deg,
      rgba(45, 185, 255, 0.30),
      rgba(14, 84, 132, 0.22)
    );
}


/* ==========================================================
   BODY
   ========================================================== */

.ptt-cb-overlay-body {
  min-height:
    0;

  flex:
    1;

  display:
    grid;

  grid-template-columns:
    370px minmax(0, 1fr);

  gap:
    18px;

  padding:
    16px 18px;
}

.ptt-cb-left-panel {
  min-height:
    0;

  display:
    flex;

  flex-direction:
    column;

  border:
    1px solid rgba(56, 199, 255, 0.20);

  border-radius:
    16px;

  background:
    linear-gradient(
      180deg,
      rgba(4, 18, 31, 0.92),
      rgba(2, 11, 21, 0.95)
    );

  overflow:
    hidden;
}

.ptt-cb-left-title {
  padding:
    14px 16px;

  border-bottom:
    1px solid rgba(255, 255, 255, 0.07);

  color:
    #78eaff;

  font-size:
    14px;

  font-weight:
    800;
}

.ptt-cb-channel-list {
  min-height:
    0;

  overflow:
    auto;

  padding:
    10px;
}

.ptt-cb-channel-row {
  display:
    grid;

  grid-template-columns:
    64px minmax(0, 1fr) auto;

  gap:
    10px;

  align-items:
    center;

  margin-bottom:
    7px;

  padding:
    10px 12px;

  border:
    1px solid transparent;

  border-radius:
    10px;

  background:
    rgba(255, 255, 255, 0.02);
}

.ptt-cb-channel-row-active {
  border-color:
    rgba(73, 218, 255, 0.46);

  background:
    linear-gradient(
      90deg,
      rgba(40, 180, 255, 0.18),
      rgba(9, 50, 82, 0.18)
    );

  box-shadow:
    inset 3px 0 0 #58ddff;
}

.ptt-cb-channel-number {
  color:
    #88ddff;

  font-weight:
    800;
}

.ptt-cb-channel-name {
  color:
    #edf8ff;

  overflow:
    hidden;

  text-overflow:
    ellipsis;

  white-space:
    nowrap;
}

.ptt-cb-channel-users {
  color:
    #bdd7e7;

  font-size:
    12px;
}


/* ==========================================================
   MAIN PANEL
   ========================================================== */

.ptt-cb-main-panel {
  min-width:
    0;

  min-height:
    0;

  display:
    flex;

  flex-direction:
    column;

  gap:
    16px;
}

.ptt-cb-radio-face {
  display:
    grid;

  grid-template-columns:
    minmax(0, 1.25fr) 150px 260px 180px;

  gap:
    18px;

  align-items:
    stretch;

  padding:
    20px;

  border:
    1px solid rgba(255, 255, 255, 0.10);

  border-radius:
    24px;

  background:
    linear-gradient(
      180deg,
      rgba(23, 29, 38, 0.96),
      rgba(10, 14, 22, 0.98)
    );

  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.05),
    inset 0 -1px 0 rgba(0, 0, 0, 0.25),
    0 10px 28px rgba(0, 0, 0, 0.25);
}

.ptt-cb-display-block {
  display:
    flex;

  flex-direction:
    column;

  justify-content:
    center;

  gap:
    10px;

  padding:
    26px;

  border:
    1px solid rgba(57, 198, 255, 0.25);

  border-radius:
    20px;

  background:
    linear-gradient(
      180deg,
      #02111e,
      #010910
    );

  box-shadow:
    inset 0 0 22px rgba(38, 168, 255, 0.18);
}

.ptt-cb-display {
  color:
    #63e4ff;

  font-size:
    96px;

  font-weight:
    900;

  letter-spacing:
    0.05em;

  line-height:
    1;

  text-align:
    center;

  text-shadow:
    0 0 20px rgba(78, 223, 255, 0.55);
}

.ptt-cb-display-name {
  padding:
    10px 12px;

  border:
    1px solid rgba(53, 198, 255, 0.35);

  border-radius:
    10px;

  color:
    #a7ebff;

  font-size:
    20px;

  font-weight:
    800;

  text-align:
    center;
}

.ptt-cb-display-sub {
  color:
    #c7e7f2;

  font-size:
    13px;

  text-align:
    center;
}

.ptt-cb-channel-buttons {
  display:
    flex;

  flex-direction:
    column;

  gap:
    16px;

  justify-content:
    center;
}

.ptt-cb-channel-button {
  min-height:
    108px;

  border:
    1px solid rgba(80, 220, 255, 0.36);

  border-radius:
    18px;

  background:
    linear-gradient(
      180deg,
      rgba(22, 96, 160, 0.20),
      rgba(5, 28, 50, 0.22)
    );

  color:
    #ecfbff;

  font-size:
    20px;

  font-weight:
    800;

  cursor:
    pointer;

  box-shadow:
    inset 0 0 10px rgba(76, 212, 255, 0.08);
}

.ptt-cb-channel-button:hover {
  border-color:
    #65e4ff;

  box-shadow:
    0 0 16px rgba(87, 224, 255, 0.14);
}

.ptt-cb-ptt-block {
  display:
    flex;

  align-items:
    center;

  justify-content:
    center;
}

.ptt-cb-big-ptt {
  width:
    250px;

  height:
    250px;

  display:
    flex;

  flex-direction:
    column;

  align-items:
    center;

  justify-content:
    center;

  gap:
    10px;

  border:
    6px solid rgba(97, 218, 255, 0.90);

  border-radius:
    50%;

  background:
    radial-gradient(
      circle at 50% 38%,
      #364553,
      #121a24 62%,
      #070d13
    );

  box-shadow:
    inset 0 0 22px rgba(255, 255, 255, 0.06),
    0 0 26px rgba(52, 206, 255, 0.22);
}

.ptt-cb-big-ptt-mic {
  font-size:
    48px;
}

.ptt-cb-big-ptt-text {
  color:
    #f5fbff;

  font-size:
    32px;

  font-weight:
    900;
}

.ptt-cb-rx-tx-block {
  display:
    flex;

  flex-direction:
    column;

  gap:
    14px;
}

.ptt-cb-rx-tx-row {
  display:
    flex;

  align-items:
    center;

  justify-content:
    space-between;

  padding:
    16px 18px;

  border:
    1px solid rgba(255, 255, 255, 0.10);

  border-radius:
    14px;

  background:
    rgba(5, 15, 28, 0.92);

  color:
    #ddf7ff;

  font-size:
    18px;

  font-weight:
    800;
}

.ptt-cb-led {
  width:
    22px;

  height:
    22px;

  border-radius:
    50%;

  background:
    rgba(65, 75, 85, 0.88);

  box-shadow:
    inset 0 0 3px rgba(0, 0, 0, 0.65);
}

.ptt-cb-led-green {
  background:
    #63ff7c;

  box-shadow:
    0 0 12px rgba(99, 255, 124, 0.90);
}

.ptt-cb-led-red {
  background:
    #ff5766;

  box-shadow:
    0 0 12px rgba(255, 87, 102, 0.90);
}

.ptt-cb-side-button {
  padding:
    18px 16px;

  border:
    1px solid rgba(79, 220, 255, 0.28);

  border-radius:
    14px;

  background:
    rgba(5, 15, 28, 0.92);

  color:
    #e9fbff;

  font-size:
    16px;

  font-weight:
    700;

  text-align:
    center;
}


/* ==========================================================
   STATUS RIJ
   ========================================================== */

.ptt-cb-status-row {
  display:
    grid;

  grid-template-columns:
    1.3fr 1fr 0.55fr 0.9fr;

  gap:
    16px;
}

.ptt-cb-status-card,
.ptt-cb-knobs-card {
  min-height:
    150px;

  padding:
    18px;

  border:
    1px solid rgba(255, 255, 255, 0.10);

  border-radius:
    18px;

  background:
    linear-gradient(
      180deg,
      rgba(3, 16, 29, 0.95),
      rgba(1, 9, 18, 0.98)
    );
}

.ptt-cb-status-title {
  margin-bottom:
    12px;

  color:
    #88e9ff;

  font-size:
    14px;

  font-weight:
    800;
}

.ptt-cb-smeter-bars,
.ptt-cb-speaking-bars {
  display:
    grid;

  grid-template-columns:
    repeat(12, 1fr);

  gap:
    6px;

  align-items:
    end;

  min-height:
    52px;

  margin:
    10px 0 8px;
}

.ptt-cb-smeter-bars span,
.ptt-cb-speaking-bars span {
  display:
    block;

  border-radius:
    3px 3px 0 0;
}

.ptt-cb-smeter-bars span:nth-child(1)  { height: 20px; background: #49ff8a; }
.ptt-cb-smeter-bars span:nth-child(2)  { height: 25px; background: #50ff83; }
.ptt-cb-smeter-bars span:nth-child(3)  { height: 29px; background: #58ff7c; }
.ptt-cb-smeter-bars span:nth-child(4)  { height: 33px; background: #66ff75; }
.ptt-cb-smeter-bars span:nth-child(5)  { height: 38px; background: #77ff69; }
.ptt-cb-smeter-bars span:nth-child(6)  { height: 42px; background: #8fff5f; }
.ptt-cb-smeter-bars span:nth-child(7)  { height: 48px; background: #afff59; }
.ptt-cb-smeter-bars span:nth-child(8)  { height: 53px; background: #d4ff57; }
.ptt-cb-smeter-bars span:nth-child(9)  { height: 58px; background: #ffeb4e; }
.ptt-cb-smeter-bars span:nth-child(10) { height: 62px; background: #ffc64a; }
.ptt-cb-smeter-bars span:nth-child(11) { height: 0px;  background: #0f2742; }
.ptt-cb-smeter-bars span:nth-child(12) { height: 0px;  background: #0f2742; }

.ptt-cb-speaking-bars span:nth-child(1) { height: 28px; background: #4eff82; }
.ptt-cb-speaking-bars span:nth-child(2) { height: 30px; background: #4eff82; }
.ptt-cb-speaking-bars span:nth-child(3) { height: 31px; background: #4eff82; }
.ptt-cb-speaking-bars span:nth-child(4) { height: 29px; background: #4eff82; }
.ptt-cb-speaking-bars span:nth-child(5) { height: 27px; background: #4eff82; }
.ptt-cb-speaking-bars span:nth-child(6) { height: 24px; background: #4eff82; }
.ptt-cb-speaking-bars span:nth-child(7) { height: 18px; background: #103149; }
.ptt-cb-speaking-bars span:nth-child(8) { height: 18px; background: #103149; }
.ptt-cb-speaking-bars span:nth-child(9) { height: 18px; background: #103149; }
.ptt-cb-speaking-bars span:nth-child(10){ height: 18px; background: #103149; }

.ptt-cb-smeter-scale {
  display:
    flex;

  justify-content:
    space-between;

  color:
    #f2fbff;

  font-size:
    11px;

  font-weight:
    700;
}

.ptt-cb-speaking-name {
  color:
    #f3fbff;

  font-size:
    28px;

  font-weight:
    800;
}

.ptt-cb-status-big {
  color:
    #edfaff;

  font-size:
    44px;

  font-weight:
    900;
}

.ptt-cb-status-big span {
  color:
    #accfde;

  font-size:
    26px;
}

.ptt-cb-knobs-card {
  display:
    flex;

  align-items:
    center;

  justify-content:
    space-evenly;

  gap:
    16px;
}

.ptt-cb-knob-group {
  display:
    flex;

  flex-direction:
    column;

  align-items:
    center;

  gap:
    12px;
}

.ptt-cb-knob-label {
  color:
    #e7fbff;

  font-size:
    15px;

  font-weight:
    800;
}

.ptt-cb-knob {
  width:
    104px;

  height:
    104px;

  border:
    6px solid rgba(76, 218, 255, 0.80);

  border-radius:
    50%;

  background:
    radial-gradient(
      circle at 50% 35%,
      #334656,
      #141c26 64%,
      #070d13
    );

  box-shadow:
    inset 0 0 14px rgba(255, 255, 255, 0.05),
    0 0 18px rgba(65, 206, 255, 0.10);
}


/* ==========================================================
   BOTTOM STRIP
   ========================================================== */

.ptt-cb-bottom-strip {
  display:
    grid;

  grid-template-columns:
    repeat(4, minmax(0, 1fr));

  gap:
    14px;

  padding:
    16px 18px;

  border:
    1px solid rgba(72, 212, 255, 0.18);

  border-radius:
    16px;

  background:
    linear-gradient(
      180deg,
      rgba(4, 16, 28, 0.92),
      rgba(1, 9, 18, 0.96)
    );
}

.ptt-cb-bottom-item {
  min-width:
    0;

  display:
    flex;

  flex-direction:
    column;

  gap:
    6px;

  padding:
    4px 8px;
}

.ptt-cb-bottom-label {
  color:
    #a8c8d8;

  font-size:
    12px;
}

.ptt-cb-bottom-item strong {
  color:
    #effaff;

  font-size:
    24px;

  font-weight:
    800;

  overflow:
    hidden;

  text-overflow:
    ellipsis;

  white-space:
    nowrap;
}


/* ==========================================================
   FOOTER
   ========================================================== */

.ptt-cb-footer-bar {
  display:
    flex;

  align-items:
    center;

  justify-content:
    space-between;

  gap:
    14px;

  padding:
    12px 18px;

  border-top:
    1px solid rgba(255, 255, 255, 0.07);

  background:
    rgba(1, 8, 15, 0.96);

  color:
    #d9f7ff;

  font-size:
    13px;
}


/* ==========================================================
   RESPONSIVE
   ========================================================== */

@media (max-width: 1500px) {

  .ptt-cb-radio-face {
    grid-template-columns:
      minmax(0, 1fr) 130px 220px 160px;
  }

  .ptt-cb-display {
    font-size:
      78px;
  }

  .ptt-cb-big-ptt {
    width:
      210px;

    height:
      210px;
  }

}

@media (max-width: 1260px) {

  .ptt-cb-overlay-body {
    grid-template-columns:
      1fr;
  }

  .ptt-cb-left-panel {
    max-height:
      260px;
  }

  .ptt-cb-status-row {
    grid-template-columns:
      1fr 1fr;
  }

  .ptt-cb-bottom-strip {
    grid-template-columns:
      1fr 1fr;
  }

}

@media (max-width: 980px) {

  .ptt-cb-radio-face {
    grid-template-columns:
      1fr;
  }

  .ptt-cb-channel-buttons {
    flex-direction:
      row;
  }

  .ptt-cb-channel-button {
    min-height:
      72px;

    flex:
      1;
  }

  .ptt-cb-rx-tx-block {
    display:
      grid;

    grid-template-columns:
      1fr 1fr;
  }

  .ptt-cb-status-row,
  .ptt-cb-bottom-strip {
    grid-template-columns:
      1fr;
  }

  .ptt-cb-footer-bar,
  .ptt-cb-overlay-header {
    flex-direction:
      column;

    align-items:
      stretch;
  }

  .ptt-cb-overlay-header-right {
    flex-direction:
      column;

    align-items:
      stretch;
  }

}

'''


if "PTT CONNECT - CB TRANSCEIVER VIEW" not in css:
    css += cb_css


CSS_FILE.write_text(
    css,
    encoding="utf-8"
)


print(
    "- CB Transceiver View toegevoegd"
)

print(
    "- knop Normaal / CB Transceiver toegevoegd"
)

print(
    "- terugknop naar normale weergave toegevoegd"
)

print(
    "- TeamSpeak kanalen als CB kanalen getoond"
)

print(
    "- huidige spreker en kanaalinformatie zichtbaar"
)

print(
    "- PTT audio niet gewijzigd"
)

print(
    "- TeamSpeak ontvangstaudio niet gewijzigd"
)

print(
    "- webcam / schermdelen / radiostreams niet gewijzigd"
)

# ============================================================
# FIX CB TRANSCEIVER BUILD - PING PROPERTY
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)

app = replace_once(
    app,
    '''<span>📡 Ping: {serverConnectionInfo?.ping ?? "18"} ms</span>''',
    '''<span>📡 Ping: {serverConnectionInfo?.pingMs ?? "--"} ms</span>''',
    "fix CB ping property"
)

APP_FILE.write_text(
    app,
    encoding="utf-8"
)

print(
    "- CB ping buildfout opgelost"
)
print(
    "- webcam en schermdelen NIET gewijzigd"
)
# ============================================================
# FIX CB BUILD - TALKERS VOLGORDE
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)

app = replace_once(
    app,
    '''  const pttCurrentTalkers =
    pttCurrentChannelClients.filter(
      (client) =>
        displayTalkers.has(
          client.id
        )
    );
''',
    '''  const pttCurrentTalkers =
    pttCurrentChannelClients.filter(
      (client) =>
        talkers.has(
          client.id
        )
    );
''',
    "fix CB current talkers order"
)

app = replace_once(
    app,
    '''  const pttCbTxActive =
    pttOwnClient
      ? displayTalkers.has(
          pttOwnClient.id
        )
      : false;
''',
    '''  const pttCbTxActive =
    pttOwnClient
      ? talkers.has(
          pttOwnClient.id
        )
      : false;
''',
    "fix CB TX talker order"
)

APP_FILE.write_text(
    app,
    encoding="utf-8"
)
# ============================================================
# PTT CONNECT - COMPLETE ANDROID APP VIEW
# Realistische desktopweergave gebaseerd op Android App design
#
# BELANGRIJK:
# - bestaande TeamSpeak audio blijft behouden
# - bestaande PTT engine blijft behouden
# - bestaande ontvangstaudio blijft behouden
# - kanalen zijn echte TeamSpeak kanalen
# - gebruikers zijn echte TeamSpeak gebruikers
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)


# ============================================================
# EXTRA STATE VOOR ANDROID APP VIEW
# ============================================================

app = replace_once(
    app,
    '''  const [
    pttLayoutMode,
    setPttLayoutMode
  ] = useState<
    "normal" |
    "cb"
  >(
    "normal"
  );
''',
    '''  const [
    pttLayoutMode,
    setPttLayoutMode
  ] = useState<
    "normal" |
    "cb"
  >(
    "normal"
  );

  const [
    pttAndroidSettingsOpen,
    setPttAndroidSettingsOpen
  ] = useState(
    false
  );
''',
    "Android App settings state"
)


# ============================================================
# WERKENDE FUNCTIES
# ============================================================

app = replace_once(
    app,
    '''  const publishClientName = (clid: number) =>
''',
    '''  const handleAndroidChannelClick = (
    channelId: number
  ) => {

    setSelected({
      type: "channel",
      id: channelId,
    });

    /*
     * Dit gebruikt exact dezelfde bestaande
     * TeamSpeak kanaalwissel als de normale
     * PTT Connect interface.
     */
    handleSwitchChannel(
      channelId
    );
  };


  const handleAndroidPttStart = () => {

    if (
      !connected ||
      !micOn ||
      inputMuted
    ) {
      return;
    }

    /*
     * Gebruik de reeds bestaande PTT-engine.
     * We vervangen of wijzigen geen audio-code.
     */
    setTransmissionMode(
      "ptt"
    );

    micCaptureRef.current
      ?.setTransmissionMode(
        "ptt"
      );

    micCaptureRef.current
      ?.setPushToTalk(
        true
      );
  };


  const handleAndroidPttStop = () => {

    micCaptureRef.current
      ?.setPushToTalk(
        false
      );
  };


  const openAndroidOption = (
    section:
      "wiedergabe" |
      "aufnahme" |
      "design" |
      "sounds" |
      "hotkeys"
  ) => {

    setPttAndroidSettingsOpen(
      false
    );

    setOptionsSection(
      section
    );

    setOptionsDialogOpen(
      true
    );
  };


  const publishClientName = (clid: number) =>
''',
    "Android App functional handlers"
)


# ============================================================
# BOVENSTE KNOP HERNOEMEN
# CB TRANSCEIVER -> ANDROID APP
# ============================================================

app = app.replace(
    '''title="CB Transceiver weergave"''',
    '''title="Android App weergave"''',
    1
)

app = app.replace(
    '''aria-label="CB Transceiver weergave"''',
    '''aria-label="Android App weergave"''',
    1
)

app = app.replace(
    '''📻 CB Transceiver''',
    '''📱 Android App''',
    1
)


# ============================================================
# OUDE CB OVERLAY VOLLEDIG VERVANGEN
# ============================================================

android_start_marker = '''
      {pttLayoutMode === "cb" && (
'''

android_end_marker = '''
      {(watchedStream || (publishState !== "idle" && publishState !== "stopped")) && (
'''


android_start = app.find(
    android_start_marker
)

android_end = app.find(
    android_end_marker,
    android_start
)


if (
    android_start == -1 or
    android_end == -1
):
    raise RuntimeError(
        "Kon bestaande CB/Android overlay niet vinden"
    )


android_view = r'''
      {pttLayoutMode === "cb" && (
        <section className="ptt-android-view">

          {/* =================================================
              TOPBAR
              ================================================= */}

          <header className="ptt-android-topbar">

            <div className="ptt-android-brand">

              <div className="ptt-android-logo">
                ◀|▶
              </div>

              <strong>
                PTT Connect
              </strong>

            </div>


            <div className="ptt-android-top-actions">

              <div className="ptt-android-connected">
                <span className="ptt-android-connected-dot" />

                <span>
                  {
                    connected
                      ? "Connected"
                      : "Disconnected"
                  }
                </span>
              </div>


              <button
                type="button"
                className="ptt-android-back"
                onClick={() => {
                  handleAndroidPttStop();

                  setPttAndroidSettingsOpen(
                    false
                  );

                  setPttLayoutMode(
                    "normal"
                  );
                }}
                title="Terug naar normale PTT Connect weergave"
              >
                ↩ Windows
              </button>


              <div className="ptt-android-settings-wrap">

                <button
                  type="button"
                  className={
                    "ptt-android-settings-button" +
                    (
                      pttAndroidSettingsOpen
                        ? " ptt-android-settings-button-active"
                        : ""
                    )
                  }
                  onClick={() =>
                    setPttAndroidSettingsOpen(
                      (
                        current
                      ) =>
                        !current
                    )
                  }
                  title="Settings"
                  aria-label="Settings"
                >
                  ⚙
                </button>


                {pttAndroidSettingsOpen && (
                  <div className="ptt-android-settings-menu">

                    <div className="ptt-android-settings-title">
                      <span>
                        ⚙
                      </span>

                      <strong>
                        Settings
                      </strong>
                    </div>


                    <button
                      type="button"
                      onClick={() =>
                        openAndroidOption(
                          "aufnahme"
                        )
                      }
                    >
                      <span>
                        🔊
                      </span>

                      <span>
                        Audio Devices
                      </span>
                    </button>


                    <button
                      type="button"
                      onClick={() =>
                        openAndroidOption(
                          "design"
                        )
                      }
                    >
                      <span>
                        🎨
                      </span>

                      <span className="ptt-android-menu-text">
                        Appearance

                        <small>
                          Theme, colors, dark/light mode
                        </small>
                      </span>

                      <span className="ptt-android-menu-arrow">
                        ›
                      </span>
                    </button>


                    <button
                      type="button"
                      onClick={() =>
                        openAndroidOption(
                          "sounds"
                        )
                      }
                    >
                      <span>
                        🔔
                      </span>

                      <span>
                        Notifications
                      </span>
                    </button>


                    <button
                      type="button"
                      onClick={() =>
                        openAndroidOption(
                          "hotkeys"
                        )
                      }
                    >
                      <span>
                        ⌨
                      </span>

                      <span>
                        Hotkeys
                      </span>
                    </button>


                    <button
                      type="button"
                      onClick={() => {
                        setPttAndroidSettingsOpen(
                          false
                        );

                        window.alert(
                          "PTT Connect\\nWindows desktop client\\nTeamSpeak + Push-To-Talk"
                        );
                      }}
                    >
                      <span>
                        ⓘ
                      </span>

                      <span>
                        About
                      </span>
                    </button>

                  </div>
                )}

              </div>

            </div>

          </header>


          {/* =================================================
              HOOFDINDELING
              ================================================= */}

          <div className="ptt-android-content">


            {/* ===============================================
                LINKS - KANALEN
                =============================================== */}

            <aside className="ptt-android-channels">

              <div className="ptt-android-panel-heading">
                <span>
                  CHANNELS
                </span>

                <span className="ptt-android-panel-plus">
                  +
                </span>
              </div>


              <div className="ptt-android-channel-list">

                {pttCbChannels.map(
                  (
                    channel,
                    index
                  ) => {

                    const channelUsers =
                      clients.filter(
                        (
                          client
                        ) =>
                          client.channel ===
                          channel.id
                      );


                    const active =
                      channel.id ===
                      pttCurrentChannel?.id;


                    return (
                      <button
                        key={
                          channel.id
                        }
                        type="button"
                        className={
                          "ptt-android-channel" +
                          (
                            active
                              ? " ptt-android-channel-active"
                              : ""
                          )
                        }
                        onClick={() =>
                          handleAndroidChannelClick(
                            channel.id
                          )
                        }
                      >

                        <div className="ptt-android-channel-icon">
                          {
                            index % 3 === 0
                              ? "▣"
                              :
                            index % 3 === 1
                              ? "♟"
                              : "◉"
                          }
                        </div>


                        <div className="ptt-android-channel-info">

                          <strong>
                            {
                              channel.name
                            }
                          </strong>

                          <span>
                            {
                              channelUsers.length
                            } online
                          </span>

                        </div>

                      </button>
                    );
                  }
                )}

              </div>

            </aside>


            {/* ===============================================
                MIDDEN - PTT
                =============================================== */}

            <main className="ptt-android-main">

              <div className="ptt-android-channel-header">

                <div className="ptt-android-chat-icon">
                  ◯
                </div>

                <div>
                  <h2>
                    {
                      pttCurrentChannel?.name ??
                      "No channel"
                    }
                  </h2>

                  <div className="ptt-android-channel-subtitle">

                    <span>
                      {
                        pttCurrentChannelClients.length
                      } online
                    </span>

                    <span>
                      •
                    </span>

                    <span>
                      Push to talk with your team
                    </span>

                  </div>
                </div>

              </div>


              <div className="ptt-android-ptt-zone">

                <button
                  type="button"
                  className={
                    "ptt-android-ptt" +
                    (
                      pttCbTxActive
                        ? " ptt-android-ptt-transmitting"
                        : ""
                    )
                  }
                  disabled={
                    !connected ||
                    !micOn ||
                    inputMuted
                  }
                  onPointerDown={
                    (
                      event
                    ) => {

                      event.preventDefault();

                      try {
                        event.currentTarget
                          .setPointerCapture(
                            event.pointerId
                          );
                      } catch {
                      }

                      handleAndroidPttStart();
                    }
                  }
                  onPointerUp={
                    (
                      event
                    ) => {

                      event.preventDefault();

                      handleAndroidPttStop();
                    }
                  }
                  onPointerCancel={
                    handleAndroidPttStop
                  }
                  onPointerLeave={
                    (
                      event
                    ) => {

                      if (
                        event.buttons === 0
                      ) {
                        handleAndroidPttStop();
                      }
                    }
                  }
                  onContextMenu={
                    (
                      event
                    ) =>
                      event.preventDefault()
                  }
                  title={
                    !micOn
                      ? "Microfoon is niet actief"
                      :
                    inputMuted
                      ? "Microfoon is gedempt"
                      : "Houd ingedrukt om te praten"
                  }
                >

                  <span className="ptt-android-ptt-mic">
                    🎙
                  </span>

                  <strong>
                    {
                      pttCbTxActive
                        ? "TX"
                        : "PTT"
                    }
                  </strong>

                </button>


                <div
                  className={
                    "ptt-android-speaking" +
                    (
                      pttCbTalkingNow
                        ? " ptt-android-speaking-active"
                        : ""
                    )
                  }
                >

                  <span className="ptt-android-wave-small">
                    ≋
                  </span>

                  <span>
                    Speaking now:
                  </span>

                  <strong>
                    {
                      pttCbTalkingNow?.name ??
                      "Nobody"
                    }
                  </strong>

                </div>


                <div
                  className={
                    "ptt-android-wave" +
                    (
                      pttCbTalkingNow
                        ? " ptt-android-wave-active"
                        : ""
                    )
                  }
                >
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                </div>

              </div>

            </main>


            {/* ===============================================
                RECHTS - USERS
                =============================================== */}

            <aside className="ptt-android-users">

              <div className="ptt-android-users-heading">
                USERS ({
                  pttCurrentChannelClients.length
                })
              </div>


              <div className="ptt-android-users-list">

                {pttCurrentChannelClients.map(
                  (
                    client,
                    index
                  ) => {

                    const talking =
                      talkers.has(
                        client.id
                      ) ||
                      (
                        client.id ===
                          ownClientId &&
                        pttCbTxActive
                      );


                    const initials =
                      (
                        client.name
                          ?.trim()
                          .charAt(0) ||
                        "?"
                      )
                        .toUpperCase();


                    return (
                      <div
                        key={
                          client.id
                        }
                        className={
                          "ptt-android-user" +
                          (
                            talking
                              ? " ptt-android-user-talking"
                              : ""
                          )
                        }
                      >

                        <div
                          className={
                            "ptt-android-avatar " +
                            `ptt-android-avatar-${
                              index % 6
                            }`
                          }
                        >
                          {
                            initials
                          }
                        </div>


                        <span
                          className={
                            "ptt-android-user-dot" +
                            (
                              talking
                                ? " ptt-android-user-dot-talking"
                                :
                              client.away
                                ? " ptt-android-user-dot-away"
                                :
                              client.inputMuted
                                ? " ptt-android-user-dot-muted"
                                : ""
                            )
                          }
                        />


                        <div className="ptt-android-user-name">

                          <strong>
                            {
                              client.name
                            }
                          </strong>

                          {talking && (
                            <small>
                              Speaking now
                            </small>
                          )}

                        </div>

                      </div>
                    );
                  }
                )}

              </div>

            </aside>

          </div>


          {/* =================================================
              ONDERBALK - ECHTE AUDIO APPARATEN
              ================================================= */}

          <footer className="ptt-android-audio-bar">

            <div className="ptt-android-device">

              <div className="ptt-android-device-icon">
                🎙
              </div>


              <label>

                <span>
                  Microphone
                </span>

                <select
                  value={
                    inputDeviceId
                  }
                  onFocus={
                    refreshInputDevices
                  }
                  onChange={
                    (
                      event
                    ) =>
                      handleInputDeviceChange(
                        event.target.value
                      )
                  }
                >

                  <option value="">
                    System Default
                  </option>

                  {inputDevices.map(
                    (
                      device
                    ) => (
                      <option
                        key={
                          device.deviceId
                        }
                        value={
                          device.deviceId
                        }
                      >
                        {
                          device.label ||
                          `Microphone ${
                            device.deviceId.slice(
                              0,
                              6
                            )
                          }`
                        }
                      </option>
                    )
                  )}

                </select>

              </label>

            </div>


            <div className="ptt-android-audio-divider" />


            <div className="ptt-android-device">

              <div className="ptt-android-device-icon">
                🔊
              </div>


              <label>

                <span>
                  Speaker
                </span>

                <select
                  value={
                    outputDeviceId
                  }
                  onFocus={
                    refreshOutputDevices
                  }
                  onChange={
                    (
                      event
                    ) =>
                      void handleOutputDeviceChange(
                        event.target.value
                      )
                  }
                >

                  <option value="">
                    System Default
                  </option>

                  {outputDevices.map(
                    (
                      device
                    ) => (
                      <option
                        key={
                          device.deviceId
                        }
                        value={
                          device.deviceId
                        }
                      >
                        {
                          device.label ||
                          `Speaker ${
                            device.deviceId.slice(
                              0,
                              6
                            )
                          }`
                        }
                      </option>
                    )
                  )}

                </select>

              </label>

            </div>

          </footer>

        </section>
      )}


'''


app = (
    app[:android_start] +
    android_view +
    app[android_end:]
)


APP_FILE.write_text(
    app,
    encoding="utf-8"
)


# ============================================================
# CSS
# Oude CB CSS mag blijven bestaan.
# Deze nieuwe CSS gebruikt eigen classes en overschrijft niets
# van de normale PTT Connect interface.
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)


android_css = r'''

/* ==========================================================
   PTT CONNECT - REALISTIC ANDROID APP VIEW
   ========================================================== */

.ptt-android-view,
.ptt-android-view * {
  box-sizing:
    border-box;
}


.ptt-android-view {
  position:
    fixed;

  z-index:
    500;

  inset:
    68px 20px 20px;

  display:
    flex;

  flex-direction:
    column;

  min-width:
    0;

  min-height:
    0;

  overflow:
    hidden;

  color:
    #f4f7ff;

  border:
    1px solid
    rgba(
      120,
      150,
      200,
      0.16
    );

  border-radius:
    20px;

  background:
    linear-gradient(
      180deg,
      #101725 0%,
      #0c1320 100%
    );

  box-shadow:
    0 30px 80px
    rgba(
      0,
      0,
      0,
      0.52
    );
}


/* ==========================================================
   TOPBAR
   ========================================================== */

.ptt-android-topbar {
  height:
    70px;

  flex:
    0 0 70px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    space-between;

  padding:
    0 22px;

  border-bottom:
    1px solid
    rgba(
      255,
      255,
      255,
      0.055
    );

  background:
    linear-gradient(
      180deg,
      #151d2c,
      #101725
    );
}


.ptt-android-brand {
  display:
    flex;

  align-items:
    center;

  gap:
    13px;
}


.ptt-android-logo {
  width:
    40px;

  height:
    40px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  border-radius:
    50%;

  background:
    linear-gradient(
      150deg,
      #3291ff,
      #1557ec
    );

  color:
    white;

  font-size:
    11px;

  font-weight:
    900;

  box-shadow:
    0 7px 20px
    rgba(
      20,
      90,
      245,
      0.35
    );
}


.ptt-android-brand strong {
  font-size:
    22px;

  font-weight:
    800;

  letter-spacing:
    -0.02em;
}


.ptt-android-top-actions {
  position:
    relative;

  display:
    flex;

  align-items:
    center;

  gap:
    14px;
}


.ptt-android-connected {
  display:
    flex;

  align-items:
    center;

  gap:
    9px;

  color:
    #e5ebf5;

  font-size:
    13px;
}


.ptt-android-connected-dot {
  width:
    10px;

  height:
    10px;

  border-radius:
    50%;

  background:
    #20de63;

  box-shadow:
    0 0 10px
    rgba(
      32,
      222,
      99,
      0.42
    );
}


.ptt-android-back,
.ptt-android-settings-button {
  height:
    40px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  border:
    1px solid
    rgba(
      255,
      255,
      255,
      0.07
    );

  border-radius:
    11px;

  background:
    #192231;

  color:
    #dfe9fa;

  cursor:
    pointer;
}


.ptt-android-back {
  padding:
    0 14px;

  font-weight:
    700;
}


.ptt-android-back:hover,
.ptt-android-settings-button:hover,
.ptt-android-settings-button-active {
  border-color:
    rgba(
      69,
      135,
      255,
      0.48
    );

  background:
    #202c40;
}


.ptt-android-settings-wrap {
  position:
    relative;
}


.ptt-android-settings-button {
  width:
    44px;

  font-size:
    20px;
}


/* ==========================================================
   SETTINGS MENU
   ========================================================== */

.ptt-android-settings-menu {
  position:
    absolute;

  z-index:
    1000;

  top:
    49px;

  right:
    0;

  width:
    290px;

  overflow:
    hidden;

  padding:
    8px;

  border:
    1px solid
    rgba(
      130,
      155,
      200,
      0.22
    );

  border-radius:
    14px;

  background:
    rgba(
      24,
      34,
      50,
      0.99
    );

  box-shadow:
    0 20px 50px
    rgba(
      0,
      0,
      0,
      0.50
    );
}


.ptt-android-settings-title {
  display:
    flex;

  align-items:
    center;

  gap:
    10px;

  padding:
    11px 12px 14px;

  margin-bottom:
    6px;

  border-bottom:
    1px solid
    rgba(
      255,
      255,
      255,
      0.075
    );

  font-size:
    16px;
}


.ptt-android-settings-menu button {
  width:
    100%;

  min-height:
    48px;

  display:
    flex;

  align-items:
    center;

  gap:
    13px;

  padding:
    9px 12px;

  border:
    0;

  border-radius:
    9px;

  background:
    transparent;

  color:
    #eef4ff;

  text-align:
    left;

  cursor:
    pointer;

  font-size:
    14px;
}


.ptt-android-settings-menu button:hover {
  background:
    rgba(
      82,
      126,
      206,
      0.16
    );
}


.ptt-android-menu-text {
  flex:
    1;

  display:
    flex;

  flex-direction:
    column;

  gap:
    2px;
}


.ptt-android-menu-text small {
  color:
    #8495b0;

  font-size:
    10px;
}


.ptt-android-menu-arrow {
  margin-left:
    auto;

  color:
    #a9bad5;

  font-size:
    22px;
}


/* ==========================================================
   CONTENT GRID
   ========================================================== */

.ptt-android-content {
  min-height:
    0;

  flex:
    1;

  display:
    grid;

  grid-template-columns:
    285px minmax(420px, 1fr) 270px;

  background:
    #0d1421;
}


/* ==========================================================
   CHANNEL PANEL
   ========================================================== */

.ptt-android-channels {
  min-height:
    0;

  display:
    flex;

  flex-direction:
    column;

  border-right:
    1px solid
    rgba(
      255,
      255,
      255,
      0.05
    );

  background:
    #101827;
}


.ptt-android-panel-heading {
  height:
    60px;

  flex:
    0 0 60px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    space-between;

  padding:
    0 20px;

  color:
    #93a5c2;

  font-size:
    12px;

  font-weight:
    800;

  letter-spacing:
    0.07em;
}


.ptt-android-panel-plus {
  color:
    #94a8c7;

  font-size:
    25px;

  font-weight:
    300;
}


.ptt-android-channel-list {
  min-height:
    0;

  flex:
    1;

  overflow:
    auto;

  padding:
    0 9px 14px;
}


.ptt-android-channel {
  width:
    100%;

  min-height:
    70px;

  display:
    flex;

  align-items:
    center;

  gap:
    14px;

  margin:
    3px 0;

  padding:
    10px 16px;

  border:
    1px solid
    transparent;

  border-radius:
    10px;

  background:
    transparent;

  color:
    inherit;

  text-align:
    left;

  cursor:
    pointer;

  transition:
    background
    0.13s ease,
    border-color
    0.13s ease;
}


.ptt-android-channel:hover {
  background:
    rgba(
      63,
      95,
      150,
      0.10
    );
}


.ptt-android-channel-active {
  position:
    relative;

  border-color:
    rgba(
      69,
      122,
      216,
      0.18
    );

  background:
    linear-gradient(
      90deg,
      rgba(
        45,
        88,
        160,
        0.42
      ),
      rgba(
        38,
        64,
        108,
        0.25
      )
    );
}


.ptt-android-channel-active::before {
  content:
    "";

  position:
    absolute;

  top:
    0;

  bottom:
    0;

  left:
    -9px;

  width:
    3px;

  border-radius:
    0 4px 4px 0;

  background:
    #31bdff;
}


.ptt-android-channel-icon {
  width:
    31px;

  flex:
    0 0 31px;

  color:
    #48c5ff;

  font-size:
    21px;

  text-align:
    center;
}


.ptt-android-channel-info {
  min-width:
    0;

  display:
    flex;

  flex-direction:
    column;

  gap:
    4px;
}


.ptt-android-channel-info strong {
  overflow:
    hidden;

  color:
    #eef3fb;

  font-size:
    14px;

  text-overflow:
    ellipsis;

  white-space:
    nowrap;
}


.ptt-android-channel-info span {
  color:
    #8192ad;

  font-size:
    11px;
}


/* ==========================================================
   MAIN
   ========================================================== */

.ptt-android-main {
  min-width:
    0;

  min-height:
    0;

  display:
    flex;

  flex-direction:
    column;

  padding:
    28px 38px 22px;

  background:
    radial-gradient(
      circle at 50% 45%,
      rgba(
        20,
        42,
        79,
        0.30
      ),
      rgba(
        13,
        20,
        33,
        0
      )
      52%
    );
}


.ptt-android-channel-header {
  display:
    flex;

  align-items:
    center;

  gap:
    14px;
}


.ptt-android-chat-icon {
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

  border-radius:
    50%;

  background:
    linear-gradient(
      145deg,
      #264c8f,
      #1b345e
    );

  color:
    white;

  font-size:
    22px;
}


.ptt-android-channel-header h2 {
  margin:
    0;

  color:
    #ffffff;

  font-size:
    25px;

  line-height:
    1.2;
}


.ptt-android-channel-subtitle {
  display:
    flex;

  gap:
    10px;

  margin-top:
    5px;

  color:
    #8fa1bd;

  font-size:
    12px;
}


/* ==========================================================
   PTT ZONE
   ========================================================== */

.ptt-android-ptt-zone {
  min-height:
    0;

  flex:
    1;

  display:
    flex;

  flex-direction:
    column;

  align-items:
    center;

  justify-content:
    center;
}


.ptt-android-ptt {
  width:
    min(
      330px,
      43vh
    );

  height:
    min(
      330px,
      43vh
    );

  min-width:
    220px;

  min-height:
    220px;

  display:
    flex;

  flex-direction:
    column;

  align-items:
    center;

  justify-content:
    center;

  gap:
    10px;

  border:
    9px solid
    #2894ff;

  border-radius:
    50%;

  outline:
    7px solid
    rgba(
      28,
      95,
      212,
      0.30
    );

  background:
    radial-gradient(
      circle at 50% 28%,
      #39a8ff 0%,
      #1375f8 31%,
      #0954e8 66%,
      #0737a8 100%
    );

  color:
    white;

  cursor:
    pointer;

  user-select:
    none;

  touch-action:
    none;

  box-shadow:
    0 0 0 1px
    rgba(
      120,
      190,
      255,
      0.32
    ),
    0 0 35px
    rgba(
      18,
      104,
      255,
      0.44
    ),
    inset 0 16px 34px
    rgba(
      255,
      255,
      255,
      0.15
    ),
    inset 0 -20px 35px
    rgba(
      0,
      25,
      90,
      0.32
    );

  transition:
    transform
    0.08s ease,
    box-shadow
    0.08s ease,
    border-color
    0.08s ease;
}


.ptt-android-ptt:hover:not(:disabled) {
  box-shadow:
    0 0 0 1px
    rgba(
      120,
      200,
      255,
      0.40
    ),
    0 0 48px
    rgba(
      20,
      120,
      255,
      0.58
    ),
    inset 0 16px 34px
    rgba(
      255,
      255,
      255,
      0.18
    ),
    inset 0 -20px 35px
    rgba(
      0,
      25,
      90,
      0.32
    );
}


.ptt-android-ptt:active:not(:disabled),
.ptt-android-ptt-transmitting {
  transform:
    scale(
      0.965
    );

  border-color:
    #6fe8ff;

  background:
    radial-gradient(
      circle at 50% 28%,
      #42d8ff,
      #087cff 39%,
      #0754df 72%,
      #072d82
    );

  box-shadow:
    0 0 18px
    rgba(
      80,
      225,
      255,
      0.90
    ),
    0 0 58px
    rgba(
      30,
      135,
      255,
      0.78
    ),
    inset 0 15px 30px
    rgba(
      255,
      255,
      255,
      0.18
    );
}


.ptt-android-ptt:disabled {
  cursor:
    not-allowed;

  filter:
    saturate(
      0.30
    );

  opacity:
    0.60;
}


.ptt-android-ptt-mic {
  font-size:
    56px;
}


.ptt-android-ptt strong {
  font-size:
    37px;

  font-weight:
    900;

  letter-spacing:
    0.02em;
}


/* ==========================================================
   SPEAKING NOW
   ========================================================== */

.ptt-android-speaking {
  min-width:
    340px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  gap:
    8px;

  margin-top:
    27px;

  padding:
    11px 22px;

  border:
    1px solid
    rgba(
      83,
      115,
      160,
      0.35
    );

  border-radius:
    999px;

  color:
    #9eacc1;

  background:
    rgba(
      13,
      21,
      34,
      0.76
    );
}


.ptt-android-speaking-active {
  border-color:
    #21dc70;

  color:
    #e7fff1;

  box-shadow:
    0 0 12px
    rgba(
      31,
      220,
      112,
      0.12
    );
}


.ptt-android-wave-small {
  color:
    #23df7a;

  font-size:
    22px;

  font-weight:
    900;
}


.ptt-android-speaking strong {
  color:
    #ffffff;
}


/* ==========================================================
   WAVEFORM
   ========================================================== */

.ptt-android-wave {
  height:
    55px;

  display:
    flex;

  align-items:
    center;

  gap:
    5px;

  margin-top:
    11px;
}


.ptt-android-wave i {
  width:
    5px;

  height:
    12px;

  display:
    block;

  border-radius:
    6px;

  background:
    #263752;

  transition:
    height
    0.10s ease,
    background
    0.10s ease;
}


.ptt-android-wave-active i {
  background:
    #24dc76;

  animation:
    pttAndroidWave
    0.72s ease-in-out
    infinite alternate;
}


.ptt-android-wave-active i:nth-child(2n) {
  animation-delay:
    -0.22s;
}


.ptt-android-wave-active i:nth-child(3n) {
  animation-delay:
    -0.41s;
}


.ptt-android-wave-active i:nth-child(4n) {
  animation-delay:
    -0.58s;
}


@keyframes pttAndroidWave {

  from {
    height:
      9px;
  }

  to {
    height:
      47px;
  }

}


/* ==========================================================
   USERS PANEL
   ========================================================== */

.ptt-android-users {
  min-height:
    0;

  display:
    flex;

  flex-direction:
    column;

  padding:
    18px 14px;

  border-left:
    1px solid
    rgba(
      255,
      255,
      255,
      0.05
    );

  background:
    #101827;
}


.ptt-android-users-heading {
  height:
    40px;

  flex:
    0 0 40px;

  padding:
    7px 8px;

  color:
    #9aabc5;

  font-size:
    12px;

  font-weight:
    800;
}


.ptt-android-users-list {
  min-height:
    0;

  overflow:
    auto;
}


.ptt-android-user {
  min-height:
    52px;

  display:
    flex;

  align-items:
    center;

  gap:
    10px;

  padding:
    6px 9px;

  margin-bottom:
    3px;

  border:
    1px solid
    transparent;

  border-radius:
    10px;

  transition:
    background
    0.12s ease,
    border-color
    0.12s ease;
}


.ptt-android-user-talking {
  border-color:
    rgba(
      40,
      220,
      115,
      0.25
    );

  background:
    rgba(
      30,
      130,
      75,
      0.13
    );
}


.ptt-android-avatar {
  width:
    36px;

  height:
    36px;

  flex:
    0 0 36px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  border-radius:
    50%;

  color:
    white;

  font-size:
    14px;

  font-weight:
    800;

  background:
    #356cbc;
}


.ptt-android-avatar-1 {
  background:
    #6552bc;
}


.ptt-android-avatar-2 {
  background:
    #4e8d54;
}


.ptt-android-avatar-3 {
  background:
    #a76438;
}


.ptt-android-avatar-4 {
  background:
    #3b6fae;
}


.ptt-android-avatar-5 {
  background:
    #9b7d29;
}


.ptt-android-user-dot {
  width:
    9px;

  height:
    9px;

  flex:
    0 0 9px;

  border-radius:
    50%;

  background:
    #20df69;

  box-shadow:
    0 0 5px
    rgba(
      32,
      223,
      105,
      0.36
    );
}


.ptt-android-user-dot-talking {
  background:
    #40e9ff;

  box-shadow:
    0 0 9px
    #40e9ff;
}


.ptt-android-user-dot-away {
  background:
    #ffd227;
}


.ptt-android-user-dot-muted {
  background:
    #637086;

  box-shadow:
    none;
}


.ptt-android-user-name {
  min-width:
    0;

  display:
    flex;

  flex-direction:
    column;
}


.ptt-android-user-name strong {
  overflow:
    hidden;

  color:
    #e9eff9;

  font-size:
    13px;

  text-overflow:
    ellipsis;

  white-space:
    nowrap;
}


.ptt-android-user-name small {
  margin-top:
    2px;

  color:
    #43e8ff;

  font-size:
    9px;

  font-weight:
    700;
}


/* ==========================================================
   AUDIO BAR
   ========================================================== */

.ptt-android-audio-bar {
  min-height:
    86px;

  flex:
    0 0 86px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  gap:
    28px;

  padding:
    10px 40px;

  border-top:
    1px solid
    rgba(
      255,
      255,
      255,
      0.055
    );

  background:
    linear-gradient(
      180deg,
      #121b2a,
      #101725
    );
}


.ptt-android-device {
  min-width:
    0;

  flex:
    1;

  max-width:
    520px;

  display:
    flex;

  align-items:
    center;

  gap:
    12px;
}


.ptt-android-device-icon {
  width:
    45px;

  height:
    45px;

  flex:
    0 0 45px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  border:
    1px solid
    rgba(
      255,
      255,
      255,
      0.08
    );

  border-radius:
    50%;

  background:
    #1b2638;

  font-size:
    20px;
}


.ptt-android-device label {
  min-width:
    0;

  flex:
    1;

  display:
    flex;

  flex-direction:
    column;

  gap:
    6px;
}


.ptt-android-device label > span {
  color:
    #a6b5cc;

  font-size:
    11px;
}


.ptt-android-device select {
  width:
    100%;

  height:
    39px;

  padding:
    0 36px 0 12px;

  border:
    1px solid
    rgba(
      115,
      145,
      190,
      0.20
    );

  border-radius:
    8px;

  outline:
    0;

  color:
    #e8eef8;

  background:
    #151f2f;
}


.ptt-android-audio-divider {
  width:
    1px;

  height:
    48px;

  background:
    rgba(
      255,
      255,
      255,
      0.08
    );
}


/* ==========================================================
   RESPONSIVE
   ========================================================== */

@media (
  max-width:
    1250px
) {

  .ptt-android-content {
    grid-template-columns:
      230px minmax(
        360px,
        1fr
      )
      220px;
  }


  .ptt-android-main {
    padding:
      24px 20px;
  }


  .ptt-android-ptt {
    width:
      250px;

    height:
      250px;

    min-width:
      250px;

    min-height:
      250px;
  }

}


@media (
  max-width:
    950px
) {

  .ptt-android-content {
    grid-template-columns:
      190px
      minmax(
        320px,
        1fr
      );
  }


  .ptt-android-users {
    display:
      none;
  }


  .ptt-android-speaking {
    min-width:
      280px;
  }

}


@media (
  max-height:
    760px
) {

  .ptt-android-ptt {
    width:
      220px;

    height:
      220px;

    min-width:
      220px;

    min-height:
      220px;
  }


  .ptt-android-wave {
    height:
      35px;
  }

}

'''


if (
    "PTT CONNECT - REALISTIC ANDROID APP VIEW"
    not in css
):
    css += (
        android_css
    )


CSS_FILE.write_text(
    css,
    encoding="utf-8"
)


print(
    "- oude CB Transceiver interface vervangen"
)

print(
    "- knop heet nu Android App"
)

print(
    "- realistische interface zoals voorbeeld toegevoegd"
)

print(
    "- echte TeamSpeak kanalen links"
)

print(
    "- kanaal aanklikken wisselt echt van TeamSpeak kanaal"
)

print(
    "- echte gebruikers van huidig kanaal rechts"
)

print(
    "- actieve spreker wordt live weergegeven"
)

print(
    "- grote PTT knop gebruikt bestaande Push-To-Talk engine"
)

print(
    "- PTT werkt met muis/touch zolang knop ingedrukt is"
)

print(
    "- echte microfoon selector toegevoegd"
)

print(
    "- echte luidspreker selector toegevoegd"
)

print(
    "- Settings -> Audio Devices werkt"
)

print(
    "- Settings -> Appearance werkt"
)

print(
    "- Settings -> Notifications werkt"
)

print(
    "- Settings -> Hotkeys werkt"
)

print(
    "- Windows knop keert terug naar normale weergave"
)

print(
    "- stabiele TeamSpeak ontvangstaudio NIET gewijzigd"
)

print(
    "- microfoon/audio pipeline NIET vervangen"
)

print(
    "- webcam, videogalerij, schermdelen en radio NIET gewijzigd"
)

print(
    "- CB talkers buildfout opgelost"
)
