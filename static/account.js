(function () {
    "use strict";

    const state = {
        user: null,
        listings: [],
        savedIds: new Set(),
        savedListings: [],
        questions: [],
        notifications: [],
    };

    const $ = (sel) => document.querySelector(sel);

    const dom = {
        saved: $("#saved-listings"),
        listings: $("#customer-listings"),
        messages: $("#customer-messages"),
        notifications: $("#customer-notifications"),
        questionForm: $("#question-form"),
        questionListing: $("#question-listing"),
        markRead: $("#mark-notifications-read"),
        summarySaved: $("#summary-saved"),
        summaryQuestions: $("#summary-questions"),
        summaryUnread: $("#summary-unread"),
        toastContainer: $("#toast-container"),
    };

    function escapeHTML(value) {
        return String(value ?? "—")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function formatPrice(value) {
        return new Intl.NumberFormat("tr-TR").format(Number(value || 0));
    }

    function showToast(message, type = "success") {
        const el = document.createElement("div");
        el.className = `toast ${type}`;
        el.textContent = message;
        dom.toastContainer.appendChild(el);
        setTimeout(() => {
            el.style.opacity = "0";
            el.style.transform = "translateX(40px)";
            el.style.transition = "all .3s";
            setTimeout(() => el.remove(), 350);
        }, 3500);
    }

    async function api(url, options = {}) {
        const res = await fetch(url, {
            headers: { "Content-Type": "application/json", ...(options.headers || {}) },
            ...options,
        });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
            throw new Error(body.error || `HTTP ${res.status}`);
        }
        return body;
    }

    function empty(message) {
        return `<div class="empty-state"><span class="empty-icon">◇</span><p>${escapeHTML(message)}</p></div>`;
    }

    function table(headers, rows) {
        if (!rows.length) return empty("Kayıt bulunamadı.");
        return `
        <div class="data-table-wrap">
            <table class="data-table">
                <thead><tr>${headers.map((h) => `<th>${escapeHTML(h)}</th>`).join("")}</tr></thead>
                <tbody>${rows.map((row) => `<tr>${row.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody>
            </table>
        </div>`;
    }

    function listingTitle(item) {
        return `#${item.IlanID || item.ilan_id} · ${item.Baslik || item.baslik}`;
    }

    function renderSummary() {
        const unread = state.notifications.filter((n) => !Number(n.Okundu)).length;
        dom.summarySaved.textContent = state.savedListings.length;
        dom.summaryQuestions.textContent = state.questions.length;
        dom.summaryUnread.textContent = unread;
    }

    function renderQuestionSelect() {
        const options = [
            `<option value="">Genel soru</option>`,
            ...state.listings.map(
                (item) => `<option value="${item.IlanID}">${escapeHTML(listingTitle(item))}</option>`
            ),
        ];
        dom.questionListing.innerHTML = options.join("");
    }

    function renderSavedListings() {
        const rows = state.savedListings.map((item) => [
            escapeHTML(`#${item.IlanID}`),
            escapeHTML(item.Baslik),
            `${formatPrice(item.Fiyat)} ₺`,
            escapeHTML(item["İlce"]),
            escapeHTML(item.Mahalle),
            `<button class="btn-table-action" data-unsave="${item.IlanID}">Kaldır</button>`,
        ]);
        dom.saved.innerHTML = table(["İlan", "Başlık", "Fiyat", "İlçe", "Mahalle", ""], rows);
        dom.saved.querySelectorAll("[data-unsave]").forEach((button) => {
            button.addEventListener("click", () => unsaveListing(button.dataset.unsave));
        });
    }

    function renderListings() {
        const rows = state.listings.map((item) => {
            const saved = state.savedIds.has(Number(item.IlanID));
            return [
                escapeHTML(`#${item.IlanID}`),
                escapeHTML(item.Baslik),
                `${formatPrice(item.Fiyat)} ₺`,
                escapeHTML(item["İlce"]),
                escapeHTML(item.Mahalle),
                `<button class="btn-table-action" data-save="${item.IlanID}" ${saved ? "disabled" : ""}>${saved ? "Kaydedildi" : "Kaydet"}</button>`,
            ];
        });
        dom.listings.innerHTML = table(["İlan", "Başlık", "Fiyat", "İlçe", "Mahalle", ""], rows);
        dom.listings.querySelectorAll("[data-save]").forEach((button) => {
            button.addEventListener("click", () => saveListing(button.dataset.save));
        });
    }

    function renderMessages() {
        const rows = state.questions.map((item) => [
            escapeHTML(`#${item.SoruID}`),
            escapeHTML(item.IlanID ? `#${item.IlanID}` : "Genel"),
            escapeHTML(item.SoruMetni),
            escapeHTML(item.CevapMetni || "Henüz cevap yok"),
            escapeHTML(item.Durum),
            escapeHTML(item.SoruTarihi),
        ]);
        dom.messages.innerHTML = table(["Soru", "İlan", "Mesaj", "Cevap", "Durum", "Tarih"], rows);
    }

    function renderNotifications() {
        const rows = state.notifications.map((item) => [
            escapeHTML(item.Okundu ? "Okundu" : "Yeni"),
            escapeHTML(item.Baslik),
            escapeHTML(item.Mesaj),
            escapeHTML(item.IlanID ? `#${item.IlanID}` : "—"),
            escapeHTML(item.OlusturmaTarihi),
        ]);
        dom.notifications.innerHTML = table(["Durum", "Başlık", "Mesaj", "İlan", "Tarih"], rows);
    }

    async function loadAccount() {
        const data = await api("/api/account/bootstrap");
        state.user = data.user;
        state.listings = data.listings;
        state.savedIds = new Set((data.saved_ids || []).map(Number));
        state.savedListings = data.saved_listings;
        state.questions = data.questions;
        state.notifications = data.notifications;
        renderSummary();
        renderQuestionSelect();
        renderSavedListings();
        renderListings();
        renderMessages();
        renderNotifications();
    }

    async function saveListing(ilanId) {
        try {
            await api("/api/account/save-listing", {
                method: "POST",
                body: JSON.stringify({ ilan_id: ilanId }),
            });
            await loadAccount();
            showToast("İlan kaydedildi.");
        } catch (error) {
            showToast(error.message, "error");
        }
    }

    async function unsaveListing(ilanId) {
        try {
            await api(`/api/account/save-listing/${ilanId}`, { method: "DELETE" });
            await loadAccount();
            showToast("İlan kaydedilenlerden kaldırıldı.");
        } catch (error) {
            showToast(error.message, "error");
        }
    }

    dom.questionForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const data = new FormData(dom.questionForm);
        try {
            await api("/api/account/questions", {
                method: "POST",
                body: JSON.stringify({
                    ilan_id: data.get("ilan_id"),
                    question: data.get("question"),
                }),
            });
            dom.questionForm.reset();
            await loadAccount();
            showToast("Sorunuz admin paneline iletildi.");
        } catch (error) {
            showToast(error.message, "error");
        }
    });

    dom.markRead.addEventListener("click", async () => {
        try {
            await api("/api/account/notifications/read", { method: "POST", body: "{}" });
            await loadAccount();
            showToast("Bildirimler okundu olarak işaretlendi.");
        } catch (error) {
            showToast(error.message, "error");
        }
    });

    loadAccount().catch((error) => showToast(error.message, "error"));
})();
