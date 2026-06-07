(function () {
    "use strict";

    const state = {
        listings: [],
        agents: [],
        features: [],
        history: [],
        questions: [],
    };

    const $ = (sel) => document.querySelector(sel);

    const dom = {
        createForm: $("#create-listing-form"),
        updateForm: $("#update-listing-form"),
        priceForm: $("#price-update-form"),
        deleteForm: $("#delete-listing-form"),
        createDanisman: $("#create-danisman"),
        updateDanisman: $("#update-danisman"),
        updateSelect: $("#update-ilan-select"),
        priceSelect: $("#price-ilan-select"),
        deleteSelect: $("#delete-ilan-select"),
        createFeatureGroups: $("#create-feature-groups"),
        updateFeatureGroups: $("#update-feature-groups"),
        listingsTable: $("#admin-listings-table"),
        historyTable: $("#admin-history-table"),
        questionsTable: $("#admin-questions-table"),
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

    function formPayload(form) {
        const data = new FormData(form);
        const payload = {};
        data.forEach((value, key) => {
            if (key === "feature_ids") return;
            payload[key] = value;
        });
        payload.feature_ids = data.getAll("feature_ids");
        return payload;
    }

    function table(headers, rows) {
        if (!rows.length) {
            return `<div class="empty-state"><span class="empty-icon">◇</span><p>Kayıt bulunamadı.</p></div>`;
        }
        return `
        <div class="data-table-wrap">
            <table class="data-table">
                <thead><tr>${headers.map((h) => `<th>${escapeHTML(h)}</th>`).join("")}</tr></thead>
                <tbody>
                    ${rows
                        .map(
                            (row) =>
                                `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`
                        )
                        .join("")}
                </tbody>
            </table>
        </div>`;
    }

    function listingLabel(item) {
        return `#${item.IlanID} · ${item.Baslik}`;
    }

    function populateAgents() {
        const options = state.agents
            .map(
                (agent) =>
                    `<option value="${agent.DanismanID}">${escapeHTML(agent.AdSoyad)}</option>`
            )
            .join("");
        dom.createDanisman.innerHTML = options;
        dom.updateDanisman.innerHTML = options;
    }

    function populateListingSelects() {
        const options = state.listings
            .map(
                (item) =>
                    `<option value="${item.IlanID}">${escapeHTML(listingLabel(item))}</option>`
            )
            .join("");
        dom.updateSelect.innerHTML = options;
        dom.priceSelect.innerHTML = options;
        dom.deleteSelect.innerHTML = options;
    }

    function renderFeatureGroups(container, prefix) {
        container.innerHTML = state.features
            .map((group) => {
                const items = group.features
                    .map(
                        (feature) => `
                        <label class="feature-check">
                            <input type="checkbox" name="feature_ids" value="${feature.ozellik_id}" data-feature-prefix="${prefix}">
                            <span>${escapeHTML(feature.ozellik_adi)}</span>
                        </label>`
                    )
                    .join("");
                return `
                <section class="feature-group-box">
                    <h4>${escapeHTML(group.kategori_adi)}</h4>
                    <div class="feature-check-grid">${items}</div>
                </section>`;
            })
            .join("");
    }

    function setCheckedFeatures(form, featureIds) {
        const selected = new Set((featureIds || []).map((id) => String(id)));
        form.querySelectorAll('input[name="feature_ids"]').forEach((input) => {
            input.checked = selected.has(input.value);
        });
    }

    function fillUpdateForm(ilanId) {
        const item = state.listings.find((listing) => String(listing.IlanID) === String(ilanId));
        if (!item) return;
        const form = dom.updateForm;
        form.elements.ilan_id.value = item.IlanID;
        form.elements.baslik.value = item.Baslik || "";
        form.elements.danisman_id.value = item.DanismanID;
        form.elements.fiyat.value = item.Fiyat || "";
        form.elements.il.value = item["İl"] || "İstanbul";
        form.elements.ilce.value = item["İlce"] || "";
        form.elements.mahalle.value = item.Mahalle || "";
        form.elements.emlak_tipi.value = item.EmlakTipi || "";
        form.elements.brut_m2.value = item.BrutM2 || "";
        form.elements.net_m2.value = item.NetM2 || "";
        form.elements.oda_sayisi.value = item.OdaSayisi || "";
        form.elements.note.value = "";
        setCheckedFeatures(form, item.FeatureIDs || []);
    }

    function renderListings() {
        const rows = state.listings.map((item) => [
            escapeHTML(`#${item.IlanID}`),
            escapeHTML(item.Baslik),
            `${formatPrice(item.Fiyat)} ₺`,
            escapeHTML(item["İlce"]),
            escapeHTML(item.Mahalle),
            escapeHTML(item.Danisman),
            `<div class="admin-row-actions">
                <button class="btn-table-action" data-edit="${item.IlanID}">Düzenle</button>
                <button class="btn-table-action btn-danger" data-delete="${item.IlanID}">Sil</button>
            </div>`,
        ]);
        dom.listingsTable.innerHTML = table(
            ["İlan", "Başlık", "Fiyat", "İlçe", "Mahalle", "Danışman", ""],
            rows
        );
        dom.listingsTable.querySelectorAll("[data-edit]").forEach((button) => {
            button.addEventListener("click", () => {
                fillUpdateForm(button.dataset.edit);
                dom.updateForm.scrollIntoView({ behavior: "smooth", block: "center" });
            });
        });
        dom.listingsTable.querySelectorAll("[data-delete]").forEach((button) => {
            button.addEventListener("click", () => deleteListing(button.dataset.delete));
        });
    }

    function renderHistory() {
        const rows = state.history.map((item) => [
            escapeHTML(item.LogID),
            escapeHTML(`#${item.IlanID}`),
            escapeHTML(item.IslemTipi),
            escapeHTML(item.AlanAdi || "İlan"),
            escapeHTML(item.EskiDeger),
            escapeHTML(item.YeniDeger),
            escapeHTML(item.Kullanici),
            escapeHTML(item.DegisimTarihi),
        ]);
        dom.historyTable.innerHTML = table(
            ["Log", "İlan", "İşlem", "Alan", "Eski", "Yeni", "Kullanıcı", "Tarih"],
            rows
        );
    }

    function renderQuestions() {
        if (!state.questions.length) {
            dom.questionsTable.innerHTML =
                `<div class="empty-state"><span class="empty-icon">◇</span><p>Müşteri sorusu bulunamadı.</p></div>`;
            return;
        }
        const rows = state.questions.map((item) => [
            escapeHTML(`#${item.SoruID}`),
            escapeHTML(item.AdSoyad),
            escapeHTML(item.IlanID ? `#${item.IlanID}` : "Genel"),
            escapeHTML(item.SoruMetni),
            escapeHTML(item.Durum),
            item.CevapMetni
                ? escapeHTML(item.CevapMetni)
                : `<form class="inline-answer-form" data-question-id="${item.SoruID}">
                    <textarea class="form-input textarea-input" name="answer" rows="3" required></textarea>
                    <button class="btn-table-action" type="submit">Cevapla</button>
                  </form>`,
        ]);
        dom.questionsTable.innerHTML = table(
            ["Soru", "Kullanıcı", "İlan", "Mesaj", "Durum", "Cevap"],
            rows
        );
        dom.questionsTable.querySelectorAll(".inline-answer-form").forEach((form) => {
            form.addEventListener("submit", async (event) => {
                event.preventDefault();
                const questionId = form.dataset.questionId;
                const answer = new FormData(form).get("answer");
                try {
                    await api(`/api/admin/questions/${questionId}/answer`, {
                        method: "POST",
                        body: JSON.stringify({ answer }),
                    });
                    await loadAdmin();
                    showToast("Cevap kullanıcıya gönderildi.");
                } catch (error) {
                    showToast(error.message, "error");
                }
            });
        });
    }

    async function loadAdmin() {
        const data = await api("/api/admin/bootstrap");
        state.agents = data.agents;
        state.features = data.features;
        state.listings = data.listings;
        state.history = data.history;
        state.questions = data.questions;
        populateAgents();
        populateListingSelects();
        renderFeatureGroups(dom.createFeatureGroups, "create");
        renderFeatureGroups(dom.updateFeatureGroups, "update");
        renderListings();
        renderHistory();
        renderQuestions();
        if (state.listings.length) {
            fillUpdateForm(state.listings[0].IlanID);
        }
    }

    dom.createForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        try {
            await api("/api/admin/listings", {
                method: "POST",
                body: JSON.stringify(formPayload(dom.createForm)),
            });
            dom.createForm.reset();
            dom.createForm.elements.il.value = "İstanbul";
            setCheckedFeatures(dom.createForm, []);
            await loadAdmin();
            showToast("İlan eklendi.");
        } catch (error) {
            showToast(error.message, "error");
        }
    });

    dom.updateSelect.addEventListener("change", () => fillUpdateForm(dom.updateSelect.value));

    dom.updateForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const payload = formPayload(dom.updateForm);
        const ilanId = payload.ilan_id;
        delete payload.ilan_id;
        try {
            await api(`/api/admin/listings/${ilanId}`, {
                method: "PUT",
                body: JSON.stringify(payload),
            });
            await loadAdmin();
            dom.updateSelect.value = ilanId;
            fillUpdateForm(ilanId);
            showToast("İlan güncellendi.");
        } catch (error) {
            showToast(error.message, "error");
        }
    });

    async function deleteListing(ilanId, note = "Admin panelinden ilan silindi.") {
        const item = state.listings.find((listing) => String(listing.IlanID) === String(ilanId));
        const label = item ? listingLabel(item) : `#${ilanId}`;
        const confirmed = window.confirm(`${label} ilanı siteden kaldırılacak. Devam edilsin mi?`);
        if (!confirmed) return;
        try {
            await api(`/api/admin/listings/${ilanId}`, {
                method: "DELETE",
                body: JSON.stringify({ note }),
            });
            await loadAdmin();
            showToast("İlan silindi.");
        } catch (error) {
            showToast(error.message, "error");
        }
    }

    dom.deleteForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const payload = formPayload(dom.deleteForm);
        await deleteListing(payload.ilan_id, payload.note);
    });

    dom.priceForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const payload = formPayload(dom.priceForm);
        const ilanId = payload.ilan_id;
        try {
            await api(`/api/admin/listings/${ilanId}/price`, {
                method: "POST",
                body: JSON.stringify(payload),
            });
            dom.priceForm.elements.new_price.value = "";
            await loadAdmin();
            showToast("Fiyat güncellendi.");
        } catch (error) {
            showToast(error.message, "error");
        }
    });

    loadAdmin().catch((error) => {
        showToast(error.message, "error");
    });
})();
