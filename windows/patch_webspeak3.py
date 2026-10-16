from pathlib import Path
import subprocess


# ============================================================
# PTT CONNECT WINDOWS
# COMPLETE PATCH
#
# BASIS:
#   Groene build #37
#
# DAAR BOVENOP:
#   Nieuwe realistische Android App-weergave
#
# BELANGRIJK:
# - TeamSpeak ontvangstaudio blijft behouden
# - Push-To-Talk blijft behouden
# - webcam blijft behouden
# - videogalerij blijft behouden
# - schermdelen blijft behouden
# - radiostreams blijven behouden
# - normale Windows-weergave blijft behouden
# ============================================================


BASELINE_COMMIT = (
    "8ed94f98dae6cfce47e90116fe58b2f4392a6919"
)

BASELINE_FILE = (
    "windows/patch_webspeak3.py"
)


APP_FILE = Path(
    "upstream/web/src/App.tsx"
)

CSS_FILE = Path(
    "upstream/web/src/App.css"
)


# ============================================================
# HULPFUNCTIE
# ============================================================

def replace_once(
    text,
    old,
    new,
    name,
):
    if old not in text:
        raise RuntimeError(
            f"PTT Connect patch mislukt: "
            f"{name} niet gevonden"
        )

    count = text.count(
        old
    )

    if count != 1:
        raise RuntimeError(
            f"PTT Connect patch mislukt: "
            f"{name} komt {count} keer voor"
        )

    return text.replace(
        old,
        new,
        1,
    )


# ============================================================
# GROENE BUILD #37 ALS VASTE BASIS OPHALEN
#
# Daardoor hoeven we niet opnieuw duizenden regels van de
# reeds werkende PTT/audio/video code na te bouwen.
# ============================================================

