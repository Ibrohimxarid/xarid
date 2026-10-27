// Apps Script xizmatlarining xotiradagi soddalashtirilgan nusxalari (faqat testlar uchun).
// Formatlash metodlari hech narsa qilmaydi; qiymatlar, qatorlar soni va chegaralar esa haqiqiydek.

/** Noma'lum metodlar `this` qaytaradi — formatlash zanjirlari uchun. */
function chainable(obj) {
  const proxy = new Proxy(obj, {
    get(t, p) {
      if (p in t) return t[p];
      if (typeof p === 'symbol') return undefined;
      return () => proxy;
    }
  });
  return proxy;
}

let nextId = 1;

class FakeSheet {
  constructor(ss, name) {
    this.ss = ss; this.name = name; this.id = nextId++; this.rows = []; this.maxRows = 1000;
    this.protections = []; this.validation = null;
    return chainable(this);
  }
  cell(r, c) { return (this.rows[r - 1] || [])[c - 1] ?? ''; }
  put(r, c, v) { (this.rows[r - 1] ||= [])[c - 1] = v; }
  getRange(row, col, nr = 1, nc = 1) {
    if (row < 1 || col < 1 || row + nr - 1 > this.maxRows) {
      throw new Error(`Range out of bounds: rows ${row}..${row + nr - 1} of ${this.maxRows}`);
    }
    return new FakeRange(this, row, col, nr, nc);
  }
  getLastRow() {
    for (let i = this.rows.length; i > 0; i--) {
      if ((this.rows[i - 1] || []).some(v => v !== '' && v !== undefined && v !== null)) return i;
    }
    return 0;
  }
  appendRow(values) { this.getRange(this.getLastRow() + 1, 1, 1, values.length).setValues([values]); }
  getMaxRows() { return this.maxRows; }
  getName() { return this.name; }
  setName(n) { this.name = n; return this; }
  getSheetId() { return this.id; }
  getParent() { return this.ss; }
  getProtections() { return this.protections.slice(); }
  protect() {
    const sheet = this;
    const p = chainable({
      unprotected: [], editors: [],
      remove() { sheet.protections = sheet.protections.filter(x => x !== p); },
      setUnprotectedRanges(r) { p.unprotected = r; return p; },
      getEditors() { return p.editors.slice(); },
      addEditor(u) { p.editors.push(typeof u === 'string' ? u : u.getEmail()); return p; },
      addEditors(list) { list.forEach(e => p.editors.push(e)); return p; },
      removeEditors(list) { p.editors = p.editors.filter(e => e === 'bot@gmail.com' || !list.includes(e)); return p; },
      canDomainEdit: () => false
    });
    this.protections.push(p);
    return p;
  }
}

class FakeRange {
  constructor(sheet, row, col, nr, nc) {
    this.sheet = sheet; this.row = row; this.col = col; this.nr = nr; this.nc = nc;
    return chainable(this);
  }
  getValues() {
    return Array.from({ length: this.nr }, (_, i) =>
      Array.from({ length: this.nc }, (_, j) => this.sheet.cell(this.row + i, this.col + j)));
  }
  setValues(v) {
    if (v.length !== this.nr || v.some(r => r.length !== this.nc)) throw new Error('setValues: dimensions mismatch');
    v.forEach((r, i) => r.forEach((x, j) => this.sheet.put(this.row + i, this.col + j, x)));
    return this;
  }
  getValue() { return this.sheet.cell(this.row, this.col); }
  setValue(v) { this.sheet.put(this.row, this.col, v); return this; }
  setDataValidation(rule) { this.sheet.validation = rule; return this; }
  getRow() { return this.row; }
  getColumn() { return this.col; }
}

class FakeSpreadsheet {
  constructor(name) { this.name = name; this.id = 'ss' + nextId++; this.sheets = [new FakeSheet(this, 'Sheet1')]; this.editors = []; }
  getId() { return this.id; }
  getUrl() { return `https://docs.google.com/spreadsheets/d/${this.id}/edit`; }
  getSheets() { return this.sheets.slice(); }
  getSheetByName(n) { return this.sheets.find(s => s.name === n) || null; }
  insertSheet(n, idx) { const s = new FakeSheet(this, n); this.sheets.splice(idx ?? this.sheets.length, 0, s); return s; }
  setSpreadsheetTimeZone() {}
  getEditors() { return this.editors.map(e => ({ getEmail: () => e })); }
  addEditor(e) {
    if (e.endsWith('@nogoogle.uz')) throw new Error('Invalid email');
    this.editors.push(e);
  }
}

function makeEnv() {
  const spreadsheets = new Map();
  const props = new Map();
  const sent = [];
  const triggers = [];
  let quota = 100;

  const folder = { getFoldersByName: () => ({ hasNext: () => false }) };
  const globals = {
    console: { log() {}, warn() {}, error: (...a) => { throw new Error(a.join(' ')); } },
    Session: { getEffectiveUser: () => ({ getEmail: () => 'bot@gmail.com' }) },
    LockService: { getScriptLock: () => ({ tryLock: () => true, waitLock() {}, releaseLock() {} }) },
    PropertiesService: {
      getScriptProperties: () => ({
        getProperty: (k) => (props.has(k) ? props.get(k) : null),
        setProperty: (k, v) => props.set(k, v),
        deleteProperty: (k) => props.delete(k)
      })
    },
    Utilities: {
      formatDate: (d, tz, fmt) => {
        if (fmt !== 'yyyy-MM-dd') throw new Error('unsupported format ' + fmt);
        return new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' }).format(d);
      },
      getUuid: () => require('node:crypto').randomUUID(),
      base64Decode: (s) => [...Buffer.from(s, 'base64')],
      newBlob: (bytes, mime, name) => ({ bytes, mime, name })
    },
    ContentService: {
      MimeType: { JSON: 'json' },
      createTextOutput: (text) => {
        const out = { text, mime: 'text', setMimeType(m) { out.mime = m; return out; }, getContent: () => text };
        return out;
      }
    },
    SpreadsheetApp: {
      ProtectionType: { SHEET: 'SHEET' },
      create: (name) => { const ss = new FakeSpreadsheet(name); spreadsheets.set(ss.id, ss); return ss; },
      openById: (id) => spreadsheets.get(id),
      newDataValidation: () => {
        const b = chainable({ values: null, requireValueInList(v) { b.values = v; return b; }, build: () => ({ values: b.values }) });
        return b;
      }
    },
    DriveApp: {
      getRootFolder: () => folder,
      createFolder: () => folder,
      getFileById: () => ({ moveTo() {} })
    },
    MailApp: {
      sendEmail: (m) => { quota -= m.to.split(',').length + (m.cc ? m.cc.split(',').length : 0); sent.push(m); },
      getRemainingDailyQuota: () => quota
    },
    ScriptApp: {
      getProjectTriggers: () => triggers.slice(),
      deleteTrigger() {},
      newTrigger: (fn) => { const t = chainable({ create: () => { triggers.push(fn); return t; } }); return t; }
    }
  };

  return { globals, sent, triggers, props, spreadsheets, setQuota: (q) => { quota = q; } };
}

module.exports = { makeEnv };
