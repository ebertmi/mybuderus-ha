# myBuderus API Spec

## Auth — SingleKey ID (OAuth2 PKCE)

- **Discovery URI:** https://singlekey-id.com/auth/
- **Authorization Endpoint:** https://singlekey-id.com/auth/connect/authorize
- **Token Endpoint:** https://singlekey-id.com/auth/connect/token
- **UserInfo Endpoint:** https://singlekey-id.com/auth/connect/userinfo
- **JWKS URI:** https://singlekey-id.com/auth/.well-known/openid-configuration/jwks
- **End Session Endpoint:** https://singlekey-id.com/auth/connect/endsession
- **Client ID:** 762162C0-FA2D-4540-AE66-6489F189FADC
- **Redirect URI (App):** com.buderus.tt.dashtt://app/login
- **Redirect URI (Prototyp):** http://localhost:8765/callback
- **Scopes:** openid email profile offline_access pointt.gateway.list pointt.gateway.resource.dashapp pointt.castt.flow.token-exchange bacon hcc.tariff.read
- **PKCE:** Code Challenge Method S256 (auch `plain` unterstützt; S256 bevorzugen)
- **Flow:** Authorization Code + PKCE (kein client_secret)
- **localhost-Redirect erlaubt:** NEIN — Server antwortet mit HTTP 302 → `misconfigured-application`-Fehlerseite. `http://localhost:8765/callback` ist beim Client nicht registriert. Nur `com.buderus.tt.dashtt://app/login` (Android Custom Scheme) ist als Redirect URI hinterlegt. Für den Prototyp muss entweder ein Custom URI Scheme simuliert werden (z.B. per lokaler URL-Handler-Registrierung) oder eine alternative Methode gewählt werden.

### Discovery-Rohdaten (relevante Felder)

```json
{
  "issuer": "https://singlekey-id.com/auth",
  "authorization_endpoint": "https://singlekey-id.com/auth/connect/authorize",
  "token_endpoint": "https://singlekey-id.com/auth/connect/token",
  "userinfo_endpoint": "https://singlekey-id.com/auth/connect/userinfo",
  "jwks_uri": "https://singlekey-id.com/auth/.well-known/openid-configuration/jwks",
  "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
  "response_types_supported": ["code", "code id_token"],
  "code_challenge_methods_supported": ["plain", "S256"],
  "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"]
}
```

**Hinweis zu `token_endpoint_auth_methods_supported`:** Der Server listet nur `client_secret_basic` und `client_secret_post` — kein `none`. Das bedeutet die Server-Konfiguration erwartet formal ein client_secret. Die App umgeht das vermutlich, indem sie ein leeres oder hartcodiertes secret sendet, oder der Server akzeptiert Requests ohne secret für diesen spezifischen Client. Muss beim Token-Exchange getestet werden.

## REST API

- **Base URL:** https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1/
- **URL-Muster:** gateways/{gatewayId}/resource/{path}
- **Auth Header:** Authorization: Bearer {access_token}