def load_green_baseline():

    target = (
        f"{BASELINE_COMMIT}:"
        f"{BASELINE_FILE}"
    )

    # Eerst proberen of commit al lokaal aanwezig is.
    first_try = subprocess.run(
        [
            "git",
            "show",
            target,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if first_try.returncode == 0:
        return first_try.stdout

    print(
        "- groene basis #37 nog niet lokaal"
    )

    print(
        "- commit wordt opgehaald via GitHub"
    )

    subprocess.run(
        [
            "git",
            "fetch",
            "--quiet",
            "--depth=1",
            "origin",
            BASELINE_COMMIT,
        ],
        check=True,
    )

    second_try = subprocess.run(
        [
            "git",
            "show",
            target,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )

    return second_try.stdout


print(
    "============================================"
)

print(
    "PTT Connect complete Windows patch"
)

print(
    "Basis: groene build #37"
)

print(
    "============================================"
)


baseline_script = (
    load_green_baseline()
)


# ============================================================
# EERST ALLE BEWEZEN WERKENDE FUNCTIES VAN BUILD #37
# ============================================================

exec(
    compile(
        baseline_script,
        (
            "<PTTConnect-green-"
            "build-37>"
        ),
        "exec",
    ),
    {
        "__name__":
            "__main__",
    },
)


print(
    "- groene PTT Connect basis toegepast"
)


# ============================================================
# VANAF HIER:
# NIEUWE ANDROID APP VIEW
# ============================================================

app = APP_FILE.read_text(
    encoding="utf-8"
)


# ============================================================
# ANDROID APP STATE
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

  const pttAndroidPressedRef =
    useRef(
      false
    );
''',
    "Android App state",
)


# ============================================================
# ANDROID APP FUNCTIES
# ============================================================

app = replace_once(
    app,
    '''  const publishClientName = (clid: number) =>
''',
    '''  /*
   * De oude CB-weergave gebruikte deze helpers.
   * De Android-weergave gebruikt echte kanaalklikken.
   * Markeer ze als gebruikt zodat TypeScript
   * noUnusedLocals niet laat falen.
   */
  void pttCbCurrentNumber;
  void pttCbRxActive;
  void pttCbPrevChannel;
  void pttCbNextChannel;


  const handleAndroidChannelClick = (
    channelId: number
  ) => {

    setSelected({
      type: "channel",
      id: channelId,
    });

    /*
     * Echt TeamSpeak-kanaal wisselen.
     */
    handleSwitchChannel(
      channelId
    );
  };


  const handleAndroidPttStart =
    async () => {

      if (!connected) {
        return;
      }

      pttAndroidPressedRef.current =
        true;

      /*
       * Android-knop gebruikt dezelfde
       * bestaande Push-To-Talk engine.
       */
      setTransmissionMode(
        "ptt"
      );

      /*
       * Als de microfoon nog niet gestart
       * is, gebruik dezelfde bestaande
       * startMic functie.
       */
      if (!micOn) {
        await startMic();
      }

      /*
       * De gebruiker kan de knop alweer
       * hebben losgelaten terwijl Windows
       * toestemming voor de microfoon vroeg.
       */
      if (
        !pttAndroidPressedRef.current
      ) {
        micCaptureRef.current
          ?.setPushToTalk(
            false
          );

        return;
      }

      micCaptureRef.current
        ?.setTransmissionMode(
          "ptt"
        );

      micCaptureRef.current
        ?.setPushToTalk(
          true
        );
    };


  const handleAndroidPttStop =
    () => {

      pttAndroidPressedRef.current =
        false;

      micCaptureRef.current
        ?.setPushToTalk(
          false
        );
    };


  const openAndroidOption = (
    section:
      | "wiedergabe"
      | "aufnahme"
      | "sounds"
      | "design"
      | "hotkeys"
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
    "Android App functies",
)


# ============================================================
# BOVENSTE KNOP
# CB TRANSCEIVER -> ANDROID APP
# ============================================================

app = replace_once(
    app,
    '''title="CB Transceiver weergave"
              aria-label="CB Transceiver weergave"
            >
              📻 CB Transceiver''',
    '''title="Android App weergave"
              aria-label="Android App weergave"
            >
              📱 Android App''',
    "Android App knopnaam",
)


# ============================================================
# OUDE CB OVERLAY VINDEN
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
    android_start,
)


if android_start == -1:
    raise RuntimeError(
        "Oude CB overlay niet gevonden"
    )


if android_end == -1:
    raise RuntimeError(
        "Einde oude CB overlay niet gevonden"
    )


# ============================================================
# COMPLETE NIEUWE ANDROID APP VIEW
# ============================================================

android_view = r'''
      {pttLayoutMode === "cb" && (

        <section className="ptt-android-view">


          {/* ===============================================
              BOVENBALK
              =============================================== */}

          <header className="ptt-android-topbar">

            <div className="ptt-android-brand">

              <div className="ptt-android-logo">

                <span className="ptt-android-logo-left">
                  ◀
                </span>

                <span className="ptt-android-logo-line">
                  |
                </span>

                <span className="ptt-android-logo-right">
                  ▶
                </span>

              </div>


              <div className="ptt-android-brand-text">

                <strong>
                  PTT Connect
                </strong>

                <span>
                  Push-To-Talk Communication
                </span>

              </div>

            </div>


            <div className="ptt-android-top-actions">


              <div
                className={
                  "ptt-android-connection" +
                  (
                    connected
                      ? " ptt-android-connection-online"
                      : ""
                  )
                }
              >

                <span className="ptt-android-connection-dot" />

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
                className="ptt-android-windows-button"
                onClick={() => {

                  handleAndroidPttStop();

                  setPttAndroidSettingsOpen(
                    false
                  );

                  setPttLayoutMode(
                    "normal"
                  );

                }}
                title="Terug naar normale Windows weergave"
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
                        ? " ptt-android-settings-active"
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


                    <div className="ptt-android-settings-header">

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

                      <span className="ptt-android-setting-icon">
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

                      <span className="ptt-android-setting-icon">
                        🎨
                      </span>

                      <span className="ptt-android-setting-main">

                        Appearance

                        <small>
                          Theme, colors, dark/light mode
                        </small>

                      </span>

                      <span className="ptt-android-setting-arrow">
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

                      <span className="ptt-android-setting-icon">
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

                      <span className="ptt-android-setting-icon">
                        ⌨
                      </span>

                      <span>
                        Hotkeys
                      </span>

                    </button>


                    <div className="ptt-android-settings-separator" />


                    <button
                      type="button"
                      onClick={() => {

                        setPttAndroidSettingsOpen(
                          false
                        );

                        window.alert(
                          "PTT Connect\\n" +
                          "Windows Desktop Client\\n\\n" +
                          "TeamSpeak + Push-To-Talk"
                        );

                      }}
                    >

                      <span className="ptt-android-setting-icon">
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


          {/* ===============================================
              HOOFDGEDEELTE
              =============================================== */}

          <div className="ptt-android-body">


            {/* =============================================
                LINKERZIJDE - TEAMSpeak KANALEN
                ============================================= */}

            <aside className="ptt-android-channel-panel">


              <div className="ptt-android-section-title">

                <span>
                  CHANNELS
                </span>

                <span className="ptt-android-add-symbol">
                  +
                </span>

              </div>


              <div className="ptt-android-channel-scroll">


                {pttCbChannels.length === 0 && (

                  <div className="ptt-android-empty">

                    Geen TeamSpeak kanalen

                  </div>

                )}


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
                        type="button"
                        key={
                          channel.id
                        }
                        className={
                          "ptt-android-channel-row" +
                          (
                            active
                              ? " ptt-android-channel-row-active"
                              : ""
                          )
                        }
                        onClick={() =>
                          handleAndroidChannelClick(
                            channel.id
                          )
                        }
                        title={
                          `Ga naar ${channel.name}`
                        }
                      >


                        <span
                          className={
                            "ptt-android-channel-icon " +
                            `ptt-android-channel-icon-${
                              index % 4
                            }`
                          }
                        >

                          {
                            index % 4 === 0
                              ? "▣"
                              :
                            index % 4 === 1
                              ? "♟"
                              :
                            index % 4 === 2
                              ? "◉"
                              : "◆"
                          }

                        </span>


                        <span className="ptt-android-channel-info">

                          <strong>
                            {
                              channel.name
                            }
                          </strong>

                          <small>
                            {
                              channelUsers.length
                            } online
                          </small>

                        </span>


                        {active && (

                          <span className="ptt-android-channel-active-dot" />

                        )}


                      </button>

                    );

                  }
                )}


              </div>

            </aside>


            {/* =============================================
                MIDDEN - GROTE PTT
                ============================================= */}

            <main className="ptt-android-main">


              <div className="ptt-android-current-channel">


                <div className="ptt-android-current-icon">

                  <span>
                    ◯
                  </span>

                  <span className="ptt-android-current-icon-tail">
                    ▾
                  </span>

                </div>


                <div className="ptt-android-current-info">

                  <h2>
                    {
                      pttCurrentChannel?.name ??
                      "No channel"
                    }
                  </h2>


                  <div className="ptt-android-current-sub">

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


              <div className="ptt-android-center">


                <div className="ptt-android-ptt-halo">


                  <button
                    type="button"
                    className={
                      "ptt-android-ptt-button" +
                      (
                        selfActive ||
                        pttCbTxActive
                          ? " ptt-android-ptt-tx"
                          : ""
                      )
                    }
                    disabled={
                      !connected
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

                        void handleAndroidPttStart();

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
                    onContextMenu={
                      (
                        event
                      ) =>
                        event.preventDefault()
                    }
                    title={
                      connected
                        ? "Houd ingedrukt om te praten"
                        : "Niet verbonden"
                    }
                  >


                    <span className="ptt-android-ptt-mic">
                      🎙
                    </span>


                    <strong>
                      {
                        selfActive ||
                        pttCbTxActive
                          ? "TX"
                          : "PTT"
                      }
                    </strong>


                  </button>


                </div>


                <div
                  className={
                    "ptt-android-speaking-now" +
                    (
                      pttCbTalkingNow
                        ? " ptt-android-speaking-now-active"
                        : ""
                    )
                  }
                >


                  <span className="ptt-android-speaking-wave-icon">
                    ≋
                  </span>


                  <span>
                    Speaking now:
                  </span>


                  <strong>

                    {
                      pttCbTalkingNow?.name ??
                      (
                        selfActive
                          ? pttOwnClient?.name
                          : "Nobody"
                      ) ??
                      "Nobody"
                    }

                  </strong>


                </div>


                <div
                  className={
                    "ptt-android-waveform" +
                    (
                      pttCbTalkingNow ||
                      selfActive
                        ? " ptt-android-waveform-active"
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
                  <i />
                  <i />
                  <i />
                  <i />

                </div>


              </div>

            </main>


            {/* =============================================
                RECHTERZIJDE - USERS
                ============================================= */}

            <aside className="ptt-android-user-panel">


              <div className="ptt-android-user-title">

                USERS (
                {
                  pttCurrentChannelClients.length
                }
                )

              </div>


              <div className="ptt-android-user-scroll">


                {pttCurrentChannelClients.length === 0 && (

                  <div className="ptt-android-empty">

                    Niemand in dit kanaal

                  </div>

                )}


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
                        selfActive
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
                          "ptt-android-user-row" +
                          (
                            talking
                              ? " ptt-android-user-row-talking"
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
                            "ptt-android-user-status" +
                            (
                              talking
                                ? " ptt-android-user-status-talking"
                                :
                              client.away
                                ? " ptt-android-user-status-away"
                                :
                              client.inputMuted ||
                              !client.inputHardwareEnabled
                                ? " ptt-android-user-status-muted"
                                : ""
                            )
                          }
                        />


                        <div className="ptt-android-user-info">

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


                          {!talking &&
                            client.id ===
                              ownClientId && (

                            <small>
                              You
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


          {/* ===============================================
              ONDERBALK AUDIO APPARATEN
              =============================================== */}

          <footer className="ptt-android-audio-footer">


            <div className="ptt-android-audio-device">


              <div className="ptt-android-device-circle">
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
                  onFocus={() =>
                    void refreshInputDevices()
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


            <div className="ptt-android-footer-divider" />


            <div className="ptt-android-audio-device">


              <div className="ptt-android-device-circle">
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
                  onFocus={() =>
                    void refreshOutputDevices()
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
# ANDROID APP CSS
# ============================================================

css = CSS_FILE.read_text(
    encoding="utf-8"
)


android_css = r'''

/* ==========================================================
   PTT CONNECT - REALISTIC ANDROID APP VIEW
   ========================================================== */

.ptt-android-view,
.ptt-android-view *,
.ptt-android-view *::before,
.ptt-android-view *::after {
  box-sizing:
    border-box;
}


.ptt-android-view {
  position:
    fixed;

  z-index:
    500;

  inset:
    70px 18px 18px;

  min-width:
    0;

  min-height:
    0;

  display:
    flex;

  flex-direction:
    column;

  overflow:
    hidden;

  border:
    1px solid
    rgba(
      135,
      160,
      205,
      0.15
    );

  border-radius:
    20px;

  background:
    linear-gradient(
      180deg,
      #101827,
      #0b121e
    );

  color:
    #f5f8ff;

  font-family:
    "Segoe UI",
    Arial,
    sans-serif;

  box-shadow:
    0 28px 80px
    rgba(
      0,
      0,
      0,
      0.56
    );
}


/* ==========================================================
   TOPBAR
   ========================================================== */

.ptt-android-topbar {
  min-height:
    72px;

  flex:
    0 0 72px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    space-between;

  gap:
    20px;

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
      #151e2e,
      #101827
    );
}


.ptt-android-brand {
  min-width:
    0;

  display:
    flex;

  align-items:
    center;

  gap:
    13px;
}


.ptt-android-logo {
  width:
    42px;

  height:
    42px;

  flex:
    0 0 42px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  gap:
    1px;

  border:
    1px solid
    rgba(
      110,
      180,
      255,
      0.48
    );

  border-radius:
    50%;

  background:
    radial-gradient(
      circle at 35% 28%,
      #53bfff,
      #1977f5 45%,
      #0d45b3
    );

  box-shadow:
    0 5px 20px
    rgba(
      30,
      105,
      255,
      0.32
    );

  color:
    #ffffff;

  font-size:
    10px;

  font-weight:
    900;
}


.ptt-android-logo-line {
  opacity:
    0.80;
}


.ptt-android-brand-text {
  min-width:
    0;

  display:
    flex;

  flex-direction:
    column;

  gap:
    2px;
}


.ptt-android-brand-text strong {
  color:
    #ffffff;

  font-size:
    22px;

  font-weight:
    800;

  letter-spacing:
    -0.3px;
}


.ptt-android-brand-text span {
  color:
    #8698b5;

  font-size:
    10px;
}


.ptt-android-top-actions {
  position:
    relative;

  display:
    flex;

  align-items:
    center;

  gap:
    12px;
}


.ptt-android-connection {
  display:
    inline-flex;

  align-items:
    center;

  gap:
    8px;

  padding:
    7px 11px;

  border:
    1px solid
    rgba(
      255,
      255,
      255,
      0.06
    );

  border-radius:
    999px;

  background:
    rgba(
      255,
      255,
      255,
      0.025
    );

  color:
    #a5b2c8;

  font-size:
    12px;
}


.ptt-android-connection-dot {
  width:
    9px;

  height:
    9px;

  border-radius:
    50%;

  background:
    #6f7887;
}


.ptt-android-connection-online
.ptt-android-connection-dot {
  background:
    #22dc68;

  box-shadow:
    0 0 9px
    rgba(
      34,
      220,
      104,
      0.68
    );
}


.ptt-android-connection-online {
  color:
    #e2eaf5;
}


.ptt-android-windows-button,
.ptt-android-settings-button {
  height:
    40px;

  border:
    1px solid
    rgba(
      255,
      255,
      255,
      0.075
    );

  border-radius:
    10px;

  background:
    linear-gradient(
      180deg,
      #1b2638,
      #151f2f
    );

  color:
    #e6eefc;

  cursor:
    pointer;

  transition:
    border-color 0.14s ease,
    background 0.14s ease,
    transform 0.14s ease;
}


.ptt-android-windows-button {
  padding:
    0 14px;

  font-weight:
    700;
}


.ptt-android-settings-button {
  width:
    42px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  font-size:
    19px;
}


.ptt-android-windows-button:hover,
.ptt-android-settings-button:hover,
.ptt-android-settings-active {
  border-color:
    rgba(
      65,
      135,
      255,
      0.55
    );

  background:
    linear-gradient(
      180deg,
      #25344c,
      #1a273a
    );
}


.ptt-android-windows-button:active,
.ptt-android-settings-button:active {
  transform:
    translateY(
      1px
    );
}


.ptt-android-settings-wrap {
  position:
    relative;
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
    50px;

  right:
    0;

  width:
    285px;

  padding:
    7px;

  overflow:
    hidden;

  border:
    1px solid
    rgba(
      125,
      150,
      195,
      0.20
    );

  border-radius:
    14px;

  background:
    rgba(
      25,
      35,
      52,
      0.99
    );

  box-shadow:
    0 20px 55px
    rgba(
      0,
      0,
      0,
      0.58
    );
}


.ptt-android-settings-header {
  display:
    flex;

  align-items:
    center;

  gap:
    10px;

  min-height:
    45px;

  padding:
    8px 11px;

  border-bottom:
    1px solid
    rgba(
      255,
      255,
      255,
      0.075
    );

  color:
    #f0f5ff;

  font-size:
    15px;
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
    12px;

  padding:
    9px 11px;

  border:
    0;

  border-radius:
    9px;

  background:
    transparent;

  color:
    #edf3ff;

  text-align:
    left;

  cursor:
    pointer;

  font-size:
    13px;
}


.ptt-android-settings-menu button:hover {
  background:
    rgba(
      79,
      121,
      190,
      0.17
    );
}


.ptt-android-setting-icon {
  width:
    24px;

  display:
    inline-flex;

  justify-content:
    center;

  font-size:
    16px;
}


.ptt-android-setting-main {
  flex:
    1;

  display:
    flex;

  flex-direction:
    column;

  gap:
    2px;
}


.ptt-android-setting-main small {
  color:
    #7e90ab;

  font-size:
    9px;
}


.ptt-android-setting-arrow {
  margin-left:
    auto;

  color:
    #94a6c2;

  font-size:
    20px;
}


.ptt-android-settings-separator {
  height:
    1px;

  margin:
    6px 7px;

  background:
    rgba(
      255,
      255,
      255,
      0.07
    );
}


/* ==========================================================
   HOOFDINDELING
   ========================================================== */

.ptt-android-body {
  min-height:
    0;

  flex:
    1;

  display:
    grid;

  grid-template-columns:
    280px
    minmax(
      420px,
      1fr
    )
    270px;

  background:
    #0d1421;
}


/* ==========================================================
   KANALEN
   ========================================================== */

.ptt-android-channel-panel {
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
    linear-gradient(
      180deg,
      #111a2a,
      #0f1725
    );
}


.ptt-android-section-title {
  height:
    58px;

  flex:
    0 0 58px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    space-between;

  padding:
    0 20px;

  color:
    #91a3bf;

  font-size:
    11px;

  font-weight:
    800;

  letter-spacing:
    0.08em;
}


.ptt-android-add-symbol {
  color:
    #91a5c5;

  font-size:
    24px;

  font-weight:
    300;
}


.ptt-android-channel-scroll {
  min-height:
    0;

  flex:
    1;

  overflow:
    auto;

  padding:
    0 9px 12px;
}


.ptt-android-channel-row {
  position:
    relative;

  width:
    100%;

  min-height:
    66px;

  display:
    flex;

  align-items:
    center;

  gap:
    13px;

  margin:
    3px 0;

  padding:
    9px 15px;

  border:
    1px solid
    transparent;

  border-radius:
    9px;

  background:
    transparent;

  color:
    inherit;

  text-align:
    left;

  cursor:
    pointer;

  transition:
    background 0.12s ease,
    border-color 0.12s ease,
    transform 0.12s ease;
}


.ptt-android-channel-row:hover {
  background:
    rgba(
      58,
      88,
      138,
      0.13
    );
}


.ptt-android-channel-row:active {
  transform:
    scale(
      0.99
    );
}


.ptt-android-channel-row-active {
  border-color:
    rgba(
      71,
      129,
      231,
      0.19
    );

  background:
    linear-gradient(
      90deg,
      rgba(
        42,
        83,
        154,
        0.50
      ),
      rgba(
        34,
        57,
        98,
        0.28
      )
    );
}


.ptt-android-channel-row-active::before {
  content:
    "";

  position:
    absolute;

  top:
    4px;

  bottom:
    4px;

  left:
    -9px;

  width:
    3px;

  border-radius:
    0 4px 4px 0;

  background:
    #36c7ff;

  box-shadow:
    0 0 9px
    rgba(
      54,
      199,
      255,
      0.45
    );
}


.ptt-android-channel-icon {
  width:
    31px;

  flex:
    0 0 31px;

  text-align:
    center;

  color:
    #45c8ff;

  font-size:
    20px;
}


.ptt-android-channel-icon-1 {
  color:
    #45d18b;
}


.ptt-android-channel-icon-2 {
  color:
    #b38cff;
}


.ptt-android-channel-icon-3 {
  color:
    #ffb24f;
}


.ptt-android-channel-info {
  min-width:
    0;

  flex:
    1;

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
    #edf3fc;

  font-size:
    13px;

  text-overflow:
    ellipsis;

  white-space:
    nowrap;
}


.ptt-android-channel-info small {
  color:
    #7d8faa;

  font-size:
    10px;
}


.ptt-android-channel-active-dot {
  width:
    8px;

  height:
    8px;

  flex:
    0 0 8px;

  border-radius:
    50%;

  background:
    #2adb70;

  box-shadow:
    0 0 7px
    rgba(
      42,
      219,
      112,
      0.55
    );
}


/* ==========================================================
   MIDDEN
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
    26px 35px 16px;

  background:
    radial-gradient(
      circle at 50% 49%,
      rgba(
        24,
        53,
        100,
        0.28
      ),
      transparent 52%
    ),
    #0d1421;
}


.ptt-android-current-channel {
  display:
    flex;

  align-items:
    center;

  gap:
    13px;
}


.ptt-android-current-icon {
  position:
    relative;

  width:
    46px;

  height:
    46px;

  flex:
    0 0 46px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  border:
    1px solid
    rgba(
      82,
      135,
      225,
      0.28
    );

  border-radius:
    50%;

  background:
    linear-gradient(
      145deg,
      #285092,
      #1b365f
    );

  color:
    #e7f0ff;

  font-size:
    22px;
}


.ptt-android-current-icon-tail {
  position:
    absolute;

  right:
    -2px;

  bottom:
    -2px;

  width:
    16px;

  height:
    16px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  border-radius:
    50%;

  background:
    #1b273a;

  color:
    #8aa5ce;

  font-size:
    9px;
}


.ptt-android-current-info {
  min-width:
    0;
}


.ptt-android-current-info h2 {
  margin:
    0;

  overflow:
    hidden;

  color:
    #ffffff;

  font-size:
    24px;

  font-weight:
    800;

  text-overflow:
    ellipsis;

  white-space:
    nowrap;
}


.ptt-android-current-sub {
  display:
    flex;

  align-items:
    center;

  gap:
    8px;

  margin-top:
    5px;

  color:
    #8798b2;

  font-size:
    11px;
}


/* ==========================================================
   GROTE PTT KNOP
   ========================================================== */

.ptt-android-center {
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

  padding-top:
    5px;
}


.ptt-android-ptt-halo {
  padding:
    12px;

  border:
    1px solid
    rgba(
      53,
      134,
      255,
      0.18
    );

  border-radius:
    50%;

  box-shadow:
    0 0 40px
    rgba(
      27,
      104,
      255,
      0.12
    );
}


.ptt-android-ptt-button {
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
    215px;

  min-height:
    215px;

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

  padding:
    0;

  border:
    9px solid
    #2b98ff;

  border-radius:
    50%;

  outline:
    7px solid
    rgba(
      26,
      84,
      197,
      0.30
    );

  background:
    radial-gradient(
      circle at 48% 25%,
      #4ab9ff 0%,
      #1882ff 26%,
      #0b60f0 58%,
      #073daf 100%
    );

  color:
    #ffffff;

  cursor:
    pointer;

  touch-action:
    none;

  user-select:
    none;

  box-shadow:
    0 0 0 1px
    rgba(
      130,
      200,
      255,
      0.32
    ),
    0 0 39px
    rgba(
      17,
      105,
      255,
      0.48
    ),
    inset 0 18px 37px
    rgba(
      255,
      255,
      255,
      0.17
    ),
    inset 0 -24px 40px
    rgba(
      0,
      22,
      87,
      0.34
    );

  transition:
    transform 0.07s ease,
    box-shadow 0.08s ease,
    border-color 0.08s ease,
    filter 0.08s ease;
}


.ptt-android-ptt-button:hover:not(:disabled) {
  filter:
    brightness(
      1.07
    );

  box-shadow:
    0 0 0 1px
    rgba(
      135,
      210,
      255,
      0.42
    ),
    0 0 52px
    rgba(
      20,
      119,
      255,
      0.60
    ),
    inset 0 18px 37px
    rgba(
      255,
      255,
      255,
      0.18
    ),
    inset 0 -24px 40px
    rgba(
      0,
      22,
      87,
      0.34
    );
}


.ptt-android-ptt-button:active:not(:disabled),
.ptt-android-ptt-tx {
  transform:
    scale(
      0.965
    );

  border-color:
    #6cecff;

  background:
    radial-gradient(
      circle at 48% 25%,
      #58e5ff 0%,
      #178aff 30%,
      #075ce7 63%,
      #062c83 100%
    );

  box-shadow:
    0 0 18px
    rgba(
      86,
      230,
      255,
      0.90
    ),
    0 0 64px
    rgba(
      29,
      132,
      255,
      0.82
    ),
    inset 0 17px 34px
    rgba(
      255,
      255,
      255,
      0.20
    );
}


.ptt-android-ptt-button:disabled {
  cursor:
    not-allowed;

  opacity:
    0.48;

  filter:
    saturate(
      0.35
    );
}


.ptt-android-ptt-mic {
  font-size:
    55px;

  filter:
    drop-shadow(
      0 4px 6px
      rgba(
        0,
        0,
        0,
        0.25
      )
    );
}


.ptt-android-ptt-button strong {
  font-size:
    39px;

  font-weight:
    900;

  letter-spacing:
    1px;

  text-shadow:
    0 3px 8px
    rgba(
      0,
      0,
      0,
      0.20
    );
}


/* ==========================================================
   SPREKER
   ========================================================== */

.ptt-android-speaking-now {
  min-width:
    340px;

  max-width:
    min(
      560px,
      90%
    );

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  gap:
    8px;

  margin-top:
    26px;

  padding:
    10px 20px;

  overflow:
    hidden;

  border:
    1px solid
    rgba(
      91,
      115,
      154,
      0.31
    );

  border-radius:
    999px;

  background:
    rgba(
      12,
      21,
      35,
      0.82
    );

  color:
    #96a5bc;

  font-size:
    12px;
}


.ptt-android-speaking-now strong {
  overflow:
    hidden;

  color:
    #ffffff;

  text-overflow:
    ellipsis;

  white-space:
    nowrap;
}


.ptt-android-speaking-now-active {
  border-color:
    rgba(
      37,
      224,
      116,
      0.60
    );

  background:
    rgba(
      19,
      73,
      49,
      0.25
    );

  color:
    #dffbea;

  box-shadow:
    0 0 12px
    rgba(
      37,
      224,
      116,
      0.10
    );
}


.ptt-android-speaking-wave-icon {
  color:
    #24e077;

  font-size:
    20px;

  font-weight:
    900;
}


/* ==========================================================
   AUDIO WAVEFORM
   ========================================================== */

.ptt-android-waveform {
  height:
    52px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  gap:
    4px;

  margin-top:
    8px;
}


.ptt-android-waveform i {
  width:
    4px;

  height:
    10px;

  display:
    block;

  border-radius:
    999px;

  background:
    #26364f;
}


.ptt-android-waveform-active i {
  background:
    #25dd77;

  animation:
    pttAndroidWave
    0.58s
    ease-in-out
    infinite alternate;
}


.ptt-android-waveform-active i:nth-child(2n) {
  animation-delay:
    -0.12s;
}


.ptt-android-waveform-active i:nth-child(3n) {
  animation-delay:
    -0.23s;
}


.ptt-android-waveform-active i:nth-child(4n) {
  animation-delay:
    -0.34s;
}


.ptt-android-waveform-active i:nth-child(5n) {
  animation-delay:
    -0.45s;
}


@keyframes pttAndroidWave {

  from {
    height:
      9px;
  }

  to {
    height:
      45px;
  }

}


/* ==========================================================
   USER PANEL
   ========================================================== */

.ptt-android-user-panel {
  min-height:
    0;

  display:
    flex;

  flex-direction:
    column;

  padding:
    16px 13px;

  border-left:
    1px solid
    rgba(
      255,
      255,
      255,
      0.05
    );

  background:
    linear-gradient(
      180deg,
      #111a2a,
      #0f1725
    );
}


.ptt-android-user-title {
  height:
    40px;

  flex:
    0 0 40px;

  padding:
    7px 8px;

  color:
    #92a4c0;

  font-size:
    11px;

  font-weight:
    800;

  letter-spacing:
    0.06em;
}


.ptt-android-user-scroll {
  min-height:
    0;

  flex:
    1;

  overflow:
    auto;
}


.ptt-android-user-row {
  min-height:
    52px;

  display:
    flex;

  align-items:
    center;

  gap:
    9px;

  margin-bottom:
    3px;

  padding:
    6px 8px;

  border:
    1px solid
    transparent;

  border-radius:
    10px;

  transition:
    background 0.12s ease,
    border-color 0.12s ease;
}


.ptt-android-user-row-talking {
  border-color:
    rgba(
      38,
      224,
      115,
      0.28
    );

  background:
    linear-gradient(
      90deg,
      rgba(
        23,
        112,
        65,
        0.22
      ),
      rgba(
        13,
        67,
        44,
        0.10
      )
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
    linear-gradient(
      145deg,
      #3b7ccc,
      #28549a
    );

  color:
    #ffffff;

  font-size:
    13px;

  font-weight:
    800;

  box-shadow:
    inset 0 1px 0
    rgba(
      255,
      255,
      255,
      0.10
    );
}


.ptt-android-avatar-1 {
  background:
    linear-gradient(
      145deg,
      #7962cf,
      #4e3d99
    );
}


.ptt-android-avatar-2 {
  background:
    linear-gradient(
      145deg,
      #4e9a60,
      #356b41
    );
}


.ptt-android-avatar-3 {
  background:
    linear-gradient(
      145deg,
      #bc7445,
      #814b2a
    );
}


.ptt-android-avatar-4 {
  background:
    linear-gradient(
      145deg,
      #3f82b9,
      #285476
    );
}


.ptt-android-avatar-5 {
  background:
    linear-gradient(
      145deg,
      #aa8b35,
      #746026
    );
}


.ptt-android-user-status {
  width:
    8px;

  height:
    8px;

  flex:
    0 0 8px;

  border-radius:
    50%;

  background:
    #24de69;

  box-shadow:
    0 0 5px
    rgba(
      36,
      222,
      105,
      0.38
    );
}


.ptt-android-user-status-talking {
  background:
    #49e7ff;

  box-shadow:
    0 0 10px
    rgba(
      73,
      231,
      255,
      0.90
    );
}


.ptt-android-user-status-away {
  background:
    #f4c93f;

  box-shadow:
    none;
}


.ptt-android-user-status-muted {
  background:
    #677488;

  box-shadow:
    none;
}


.ptt-android-user-info {
  min-width:
    0;

  display:
    flex;

  flex-direction:
    column;
}


.ptt-android-user-info strong {
  overflow:
    hidden;

  color:
    #eaf0fa;

  font-size:
    12px;

  text-overflow:
    ellipsis;

  white-space:
    nowrap;
}


.ptt-android-user-info small {
  margin-top:
    2px;

  color:
    #43e7ff;

  font-size:
    9px;

  font-weight:
    700;
}


/* ==========================================================
   LEGE LIJST
   ========================================================== */

.ptt-android-empty {
  padding:
    20px 10px;

  color:
    #6f819d;

  font-size:
    11px;

  text-align:
    center;
}


/* ==========================================================
   ONDERBALK
   ========================================================== */

.ptt-android-audio-footer {
  min-height:
    87px;

  flex:
    0 0 87px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  gap:
    28px;

  padding:
    10px 38px;

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
      #0f1725
    );
}


.ptt-android-audio-device {
  min-width:
    0;

  max-width:
    520px;

  flex:
    1;

  display:
    flex;

  align-items:
    center;

  gap:
    12px;
}


.ptt-android-device-circle {
  width:
    44px;

  height:
    44px;

  flex:
    0 0 44px;

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
      0.075
    );

  border-radius:
    50%;

  background:
    linear-gradient(
      145deg,
      #202d42,
      #172235
    );

  font-size:
    19px;
}


