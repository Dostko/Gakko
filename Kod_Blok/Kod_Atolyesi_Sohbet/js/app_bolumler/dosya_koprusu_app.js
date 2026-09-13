// DOSYA KÖPRÜSÜ: BAŞLANGIÇ

function connectBridge() {
  if (typeof QWebChannel === "undefined" || !window.qt || !qt.webChannelTransport) {
    statusNote.textContent = "Qwen bağlantısı kurulamadı";
    return;
  }

  new QWebChannel(qt.webChannelTransport, channel => {
    bridge = channel.objects.gakkoBridge;
    recordsBridge = channel.objects.kayitlarBridge || null;

    if (recordsBridge) {
      recordsBridge.records_list_ready.connect(payloadText => {
        try {
          renderRecordsList(JSON.parse(String(payloadText || "{}")));
        } catch (error) {
          statusNote.textContent = "Kayıtlar okunamadı";
        }
      });

      recordsBridge.record_ready.connect(payloadText => {
        try {
          renderRecordDetail(JSON.parse(String(payloadText || "{}")));
        } catch (error) {
          statusNote.textContent = "Kayıt açılamadı";
        }
      });

      recordsBridge.record_action_ready.connect(payloadText => {
        try {
          const payload = JSON.parse(String(payloadText || "{}"));
          statusNote.textContent = payload.deleted
            ? "Kayıt silindi"
            : "Kayıt silinemedi";
          clearRecordDetail();
          requestRecords();
        } catch (error) {
          statusNote.textContent = "Kayıt işlemi tamamlanamadı";
        }
      });

      recordsBridge.error_ready.connect(error => {
        statusNote.textContent = String(error || "Kayıt işlemi başarısız");
      });
    }

    bridge.project_selected.connect(path => {
      showActiveProject(path, true);
    });

    if (typeof bridge.get_active_project === "function") {
      bridge.get_active_project(projectPath => {
        showActiveProject(projectPath, false);
      });
    }

    if (
      bridge.file_browser_project_selected
      && typeof bridge.file_browser_project_selected.connect === "function"
    ) {
      bridge.file_browser_project_selected.connect(path => {
        showFileBrowserRoot(path);
      });
    }

    if (
      bridge.file_browser_directory_ready
      && typeof bridge.file_browser_directory_ready.connect === "function"
    ) {
      bridge.file_browser_directory_ready.connect(payloadText => {
        try {
          const payload = JSON.parse(String(payloadText || "{}"));
          const path = String(payload.path || "");
          const entries = Array.isArray(payload.entries) ? payload.entries : [];
          fileDirectoryCache.set(path, { path, entries });
          renderFileTree();
        } catch (error) {
          statusNote.textContent = "Dosya klasörü okunamadı";
        }
      });
    }

    if (
      bridge.file_browser_file_ready
      && typeof bridge.file_browser_file_ready.connect === "function"
    ) {
      bridge.file_browser_file_ready.connect(payloadText => {
        try {
          renderFileBrowserFile(JSON.parse(String(payloadText || "{}")));
        } catch (error) {
          statusNote.textContent = "Dosya açılamadı";
        }
      });
    }

    bridge.history_sessions_ready.connect(payloadText => {
      try {
        renderHistorySessions(JSON.parse(String(payloadText || "{}")));
      } catch (error) {
        statusNote.textContent = "Sohbet geçmişi okunamadı";
      }
    });

    bridge.history_session_ready.connect(payloadText => {
      try {
        renderHistorySession(JSON.parse(String(payloadText || "{}")));
      } catch (error) {
        statusNote.textContent = "Sohbet geçmişi açılamadı";
      }
    });

    bridge.history_action_ready.connect(payloadText => {
      try {
        const payload = JSON.parse(String(payloadText || "{}"));
        const deleted = Number(payload.deleted) || 0;
        statusNote.textContent = deleted > 0
          ? `${deleted} geçmiş kaydı silindi`
          : "Silinecek geçmiş kaydı bulunamadı";
        clearHistoryDetail();
      } catch (error) {
        statusNote.textContent = "Geçmiş işlemi tamamlanamadı";
      }
    });

    if (
      bridge.context_remaining_ready
      && typeof bridge.context_remaining_ready.connect === "function"
    ) {
      bridge.context_remaining_ready.connect(value => {
        remainingDisplay.textContent = formatRemainingPercentage(value);
        if (!waiting && statusNote.textContent === "Bağlam sıfırlanıyor...") {
          statusNote.textContent = "Gakko AI";
        }
      });
    }

    bridge.chat_files_selected.connect(payloadText => {
      try {
        const payload = JSON.parse(String(payloadText || "{}"));
        mergeSelectedChatFiles(payload.files);
        statusNote.textContent = "Ekler hazır";
        input.focus();
      } catch (error) {
        statusNote.textContent = "Ekli dosyalar alınamadı";
      }
    });

    bridge.reply_ready.connect(reply => {
      const thinkingDuration = finishThinkingMessage();
      const assistantImages = pendingAssistantImageAttachments;
      pendingAssistantImageAttachments = [];
      addMessage(reply, "assistant", assistantImages, thinkingDuration);
      setWaiting(false);
      refreshVisibleFileDirectories();
    });

    if (
      bridge.tool_activity
      && typeof bridge.tool_activity.connect === "function"
    ) {
      bridge.tool_activity.connect(payloadText => {
        appendThinkingActivity(payloadText);
      });
    }

    if (
      bridge.generation_cancelled
      && typeof bridge.generation_cancelled.connect === "function"
    ) {
      bridge.generation_cancelled.connect(() => {
        pendingAssistantImageAttachments = [];
        removeThinkingMessage();
        addMessage("İşlem durduruldu.", "assistant");
        setWaiting(false);
        statusNote.textContent = "İşlem durduruldu";
      });
    }

    bridge.error_ready.connect(error => {
      pendingAssistantImageAttachments = [];
      removeThinkingMessage();
      addMessage("Hata: " + error, "assistant");
      setWaiting(false);
    });

    statusNote.textContent = "Gakko AI";
  });
}

connectBridge();

// DOSYA KÖPRÜSÜ: BİTİŞ
