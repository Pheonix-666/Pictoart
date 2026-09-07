// ── PICTOART Upload Form — Client-side Logic ─────────────────────────────────

(function () {
  "use strict";

  // ── Helpers ─────────────────────────────────────────────────────────────────

  function showError(msg) {
    var clientError = document.getElementById("client-error");
    if (clientError) {
      clientError.textContent = msg;
      clientError.style.display = "block";
    } else {
      alert(msg);
    }
  }

  function hideError() {
    var clientError = document.getElementById("client-error");
    if (clientError) {
      clientError.style.display = "none";
      clientError.textContent = "";
    }
  }

  // ── Photo upload box ────────────────────────────────────────────────────────

  function initPhotoUpload() {
    var photoInput = document.getElementById("photo-input");
    var photoPreview = document.getElementById("photo-preview");
    var uploadBox = document.getElementById("photo-upload-box");

    if (!uploadBox || !photoInput) return;

    uploadBox.addEventListener("click", function (e) {
      // Prevent triggering if clicking directly on the input
      if (e.target !== photoInput) photoInput.click();
    });

    photoInput.addEventListener("change", function (e) {
      var file = e.target.files[0];
      if (!file) return;

      // File type check
      var validTypes = ["image/jpeg", "image/png", "image/jpg", "image/webp"];
      if (validTypes.indexOf(file.type.toLowerCase()) === -1) {
        showError("Invalid file type. Please upload a JPEG, PNG, or WebP image.");
        photoInput.value = "";
        return;
      }

      // File size check (max 10 MB)
      var maxSize = 10 * 1024 * 1024;
      if (file.size > maxSize) {
        showError("Photo file size exceeds the 10 MB limit.");
        photoInput.value = "";
        return;
      }

      // Resolution check via Image object
      var img = new Image();
      img.onload = function () {
        URL.revokeObjectURL(img.src);
        if (img.width < 300 || img.height < 300) {
          showError(
            "Photo resolution (" + img.width + "×" + img.height +
            " px) is too small. Please upload at least 300×300 px."
          );
          photoInput.value = "";
          if (photoPreview) photoPreview.style.display = "none";
          return;
        }
        hideError();
        if (photoPreview) {
          photoPreview.src = URL.createObjectURL(file);
          photoPreview.style.display = "block";
        }
      };
      img.onerror = function () {
        showError("Unable to read the image file. Please try a different photo.");
      };
      img.src = URL.createObjectURL(file);
    });
  }

  // ── State / District dropdowns ───────────────────────────────────────────────

  function populateDistricts(stateSelect, districtSelect, selectedState, selectedDistrict) {
    // Reset district dropdown
    districtSelect.innerHTML = '<option value="">-- Select District --</option>';

    if (!selectedState || !window.INDIA_LOCATIONS || !window.INDIA_LOCATIONS[selectedState]) {
      districtSelect.disabled = true;
      return;
    }

    var districts = window.INDIA_LOCATIONS[selectedState].slice().sort();
    districts.forEach(function (district) {
      var opt = document.createElement("option");
      opt.value = district;
      opt.textContent = district;
      if (district === selectedDistrict) opt.selected = true;
      districtSelect.appendChild(opt);
    });
    districtSelect.disabled = false;
  }

  function initLocationDropdowns() {
    var stateSelect    = document.getElementById("state");
    var districtSelect = document.getElementById("district");

    if (!stateSelect || !districtSelect) return;

    // If INDIA_LOCATIONS not loaded yet, log and bail
    if (typeof window.INDIA_LOCATIONS === "undefined") {
      console.error("INDIA_LOCATIONS is not defined — locations_india.js may not have loaded.");
      return;
    }

    var preSelectedState    = stateSelect.getAttribute("data-selected")    || "";
    var preSelectedDistrict = districtSelect.getAttribute("data-selected") || "";

    // Populate states (sorted)
    var states = Object.keys(window.INDIA_LOCATIONS).sort();
    states.forEach(function (state) {
      var opt = document.createElement("option");
      opt.value = state;
      opt.textContent = state;
      if (state === preSelectedState) opt.selected = true;
      stateSelect.appendChild(opt);
    });

    // Pre-fill districts if a state was previously selected
    if (preSelectedState) {
      populateDistricts(stateSelect, districtSelect, preSelectedState, preSelectedDistrict);
    } else {
      districtSelect.disabled = true;
    }

    // Update districts on state change
    stateSelect.addEventListener("change", function () {
      populateDistricts(stateSelect, districtSelect, this.value, "");
    });
  }

  // ── Bootstrap on DOM ready ───────────────────────────────────────────────────

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initPhotoUpload();
      initLocationDropdowns();
    });
  } else {
    // DOM is already ready (script loaded with defer / at bottom of body)
    initPhotoUpload();
    initLocationDropdowns();
  }
})();
