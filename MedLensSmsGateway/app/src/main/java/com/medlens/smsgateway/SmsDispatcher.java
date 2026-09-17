package com.medlens.smsgateway;

import android.app.Activity;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Build;
import android.telephony.SmsManager;
import android.util.Log;

import java.util.ArrayList;

public class SmsDispatcher {
    private static final String TAG = "SmsDispatcher";
    public static final String ACTION_SMS_SENT = "com.medlens.smsgateway.SMS_SENT";
    public static final String ACTION_SMS_DELIVERED = "com.medlens.smsgateway.SMS_DELIVERED";
    public static final String EXTRA_MESSAGE_ID = "extra_message_id";

    public interface SmsResultCallback {
        void onSent(int messageId);
        void onFailed(int messageId, String reason);
    }

    private final Context context;
    private final SmsResultCallback callback;
    private BroadcastReceiver sentReceiver;

    public SmsDispatcher(Context context, SmsResultCallback callback) {
        this.context = context;
        this.callback = callback;
        registerSentReceiver();
    }

    private void registerSentReceiver() {
        sentReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                int messageId = intent.getIntExtra(EXTRA_MESSAGE_ID, -1);
                if (messageId == -1) return;

                int resultCode = getResultCode();
                if (resultCode == Activity.RESULT_OK) {
                    Log.i(TAG, "SMS successfully dispatched for message ID: " + messageId);
                    if (callback != null) callback.onSent(messageId);
                } else {
                    String reason;
                    switch (resultCode) {
                        case SmsManager.RESULT_ERROR_GENERIC_FAILURE:
                            reason = "Generic radio failure";
                            break;
                        case SmsManager.RESULT_ERROR_NO_SERVICE:
                            reason = "No SIM network service";
                            break;
                        case SmsManager.RESULT_ERROR_NULL_PDU:
                            reason = "Null PDU error";
                            break;
                        case SmsManager.RESULT_ERROR_RADIO_OFF:
                            reason = "Phone radio/Airplane mode is OFF";
                            break;
                        default:
                            reason = "Error code: " + resultCode;
                            break;
                    }
                    Log.e(TAG, "SMS dispatch failed for ID: " + messageId + " Reason: " + reason);
                    if (callback != null) callback.onFailed(messageId, reason);
                }
            }
        };

        int flags = (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) ?
                Context.RECEIVER_NOT_EXPORTED : 0;
        context.registerReceiver(sentReceiver, new IntentFilter(ACTION_SMS_SENT), flags);
    }

    public void destroy() {
        if (sentReceiver != null) {
            try {
                context.unregisterReceiver(sentReceiver);
            } catch (Exception ignored) {}
            sentReceiver = null;
        }
    }

    public void sendSms(int messageId, String recipientPhone, String messageText) {
        try {
            SmsManager smsManager;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                smsManager = context.getSystemService(SmsManager.class);
            } else {
                smsManager = SmsManager.getDefault();
            }

            if (smsManager == null) {
                if (callback != null) callback.onFailed(messageId, "SmsManager unavailable on device");
                return;
            }

            Intent sentIntent = new Intent(ACTION_SMS_SENT);
            sentIntent.putExtra(EXTRA_MESSAGE_ID, messageId);

            int pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                pendingFlags |= PendingIntent.FLAG_IMMUTABLE;
            }

            PendingIntent sentPi = PendingIntent.getBroadcast(
                    context,
                    messageId,
                    sentIntent,
                    pendingFlags
            );

            // Handle multi-part SMS for messages longer than standard GSM 160 characters
            ArrayList<String> parts = smsManager.divideMessage(messageText);
            if (parts.size() > 1) {
                ArrayList<PendingIntent> sentIntents = new ArrayList<>();
                for (int i = 0; i < parts.size(); i++) {
                    // Only attach notification PendingIntent to the last segment
                    sentIntents.add(i == parts.size() - 1 ? sentPi : null);
                }
                smsManager.sendMultipartTextMessage(recipientPhone, null, parts, sentIntents, null);
                Log.d(TAG, "Multipart SMS (" + parts.size() + " parts) sent to " + recipientPhone);
            } else {
                smsManager.sendTextMessage(recipientPhone, null, messageText, sentPi, null);
                Log.d(TAG, "Single SMS sent to " + recipientPhone);
            }

        } catch (SecurityException se) {
            Log.e(TAG, "SecurityException: SEND_SMS permission denied", se);
            if (callback != null) callback.onFailed(messageId, "SEND_SMS permission missing");
        } catch (Exception ex) {
            Log.e(TAG, "Exception while sending SMS", ex);
            if (callback != null) callback.onFailed(messageId, "Dispatch exception: " + ex.getMessage());
        }
    }
}
