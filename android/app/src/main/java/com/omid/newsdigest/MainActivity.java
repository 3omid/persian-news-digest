package com.omid.newsdigest;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * کل اپ: یک WebView تمام‌صفحه که سایت اپ رو باز می‌کنه. خبرها (لینک‌های سایت‌های دیگه) تو
 * مرورگر گوشی باز می‌شن، دکمه‌ی برگشت گوشی تو اپ برمی‌گرده، و رنگ نوار بالای گوشی همراه
 * تم اپ عوض می‌شه. Service worker سایت هم این‌جا کار می‌کنه، پس بدون اینترنت هم باز می‌شه.
 */
public class MainActivity extends Activity {
    private WebView web;
    private String appHost;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        appHost = Uri.parse(BuildConfig.START_URL).getHost();

        web = new WebView(this);
        web.setFitsSystemWindows(true);
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setUserAgentString(s.getUserAgentString() + " NewsDigestAndroid/" + BuildConfig.VERSION_NAME);

        web.addJavascriptInterface(new Bridge(), "NewsApp");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (appHost.equals(uri.getHost())) return false;
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                } catch (ActivityNotFoundException ignored) {
                }
                return true;
            }
        });

        if (savedInstanceState != null) web.restoreState(savedInstanceState);
        else web.loadUrl(BuildConfig.START_URL);
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        web.saveState(outState);
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }

    /** صفحه (theme.js) با window.NewsApp.setBarColors رنگ تم رو به اپ می‌گه. */
    private class Bridge {
        @JavascriptInterface
        public void setBarColors(final String status, final String nav) {
            runOnUiThread(() -> {
                try {
                    getWindow().setStatusBarColor(Color.parseColor(status));
                    getWindow().setNavigationBarColor(Color.parseColor(nav));
                } catch (IllegalArgumentException ignored) {
                }
            });
        }
    }
}
