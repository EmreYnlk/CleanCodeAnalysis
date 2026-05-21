const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const SAMPLE_CODE = `import os
import json
import math

class KullaniciRaporServisi:
    def __init__(self):
        self.kayitlar = []
        self.hatalar = []

    def rapor_uret(self, kullanicilar, filtreler, yetkiler, format_tipi, tarih_araligi, para_birimi):
        toplam = 0
        gecici_deger = 42
        for kullanici in kullanicilar:
            if kullanici is not None:
                if kullanici.get("aktif"):
                    if kullanici.get("rol") in yetkiler:
                        for siparis in kullanici.get("siparisler", []):
                            if siparis.get("durum") == "tamamlandi":
                                toplam += siparis.get("tutar", 0)
        return {"toplam": toplam, "format": format_tipi}

    def harici_profili_oku(self, profil):
        ad = profil.ad
        soyad = profil.soyad
        mail = profil.eposta
        telefon = profil.telefon
        adres = profil.adres
        return f"{ad} {soyad} - {mail} - {telefon} - {adres}"
`;

const state = {
    mode: "paste",
    selectedFile: null,
    selectedZip: null,
    report: null,
    scopeName: "PastedCode.py",
    scopeType: "Kod Analizi",
    activeFile: null,
    severityFilter: "ALL",
    search: "",
};

document.addEventListener("DOMContentLoaded", init);

function init() {
    bindModeTabs();
    bindResultTabs();
    bindFileInputs();
    bindActions();
    bindViolationFilters();
}

function bindModeTabs() {
    $$(".segment").forEach((button) => {
        button.addEventListener("click", () => switchMode(button.dataset.mode));
    });
}

function bindResultTabs() {
    $$(".result-tab").forEach((button) => {
        button.addEventListener("click", () => {
            const tab = button.dataset.resultTab;
            $$(".result-tab").forEach((item) => item.classList.toggle("active", item === button));
            $$("[data-result-panel]").forEach((panel) => {
                panel.classList.toggle("active", panel.dataset.resultPanel === tab);
            });
        });
    });
}

function bindFileInputs() {
    bindDropZone($("#fileDrop"), $("#fileInput"), ".py", selectPythonFile);
    bindDropZone($("#zipDrop"), $("#zipInput"), ".zip", selectZipFile);
}

function bindActions() {
    $("#sampleButton").addEventListener("click", () => {
        switchMode("paste");
        $("#codeInput").value = SAMPLE_CODE;
        showToast("Örnek Python kodu editöre yüklendi.");
    });

    $("#pasteAnalyze").addEventListener("click", analyzePastedCode);
    $("#fileAnalyze").addEventListener("click", analyzeSelectedFile);
    $("#projectAnalyze").addEventListener("click", analyzeSelectedProject);
    $("#exportJson").addEventListener("click", exportJsonReport);
    $("#printReport").addEventListener("click", () => window.print());
}

function bindViolationFilters() {
    $("#severityFilters").addEventListener("click", (event) => {
        const button = event.target.closest("[data-severity]");
        if (!button) return;

        state.severityFilter = button.dataset.severity;
        $$(".filter-chip", $("#severityFilters")).forEach((item) => {
            item.classList.toggle("active", item === button);
        });
        renderViolationTable();
    });

    $("#violationSearch").addEventListener("input", (event) => {
        state.search = event.target.value.trim().toLowerCase();
        renderViolationTable();
    });
}

function switchMode(mode) {
    state.mode = mode;
    $$(".segment").forEach((button) => button.classList.toggle("active", button.dataset.mode === mode));
    $$("[data-input-panel]").forEach((panel) => {
        panel.classList.toggle("active", panel.dataset.inputPanel === mode);
    });
}

function bindDropZone(dropZone, input, extension, onSelect) {
    dropZone.addEventListener("click", () => input.click());
    input.addEventListener("change", () => {
        const [file] = input.files;
        if (file) onSelect(file);
    });

    ["dragenter", "dragover"].forEach((eventName) => {
        dropZone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropZone.classList.add("drag-over");
        });
    });

    ["dragleave", "drop"].forEach((eventName) => {
        dropZone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropZone.classList.remove("drag-over");
        });
    });

    dropZone.addEventListener("drop", (event) => {
        const [file] = event.dataTransfer.files;
        if (!file) return;
        if (!file.name.toLowerCase().endsWith(extension)) {
            showToast(`${extension} uzantılı bir dosya seçin.`);
            return;
        }
        onSelect(file);
    });
}