.ptt-android-audio-device label {
  min-width:
    0;

  flex:
    1;

  display:
    flex;

  flex-direction:
    column;

  gap:
    5px;
}


.ptt-android-audio-device label > span {
  color:
    #99a9c1;

  font-size:
    10px;
}


.ptt-android-audio-device select {
  width:
    100%;

  height:
    39px;

  padding:
    0 11px;

  border:
    1px solid
    rgba(
      105,
      135,
      180,
      0.20
    );

  border-radius:
    8px;

  outline:
    none;

  background:
    #151f30;

  color:
    #e7eef9;

  font-size:
    12px;
}


.ptt-android-audio-device select:focus {
  border-color:
    rgba(
      65,
      139,
      255,
      0.60
    );

  box-shadow:
    0 0 0 2px
    rgba(
      65,
      139,
      255,
      0.10
    );
}


.ptt-android-footer-divider {
  width:
    1px;

  height:
    48px;

  background:
    rgba(
      255,
      255,
      255,
      0.075
    );
}


/* ==========================================================
   SCROLLBARS
   ========================================================== */

.ptt-android-view ::-webkit-scrollbar {
  width:
    8px;

  height:
    8px;
}


.ptt-android-view ::-webkit-scrollbar-track {
  background:
    transparent;
}


.ptt-android-view ::-webkit-scrollbar-thumb {
  border-radius:
    999px;

  background:
    #283851;
}


