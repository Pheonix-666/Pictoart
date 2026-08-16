// Client-side image validation and live preview
document.addEventListener("DOMContentLoaded", function () {
  const photoInput = document.getElementById("photo-input");
  const photoPreview = document.getElementById("photo-preview");
  const uploadBox = document.getElementById("photo-upload-box");
  const uploadForm = document.getElementById("doctor-upload-form");
  const clientError = document.getElementById("client-error");

  if (uploadBox && photoInput) {
    uploadBox.addEventListener("click", function () {
      photoInput.click();
    });

    photoInput.addEventListener("change", function (e) {
      const file = e.target.files[0];
      if (!file) return;

      // File type check
      const validTypes = ["image/jpeg", "image/png", "image/jpg", "image/webp"];
      if (!validTypes.includes(file.type.toLowerCase())) {
        showError("Invalid file type. Please upload a JPEG or PNG image.");
        photoInput.value = "";
        return;
      }

      // File size check (max 10MB)
      const maxSize = 10 * 1024 * 1024;
      if (file.size > maxSize) {
        showError("Photo file size exceeds maximum limit of 10MB.");
        photoInput.value = "";
        return;
      }

      // Resolution check using Image object
      const img = new Image();
      img.onload = function () {
        if (this.width < 600 || this.height < 600) {
          showError(`Photo resolution (${this.width}x${this.height}px) is below minimum required 600x600px.`);
          photoInput.value = "";
          photoPreview.style.display = "none";
          return;
        }

        // Image is valid -> show preview
        hideError();
        photoPreview.src = img.src;
        photoPreview.style.display = "block";
      };

      img.onerror = function () {
        showError("Unable to read image file.");
      };

      img.src = URL.createObjectURL(file);
    });
  }

  function showError(msg) {
    if (clientError) {
      clientError.textContent = msg;
      clientError.style.display = "block";
    } else {
      alert(msg);
    }
  }

  function hideError() {
    if (clientError) {
      clientError.style.display = "none";
      clientError.textContent = "";
    }
  }
});