function selectPythonFile(file) {
    if (!file.name.toLowerCase().endsWith(".py")) {
        showToast("Yalnızca .py uzantılı Python dosyaları desteklenir.");
        return;
    }

    state.selectedFile = file;
    $("#fileAnalyze").disabled = false;
    $("#fileMeta").textContent = `${file.name} · ${formatBytes(file.size)}`;
}

function selectZipFile(file) {
    if (!file.name.toLowerCase().endsWith(".zip")) {
        showToast("Proje analizi için .zip arşivi seçin.");
        return;
    }

    state.selectedZip = file;
    $("#projectAnalyze").disabled = false;
    $("#zipMeta").textContent = `${file.name} · ${formatBytes(file.size)}`;
}

async function analyzePastedCode() {
    const code = $("#codeInput").value;
    if (!code.trim()) {
        showToast("Analiz için Python kodu girin.");
        return;
    }

    showLoading("Kod analiz ediliyor...");
    try {
        const data = await fetchJson("/api/v1/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ kaynak_kod: code }),
        });

        state.scopeType = "Kod Analizi";
        state.scopeName = "PastedCode.py";
        state.report = normalizeSingleReport(data.rapor, "PastedCode.py", code);
        renderReport();
    } catch (error) {
        showToast(error.message);
    } finally {
        hideLoading();
    }
}

async function analyzeSelectedFile() {
    if (!state.selectedFile) {
        showToast("Önce bir Python dosyası seçin.");
        return;
    }

    const formData = new FormData();
    formData.append("file", state.selectedFile);

    showLoading("Python dosyası analiz ediliyor...");
    try {
        const data = await fetchJson("/api/v1/analyze/file", {
            method: "POST",
            body: formData,
        });

        const filename = data.filename || state.selectedFile.name;
        state.scopeType = "Dosya Analizi";
        state.scopeName = filename;
        state.report = normalizeSingleReport(data.rapor, filename, data.content || "");
        renderReport();
    } catch (error) {
        showToast(error.message);
    } finally {
        hideLoading();
    }
}

async function analyzeSelectedProject() {
    if (!state.selectedZip) {
        showToast("Önce bir ZIP arşivi seçin.");
        return;
    }

    const formData = new FormData();
    formData.append("file", state.selectedZip);

    showLoading("Proje arşivi analiz ediliyor...");
    try {
        const data = await fetchJson("/api/v1/analyze/project", {
            method: "POST",
            body: formData,
        });

        state.scopeType = "Proje Analizi";
        state.scopeName = state.selectedZip.name;
        state.report = normalizeProjectReport(data.rapor, data.files || []);
        renderReport();
    } catch (error) {
        showToast(error.message);
    } finally {
        hideLoading();
    }
}

async function fetchJson(url, options) {
    const response = await fetch(url, options);
    let payload = null;

    try {
        payload = await response.json();
    } catch {
        payload = {};
    }

    if (!response.ok) {
        throw new Error(payload.detail || "İstek tamamlanamadı.");
    }

    return payload;
}

function normalizeSingleReport(report = {}, filename, content) {
    const fileReport = {
        ...report,
        violations: normalizeViolations(report.violations || [], filename),
    };

    const totalDebt = Number(report.technical_debt ?? sumDebt(fileReport.violations));

    return {
        dosya_sayisi: 1,
        toplam_satir: countLines(content),
        bakim_yapilabilirlik_ortalamasi: Number(report.bakim_yapilabilirlik_puani ?? 0),
        toplam_teknik_borc: totalDebt,
        quality_gate: report.quality_gate || inferGate(report.quality_grade, fileReport.violations),
        quality_grade: report.quality_grade || "A",
        violations: fileReport.violations,
        halstead_toplam: report.halstead || {},
        dosyalar: {
            [filename]: {
                content,
                report: {
                    ...fileReport,
                    technical_debt: totalDebt,
                },
            },
        },
    };
}

