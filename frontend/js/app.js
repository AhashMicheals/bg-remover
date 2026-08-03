/**
 * PureCut AI - Main Application Logic
 * Vanilla JavaScript (ES6) for handling file upload, batch queue, status polling,
 * interactive split preview modal, dark mode, keyboard shortcuts, and downloads.
 */

document.addEventListener('DOMContentLoaded', () => {
  // State variables
  let queueFiles = [];          // Local array of File objects
  let currentJobId = null;      // Active FastAPI Job ID
  let pollingInterval = null;   // Handle for status polling
  let currentZoom = 1.0;        // Modal zoom scale
  let isDraggingSplit = false;  // Split slider drag state

  // DOM Elements
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const browseFilesBtn = document.getElementById('browseFilesBtn');
  const queueGrid = document.getElementById('queueGrid');
  const batchControlBar = document.getElementById('batchControlBar');
  const queueCountBadge = document.getElementById('queueCountBadge');
  const processBatchBtn = document.getElementById('processBatchBtn');
  const downloadZipBtn = document.getElementById('downloadZipBtn');
  const clearQueueBtn = document.getElementById('clearQueueBtn');

  const statCompleted = document.getElementById('statCompleted').querySelector('b');
  const statRemaining = document.getElementById('statRemaining').querySelector('b');
  const statSpeed = document.getElementById('statSpeed').querySelector('b');

  const overallProgressCard = document.getElementById('overallProgressCard');
  const overallStatusText = document.getElementById('overallStatusText');
  const overallPercentText = document.getElementById('overallPercentText');
  const overallProgressBar = document.getElementById('overallProgressBar');

  // Preview Modal Elements
  const previewModal = document.getElementById('previewModal');
  const modalFilename = document.getElementById('modalFilename');
  const modalImgOriginal = document.getElementById('modalImgOriginal');
  const modalImgProcessed = document.getElementById('modalImgProcessed');
  const modalDownloadBtn = document.getElementById('modalDownloadBtn');
  const modalCloseBtn = document.getElementById('modalCloseBtn');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const splitSliderContainer = document.getElementById('splitSliderContainer');
  const splitLayerProcessed = document.getElementById('splitLayerProcessed');
  const splitHandle = document.getElementById('splitHandle');

  const zoomInBtn = document.getElementById('zoomInBtn');
  const zoomOutBtn = document.getElementById('zoomOutBtn');
  const zoomResetBtn = document.getElementById('zoomResetBtn');
  const fullscreenBtn = document.getElementById('fullscreenBtn');

  // Theme Toggle
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const themeIcon = document.getElementById('themeIcon');

  // Toast Container
  const toastContainer = document.getElementById('toastContainer');

  // =========================================================================
  // Theme Manager (Dark / Light Mode)
  // =========================================================================
  const savedTheme = localStorage.getItem('theme') || 'light';
  setTheme(savedTheme);

  themeToggleBtn.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
  });

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    if (theme === 'dark') {
      themeIcon.className = 'fa-solid fa-sun';
    } else {
      themeIcon.className = 'fa-solid fa-moon';
    }
  }

  // =========================================================================
  // Toast Notification System
  // =========================================================================
  function showToast(message, type = 'info', duration = 3500) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconClass = 'fa-info-circle';
    if (type === 'success') iconClass = 'fa-circle-check';
    if (type === 'error') iconClass = 'fa-triangle-exclamation';
    if (type === 'warning') iconClass = 'fa-exclamation-circle';

    toast.innerHTML = `<i class="fa-solid ${iconClass}"></i> <span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  // =========================================================================
  // Drag & Drop / File Input / Clipboard Paste Handlers
  // =========================================================================
  browseFilesBtn.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFilesSelected(Array.from(e.target.files));
      fileInput.value = '';
    }
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files.length > 0) {
      handleFilesSelected(Array.from(dt.files));
    }
  });

  // Global Paste (Ctrl+V) Image Support
  window.addEventListener('paste', (e) => {
    const items = e.clipboardData || e.originalEvent?.clipboardData;
    if (!items || !items.items) return;

    const pastedFiles = [];
    for (const item of items.items) {
      if (item.type.indexOf('image') === 0) {
        const blob = item.getAsFile();
        if (blob) {
          const file = new File([blob], `pasted_image_${Date.now()}.png`, { type: blob.type });
          pastedFiles.push(file);
        }
      }
    }

    if (pastedFiles.length > 0) {
      showToast(`Pasted ${pastedFiles.length} image(s) from clipboard!`, 'success');
      handleFilesSelected(pastedFiles);
    }
  });

  // =========================================================================
  // File Validation & Queue Logic
  // =========================================================================
  function handleFilesSelected(newFiles) {
    const MAX_FILES = 20;
    const MAX_SIZE_MB = 20;
    const ALLOWED_EXTS = ['jpg', 'jpeg', 'png', 'webp'];

    if (queueFiles.length + newFiles.length > MAX_FILES) {
      showToast(`Upload limit exceeded. Maximum ${MAX_FILES} images allowed per batch.`, 'error');
      return;
    }

    let addedCount = 0;

    newFiles.forEach(file => {
      const ext = file.name.split('.').pop().toLowerCase();
      if (!ALLOWED_EXTS.includes(ext)) {
        showToast(`Skipped '${file.name}': Unsupported format. Allowed: JPG, PNG, WEBP.`, 'warning');
        return;
      }

      if (file.size > MAX_SIZE_MB * 1024 * 1024) {
        showToast(`Skipped '${file.name}': Exceeds 20MB limit.`, 'warning');
        return;
      }

      // Check duplicates
      const isDuplicate = queueFiles.some(f => f.name === file.name && f.size === file.size);
      if (isDuplicate) {
        showToast(`Skipped '${file.name}': Already in upload queue.`, 'info');
        return;
      }

      queueFiles.push(file);
      addedCount++;
    });

    if (addedCount > 0) {
      showToast(`Added ${addedCount} image(s) to queue. Triggering upload...`, 'success');
      uploadQueueToBackend();
    }
  }

  // =========================================================================
  // API Integration: Upload, Process, Status Polling
  // =========================================================================
  async function uploadQueueToBackend() {
    if (queueFiles.length === 0) return;

    const formData = new FormData();
    queueFiles.forEach(file => formData.append('files', file));

    try {
      showToast('Uploading files to server...', 'info');
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Upload failed');
      }

      const data = await response.json();
      currentJobId = data.job_id;
      renderQueueUI(data);

      showToast('Images ready for AI background removal!', 'success');
    } catch (err) {
      showToast(`Error uploading: ${err.message}`, 'error');
    }
  }

  async function startProcessing() {
    if (!currentJobId) {
      showToast('No active job to process.', 'warning');
      return;
    }

    processBatchBtn.disabled = true;
    processBatchBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
    overallProgressCard.classList.remove('hidden');

    try {
      const response = await fetch('/api/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: currentJobId, output_format: 'jpg' })
      });

      if (!response.ok) {
        throw new Error('Failed to initiate processing');
      }

      // Start polling status every second
      if (pollingInterval) clearInterval(pollingInterval);
      pollingInterval = setInterval(pollJobStatus, 1000);
      showToast('Started background removal & white canvas compositing.', 'info');
    } catch (err) {
      showToast(`Processing error: ${err.message}`, 'error');
      processBatchBtn.disabled = false;
      processBatchBtn.innerHTML = '<i class="fa-solid fa-play"></i> Process All';
    }
  }

  async function pollJobStatus() {
    if (!currentJobId) return;

    try {
      const response = await fetch(`/api/status/${currentJobId}`);
      if (!response.ok) return;

      const data = await response.json();
      updateQueueUI(data);

      if (data.status === 'Completed' || data.status === 'Completed With Errors' || data.status === 'Cancelled') {
        clearInterval(pollingInterval);
        pollingInterval = null;

        processBatchBtn.disabled = false;
        processBatchBtn.innerHTML = '<i class="fa-solid fa-check-double"></i> Processing Done';
        downloadZipBtn.disabled = data.completed_images === 0;

        if (data.status === 'Completed') {
          showToast('All backgrounds removed successfully! Pure white images ready.', 'success');
        } else if (data.status === 'Completed With Errors') {
          showToast('Batch completed with some item errors.', 'warning');
        }
      }
    } catch (err) {
      console.error('Error polling status:', err);
    }
  }

  // =========================================================================
  // UI Rendering & Queue Updates
  // =========================================================================
  function renderQueueUI(jobData) {
    batchControlBar.classList.remove('hidden');
    queueCountBadge.textContent = `${jobData.total_images} / 20`;

    statCompleted.textContent = jobData.completed_images;
    statRemaining.textContent = jobData.total_images - (jobData.completed_images + jobData.failed_images);
    statSpeed.textContent = `${jobData.processing_speed} img/s`;

    queueGrid.innerHTML = '';

    jobData.images.forEach(img => {
      const card = createQueueItemCard(img);
      queueGrid.appendChild(card);
    });

    processBatchBtn.disabled = false;
  }

  function updateQueueUI(jobData) {
    queueCountBadge.textContent = `${jobData.total_images} / 20`;
    statCompleted.textContent = jobData.completed_images;
    statRemaining.textContent = jobData.remaining_images;
    statSpeed.textContent = `${jobData.processing_speed} img/s`;

    overallPercentText.textContent = `${jobData.overall_progress}%`;
    overallProgressBar.style.width = `${jobData.overall_progress}%`;
    overallStatusText.textContent = `Processing Batch (${jobData.completed_images}/${jobData.total_images} Completed)...`;

    jobData.images.forEach(img => {
      const card = document.getElementById(`card-${img.id}`);
      if (card) {
        updateCardElement(card, img);
      } else {
        queueGrid.appendChild(createQueueItemCard(img));
      }
    });

    downloadZipBtn.disabled = jobData.completed_images === 0;
  }

  function createQueueItemCard(img) {
    const card = document.createElement('div');
    card.className = 'queue-item-card glass-card';
    card.id = `card-${img.id}`;

    const thumbUrl = `/api/preview/${currentJobId}/${img.id}/thumb`;

    card.innerHTML = `
      <div class="item-thumb-wrapper">
        <img src="${thumbUrl}" alt="${img.original_filename}" onerror="this.src='https://via.placeholder.com/200?text=Preview';" />
        <div class="status-badge status-${img.status.replace(/ /g, '-')}">
          ${getStatusIcon(img.status)} <span>${img.status}</span>
        </div>
      </div>
      <div class="item-meta">
        <span class="item-filename" title="${img.original_filename}">${img.original_filename}</span>
        <span class="item-size">${img.file_size_formatted}</span>
      </div>
      <div class="item-progress-track">
        <div class="item-progress-fill" style="width: ${img.progress}%;"></div>
      </div>
      <div class="item-actions">
        ${img.status === 'Completed' ? `
          <button class="btn btn-secondary btn-sm preview-btn" data-id="${img.id}">
            <i class="fa-solid fa-eye"></i> Preview
          </button>
          <a href="/api/download/${currentJobId}/${img.id}" class="btn btn-primary btn-sm download-btn" download>
            <i class="fa-solid fa-download"></i>
          </a>
        ` : img.status === 'Failed' ? `
          <button class="btn btn-secondary btn-sm retry-btn" data-id="${img.id}">
            <i class="fa-solid fa-rotate-right"></i> Retry
          </button>
        ` : `
          <button class="btn btn-secondary btn-sm disabled" disabled>
            <i class="fa-solid fa-spinner fa-spin"></i> Working
          </button>
        `}
        <button class="icon-btn close-btn remove-btn" data-id="${img.id}" title="Remove Item">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </div>
    `;

    bindCardEvents(card, img.id);
    return card;
  }

  function updateCardElement(card, img) {
    const badge = card.querySelector('.status-badge');
    badge.className = `status-badge status-${img.status.replace(/ /g, '-')}`;
    badge.innerHTML = `${getStatusIcon(img.status)} <span>${img.status}</span>`;

    const progressFill = card.querySelector('.item-progress-fill');
    progressFill.style.width = `${img.progress}%`;

    const actionsDiv = card.querySelector('.item-actions');
    if (img.status === 'Completed') {
      actionsDiv.innerHTML = `
        <button class="btn btn-secondary btn-sm preview-btn" data-id="${img.id}">
          <i class="fa-solid fa-eye"></i> Preview
        </button>
        <a href="/api/download/${currentJobId}/${img.id}" class="btn btn-primary btn-sm download-btn" download>
          <i class="fa-solid fa-download"></i>
        </a>
        <button class="icon-btn close-btn remove-btn" data-id="${img.id}" title="Remove Item">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      `;
    } else if (img.status === 'Failed') {
      actionsDiv.innerHTML = `
        <button class="btn btn-secondary btn-sm retry-btn" data-id="${img.id}">
          <i class="fa-solid fa-rotate-right"></i> Retry
        </button>
        <button class="icon-btn close-btn remove-btn" data-id="${img.id}" title="Remove Item">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      `;
    }
    bindCardEvents(card, img.id);
  }

  function getStatusIcon(status) {
    switch (status) {
      case 'Waiting': return '<i class="fa-solid fa-clock"></i>';
      case 'Uploading': return '<i class="fa-solid fa-arrow-up-from-bracket"></i>';
      case 'Removing Background': return '<i class="fa-solid fa-wand-magic-sparkles fa-spin"></i>';
      case 'Adding White Background': return '<i class="fa-solid fa-palette"></i>';
      case 'Compressing': return '<i class="fa-solid fa-file-contract"></i>';
      case 'Completed': return '<i class="fa-solid fa-circle-check"></i>';
      case 'Failed': return '<i class="fa-solid fa-circle-xmark"></i>';
      default: return '<i class="fa-solid fa-spinner fa-spin"></i>';
    }
  }

  function bindCardEvents(card, imgId) {
    const previewBtn = card.querySelector('.preview-btn');
    if (previewBtn) {
      previewBtn.onclick = () => openPreviewModal(imgId);
    }

    const retryBtn = card.querySelector('.retry-btn');
    if (retryBtn) {
      retryBtn.onclick = () => retryItem(imgId);
    }

    const removeBtn = card.querySelector('.remove-btn');
    if (removeBtn) {
      removeBtn.onclick = () => removeItem(imgId);
    }
  }

  // =========================================================================
  // Single Item Actions & Controls
  // =========================================================================
  async function retryItem(imgId) {
    if (!currentJobId) return;
    showToast('Retrying background removal...', 'info');
    fetch('/api/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: currentJobId, image_ids: [imgId] })
    });
    if (!pollingInterval) pollingInterval = setInterval(pollJobStatus, 1000);
  }

  function removeItem(imgId) {
    const card = document.getElementById(`card-${imgId}`);
    if (card) card.remove();

    queueFiles = queueFiles.filter(f => f.id !== imgId);
    showToast('Item removed from queue.', 'info');
  }

  clearQueueBtn.addEventListener('click', () => {
    if (currentJobId) {
      fetch(`/api/cancel/${currentJobId}`, { method: 'DELETE' });
    }
    currentJobId = null;
    queueFiles = [];
    if (pollingInterval) clearInterval(pollingInterval);

    queueGrid.innerHTML = '';
    batchControlBar.classList.add('hidden');
    overallProgressCard.classList.add('hidden');
    processBatchBtn.innerHTML = '<i class="fa-solid fa-play"></i> Process All';
    showToast('Queue cleared.', 'info');
  });

  processBatchBtn.addEventListener('click', startProcessing);

  downloadZipBtn.addEventListener('click', () => {
    if (!currentJobId) return;
    window.location.href = `/api/download-zip/${currentJobId}`;
    showToast('Preparing ZIP archive download...', 'success');
  });

  // =========================================================================
  // Interactive Split Comparison Modal Logic
  // =========================================================================
  function openPreviewModal(imgId) {
    if (!currentJobId) return;

    const origUrl = `/api/preview/${currentJobId}/${imgId}/original`;
    const procUrl = `/api/preview/${currentJobId}/${imgId}/processed`;
    const downUrl = `/api/download/${currentJobId}/${imgId}`;

    modalImgOriginal.src = origUrl;
    modalImgProcessed.src = procUrl;
    modalDownloadBtn.href = downUrl;

    currentZoom = 1.0;
    applyZoom();

    splitLayerProcessed.style.width = '50%';
    splitHandle.style.left = '50%';

    previewModal.classList.remove('hidden');
  }

  function closePreviewModal() {
    previewModal.classList.add('hidden');
  }

  modalCloseBtn.addEventListener('click', closePreviewModal);
  closeModalBtn.addEventListener('click', closePreviewModal);

  previewModal.addEventListener('click', (e) => {
    if (e.target === previewModal) closePreviewModal();
  });

  // Draggable Split Slider Handle
  splitHandle.addEventListener('mousedown', (e) => {
    isDraggingSplit = true;
    e.preventDefault();
  });

  window.addEventListener('mouseup', () => {
    isDraggingSplit = false;
  });

  window.addEventListener('mousemove', (e) => {
    if (!isDraggingSplit) return;
    updateSplitPosition(e.clientX);
  });

  splitSliderContainer.addEventListener('touchstart', (e) => {
    if (e.touches.length === 1) {
      isDraggingSplit = true;
    }
  });

  window.addEventListener('touchend', () => {
    isDraggingSplit = false;
  });

  window.addEventListener('touchmove', (e) => {
    if (!isDraggingSplit || e.touches.length === 0) return;
    updateSplitPosition(e.touches[0].clientX);
  });

  function updateSplitPosition(clientX) {
    const rect = splitSliderContainer.getBoundingClientRect();
    let x = clientX - rect.left;

    if (x < 0) x = 0;
    if (x > rect.width) x = rect.width;

    const percent = (x / rect.width) * 100;
    splitLayerProcessed.style.width = `${percent}%`;
    splitHandle.style.left = `${percent}%`;
  }

  // Zoom Controls
  zoomInBtn.addEventListener('click', () => {
    currentZoom = Math.min(currentZoom + 0.25, 2.5);
    applyZoom();
  });

  zoomOutBtn.addEventListener('click', () => {
    currentZoom = Math.max(currentZoom - 0.25, 0.5);
    applyZoom();
  });

  zoomResetBtn.addEventListener('click', () => {
    currentZoom = 1.0;
    applyZoom();
  });

  function applyZoom() {
    splitSliderContainer.style.transform = `scale(${currentZoom})`;
  }

  fullscreenBtn.addEventListener('click', () => {
    if (!document.fullscreenElement) {
      previewModal.requestFullscreen?.() || previewModal.webkitRequestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  });

  // =========================================================================
  // Keyboard Shortcuts
  // =========================================================================
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closePreviewModal();
    }
    if (e.ctrlKey && e.key.toLowerCase() === 'd') {
      e.preventDefault();
      if (!downloadZipBtn.disabled) {
        downloadZipBtn.click();
      }
    }
  });
});
