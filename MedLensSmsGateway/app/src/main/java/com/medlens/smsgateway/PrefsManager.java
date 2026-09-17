package com.medlens.smsgateway;

import android.content.Context;
import android.content.SharedPreferences;

import java.util.UUID;

public class PrefsManager {
    private static final String PREF_NAME = "medlens_sms_gateway_prefs";
    private static final String KEY_BASE_URL = "base_url";
    private static final String KEY_ADMIN_TOKEN = "admin_token";
    private static final String KEY_GATEWAY_TOKEN = "gateway_token";
    private static final String KEY_DEVICE_ID = "device_id";
    private static final String KEY_DEVICE_NAME = "device_name";
    private static final String KEY_POLL_INTERVAL = "poll_interval_sec";
    private static final String KEY_SERVICE_ENABLED = "service_enabled";
    private static final String KEY_TOTAL_SENT = "total_sent";
    private static final String KEY_TOTAL_FAILED = "total_failed";

    private final SharedPreferences prefs;

    public PrefsManager(Context context) {
        this.prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
    }

    public String getBaseUrl() {
        return prefs.getString(KEY_BASE_URL, "http://10.0.2.2:8000");
    }

    public void setBaseUrl(String url) {
        if (url != null && url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }
        prefs.edit().putString(KEY_BASE_URL, url).apply();
    }

    public String getAdminToken() {
        return prefs.getString(KEY_ADMIN_TOKEN, "medlens-sms-gateway-secret-2026");
    }

    public void setAdminToken(String token) {
        prefs.edit().putString(KEY_ADMIN_TOKEN, token).apply();
    }

    public String getGatewayToken() {
        return prefs.getString(KEY_GATEWAY_TOKEN, "");
    }

    public void setGatewayToken(String token) {
        prefs.edit().putString(KEY_GATEWAY_TOKEN, token).apply();
    }

    public String getDeviceId() {
        String id = prefs.getString(KEY_DEVICE_ID, null);
        if (id == null || id.isEmpty()) {
            id = "android-" + UUID.randomUUID().toString().substring(0, 8);
            prefs.edit().putString(KEY_DEVICE_ID, id).apply();
        }
        return id;
    }

    public void setDeviceId(String id) {
        prefs.edit().putString(KEY_DEVICE_ID, id).apply();
    }

    public String getDeviceName() {
        return prefs.getString(KEY_DEVICE_NAME, android.os.Build.MANUFACTURER + " " + android.os.Build.MODEL);
    }

    public void setDeviceName(String name) {
        prefs.edit().putString(KEY_DEVICE_NAME, name).apply();
    }

    public int getPollIntervalSeconds() {
        return prefs.getInt(KEY_POLL_INTERVAL, 30);
    }

    public void setPollIntervalSeconds(int seconds) {
        prefs.edit().putInt(KEY_POLL_INTERVAL, Math.max(5, seconds)).apply();
    }

    public boolean isServiceEnabled() {
        return prefs.getBoolean(KEY_SERVICE_ENABLED, false);
    }

    public void setServiceEnabled(boolean enabled) {
        prefs.edit().putBoolean(KEY_SERVICE_ENABLED, enabled).apply();
    }

    public int getTotalSent() {
        return prefs.getInt(KEY_TOTAL_SENT, 0);
    }

    public synchronized void incrementTotalSent() {
        prefs.edit().putInt(KEY_TOTAL_SENT, getTotalSent() + 1).apply();
    }

    public int getTotalFailed() {
        return prefs.getInt(KEY_TOTAL_FAILED, 0);
    }

    public synchronized void incrementTotalFailed() {
        prefs.edit().putInt(KEY_TOTAL_FAILED, getTotalFailed() + 1).apply();
    }

    public boolean isRegistered() {
        String token = getGatewayToken();
        return token != null && !token.trim().isEmpty();
    }
}