function normalizeProjectReport(report = {}, files = []) {
    const contentByPath = Object.fromEntries(files.map((file) => [file.path, file.content || ""]));
    const normalizedFiles = {};

    Object.entries(report.dosyalar || {}).forEach(([path, fileReport]) => {
        const content = contentByPath[path] || "";
        normalizedFiles[path] = {
            content,
            report: {
                ...fileReport,
                violations: normalizeViolations(fileReport.violations || [], path),
            },
        };
    });

    files.forEach((file) => {
        if (!normalizedFiles[file.path]) {
            normalizedFiles[file.path] = {
                content: file.content || "",
                report: {
                    bakim_yapilabilirlik_puani: 0,
                    technical_debt: 0,
                    violations: [],
                    karmasiklik: [],
                    lcom: [],
                },
            };
        }
    });

    const allViolations = normalizeViolations(report.violations || flattenFileViolations(normalizedFiles));
    const lineCount = Number(report.toplam_satir ?? Object.values(normalizedFiles).reduce((sum, file) => sum + countLines(file.content), 0));

    return {
        ...report,
        dosya_sayisi: Number(report.dosya_sayisi ?? Object.keys(normalizedFiles).length),
        toplam_satir: lineCount,
        bakim_yapilabilirlik_ortalamasi: Number(report.bakim_yapilabilirlik_ortalamasi ?? averageMaintainability(normalizedFiles)),
        toplam_teknik_borc: Number(report.toplam_teknik_borc ?? sumDebt(allViolations)),
        quality_gate: report.quality_gate || inferGate(report.quality_grade, allViolations),
        quality_grade: report.quality_grade || "A",
        violations: allViolations,
        halstead_toplam: report.halstead_toplam || {},
        dosyalar: normalizedFiles,
    };
}

function normalizeViolations(violations, fallbackFile = "PastedCode.py") {
    return violations.map((violation) => ({
        type: violation.type || "Bilinmeyen Kural",
        severity: violation.severity || "MINOR",
        line: Number(violation.line || 1),
        description: violation.description || "Açıklama bulunamadı.",
        cost_mins: Number(violation.cost_mins || 0),
        file: violation.file || fallbackFile,
    }));
}

function flattenFileViolations(files) {
    return Object.entries(files).flatMap(([path, file]) => normalizeViolations(file.report.violations || [], path));
}

