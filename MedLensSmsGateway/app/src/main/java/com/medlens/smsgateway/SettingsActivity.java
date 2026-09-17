package com.medlens.smsgateway;

import android.app.ProgressDialog;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.google.gson.JsonObject;

public class SettingsActivity extends AppCompatActivity {
    private EditText etBaseUrl;
    private EditText etAdminToken;
    private EditText etDeviceName;
    private EditText etPollInterval;
    private TextView tvDeviceId;
    private TextView tvStatus;
    private Button btnTest;
    private Button btnSave;

    private PrefsManager prefs;
    private ApiClient apiClient;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);

        prefs = new PrefsManager(this);
        apiClient = new ApiClient();

        initViews();
        loadCurrentSettings();
    }

    private void initViews() {
        etBaseUrl = findViewById(R.id.et_base_url);
        etAdminToken = findViewById(R.id.et_admin_token);
        etDeviceName = findViewById(R.id.et_device_name);
        etPollInterval = findViewById(R.id.et_poll_interval);
        tvDeviceId = findViewById(R.id.tv_device_id);
        tvStatus = findViewById(R.id.tv_pairing_status);
        btnTest = findViewById(R.id.btn_test_connection);
        btnSave = findViewById(R.id.btn_save_settings);

        btnTest.setOnClickListener(v -> testConnectionAndPair());
        btnSave.setOnClickListener(v -> saveSettings());
    }

    private void loadCurrentSettings() {
        etBaseUrl.setText(prefs.getBaseUrl());
        etAdminToken.setText(prefs.getAdminToken());
        etDeviceName.setText(prefs.getDeviceName());
        etPollInterval.setText(String.valueOf(prefs.getPollIntervalSeconds()));
        tvDeviceId.setText("Device ID: " + prefs.getDeviceId());

        if (prefs.isRegistered()) {
            tvStatus.setText("Status: Paired with MedLens AI Backend");
            tvStatus.setTextColor(0xFF16A34A);
        } else {
            tvStatus.setText("Status: Not paired yet. Click 'Test & Pair Device'.");
            tvStatus.setTextColor(0xFFDC2626);
        }
    }

    private void saveSettings() {
        String url = etBaseUrl.getText().toString().trim();
        String adminToken = etAdminToken.getText().toString().trim();
        String name = etDeviceName.getText().toString().trim();
        int interval = 30;

        try {
            interval = Integer.parseInt(etPollInterval.getText().toString().trim());
        } catch (NumberFormatException ignored) {}

        if (url.isEmpty()) {
            etBaseUrl.setError("Server URL is required");
            return;
        }

        prefs.setBaseUrl(url);
        prefs.setAdminToken(adminToken);
        prefs.setDeviceName(name);
        prefs.setPollIntervalSeconds(interval);

        Toast.makeText(this, "Settings saved successfully", Toast.LENGTH_SHORT).show();
        finish();
    }

    private void testConnectionAndPair() {
        String url = etBaseUrl.getText().toString().trim();
        String adminToken = etAdminToken.getText().toString().trim();
        String deviceId = prefs.getDeviceId();
        String deviceName = etDeviceName.getText().toString().trim();

        if (url.isEmpty()) {
            etBaseUrl.setError("Server URL required");
            return;
        }

        ProgressDialog progress = new ProgressDialog(this);
        progress.setMessage("Registering with MedLens AI server...");
        progress.show();

        apiClient.registerDevice(url, deviceId, deviceName, adminToken, new ApiClient.ApiCallback<String>() {
            @Override
            public void onSuccess(String gatewayToken) {
                progress.dismiss();
                prefs.setBaseUrl(url);
                prefs.setAdminToken(adminToken);
                prefs.setDeviceName(deviceName);
                prefs.setGatewayToken(gatewayToken);

                tvStatus.setText("Status: Successfully Paired! (Token Received)");
                tvStatus.setTextColor(0xFF16A34A);
                Toast.makeText(SettingsActivity.this, "Device Paired with MedLens AI Server!", Toast.LENGTH_LONG).show();
            }

            @Override
            public void onError(String error) {
                progress.dismiss();
                tvStatus.setText("Error: " + error);
                tvStatus.setTextColor(0xFFDC2626);
                Toast.makeText(SettingsActivity.this, "Pairing error: " + error, Toast.LENGTH_LONG).show();
            }
        });
    }
}