.ptt-android-view ::-webkit-scrollbar-thumb:hover {
  background:
    #395170;
}


/* ==========================================================
   RESPONSIVE
   ========================================================== */

@media (
  max-width:
    1250px
) {

  .ptt-android-body {
    grid-template-columns:
      225px
      minmax(
        350px,
        1fr
      )
      220px;
  }


  .ptt-android-main {
    padding:
      23px 20px 13px;
  }


  .ptt-android-ptt-button {
    width:
      245px;

    height:
      245px;

    min-width:
      245px;

    min-height:
      245px;
  }

}


@media (
  max-width:
    950px
) {

  .ptt-android-body {
    grid-template-columns:
      190px
      minmax(
        320px,
        1fr
      );
  }


  .ptt-android-user-panel {
    display:
      none;
  }


  .ptt-android-speaking-now {
    min-width:
      275px;
  }


  .ptt-android-audio-footer {
    padding-left:
      18px;

    padding-right:
      18px;
  }

}


@media (
  max-width:
    720px
) {

  .ptt-android-view {
    inset:
      62px 8px 8px;
  }


  .ptt-android-body {
    display:
      flex;

    flex-direction:
      column;
  }


  .ptt-android-channel-panel {
    max-height:
      180px;

    border-right:
      0;

    border-bottom:
      1px solid
      rgba(
        255,
        255,
        255,
        0.05
      );
  }


  .ptt-android-channel-scroll {
    display:
      flex;

    overflow-x:
      auto;
  }


  .ptt-android-channel-row {
    min-width:
      185px;
  }


  .ptt-android-main {
    min-height:
      430px;
  }


  .ptt-android-audio-footer {
    min-height:
      auto;

    flex-direction:
      column;

    align-items:
      stretch;

    gap:
      10px;

    padding:
      12px;
  }


  .ptt-android-footer-divider {
    width:
      100%;

    height:
      1px;
  }


  .ptt-android-audio-device {
    max-width:
      none;
  }


  .ptt-android-connection {
    display:
      none;
  }

}


