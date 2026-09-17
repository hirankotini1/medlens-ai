package com.medlens.smsgateway;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;

import androidx.core.app.NotificationCompat;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class GatewayService extends Service implements SmsDispatcher.SmsResultCallback {
    private static final String TAG = "GatewayService";
    private static final String CHANNEL_ID = "medlens_sms_gateway_channel";
    private static final int NOTIFICATION_ID = 1001;

    public static final String ACTION_STATUS_UPDATE = "com.medlens.smsgateway.STATUS_UPDATE";
    public static final String EXTRA_LOG_MESSAGE = "extra_log_message";
    public static final String EXTRA_LAST_PING = "extra_last_ping";

    private PrefsManager prefs;
    private ApiClient apiClient;
    private SmsDispatcher smsDispatcher;
    private Handler pollHandler;
    private Runnable pollRunnable;
    private boolean isPolling = false;

    @Override
    public void onCreate() {
        super.onCreate();
        prefs = new PrefsManager(this);
        apiClient = new ApiClient();
        smsDispatcher = new SmsDispatcher(this, this);
        pollHandler = new Handler(Looper.getMainLooper());

        createNotificationChannel();
        startForeground(NOTIFICATION_ID, buildNotification("Service initialized. Standby for queue dispatch..."));
        Log.i(TAG, "MedLens SMS Gateway service created.");
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startPollingLoop();
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        stopPollingLoop();
        if (smsDispatcher != null) {
            smsDispatcher.destroy();
            smsDispatcher = null;
        }
        Log.i(TAG, "MedLens SMS Gateway service destroyed.");
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "MedLens SMS Gateway Service",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Background monitoring and SIM alert dispatching");
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }

    private Notification buildNotification(String statusText) {
        Intent notificationIntent = new Intent(this, MainActivity.class);
        int pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            pendingFlags |= PendingIntent.FLAG_IMMUTABLE;
        }
        PendingIntent pendingIntent = PendingIntent.getActivity(this, 0, notificationIntent, pendingFlags);

        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("MedLens AI — SIM Alert Gateway Active")
                .setContentText(statusText)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .build();
    }

    private void updateNotification(String statusText) {
        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager != null) {
            manager.notify(NOTIFICATION_ID, buildNotification(statusText));
        }
    }

    private void startPollingLoop() {
        if (isPolling) return;
        isPolling = true;

        pollRunnable = new Runnable() {
            @Override
            public void run() {
                if (!isPolling) return;
                pollQueueOnce();
                int intervalMs = prefs.getPollIntervalSeconds() * 1000;
                pollHandler.postDelayed(this, intervalMs);
            }
        };

        pollHandler.post(pollRunnable);
        broadcastStatus("Gateway started polling every " + prefs.getPollIntervalSeconds() + "s");
    }

    private void stopPollingLoop() {
        isPolling = false;
        if (pollHandler != null && pollRunnable != null) {
            pollHandler.removeCallbacks(pollRunnable);
        }
    }

    private void pollQueueOnce() {
        if (!prefs.isRegistered()) {
            broadcastStatus("Device not paired yet. Please open Settings and pair with server.");
            updateNotification("Device not paired. Standby...");
            return;
        }

        String baseUrl = prefs.getBaseUrl();
        String token = prefs.getGatewayToken();

        apiClient.fetchQueue(baseUrl, token, new ApiClient.ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject result) {
                String timeNow = new SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(new Date());
                int count = result.has("count") ? result.get("count").getAsInt() : 0;

                if (count == 0) {
                    updateNotification("Idle. Polled at " + timeNow + " (Queue empty)");
                    broadcastStatus("Polled at " + timeNow + ": 0 pending messages");
                    return;
                }

                broadcastStatus("Found " + count + " pending messages. Processing...");
                JsonArray messages = result.getAsJsonArray("messages");
                for (JsonElement el : messages) {
                    JsonObject msgObj = el.getAsJsonObject();
                    int msgId = msgObj.get("id").getAsInt();
                    processQueueMessage(msgId);
                }
            }

            @Override
            public void onError(String error) {
                Log.w(TAG, "Poll error: " + error);
                broadcastStatus("Poll warning: " + error);
                updateNotification("Connection error: " + error);
            }
        });
    }

    private void processQueueMessage(int messageId) {
        String baseUrl = prefs.getBaseUrl();
        String token = prefs.getGatewayToken();

        // 1. Atomically claim message from backend
        apiClient.claimMessage(baseUrl, token, messageId, new ApiClient.ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject claimResult) {
                String phone = claimResult.get("phone_number").getAsString();
                String text = claimResult.get("message").getAsString();

                broadcastStatus("Claimed SMS #" + messageId + " for " + phone + ". Dispatching via SIM...");
                updateNotification("Dispatching SMS #" + messageId + " via SIM...");

                // 2. Dispatch via mobile SIM hardware
                if (smsDispatcher != null) {
                    smsDispatcher.sendSms(messageId, phone, text);
                }
            }

            @Override
            public void onError(String error) {
                Log.w(TAG, "Could not claim message #" + messageId + ": " + error);
            }
        });
    }

    // SmsDispatcher Callbacks
    @Override
    public void onSent(int messageId) {
        Log.i(TAG, "SMS successfully broadcasted via SIM for message #" + messageId);
        prefs.incrementTotalSent();

        // Report SENT to backend
        apiClient.reportStatus(prefs.getBaseUrl(), prefs.getGatewayToken(), messageId, "sent", null, new ApiClient.ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject result) {
                broadcastStatus("Delivered SMS #" + messageId + " via SIM. Confirmed by server.");
                updateNotification("Sent SMS #" + messageId + ". Total sent: " + prefs.getTotalSent());
            }

            @Override
            public void onError(String error) {
                broadcastStatus("SMS #" + messageId + " sent via SIM, but status report had error: " + error);
            }
        });
    }

    @Override
    public void onFailed(int messageId, String reason) {
        Log.e(TAG, "SMS failed via SIM for message #" + messageId + " (" + reason + ")");
        prefs.incrementTotalFailed();

        // Report FAILED to backend
        apiClient.reportStatus(prefs.getBaseUrl(), prefs.getGatewayToken(), messageId, "failed", reason, new ApiClient.ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject result) {
                broadcastStatus("Marked SMS #" + messageId + " as failed (" + reason + ")");
            }

            @Override
            public void onError(String error) {
                Log.e(TAG, "Failed to report SMS failure to backend: " + error);
            }
        });
    }

    private void broadcastStatus(String message) {
        Intent intent = new Intent(ACTION_STATUS_UPDATE);
        intent.putExtra(EXTRA_LOG_MESSAGE, message);
        intent.putExtra(EXTRA_LAST_PING, System.currentTimeMillis());
        sendBroadcast(intent);
    }
}
