const { app, BrowserWindow, shell } = require("electron");
const path = require("node:path");

function rendererUrl() {
  if (process.env.LABORATORIO_WEB_URL) {
    return process.env.LABORATORIO_WEB_URL;
  }
  return `file://${path.join(__dirname, "renderer", "index.html")}`;
}

function createWindow() {
  const window = new BrowserWindow({
    width: 1320,
    height: 860,
    minWidth: 980,
    minHeight: 680,
    title: "Laboratorio",
    backgroundColor: "#eef2f3",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  window.loadURL(rendererUrl());
  window.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
