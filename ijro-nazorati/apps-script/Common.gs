/**
 * Umumiy yordamchilar: xususiyatlar, reyestrni ochish, sozlamalar, jurnal, sanalar va xat yuborish.
 */

function prop_(key) {
  var v = PropertiesService.getScriptProperties().getProperty(key);
  if (!v) throw new Error(key + " topilmadi — avval setup() ni ishga tushiring");
  return v;
}

function registrySs_() {
  return SpreadsheetApp.openById(prop_(PROP.REGISTRY_SS_ID));
}

function isYes_(v) {
  return /^(ha|да|yes|1|true)$/i.test(String(v).trim());
}

/** "Sozlamalar" varag'idan o'qiladi; bo'sh qiymat standart qiymat bilan almashtiriladi. */
function readSettings_(registry) {
  var raw = {};
  SETTINGS_DEFAULTS.forEach(function (d) { raw[d[0]] = d[1]; });
  var sh = registry.getSheetByName(CFG.SHEET_SETTINGS);
  if (sh && sh.getLastRow() > 1) {
    sh.getRange(2, 1, sh.getLastRow() - 1, 2).getValues().forEach(function (r) {
      var key = String(r[0]).trim();
      if (key && raw.hasOwnProperty(key) && String(r[1]).trim() !== '') raw[key] = String(r[1]);
    });
  }
  return {
    staff: splitEmails(raw['Xodimlar']),
    corpMail: splitEmails(raw['Korporativ pochta']),
    managerMail: splitEmails(raw['Rahbar pochtasi']),
    senderName: String(raw["Jo'natuvchi nomi"]).trim(),
    statusValues: splitList(raw['Ijro holati qiymatlari']),
    doneStatuses: splitList(raw['Yakunlangan holatlar']).map(function (s) { return s.toLowerCase(); }),
    autoShare: isYes_(raw['Ijrochilarga avtomatik ruxsat']),
    title: String(raw['Jadval sarlavhasi'])
  };
}

function logEvent_(registry, event, docRef, details) {
  try {
    registry.getSheetByName(CFG.SHEET_LOG).appendRow([new Date(), event, docRef || '', details || '']);
  } catch (err) {
    console.error("Jurnalga yozib bo'lmadi: " + err);
  }
}

// ---------- Sanalar (jadval va skript Asia/Tashkent vaqt zonasida) ----------

function todayYmd_() {
  return parseIsoDate(Utilities.formatDate(new Date(), CFG.TIMEZONE, 'yyyy-MM-dd'));
}

/** Katakdagi qiymat (Date yoki "dd.MM.yyyy"/"yyyy-MM-dd" matni) -> ymd yoki null. */
function cellToYmd_(v) {
  if (v instanceof Date && !isNaN(v.getTime())) {
    return parseIsoDate(Utilities.formatDate(v, CFG.TIMEZONE, 'yyyy-MM-dd'));
  }
  var s = String(v || '').trim();
  var m = /^(\d{1,2})\.(\d{1,2})\.(\d{4})$/.exec(s);
  if (m) return parseIsoDate(m[3] + '-' + pad2(Number(m[2])) + '-' + pad2(Number(m[1])));
  return parseIsoDate(s);
}

function ymdToDate_(ymd) {
  return ymd ? new Date(ymd.y, ymd.m - 1, ymd.d) : '';
}

// ---------- Pochta ----------

/** mail: {subject, html, text}. */
function sendMail_(settings, to, cc, mail, attachments) {
  cc = cc.filter(function (e, i) { return to.indexOf(e) < 0 && cc.indexOf(e) === i; });
  var recipients = to.length + cc.length;
  if (MailApp.getRemainingDailyQuota() < recipients) {
    throw new Error('Kunlik pochta limiti tugadi — xat ertaga qayta yuboriladi');
  }
  var msg = {
    to: to.join(','),
    subject: mail.subject,
    body: mail.text,
    htmlBody: mail.html,
    name: settings.senderName || 'Ijro nazorati'
  };
  if (cc.length) msg.cc = cc.join(',');
  if (settings.corpMail.length) msg.replyTo = settings.corpMail[0];
  if (attachments && attachments.length) msg.attachments = attachments;
  MailApp.sendEmail(msg);
}

/** Reyestrdagi qatorga havola (ijrochi to'g'ridan-to'g'ri I ustuniga tushadi). */
function registryRowLink_(registry, sheet, row) {
  return registry.getUrl().replace(/\/edit.*$/, '') + '/edit#gid=' + sheet.getSheetId() + '&range=I' + row;
}
