package com.medlens.smsgateway;

import android.Manifest;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class MainActivity extends AppCompatActivity {
    private static final int PERMISSION_REQUEST_CODE = 2001;

    private TextView tvServiceStatus;
    private TextView tvDeviceMeta;
    private TextView tvSentCount;
    private TextView tvFailedCount;
    private TextView tvLiveLogs;
    private Button btnToggleService;
    private Button btnOpenSettings;

    private PrefsManager prefs;
    private BroadcastReceiver statusReceiver;
    private final List<String> logsList = new ArrayList<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        prefs = new PrefsManager(this);
        initViews();
        checkAndRequestPermissions();
        registerStatusReceiver();
        updateUiState();
    }

    private void initViews() {
        tvServiceStatus = findViewById(R.id.tv_service_status);
        tvDeviceMeta = findViewById(R.id.tv_device_meta);
        tvSentCount = findViewById(R.id.tv_sent_count);
        tvFailedCount = findViewById(R.id.tv_failed_count);
        tvLiveLogs = findViewById(R.id.tv_live_logs);
        btnToggleService = findViewById(R.id.btn_toggle_service);
        btnOpenSettings = findViewById(R.id.btn_open_settings);

        btnToggleService.setOnClickListener(v -> toggleService());
        btnOpenSettings.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, SettingsActivity.class);
            startActivity(intent);
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateUiState();
    }

    @Override
    protected void onDestroy() {
        if (statusReceiver != null) {
            try {
                unregisterReceiver(statusReceiver);
            } catch (Exception ignored) {}
        }
        super.onDestroy();
    }

    private void updateUiState() {
        boolean isRunning = prefs.isServiceEnabled();
        tvServiceStatus.setText(isRunning ? "● GATEWAY ACTIVE (POLLING)" : "○ GATEWAY IDLE (STOPPED)");
        tvServiceStatus.setTextColor(isRunning ? 0xFF16A34A : 0xFF64748B);
        btnToggleService.setText(isRunning ? "Stop Gateway Service" : "Start Gateway Service");

        tvDeviceMeta.setText("Device: " + prefs.getDeviceName() + "\nServer: " + prefs.getBaseUrl() +
                (prefs.isRegistered() ? " (Paired)" : " (NOT PAIRED)"));

        tvSentCount.setText(String.valueOf(prefs.getTotalSent()));
        tvFailedCount.setText(String.valueOf(prefs.getTotalFailed()));
    }

    private void toggleService() {
        if (!hasSmsPermission()) {
            Toast.makeText(this, "SMS Permission is required to dispatch alerts!", Toast.LENGTH_LONG).show();
            checkAndRequestPermissions();
            return;
        }

        if (!prefs.isRegistered()) {
            Toast.makeText(this, "Please configure and pair with the MedLens server in Settings first!", Toast.LENGTH_LONG).show();
            startActivity(new Intent(this, SettingsActivity.class));
            return;
        }

        boolean newState = !prefs.isServiceEnabled();
        prefs.setServiceEnabled(newState);

        Intent serviceIntent = new Intent(this, GatewayService.class);
        if (newState) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent);
            } else {
                startService(serviceIntent);
            }
            appendLog("Gateway service started.");
        } else {
            stopService(serviceIntent);
            appendLog("Gateway service stopped.");
        }

        updateUiState();
    }

    private void registerStatusReceiver() {
        statusReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                if (GatewayService.ACTION_STATUS_UPDATE.equals(intent.getAction())) {
                    String msg = intent.getStringExtra(GatewayService.EXTRA_LOG_MESSAGE);
                    if (msg != null) {
                        appendLog(msg);
                    }
                    updateUiState();
                }
            }
        };

        int flags = (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) ?
                Context.RECEIVER_NOT_EXPORTED : 0;
        registerReceiver(statusReceiver, new IntentFilter(GatewayService.ACTION_STATUS_UPDATE), flags);
    }

    private void appendLog(String message) {
        String timestamp = new SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(new Date());
        String logEntry = "[" + timestamp + "] " + message;
        logsList.add(0, logEntry);

        if (logsList.size() > 50) {
            logsList.remove(logsList.size() - 1);
        }

        StringBuilder sb = new StringBuilder();
        for (String l : logsList) {
            sb.append(l).append("\n");
        }
        tvLiveLogs.setText(sb.toString());
    }

    private boolean hasSmsPermission() {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.SEND_SMS) == PackageManager.PERMISSION_GRANTED;
    }

    private void checkAndRequestPermissions() {
        List<String> permissionsNeeded = new ArrayList<>();

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.SEND_SMS) != PackageManager.PERMISSION_GRANTED) {
            permissionsNeeded.add(Manifest.permission.SEND_SMS);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                permissionsNeeded.add(Manifest.permission.POST_NOTIFICATIONS);
            }
        }

        if (!permissionsNeeded.isEmpty()) {
            ActivityCompat.requestPermissions(this, permissionsNeeded.toArray(new String[0]), PERMISSION_REQUEST_CODE);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (hasSmsPermission()) {
                appendLog("SEND_SMS permission granted.");
                Toast.makeText(this, "SMS Permission granted!", Toast.LENGTH_SHORT).show();
            } else {
                appendLog("Warning: SEND_SMS permission was DENIED.");
                Toast.makeText(this, "SMS Permission is required to send patient alerts.", Toast.LENGTH_LONG).show();
            }
        }
    }
}
