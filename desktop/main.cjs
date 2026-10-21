// اپ ویندوز خلاصه اخبار (Electron) - مثل اپ ویندوز اپ شیفت.
// خودِ سایت اپ رو تو یک پنجره‌ی معمولی (بدون نوار آدرس و منو) باز می‌کنه، پس هر تغییری تو
// اپ وب بدون نصب دوباره اینجا هم دیده می‌شه. لینک خبرها تو مرورگر پیش‌فرض ویندوز باز می‌شن.
const { app, BrowserWindow, Menu, shell } = require("electron");
const path = require("path");

const START_URL = "https://3omid.github.io/persian-news-digest/";
const APP_ORIGIN = new URL(START_URL).origin;

app.setName("News Digest");

function createWindow() {
  const win = new BrowserWindow({
    width: 1100,
    height: 800,
    minWidth: 380,
    minHeight: 560,
    title: "خلاصه اخبار",
    icon: path.join(__dirname, "icon.png"),
    autoHideMenuBar: true,
    backgroundColor: "#E1EFEB",
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  win.setMenuBarVisibility(false);

  // خبرها (هر لینکی بیرون از سایت اپ) تو مرورگر ویندوز باز می‌شن، نه داخل اپ.
  const openOutside = (url) => {
    if (/^https?:/i.test(url)) shell.openExternal(url);
  };
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith(APP_ORIGIN)) return { action: "allow" };
    openOutside(url);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (e, url) => {
    if (!url.startsWith(APP_ORIGIN) && !url.startsWith("file:")) {
      e.preventDefault();
      openOutside(url);
    }
  });

  // اولین اجرا بدون اینترنت: یه صفحه‌ی ساده با دکمه‌ی «دوباره». بعد از اولین اجرا، خودِ
  // اپ (service worker) نسخه‌ی ذخیره‌شده رو بدون اینترنت هم باز می‌کنه.
  win.webContents.on("did-fail-load", (_e, code, _desc, url, isMainFrame) => {
    if (isMainFrame && code !== -3 && url.startsWith(APP_ORIGIN)) {
      win.loadFile(path.join(__dirname, "offline.html"), { query: { url: START_URL } });
    }
  });

  win.loadURL(START_URL);
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  createWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
