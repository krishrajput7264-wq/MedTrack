/**
 * MedTrack Dashboard Script
 * Dynamic slot selection, doctor-patient linkage, live filtering, and file upload UX.
 */

document.addEventListener("DOMContentLoaded", () => {
  // ----------------------------------------------------
  // PATIENT: Dynamic Slot Selection based on Doctor
  // ----------------------------------------------------
  const doctorSelect = document.getElementById("bookingDoctorSelect");
  const slotsContainer = document.getElementById("availableSlotsContainer");
  const timeSlotInput = document.getElementById("selectedTimeSlot");

  if (doctorSelect && slotsContainer && timeSlotInput) {
    function updateSlots() {
      const selectedOption = doctorSelect.options[doctorSelect.selectedIndex];
      if (!selectedOption) return;

      const rawSlots = selectedOption.getAttribute("data-slots");
      let slots = [];
      try {
        slots = JSON.parse(rawSlots || "[]");
      } catch (e) {
        slots = ["09:00 AM", "10:30 AM", "02:00 PM", "04:30 PM"];
      }

      slotsContainer.innerHTML = "";
      timeSlotInput.value = "";

      if (slots.length === 0) {
        slotsContainer.innerHTML = `<div style="color: var(--text-dim); font-size: 0.85rem;">No slots currently open for this physician.</div>`;
        return;
      }

      slots.forEach((slot, index) => {
        const slotEl = document.createElement("div");
        slotEl.className = `slot-item ${index === 0 ? "selected" : ""}`;
        slotEl.textContent = slot;
        slotEl.addEventListener("click", () => {
          document.querySelectorAll(".slot-item").forEach(s => s.classList.remove("selected"));
          slotEl.classList.add("selected");
          timeSlotInput.value = slot;
        });
        slotsContainer.appendChild(slotEl);

        // Pre-select first
        if (index === 0) timeSlotInput.value = slot;
      });
    }

    doctorSelect.addEventListener("change", updateSlots);
    // Initial call
    updateSlots();
  }

  // ----------------------------------------------------
  // DOCTOR: Link Appointment to Diagnosis Modal
  // ----------------------------------------------------
  document.querySelectorAll("[data-diagnose-appt]").forEach(btn => {
    btn.addEventListener("click", () => {
      const apptId = btn.getAttribute("data-diagnose-appt");
      const patientId = btn.getAttribute("data-patient-id");
      const patientName = btn.getAttribute("data-patient-name");

      const modalPatientSelect = document.getElementById("diagPatientSelect");
      const modalApptIdInput = document.getElementById("diagApptIdInput");
      const modalApptBadge = document.getElementById("diagApptBadge");

      if (modalPatientSelect && patientId) {
        modalPatientSelect.value = patientId;
      }
      if (modalApptIdInput) {
        modalApptIdInput.value = apptId || "";
      }
      if (modalApptBadge) {
        modalApptBadge.textContent = apptId ? `Linked to Appointment: ${apptId} (${patientName})` : "";
      }

      openModal("diagnoseModal");
    });
  });

  // Clear appointment linkage when clicking "New Clinical Diagnosis" button
  const newDiagBtn = document.querySelector('[data-modal-target="diagnoseModal"]');
  if (newDiagBtn) {
    newDiagBtn.addEventListener("click", () => {
      const modalApptIdInput = document.getElementById("diagApptIdInput");
      const modalApptBadge = document.getElementById("diagApptBadge");
      if (modalApptIdInput) modalApptIdInput.value = "";
      if (modalApptBadge) modalApptBadge.textContent = "Outpatient Consultation Assessment (No specific appointment linked)";
    });
  }

  // ----------------------------------------------------
  // FILE UPLOAD UX (Custom file label display)
  // ----------------------------------------------------
  const fileInput = document.getElementById("reportFileInput");
  const fileLabel = document.getElementById("reportFileNameDisplay");
  if (fileInput && fileLabel) {
    fileInput.addEventListener("change", () => {
      if (fileInput.files.length > 0) {
        const f = fileInput.files[0];
        const sizeMb = (f.size / (1024 * 1024)).toFixed(2);
        fileLabel.innerHTML = `<strong>Selected:</strong> ${f.name} <span style="color:var(--text-dim)">(${sizeMb} MB)</span>`;
      } else {
        fileLabel.textContent = "No file selected. PDF, PNG, JPG, or DOCX allowed.";
      }
    });
  }

  // ----------------------------------------------------
  // FILTER MEDICAL HISTORY / APPOINTMENTS (Live search)
  // ----------------------------------------------------
  const searchInput = document.getElementById("timelineSearchInput");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase();
      const items = document.querySelectorAll(".timeline-item, .appointment-card");
      items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(q)) {
          item.style.display = "";
        } else {
          item.style.display = "none";
        }
      });
    });
  }
});
