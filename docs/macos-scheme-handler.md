# macOS URL Scheme Handler for SingleKey ID Auth

## Problem

The SingleKey ID OAuth2 server only accepts `com.buderus.tt.dashtt://app/login` as the redirect URI. When the browser receives this redirect, it fails with:

> Failed to launch 'com.buderus.tt.dashtt://app/login?code=...' because the scheme does not have a registered handler.

Currently the workaround is to open DevTools (F12) → Network tab → filter for `com.buderus.tt.dashtt` and copy the redirect URL manually into the HA config flow.

## Proposed Improvement

Create a minimal macOS `.app` bundle that registers itself as the handler for the `com.buderus.tt.dashtt://` scheme. When the browser fires the redirect after login, macOS launches the app, which extracts the `code` parameter and copies it to the clipboard. The user then just pastes into the HA config flow — no DevTools required.

## Implementation Sketch

### Bundle structure

```
BuderusAuth.app/
└── Contents/
    ├── Info.plist      ← registers the URL scheme with macOS
    └── MacOS/
        └── handler     ← executable script (shell or Python)
```

### Info.plist (key parts)

```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLName</key>
    <string>Buderus Auth Callback</string>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>com.buderus.tt.dashtt</string>
    </array>
  </dict>
</array>
```

### handler script

The script receives the full URL as an Apple Event. It should:
1. Extract the `code` query parameter from the URL
2. Copy it to the clipboard (`pbcopy`)
3. Optionally show a brief notification (`osascript`)

After building the bundle, register it once with:

```bash
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f BuderusAuth.app
```

## Result

Auth flow becomes:
1. Click the auth link in the HA config flow
2. Log in with SingleKey ID credentials
3. Browser fires the redirect → macOS opens `BuderusAuth.app` silently
4. Code is in the clipboard
5. Paste into the HA config flow field
