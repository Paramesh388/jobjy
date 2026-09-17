/**
 * JobMatch AI - Client-side Interactive Functionality
 * Handles:
 * 1. File Upload Dropzone
 * 2. Interactive Skills Tag Editor (Add/Remove)
 * 3. Dynamic Job Filters & Sorting
 * 4. Async Save/Unsave Jobs
 * 5. Multi-Job Comparison Selector
 */

document.addEventListener("DOMContentLoaded", () => {
  initDropzone();
  initSkillsEditor();
  initSaveJobButtons();
  initJobComparisonSelector();
});

// ==========================================
// 1. Dropzone & File Upload
// ==========================================
function initDropzone() {
  const dropzone = document.getElementById("uploadDropzone");
  const fileInput = document.getElementById("resumeFileInput");
  const fileNameDisplay = document.getElementById("selectedFileName");
  const submitBtn = document.getElementById("submitUploadBtn");

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener("click", () => fileInput.click());

  ["dragenter", "dragover"].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    }, false);
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    }, false);
  });

  dropzone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length) {
      fileInput.files = files;
      handleFileSelected(files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length) {
      handleFileSelected(e.target.files[0]);
    }
  });

  function handleFileSelected(file) {
    const validExtensions = ["pdf", "docx", "txt"];
    const ext = file.name.split(".").pop().toLowerCase();

    if (!validExtensions.includes(ext)) {
      alert("Please select a valid resume format: PDF, DOCX, or TXT.");
      fileInput.value = "";
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      alert("File exceeds maximum allowed size of 5 MB.");
      fileInput.value = "";
      return;
    }

    if (fileNameDisplay) {
      fileNameDisplay.innerHTML = `
        <div class="alert alert-info py-2 px-3 d-inline-flex align-items-center gap-2 mt-3">
          <i class="bi bi-file-earmark-check"></i>
          <strong>Selected:</strong> ${file.name} (${(file.size / 1024).toFixed(1)} KB)
        </div>
      `;
    }

    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.classList.remove("d-none");
    }
  }
}

// ==========================================
// 2. Interactive Skills Editor
// ==========================================
function initSkillsEditor() {
  const container = document.getElementById("skillsTagsContainer");
  const addBtn = document.getElementById("addSkillBtn");
  const input = document.getElementById("newSkillInput");
  const saveStatus = document.getElementById("skillsSaveStatus");

  if (!container) return;

  // Delegate click for removing skill tags
  container.addEventListener("click", (e) => {
    const removeBtn = e.target.closest(".remove-skill-icon");
    if (removeBtn) {
      const tag = removeBtn.closest(".skill-tag");
      if (tag) {
        tag.remove();
        syncSkillsToServer();
      }
    }
  });

  function addSkill() {
    if (!input) return;
    const val = input.value.trim();
    if (!val) return;

    // Check if skill already exists
    const existing = Array.from(container.querySelectorAll(".skill-name"))
      .map(el => el.textContent.trim().toLowerCase());

    if (existing.includes(val.toLowerCase())) {
      alert(`"${val}" is already in your skills list.`);
      input.value = "";
      return;
    }

    const tag = document.createElement("span");
    tag.className = "skill-tag skill-tag-matched skill-tag-removable";
    tag.innerHTML = `
      <span class="skill-name">${val}</span>
      <i class="bi bi-x-circle ms-1 remove-skill-icon" title="Remove skill"></i>
    `;
    container.appendChild(tag);
    input.value = "";
    syncSkillsToServer();
  }

  if (addBtn) addBtn.addEventListener("click", addSkill);
  if (input) {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addSkill();
      }
    });
  }

  function syncSkillsToServer() {
    const skills = Array.from(container.querySelectorAll(".skill-name"))
      .map(el => el.textContent.trim());

    if (saveStatus) {
      saveStatus.innerHTML = '<span class="text-muted"><i class="spinner-border spinner-border-sm"></i> Saving changes...</span>';
    }

    fetch("/api/update-skills", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skills: skills })
    })
    .then(res => res.json())
    .then(data => {
      if (saveStatus) {
        if (data.success) {
          saveStatus.innerHTML = '<span class="text-success"><i class="bi bi-check-circle"></i> Skills updated successfully.</span>';
          setTimeout(() => { saveStatus.innerHTML = ""; }, 3000);
        } else {
          saveStatus.innerHTML = '<span class="text-danger">Failed to save skills.</span>';
        }
      }
    })
    .catch(err => {
      console.error(err);
      if (saveStatus) {
        saveStatus.innerHTML = '<span class="text-danger">Error communicating with server.</span>';
      }
    });
  }
}

