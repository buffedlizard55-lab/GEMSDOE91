(function () {
  "use strict";

  function b64ToBytes(b64) {
    const bin = atob(b64);
    const len = bin.length;
    const out = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      out[i] = bin.charCodeAt(i);
    }
    return out;
  }

  async function sha256Hex(bytes) {
    if (!window.crypto || !window.crypto.subtle) {
      return null;
    }
    const digest = await window.crypto.subtle.digest("SHA-256", bytes);
    const arr = Array.from(new Uint8Array(digest));
    return arr.map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  function triggerBlobDownload(bytes, filename) {
    const blob = new Blob([bytes], { type: "image/tiff" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 500);
  }

  function evaluateAutomatedGates(rc) {
    if (!rc || !rc.submission || !rc.submission.validators) {
      return { ok: false, failed: ["run_card_missing"] };
    }
    const s = rc.submission;
    const v = s.validators;
    const checks = [
      ["verdict_promote", rc.verdict === "promote" && rc.ok_to_download_and_submit === true],
      ["leakage_canary_pass", rc.leakage_canary && rc.leakage_canary.all_pass === true && rc.leakage_canary.worst_symmetric_auc <= 0.90],
      ["registry_uniqueness_pass", rc.registry_uniqueness && rc.registry_uniqueness.uniqueness_pass === true && rc.registry_uniqueness.max_3px_dot_overlap <= 0.70 && rc.registry_uniqueness.max_surface_abs_rank_corr <= 0.90],
      ["holdout_lift_positive", rc.scores && rc.scores.primary_holdout && rc.scores.primary_holdout.lift_over_b0 > 0],
      ["gems91_gates_certified", v.gems91_gates_verdict === "CERTIFIED"],
      ["release_gates_zeros_pass", v.release_gates_zeros_pass === true],
      ["release_gates_nan_pass", v.release_gates_nan_pass === true],
      ["validate_raster_zeros_pass", v.validate_raster_zeros_pass === true],
      ["validate_raster_nan_pass", v.validate_raster_nan_pass === true],
      ["range_0_1_portal_safe", v.range_0_1_portal_safe === true && s.min_value >= 0.0 && s.max_value <= 1.0],
      ["all_cells_finite", s.all_12279160_cells_finite === true && s.nodata_zeros_tif === null],
      ["collar_gt_3px", s.dots_le_3px === 0 && s.min_catalogue_distance_px > 3.0],
      ["note_le_140_chars", typeof s.recommended_form_note === "string" && s.recommended_form_note.length <= 140],
    ];
    const failed = checks.filter((c) => !c[1]).map((c) => c[0]);
    return { ok: failed.length === 0, total: checks.length, passed: checks.length - failed.length, failed };
  }

  async function initPage() {
    const rc = window.GEMS91_RUN_CARD;
    const bundle = window.GEMS91_SUBMISSION_BUNDLE;
    const gateStatus = evaluateAutomatedGates(rc);

    const hero = document.getElementById("verdict-hero");
    const pill = document.getElementById("verdict-pill");
    const shaBadge = document.getElementById("sha-live-badge");
    const runCardPre = document.getElementById("run-card-json");

    if (runCardPre && rc) {
      runCardPre.textContent = JSON.stringify(rc, null, 2);
    }

    let decodedPrimary = null;
    let decodedCompanion = null;
    let shaVerified = false;

    if (bundle && bundle.primary_zeros && bundle.primary_zeros.base64) {
      try {
        decodedPrimary = b64ToBytes(bundle.primary_zeros.base64);
        const liveSha = await sha256Hex(decodedPrimary);
        if (liveSha === null) {
          shaVerified = decodedPrimary.byteLength === bundle.primary_zeros.bytes;
          if (shaBadge) {
            shaBadge.textContent = "Byte-length verified (" + decodedPrimary.byteLength.toLocaleString() + " B)";
          }
        } else if (liveSha === bundle.primary_zeros.sha256) {
          shaVerified = true;
          if (shaBadge) {
            shaBadge.textContent = "WebCrypto SHA-256 Verified: " + liveSha.slice(0, 12) + "…";
            shaBadge.style.borderColor = "#10b981";
            shaBadge.style.color = "#065f46";
          }
        } else {
          shaVerified = false;
          if (shaBadge) {
            shaBadge.textContent = "SHA-256 MISMATCH — HOLD";
            shaBadge.style.borderColor = "#ef4444";
            shaBadge.style.color = "#991b1b";
          }
        }
      } catch (err) {
        if (shaBadge) {
          shaBadge.textContent = "Payload decode error: " + err.message;
        }
      }
    }

    const allGreen = gateStatus.ok && shaVerified;
    if (hero && pill) {
      if (allGreen) {
        hero.classList.remove("is-hold");
        pill.textContent = "AUTOMATED GATES: " + gateStatus.passed + "/" + gateStatus.total + " PASSED — OK TO DOWNLOAD & SUBMIT";
      } else {
        hero.classList.add("is-hold");
        const reason = !gateStatus.ok ? gateStatus.failed.join(", ") : "WebCrypto SHA check pending/failed";
        pill.textContent = "AUTOMATED GATE HOLD — DO NOT SUBMIT (" + reason + ")";
      }
    }

    const btnTif = document.getElementById("btn-download-zeros-tif");
    if (btnTif) {
      btnTif.addEventListener("click", async function (ev) {
        ev.preventDefault();
        if (!bundle || !bundle.primary_zeros) {
          alert("Submission bundle not loaded.");
          return;
        }
        if (!decodedPrimary) {
          decodedPrimary = b64ToBytes(bundle.primary_zeros.base64);
        }
        const checkSha = await sha256Hex(decodedPrimary);
        if (checkSha !== null && checkSha !== bundle.primary_zeros.sha256) {
          alert("Blocked: SHA-256 mismatch against certified manifest!");
          return;
        }
        triggerBlobDownload(decodedPrimary, bundle.primary_zeros.filename);
      });
    }

    const btnNan = document.getElementById("btn-download-nan-tif");
    if (btnNan) {
      btnNan.addEventListener("click", async function (ev) {
        ev.preventDefault();
        if (!bundle || !bundle.companion_nan) {
          alert("Companion NaN bundle not loaded.");
          return;
        }
        if (!decodedCompanion) {
          decodedCompanion = b64ToBytes(bundle.companion_nan.base64);
        }
        const checkSha = await sha256Hex(decodedCompanion);
        if (checkSha !== null && checkSha !== bundle.companion_nan.sha256) {
          alert("Blocked: SHA-256 mismatch on companion NaN GeoTIFF!");
          return;
        }
        triggerBlobDownload(decodedCompanion, bundle.companion_nan.filename);
      });
    }

    document.querySelectorAll("[data-copy-target]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const targetId = btn.getAttribute("data-copy-target");
        const el = document.getElementById(targetId);
        if (!el) return;
        const txt = el.textContent.trim();
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(txt).then(function () {
            const orig = btn.textContent;
            btn.textContent = "Copied!";
            setTimeout(function () {
              btn.textContent = orig;
            }, 1400);
          });
        }
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPage);
  } else {
    initPage();
  }
})();
