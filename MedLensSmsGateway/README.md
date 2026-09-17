# MedLens AI — Android SIM-Based SMS Patient Alert Gateway

An open-source, cost-free SMS dispatch bridge for **MedLens AI**. Converts any standard Android smartphone with a working SIM card into an automated SMS alert gateway.

---

## 🌟 Architecture & Data Flow

```
[Doctor Console / Patient Portal]
           │
           │  1. Doctor creates Care Directive (with SMS enabled)
           ▼
[MedLens FastAPI Backend]
   • Saves care directive in DB
   • Validates patient phone number (+91 Indian mobile format)
   • Generates safe clinical alert text (< 320 chars, no sensitive lab values)
   • Places message into `sms_outbox` queue (status: 'queued')
           │
           │  2. Android Phone polls `GET /api/sms-gateway/queue` every 30s
           ▼
[Android Gateway App (MedLensSmsGateway)]
   • Claims message atomically via `POST /api/sms-gateway/{id}/claim`
   • Receives recipient mobile number
   • Dispatches physical SMS via device SIM card (`android.telephony.SmsManager`)
   • Listens for radio broadcast intent `RESULT_OK`
           │
           │  3. Reports delivery status `POST /api/sms-gateway/{id}/status`
           ▼
[MedLens Database & UI Updates]
   • Outbox status updated to `sent` with timestamp
   • Doctor Console & Patient Portal display `📱 SMS Sent` badge
```

---

## 🚀 Key Features

1. **Zero Third-Party Cost**: No Twilio, MSG91, or AWS SNS paid SMS credits required. Uses existing SIM SMS packs (e.g. standard 100 SMS/day packs in India).
2. **Atomic Lock Protection**: Multiple gateways or concurrent polls cannot duplicate an SMS. Messages are claimed before dispatch.
3. **Stale Recovery**: Messages stuck in `processing` for > 5 minutes are automatically reset to `queued`.
4. **Privacy First**: Sensitive medical diagnoses and lab results are never sent over unencrypted SMS. Generic directives and appointment notices are sent instead.
5. **Daily Quota Safety**: Built-in 100 SMS/day limit to protect phone SIM from telecom spam bans.
6. **24/7 Background Service**: Runs as an Android Sticky Foreground Service with automatic boot recovery.

---

## 📱 How to Build and Run the Android App

### Requirements
- Android Studio Hedgehog (2023.1.1) or newer
- Android SDK 34 (Android 14)
- Physical Android phone with a working SIM card (or Android Emulator for testing network calls)
- Minimum Android version: Android 5.0 Lollipop (API 21)

### Setup Steps
1. Open **Android Studio**.
2. Select **Open Project** and navigate to `learnathon/MedLensSmsGateway/`.
3. Allow Gradle to sync dependencies (`OkHttp 4.12.0`, `Gson 2.10.1`, `Material Components`).
4. Connect your Android phone via USB and enable **USB Debugging** (in Developer Options).
5. Grant the app **SMS Sending** and **Notifications** permissions when prompted on first launch.

### Pairing with MedLens AI Backend
1. Ensure your PC running FastAPI and your Android phone are on the **same Wi-Fi network**.
2. Find your PC's local IP address (e.g. run `ipconfig` on Windows -> `192.168.1.105`).
3. In the MedLens SMS Gateway Android app:
   - Tap **Configure Server & Pair Device**.
   - Set **Server Base URL** to `http://<YOUR_PC_IP>:8000` (e.g. `http://192.168.1.105:8000`).
   - If testing via Android Studio Emulator, use `http://10.0.2.2:8000`.
   - Set **Admin Pairing Secret** to the value in your `.env` (default: `medlens-sms-gateway-secret-2026`).
   - Tap **Test Connection & Pair Device**.
4. Once paired, return to the dashboard and tap **Start Gateway Service**.

---

## 🧪 Demonstration & Testing Flow

1. Open the MedLens AI Web Application in your browser: `http://localhost:8000`.
2. Go to **Doctor Console** -> **Care Directives & Reminders**.
3. Notice the **Android SIM SMS Patient Alert Gateway** monitor at the bottom of the table.
4. Click **✉️ Send Direct Test SMS**:
   - Enter your personal Indian mobile number (e.g. `+91 9876543210`).
   - Enter a test alert message.
   - Click **Queue for SIM Dispatch**.
5. Within 30 seconds (or current poll interval), the connected Android phone will:
   - Claim the message.
   - Send the SMS via its SIM card.
   - Report success to MedLens backend.
6. The Doctor Console and Patient Portal will update to show:
   `📱 SMS Sent`.

---

## 🔒 Security Specifications
- All gateway polling requires a per-device `X-Gateway-Token` generated during pairing.
- Admin endpoints require `X-Admin-Token` matching `SMS_GATEWAY_TOKEN_SECRET`.
- Phone numbers are masked in logs and queue previews (e.g. `+91 98765 43210` -> `***3210`).
