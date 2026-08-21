/** @odoo-module **/

function initSignatureCanvas() {
    const canvas = document.getElementById("signature-canvas");
    if (!canvas) return;

    if (canvas.dataset.initialized === "true") return;
    canvas.dataset.initialized = "true";

    const ctx = canvas.getContext("2d");
    let isDrawing = false;
    let hasSignature = false;

    // Set canvas dimensions
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width || 500;
    canvas.height = 180;

    // Fill Solid White Background to prevent transparent black box in image viewers
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = "#000000";
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    function getPos(e) {
        const cRect = canvas.getBoundingClientRect();
        if (e.touches && e.touches.length > 0) {
            return {
                x: e.touches[0].clientX - cRect.left,
                y: e.touches[0].clientY - cRect.top,
            };
        }
        return {
            x: e.clientX - cRect.left,
            y: e.clientY - cRect.top,
        };
    }

    function startDrawing(e) {
        isDrawing = true;
        const pos = getPos(e);
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y);
    }

    function draw(e) {
        if (!isDrawing) return;
        if (e.cancelable) e.preventDefault();
        const pos = getPos(e);
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
        hasSignature = true;
    }

    function stopDrawing() {
        isDrawing = false;
    }

    // Mouse listeners
    canvas.addEventListener("mousedown", startDrawing);
    canvas.addEventListener("mousemove", draw);
    canvas.addEventListener("mouseup", stopDrawing);
    canvas.addEventListener("mouseleave", stopDrawing);

    // Touch listeners
    canvas.addEventListener("touchstart", startDrawing, { passive: false });
    canvas.addEventListener("touchmove", draw, { passive: false });
    canvas.addEventListener("touchend", stopDrawing);

    // Clear Button
    const clearBtn = document.getElementById("clear-signature-btn");
    if (clearBtn) {
        clearBtn.addEventListener("click", function () {
            ctx.fillStyle = "#ffffff";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            hasSignature = false;
            const signatureInput = document.getElementById("signature_data");
            if (signatureInput) signatureInput.value = "";
        });
    }

    // Form submission hook
    const form = document.getElementById("portal-doc-request-form");
    if (form) {
        form.addEventListener("submit", function () {
            if (hasSignature) {
                const signatureInput = document.getElementById("signature_data");
                if (signatureInput) {
                    signatureInput.value = canvas.toDataURL("image/png");
                }
            }
        });
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSignatureCanvas);
} else {
    initSignatureCanvas();
}

setInterval(initSignatureCanvas, 400);
