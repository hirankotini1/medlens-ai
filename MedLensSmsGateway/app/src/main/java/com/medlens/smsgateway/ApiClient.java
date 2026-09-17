package com.medlens.smsgateway;

import android.os.Handler;
import android.os.Looper;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

public class ApiClient {
    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");
    private final OkHttpClient client;
    private final Gson gson;
    private final Handler mainHandler;

    public interface ApiCallback<T> {
        void onSuccess(T result);
        void onError(String error);
    }

    public ApiClient() {
        this.client = new OkHttpClient.Builder()
                .connectTimeout(15, TimeUnit.SECONDS)
                .readTimeout(20, TimeUnit.SECONDS)
                .writeTimeout(15, TimeUnit.SECONDS)
                .build();
        this.gson = new Gson();
        this.mainHandler = new Handler(Looper.getMainLooper());
    }

    public void registerDevice(String baseUrl, String deviceId, String deviceName, String adminToken, ApiCallback<String> callback) {
        JsonObject body = new JsonObject();
        body.addProperty("device_id", deviceId);
        body.addProperty("device_name", deviceName);
        body.addProperty("admin_token", adminToken);

        Request request = new Request.Builder()
                .url(baseUrl + "/api/sms-gateway/register")
                .post(RequestBody.create(body.toString(), JSON))
                .build();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                postError(callback, "Connection failed: " + e.getMessage());
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                String respStr = response.body() != null ? response.body().string() : "";
                if (!response.isSuccessful()) {
                    postError(callback, "Registration failed (" + response.code() + "): " + respStr);
                    return;
                }
                try {
                    JsonObject json = JsonParser.parseString(respStr).getAsJsonObject();
                    if (json.has("gateway_token")) {
                        String token = json.get("gateway_token").getAsString();
                        postSuccess(callback, token);
                    } else {
                        postError(callback, "No token returned: " + respStr);
                    }
                } catch (Exception ex) {
                    postError(callback, "Parse error: " + ex.getMessage());
                }
            }
        });
    }

    public void checkStatus(String baseUrl, String gatewayToken, ApiCallback<JsonObject> callback) {
        Request request = new Request.Builder()
                .url(baseUrl + "/api/sms-gateway/status")
                .header("X-Gateway-Token", gatewayToken)
                .get()
                .build();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                postError(callback, e.getMessage());
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                String respStr = response.body() != null ? response.body().string() : "";
                if (!response.isSuccessful()) {
                    postError(callback, "Server returned " + response.code() + ": " + respStr);
                    return;
                }
                try {
                    JsonObject json = JsonParser.parseString(respStr).getAsJsonObject();
                    postSuccess(callback, json);
                } catch (Exception ex) {
                    postError(callback, "Parse error: " + ex.getMessage());
                }
            }
        });
    }

    public void fetchQueue(String baseUrl, String gatewayToken, ApiCallback<JsonObject> callback) {
        Request request = new Request.Builder()
                .url(baseUrl + "/api/sms-gateway/queue")
                .header("X-Gateway-Token", gatewayToken)
                .get()
                .build();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                postError(callback, e.getMessage());
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                String respStr = response.body() != null ? response.body().string() : "";
                if (!response.isSuccessful()) {
                    postError(callback, "Queue fetch error " + response.code() + ": " + respStr);
                    return;
                }
                try {
                    JsonObject json = JsonParser.parseString(respStr).getAsJsonObject();
                    postSuccess(callback, json);
                } catch (Exception ex) {
                    postError(callback, "JSON error: " + ex.getMessage());
                }
            }
        });
    }

    public void claimMessage(String baseUrl, String gatewayToken, int messageId, ApiCallback<JsonObject> callback) {
        Request request = new Request.Builder()
                .url(baseUrl + "/api/sms-gateway/" + messageId + "/claim")
                .header("X-Gateway-Token", gatewayToken)
                .post(RequestBody.create("{}", JSON))
                .build();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                postError(callback, e.getMessage());
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                String respStr = response.body() != null ? response.body().string() : "";
                if (!response.isSuccessful()) {
                    postError(callback, "Claim error (" + response.code() + "): " + respStr);
                    return;
                }
                try {
                    JsonObject json = JsonParser.parseString(respStr).getAsJsonObject();
                    postSuccess(callback, json);
                } catch (Exception ex) {
                    postError(callback, "JSON error: " + ex.getMessage());
                }
            }
        });
    }

    public void reportStatus(String baseUrl, String gatewayToken, int messageId, String status, String reason, ApiCallback<JsonObject> callback) {
        JsonObject body = new JsonObject();
        body.addProperty("status", status);
        if (reason != null) body.addProperty("failure_reason", reason);

        Request request = new Request.Builder()
                .url(baseUrl + "/api/sms-gateway/" + messageId + "/status")
                .header("X-Gateway-Token", gatewayToken)
                .post(RequestBody.create(body.toString(), JSON))
                .build();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                postError(callback, e.getMessage());
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                String respStr = response.body() != null ? response.body().string() : "";
                if (!response.isSuccessful()) {
                    postError(callback, "Report error (" + response.code() + "): " + respStr);
                    return;
                }
                try {
                    JsonObject json = JsonParser.parseString(respStr).getAsJsonObject();
                    postSuccess(callback, json);
                } catch (Exception ex) {
                    postError(callback, "JSON error: " + ex.getMessage());
                }
            }
        });
    }

    private <T> void postSuccess(ApiCallback<T> callback, T result) {
        if (callback != null) {
            mainHandler.post(() -> callback.onSuccess(result));
        }
    }

    private <T> void postError(ApiCallback<T> callback, String error) {
        if (callback != null) {
            mainHandler.post(() -> callback.onError(error));
        }
    }
}
