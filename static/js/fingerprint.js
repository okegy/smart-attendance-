/**
 * Device Fingerprinting Module
 * Generates a composite fingerprint from browser/device characteristics.
 * Used as a secondary proxy detection layer alongside IP checking.
 */

(function () {
    'use strict';

    /**
     * Simple hash function (djb2 variant).
     * Produces a hex string from any input string.
     */
    function hashString(str) {
        let hash = 5381;
        for (let i = 0; i < str.length; i++) {
            hash = ((hash << 5) + hash + str.charCodeAt(i)) & 0xffffffff;
        }
        // Convert to positive hex
        return (hash >>> 0).toString(16).padStart(8, '0');
    }

    /**
     * Get canvas fingerprint.
     * Renders specific text and shapes, then extracts the data URL.
     * Different GPUs/browsers render slightly differently.
     */
    function getCanvasFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            canvas.width = 200;
            canvas.height = 50;
            const ctx = canvas.getContext('2d');

            // Draw text with specific styling
            ctx.textBaseline = 'top';
            ctx.font = "14px 'Arial'";
            ctx.fillStyle = '#f60';
            ctx.fillRect(50, 0, 80, 30);
            ctx.fillStyle = '#069';
            ctx.fillText('QR-Attend-FP', 2, 15);
            ctx.fillStyle = 'rgba(102,204,0,0.7)';
            ctx.fillText('QR-Attend-FP', 4, 17);

            // Draw a circle
            ctx.beginPath();
            ctx.arc(100, 25, 10, 0, Math.PI * 2);
            ctx.fillStyle = '#a33';
            ctx.fill();

            return canvas.toDataURL();
        } catch (e) {
            return 'canvas-not-supported';
        }
    }

    /**
     * Collect all fingerprint components and hash them together.
     */
    function generateFingerprint() {
        const components = [];

        // Screen properties
        components.push('sr:' + screen.width + 'x' + screen.height);
        components.push('cd:' + screen.colorDepth);
        components.push('pd:' + (window.devicePixelRatio || 1));

        // Timezone
        components.push('tz:' + Intl.DateTimeFormat().resolvedOptions().timeZone);
        components.push('tzo:' + new Date().getTimezoneOffset());

        // Platform & language
        components.push('pl:' + (navigator.platform || ''));
        components.push('lang:' + (navigator.language || ''));

        // Hardware concurrency (CPU cores)
        components.push('hc:' + (navigator.hardwareConcurrency || 0));

        // Touch support
        components.push('ts:' + ('ontouchstart' in window ? 1 : 0));
        components.push('mt:' + (navigator.maxTouchPoints || 0));

        // Canvas fingerprint
        const canvasFP = getCanvasFingerprint();
        components.push('cv:' + hashString(canvasFP));

        // WebGL renderer (if available)
        try {
            const gl = document.createElement('canvas').getContext('webgl');
            if (gl) {
                const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                if (debugInfo) {
                    components.push('glr:' + gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL));
                }
            }
        } catch (e) {
            components.push('glr:none');
        }

        // Combine all components and hash
        const raw = components.join('|');
        const hash1 = hashString(raw);
        const hash2 = hashString(raw.split('').reverse().join(''));
        return hash1 + hash2;  // 16-char hex fingerprint
    }

    /**
     * Set the fingerprint value in any form field with name="device_fingerprint"
     * or id="device_fingerprint".
     */
    function setFingerprintFields() {
        const fp = generateFingerprint();
        // Set all hidden inputs with the appropriate name
        document.querySelectorAll('input[name="device_fingerprint"]').forEach(function (el) {
            el.value = fp;
        });
        // Also store in sessionStorage for JS access
        try {
            sessionStorage.setItem('device_fingerprint', fp);
        } catch (e) {
            // Ignore if sessionStorage is not available
        }
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setFingerprintFields);
    } else {
        setFingerprintFields();
    }

    // Expose globally
    window.DeviceFingerprint = {
        generate: generateFingerprint,
        refresh: setFingerprintFields
    };

})();
