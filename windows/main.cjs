const { app, BrowserWindow, session, shell } = require("electron");
const { spawn } = require("node:child_process");
const http = require("node:http");
const path = require("node:path");

const PTT_PORT = 32137;
const PTT_PARTITION = "persist:pttconnect";

let gatewayProcess;
let mainWindow;

function waitForGateway(port, attempts = 80) {
  return new Promise((resolve, reject) => {
    const tryOnce = (left) => {
      const req = http.get(
        {
          host: "127.0.0.1",
          port,
          path: "/",
          timeout: 1000
        },
        (res) => {
          res.resume();

          if (res.statusCode && res.statusCode < 500) {
            resolve();
          } else if (left > 0) {
            setTimeout(() => tryOnce(left - 1), 250);
          } else {
            reject(new Error("PTT Connect gateway startte niet."));
          }
        }
      );

      req.on("timeout", () => {
        req.destroy();
      });

      req.on("error", () => {
        if (left > 0) {
          setTimeout(() => tryOnce(left - 1), 250);
        } else {
          reject(
            new Error("PTT Connect gateway is niet bereikbaar.")
          );
        }
      });
    };

    tryOnce(attempts);
  });
}

function runtimePath(...parts) {
  return path.join(
    process.resourcesPath,
    "runtime",
    ...parts
  );
}

function startGateway(port) {
  const gatewayEntry = runtimePath(
    "gateway",
    "dist",
    "index.js"
  );

  const connectorBin = runtimePath(
    "connector",
    "ts-connector.exe"
  );

  const webDist = runtimePath("web");

  const env = {
    ...process.env,

    ELECTRON_RUN_AS_NODE: "1",

    PORT: String(port),

    WEB_DIST: webDist,

    CONNECTOR_BIN: connectorBin,

    DEFAULT_SERVER: "Heerlen.MIJNTS3.NL",

    FEEDBACK_ENABLED: "0",

    STORE_ENABLED: "0",

    LOG_CONNECTIONS: "0"
  };

  gatewayProcess = spawn(
    process.execPath,
    [gatewayEntry],
    {
      cwd: path.dirname(gatewayEntry),
      env,
      windowsHide: true,
      stdio: [
        "ignore",
        "pipe",
        "pipe"
      ]
    }
  );

  gatewayProcess.stdout?.on(
    "data",
    (data) => {
      console.log(
        "[PTT gateway]",
        data.toString().trim()
      );
    }
  );

  gatewayProcess.stderr?.on(
    "data",
    (data) => {
      console.error(
        "[PTT gateway]",
        data.toString().trim()
      );
    }
  );
}

function stopGateway() {
  if (
    gatewayProcess &&
    !gatewayProcess.killed
  ) {
    gatewayProcess.kill();
  }

  gatewayProcess = undefined;
}

async function createWindow() {
  const localOrigin =
    `http://127.0.0.1:${PTT_PORT}`;

  startGateway(PTT_PORT);

  await waitForGateway(PTT_PORT);

  const pttSession =
    session.fromPartition(
      PTT_PARTITION
    );

  pttSession.setPermissionRequestHandler(
    (
      webContents,
      permission,
      callback
    ) => {
      const url =
        webContents.getURL();

      const allowedOrigin =
        url.startsWith(localOrigin);

      callback(
        allowedOrigin &&
        (
          permission === "media" ||
          permission === "notifications"
        )
      );
    }
  );

  pttSession.setPermissionCheckHandler(
    (
      webContents,
      permission,
      requestingOrigin
    ) => {
      return (
        requestingOrigin.startsWith(
          localOrigin
        ) &&
        (
          permission === "media" ||
          permission === "notifications"
        )
      );
    }
  );

  mainWindow = new BrowserWindow({
    width: 1440,

    height: 900,

    minWidth: 980,

    minHeight: 650,

    title: "PTT Connect",

    backgroundColor: "#07111f",

    autoHideMenuBar: true,

    webPreferences: {
      contextIsolation: true,

      nodeIntegration: false,

      sandbox: true,

      partition: PTT_PARTITION
    }
  });

  mainWindow.removeMenu();

  mainWindow.webContents
    .setWindowOpenHandler(
      ({ url }) => {
        if (
          url.startsWith("http://") ||
          url.startsWith("https://")
        ) {
          shell.openExternal(url);
        }

        return {
          action: "deny"
        };
      }
    );

  await mainWindow.loadURL(
    localOrigin
  );
}

const gotLock =
  app.requestSingleInstanceLock();

if (!gotLock) {
  app.quit();
} else {
  app.on(
    "second-instance",
    () => {
      if (mainWindow) {
        if (
          mainWindow.isMinimized()
        ) {
          mainWindow.restore();
        }

        mainWindow.focus();
      }
    }
  );

  app.on(
    "before-quit",
    () => {
      stopGateway();
    }
  );

  app.on(
    "window-all-closed",
    () => {
      stopGateway();

      if (
        process.platform !== "darwin"
      ) {
        app.quit();
      }
    }
  );

  app.whenReady()
    .then(createWindow)
    .catch((error) => {
      console.error(error);

      stopGateway();

      app.quit();
    });
}