// ==========================================
// 3. Save / Unsave Jobs Asynchronously
// ==========================================
function initSaveJobButtons() {
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-save-job");
    if (!btn) return;

    const jobId = btn.dataset.jobId;
    const isSaved = btn.dataset.saved === "true";

    btn.disabled = true;
    const endpoint = isSaved ? "/api/unsave-job" : "/api/save-job";

    // Gather job payload from dataset if saving
    const payload = {
      id: jobId,
      title: btn.dataset.jobTitle || "Job",
      company: btn.dataset.jobCompany || "Company",
      location: btn.dataset.jobLocation || "Location",
      match_score: parseFloat(btn.dataset.jobScore || 0),
      employment_type: btn.dataset.jobType || "Full-time",
      posted_date: btn.dataset.jobDate || "Recently",
      url: btn.dataset.jobUrl || "#",
      source_url: btn.dataset.jobSourceUrl || btn.dataset.jobUrl || null,
      source: btn.dataset.jobSource || "JobMatch AI",
      source_name: btn.dataset.jobSourceName || btn.dataset.jobSource || "JobMatch AI",
      is_demo: btn.dataset.jobIsDemo === "true"
    };

    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
      btn.disabled = false;
      if (data.success) {
        if (isSaved) {
          btn.dataset.saved = "false";
          btn.innerHTML = '<i class="bi bi-bookmark"></i> Save Job';
          btn.classList.remove("btn-primary");
          btn.classList.add("btn-outline-custom");
          
          // If on saved jobs page, remove card smoothly
          const card = btn.closest(".saved-job-card-col");
          if (card) {
            card.style.opacity = "0";
            setTimeout(() => card.remove(), 250);
          }
        } else {
          btn.dataset.saved = "true";
          btn.innerHTML = '<i class="bi bi-bookmark-fill text-primary"></i> Saved';
          btn.classList.remove("btn-outline-custom");
          btn.classList.add("btn-primary-light", "text-primary");
        }
      } else {
        alert(data.error || "Operation failed.");
      }
    })
    .catch(err => {
      btn.disabled = false;
      console.error(err);
    });
  });
}

// ==========================================
// 4. Multiple Job Comparison Selector
// ==========================================
function initJobComparisonSelector() {
  const compareCheckboxes = document.querySelectorAll(".compare-job-checkbox");
  const compareFloatingBar = document.getElementById("compareFloatingBar");
  const compareCountEl = document.getElementById("compareCount");
  const compareSubmitBtn = document.getElementById("compareSubmitBtn");

  if (!compareCheckboxes.length) return;

  function updateCompareBar() {
    const checked = Array.from(compareCheckboxes).filter(cb => cb.checked);
    const count = checked.length;

    if (compareCountEl) compareCountEl.textContent = count;

    if (count > 0) {
      if (compareFloatingBar) compareFloatingBar.classList.remove("d-none");
    } else {
      if (compareFloatingBar) compareFloatingBar.classList.add("d-none");
    }

    if (compareSubmitBtn) {
      compareSubmitBtn.disabled = count < 2;
    }
  }

  compareCheckboxes.forEach(cb => {
    cb.addEventListener("change", () => {
      const checked = Array.from(compareCheckboxes).filter(c => c.checked);
      if (checked.length > 4) {
        alert("You can select up to 4 jobs to compare at a time.");
        cb.checked = false;
      }
      updateCompareBar();
    });
  });

  if (compareSubmitBtn) {
    compareSubmitBtn.addEventListener("click", () => {
      const checkedIds = Array.from(compareCheckboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);

      if (checkedIds.length >= 2) {
        window.location.href = `/compare?ids=${encodeURIComponent(checkedIds.join(","))}`;
      }
    });
  }
}