function renderReport() {
    if (!state.report) return;

    $("#emptyState").hidden = true;
    $("#resultsShell").hidden = false;
    $("#scopeType").textContent = state.scopeType;
    $("#scopeName").textContent = state.scopeName;
    $("#scopeSummary").textContent = `${state.report.dosya_sayisi} dosya, ${formatNumber(state.report.toplam_satir)} satır, ${state.report.violations.length} bulgu analiz edildi.`;

    renderOverview();
    renderInspector();
    renderViolationTable();

    $("#resultsShell").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderOverview() {
    const report = state.report;
    const mi = clamp(Number(report.bakim_yapilabilirlik_ortalamasi || 0), 0, 100);
    const gate = report.quality_gate || "PASSED";
    const gateCard = $(".gate-card");

    gateCard.classList.toggle("passed", gate === "PASSED");
    gateCard.classList.toggle("failed", gate !== "PASSED");
    $("#gateValue").textContent = gate;
    $("#gateText").textContent = gate === "PASSED"
        ? "Kritik eşikler geçildi."
        : "Kritik bulgu veya düşük kalite skoru var.";

    $("#miValue").textContent = formatScore(mi);
    $("#gradeValue").textContent = report.quality_grade || "A";
    $("#gradeValue").className = `grade-chip grade-${String(report.quality_grade || "a").toLowerCase()}`;
    $("#miMeter").style.width = `${mi}%`;
    $("#debtValue").textContent = formatDebt(report.toplam_teknik_borc);
    $("#scopeValue").textContent = `${report.dosya_sayisi} dosya`;
    $("#linesValue").textContent = `${formatNumber(report.toplam_satir)} satır kod`;
    $("#totalViolations").textContent = `${report.violations.length} bulgu`;

    renderSeverityVisual(report.violations);
    renderIssueBars(report.violations);
    renderActionList(report.violations);
    renderFileHealth();
    renderMetricDetails();
}

function renderSeverityVisual(violations) {
    const container = $("#severityVisual");
    const counts = countBySeverity(violations);
    const total = Math.max(1, violations.length);
    const rows = [
        ["CRITICAL", "Kritik", counts.CRITICAL, "fill-critical"],
        ["MAJOR", "Majör", counts.MAJOR, "fill-major"],
        ["MINOR", "Minör", counts.MINOR, "fill-minor"],
    ];

    if (!violations.length) {
        container.innerHTML = `<div class="empty-mini">Kural ihlali bulunmadı. Kod sağlık görünümü temiz.</div>`;
        return;
    }

    container.innerHTML = rows.map(([, label, count, fillClass]) => {
        const width = Math.round((count / total) * 100);
        return `
            <div class="severity-line">
                <header><span>${label}</span><strong>${count}</strong></header>
                <div class="bar-track"><div class="bar-fill ${fillClass}" style="width:${width}%"></div></div>
            </div>
        `;
    }).join("");
}

function renderIssueBars(violations) {
    const container = $("#issueBars");
    if (!violations.length) {
        container.innerHTML = `<div class="empty-mini">Kod kokusu dağılımı için bulgu yok.</div>`;
        return;
    }

    const grouped = Object.entries(groupBy(violations, "type"))
        .map(([type, items]) => ({ type, count: items.length }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 6);

    const maxCount = Math.max(...grouped.map((item) => item.count), 1);
    container.innerHTML = grouped.map((item) => `
        <div class="issue-row">
            <header><span title="${escapeHtml(item.type)}">${escapeHtml(shortRuleName(item.type))}</span><strong>${item.count}</strong></header>
            <div class="bar-track"><div class="bar-fill fill-good" style="width:${Math.round((item.count / maxCount) * 100)}%"></div></div>
        </div>
    `).join("");
}

function renderActionList(violations) {
    const container = $("#actionList");
    if (!violations.length) {
        container.innerHTML = `<div class="empty-mini">Öncelikli refactoring aksiyonu gerekmiyor.</div>`;
        return;
    }

    const topItems = [...violations]
        .sort((a, b) => severityRank(b.severity) - severityRank(a.severity) || b.cost_mins - a.cost_mins || a.line - b.line)
        .slice(0, 5);

    container.innerHTML = topItems.map((violation) => {
        const advice = recommendationFor(violation);
        const severity = severityClass(violation.severity);
        return `
            <button class="action-item ${severity}" type="button" data-file="${escapeAttribute(violation.file)}" data-line="${violation.line}">
                <strong>
                    <span>${escapeHtml(advice.title)}</span>
                    <span>${displaySeverity(violation.severity)}</span>
                </strong>
                <p>${escapeHtml(advice.detail)}</p>
                <p>${escapeHtml(violation.file)} · satır ${violation.line} · ${formatDebt(violation.cost_mins)}</p>
            </button>
        `;
    }).join("");

    $$(".action-item", container).forEach((button) => {
        button.addEventListener("click", () => {
            selectFile(button.dataset.file);
            openResultTab("inspector");
            scrollToCodeLine(Number(button.dataset.line));
        });
    });
}

function renderFileHealth() {
    const container = $("#fileHealthList");
    const files = getFileEntries()
        .sort((a, b) => (b.report.violations.length - a.report.violations.length) || (a.report.bakim_yapilabilirlik_puani - b.report.bakim_yapilabilirlik_puani))
        .slice(0, 8);

    if (!files.length) {
        container.innerHTML = `<div class="empty-mini">Dosya bilgisi bulunamadı.</div>`;
        return;
    }

    container.innerHTML = files.map(({ path, report }) => {
        const mi = clamp(Number(report.bakim_yapilabilirlik_puani || 0), 0, 100);
        return `
            <div class="file-health-row">
                <header>
                    <span class="file-path" title="${escapeHtml(path)}">${escapeHtml(path)}</span>
                    <strong>${formatScore(mi)} MI</strong>
                </header>
                <div class="bar-track"><div class="bar-fill ${mi >= 70 ? "fill-good" : mi >= 45 ? "fill-major" : "fill-critical"}" style="width:${mi}%"></div></div>
                <header>
                    <span>${report.violations.length} bulgu</span>
                    <span>${formatDebt(report.technical_debt || sumDebt(report.violations))}</span>
                </header>
            </div>
        `;
    }).join("");
}

function renderMetricDetails() {
    const h = state.report.halstead_toplam || {};
    const lcomClasses = getFileEntries().flatMap(({ report }) => report.lcom || []);

    $("#hVocabulary").textContent = formatNumber(h.vocabulary || 0);
    $("#hLength").textContent = formatNumber(h.length || 0);
    $("#hVolume").textContent = formatNumber(h.volume || 0);
    $("#hDifficulty").textContent = formatNumber(h.difficulty || 0);
    $("#hEffort").textContent = formatNumber(Math.round(h.effort || 0));
    $("#hTime").textContent = `${formatNumber(Math.round(h.time || 0))} sn`;
    $("#hBugs").textContent = Number(h.bugs || 0).toFixed(3);
    $("#lcomCount").textContent = String(lcomClasses.length);
}

function renderInspector() {
    const entries = getFileEntries();
    $("#fileCountLabel").textContent = String(entries.length);
    $("#fileButtons").innerHTML = entries.map(({ path, report }) => `
        <button class="file-button" type="button" data-file="${escapeAttribute(path)}">
            <strong title="${escapeHtml(path)}">${escapeHtml(path)}</strong>
            <span>MI ${formatScore(report.bakim_yapilabilirlik_puani || 0)} · ${report.violations.length} bulgu</span>
        </button>
    `).join("");

    $$(".file-button", $("#fileButtons")).forEach((button) => {
        button.addEventListener("click", () => selectFile(button.dataset.file));
    });

    const preferred = state.activeFile && state.report.dosyalar[state.activeFile]
        ? state.activeFile
        : entries[0]?.path;

    if (preferred) {
        selectFile(preferred, { preserveTab: true });
    }
}

function selectFile(path, options = {}) {
    const file = state.report?.dosyalar?.[path];
    if (!file) return;

    state.activeFile = path;

    $$(".file-button", $("#fileButtons")).forEach((button) => {
        button.classList.toggle("active", button.dataset.file === path);
    });

    const report = file.report;
    const content = file.content || "";
    const lineCount = countLines(content);
    const debt = report.technical_debt || sumDebt(report.violations || []);

    $("#activeFilePath").textContent = path;
    $("#activeFileMeta").textContent = `${lineCount} satır · ${report.violations.length} bulgu`;
    $("#activeFileMi").textContent = `MI ${formatScore(report.bakim_yapilabilirlik_puani || 0)}`;
    $("#activeFileDebt").textContent = formatDebt(debt);
    $("#activeViolationCount").textContent = String(report.violations.length);

    renderCodeViewer(content, report.violations || []);
    renderFileViolations(path, report.violations || []);

    if (!options.preserveTab) {
        openResultTab("inspector");
    }
}

function renderCodeViewer(content, violations) {
    const viewer = $("#codeViewer");
    const byLine = groupBy(violations, "line");
    const lines = content.split(/\r\n|\n|\r/);

    viewer.innerHTML = lines.map((line, index) => {
        const lineNumber = index + 1;
        const lineViolations = byLine[lineNumber] || [];
        const highest = highestSeverity(lineViolations);
        const hasIssue = lineViolations.length > 0;
        const classes = ["code-line", hasIssue ? "has-issue" : "", highest ? severityClass(highest) : ""].filter(Boolean).join(" ");

        return `
            <div class="${classes}" id="code-line-${lineNumber}">
                <span class="num">${lineNumber}</span>
                <mark class="txt">${escapeHtml(line) || " "}</mark>
            </div>
        `;
    }).join("");
}

function renderFileViolations(path, violations) {
    const container = $("#fileViolations");

    if (!violations.length) {
        container.innerHTML = `<div class="empty-mini">Bu dosyada ihlal bulunmadı.</div>`;
        return;
    }

    container.innerHTML = [...violations]
        .sort((a, b) => a.line - b.line)
        .map((violation) => `
            <button class="file-finding ${severityClass(violation.severity)}" type="button" data-line="${violation.line}">
                <strong>${escapeHtml(shortRuleName(violation.type))}</strong>
                <small>${displaySeverity(violation.severity)} · satır ${violation.line} · ${formatDebt(violation.cost_mins)}</small>
                <small>${escapeHtml(violation.description)}</small>
            </button>
        `).join("");

    $$(".file-finding", container).forEach((button) => {
        button.addEventListener("click", () => scrollToCodeLine(Number(button.dataset.line)));
    });
}

function renderViolationTable() {
    if (!state.report) return;

    const body = $("#violationTableBody");
    const filtered = state.report.violations.filter((violation) => {
        const severityMatch = state.severityFilter === "ALL" || violation.severity === state.severityFilter;
        const haystack = `${violation.type} ${violation.file} ${violation.description}`.toLowerCase();
        const searchMatch = !state.search || haystack.includes(state.search);
        return severityMatch && searchMatch;
    });

    if (!filtered.length) {
        body.innerHTML = `<tr><td colspan="6" class="empty-row">Filtreyle eşleşen bulgu yok.</td></tr>`;
        return;
    }

    body.innerHTML = filtered
        .sort((a, b) => severityRank(b.severity) - severityRank(a.severity) || String(a.file).localeCompare(String(b.file)) || a.line - b.line)
        .map((violation) => `
            <tr>
                <td><span class="severity-badge ${severityClass(violation.severity)}">${displaySeverity(violation.severity)}</span></td>
                <td><strong>${escapeHtml(shortRuleName(violation.type))}</strong></td>
                <td class="file-path" title="${escapeHtml(violation.file)}">${escapeHtml(violation.file)}</td>
                <td>${violation.line}</td>
                <td>${escapeHtml(violation.description)}</td>
                <td>${formatDebt(violation.cost_mins)}</td>
            </tr>
        `).join("");
}

function openResultTab(tabName) {
    const button = $(`[data-result-tab="${tabName}"]`);
    if (!button) return;
    button.click();
}

function scrollToCodeLine(line) {
    requestAnimationFrame(() => {
        const target = $(`#code-line-${line}`);
        if (!target) return;

        target.scrollIntoView({ behavior: "smooth", block: "center" });
        target.animate(
            [
                { backgroundColor: "rgba(94, 234, 212, 0.22)" },
                { backgroundColor: "rgba(255, 255, 255, 0.045)" },
            ],
            { duration: 850, easing: "ease-out" },
        );
    });
}

function exportJsonReport() {
    if (!state.report) return;

    const payload = {
        proje: state.scopeName,
        tur: state.scopeType,
        olusturulma_zamani: new Date().toISOString(),
        rapor: state.report,
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "clean-code-analiz-raporu.json";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
}

function getFileEntries() {
    return Object.entries(state.report?.dosyalar || {}).map(([path, file]) => ({
        path,
        content: file.content || "",
        report: {
            technical_debt: 0,
            violations: [],
            karmasiklik: [],
            lcom: [],
            ...file.report,
            violations: normalizeViolations(file.report?.violations || [], path),
        },
    }));
}

function countBySeverity(violations) {
    return violations.reduce((acc, violation) => {
        acc[violation.severity] = (acc[violation.severity] || 0) + 1;
        return acc;
    }, { CRITICAL: 0, MAJOR: 0, MINOR: 0 });
}

function groupBy(items, key) {
    return items.reduce((acc, item) => {
        const value = item[key];
        acc[value] = acc[value] || [];
        acc[value].push(item);
        return acc;
    }, {});
}

function recommendationFor(violation) {
    const type = violation.type.toLowerCase();

    if (type.includes("syntax")) {
        return {
            title: "Sözdizimini düzelt",
            detail: "Syntax hatası giderilmeden diğer metrikler güvenilir şekilde yorumlanamaz.",
        };
    }

    if (type.includes("god class")) {
        return {
            title: "Sınıfı sorumluluklara ayır",
            detail: "Yüksek LOC ve düşük cohesion sınıfın birden fazla rol taşıdığını gösteriyor.",
        };
    }

    if (type.includes("long method")) {
        return {
            title: "Metodu küçük adımlara böl",
            detail: "Uzun metodun iş akışını anlamlı yardımcı fonksiyonlara taşıyın.",
        };
    }

    if (type.includes("mccabe") || type.includes("karma")) {
        return {
            title: "Dallanmayı sadeleştir",
            detail: "Koşulları erken dönüş, strateji veya küçük fonksiyonlarla azaltın.",
        };
    }

    if (type.includes("argument") || type.includes("parametre")) {
        return {
            title: "Parametre nesnesi tasarla",
            detail: "Birlikte taşınan parametreleri anlamlı bir veri yapısında gruplayın.",
        };
    }

    if (type.includes("feature envy")) {
        return {
            title: "Davranışı doğru nesneye taşı",
            detail: "Metot başka nesnenin verisini yoğun kullanıyorsa davranış o nesneye yaklaşmalı.",
        };
    }

    if (type.includes("unused") || type.includes("gereksiz")) {
        return {
            title: "Kullanılmayan kodu temizle",
            detail: "Gereksiz import ve değişkenleri kaldırarak okuma yükünü azaltın.",
        };
    }

    if (type.includes("duplicate") || type.includes("kopya")) {
        return {
            title: "Tekrarlı bloğu ortaklaştır",
            detail: "Aynı blokları ortak fonksiyon veya sınıf sorumluluğuna çekin.",
        };
    }

    return {
        title: "Bulguyu refactoring kuyruğuna al",
        detail: "Kural ihlalinin etkisini dosya bağlamında inceleyip küçük bir düzeltme planlayın.",
    };
}

function shortRuleName(rule) {
    return String(rule)
        .replace("Ä°", "İ")
        .replace("ÅŸ", "ş")
        .replace("Ä±", "ı")
        .replace("Ã§", "ç")
        .replace("Ã¼", "ü")
        .replace("Ã¶", "ö")
        .replace("ÄŸ", "ğ");
}

function highestSeverity(violations) {
    if (!violations.length) return null;
    return violations.reduce((highest, violation) => (
        severityRank(violation.severity) > severityRank(highest) ? violation.severity : highest
    ), "MINOR");
}

function severityRank(severity) {
    return { CRITICAL: 3, MAJOR: 2, MINOR: 1 }[severity] || 0;
}

function severityClass(severity) {
    return String(severity || "MINOR").toLowerCase();
}

function displaySeverity(severity) {
    return {
        CRITICAL: "Kritik",
        MAJOR: "Majör",
        MINOR: "Minör",
    }[severity] || severity;
}

function inferGate(grade, violations) {
    const hasCritical = violations.some((violation) => violation.severity === "CRITICAL");
    return hasCritical || ["D", "F"].includes(grade) ? "FAILED" : "PASSED";
}

function averageMaintainability(files) {
    const scores = Object.values(files).map((file) => Number(file.report.bakim_yapilabilirlik_puani || 0));
    if (!scores.length) return 0;
    return scores.reduce((sum, score) => sum + score, 0) / scores.length;
}

function sumDebt(violations) {
    return violations.reduce((sum, violation) => sum + Number(violation.cost_mins || 0), 0);
}

function countLines(content) {
    if (!content) return 0;
    return content.split(/\r\n|\n|\r/).length;
}

function formatDebt(minutes) {
    const value = Math.max(0, Math.round(Number(minutes || 0)));
    if (value < 60) return `${value} dk`;
    const hours = Math.floor(value / 60);
    const remaining = value % 60;
    return remaining ? `${hours} sa ${remaining} dk` : `${hours} sa`;
}

function formatBytes(bytes) {
    const value = Number(bytes || 0);
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
    return `${(value / (1024 * 1024)).toFixed(2)} MB`;
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString("tr-TR");
}

function formatScore(value) {
    return Number(value || 0).toLocaleString("tr-TR", { maximumFractionDigits: 1 });
}

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
    return escapeHtml(value).replaceAll("`", "&#096;");
}

function showLoading(text) {
    $("#loadingText").textContent = text;
    $("#loadingOverlay").hidden = false;
}

function hideLoading() {
    $("#loadingOverlay").hidden = true;
}

let toastTimer = null;
function showToast(message) {
    const toast = $("#toast");
    toast.textContent = message || "İşlem tamamlanamadı.";
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 3200);
}
