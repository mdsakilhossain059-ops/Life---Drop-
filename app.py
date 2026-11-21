# ==============================
# GLOBAL PWA INSTALL BUTTON
# ALL PAGES
# ==============================

@app.after_request
def add_pwa_install_to_all_pages(response):

    if (
        response.status_code == 200
        and response.mimetype == "text/html"
    ):
        html = response.get_data(as_text=True)

        pwa_code = """
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#dc2626">

<style>
#life-drop-install {
    position: fixed;
    bottom: 20px;
    right: 16px;
    z-index: 999999;
    background: #dc2626;
    color: white;
    border: none;
    border-radius: 30px;
    padding: 13px 20px;
    font-size: 15px;
    font-weight: bold;
    box-shadow: 0 4px 12px rgba(0,0,0,.25);
    cursor: pointer;
}
</style>

<button id="life-drop-install">
    📲 অ্যাপ ইনস্টল করুন
</button>

<script>
(function () {
    let installPrompt = null;
    const btn = document.getElementById('life-drop-install');

    if (window.matchMedia('(display-mode: standalone)').matches ||
        window.navigator.standalone === true) {
        btn.style.display = 'none';
        return;
    }

    window.addEventListener('beforeinstallprompt', function(e) {
        e.preventDefault();
        installPrompt = e;
        btn.style.display = 'block';
    });

    btn.addEventListener('click', async function() {
        if (installPrompt) {
            installPrompt.prompt();
            await installPrompt.userChoice;
            installPrompt = null;
        } else {
            alert(
                'Chrome ব্রাউজারের উপরের তিন ডট মেনুতে যান। ' +
                'Install app অথবা Add to Home screen নির্বাচন করুন।'
            );
        }
    });

    window.addEventListener('appinstalled', function() {
        btn.style.display = 'none';
        installPrompt = null;
    });

    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function() {
            navigator.serviceWorker.register('/sw.js')
                .catch(function(error) {
                    console.error('Service Worker Error:', error);
                });
        });
    }
})();
</script>
"""

        if "</body>" in html:
            html = html.replace(
                "</body>",
                pwa_code + "</body>"
            )
            response.set_data(html)

    return response
    