@media (
  max-height:
    760px
) {

  .ptt-android-ptt-button {
    width:
      210px;

    height:
      210px;

    min-width:
      210px;

    min-height:
      210px;
  }


  .ptt-android-ptt-mic {
    font-size:
      45px;
  }


  .ptt-android-ptt-button strong {
    font-size:
      32px;
  }


  .ptt-android-speaking-now {
    margin-top:
      17px;
  }


  .ptt-android-waveform {
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


# ============================================================
# KLAAR
# ============================================================

print(
    "============================================"
)

print(
    "PTT Connect complete patch klaar"
)

print(
    "============================================"
)

print(
    "- groene build #37 als stabiele basis"
)

print(
    "- Android App knop toegevoegd"
)

print(
    "- oude CB interface vervangen"
)

print(
    "- realistische Android App interface"
)

print(
    "- echte TeamSpeak kanalen links"
)

print(
    "- klikken op kanaal wisselt echt van kanaal"
)

print(
    "- echte gebruikers rechts"
)

print(
    "- actieve spreker zichtbaar"
)

print(
    "- grote PTT knop werkt met bestaande PTT engine"
)

print(
    "- PTT knop ingedrukt houden = praten"
)

print(
    "- PTT knop loslaten = stoppen"
)

print(
    "- echte microfoonkeuze onderaan"
)

print(
    "- echte luidsprekerkeuze onderaan"
)

print(
    "- Settings menu werkt"
)

print(
    "- Windows knop keert terug naar normale weergave"
)

print(
    "- TeamSpeak ontvangstaudio NIET veranderd"
)

print(
    "- webcam NIET veranderd"
)

print(
    "- videogalerij NIET veranderd"
)

print(
    "- schermdelen NIET veranderd"
)

print(
    "- radiostreams NIET veranderd"
)

print(
    "- Android repository NIET veranderd"
)
