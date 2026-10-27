/**
 * Sof mantiq: sanalar, eslatmalar jadvali, kiruvchi so'rovni tekshirish va xat matnlari.
 * Bu faylda Apps Script xizmatlari ishlatilmaydi, shuning uchun u Node'da testlanadi.
 */

var UZ_MONTHS = ['Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
  'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr'];

// ---------- Sanalar ----------

/** 'YYYY-MM-DD' -> {y, m, d}; noto'g'ri yoki mavjud bo'lmagan sana uchun null. */
function parseIsoDate(s) {
  var match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(s || '').trim());
  if (!match) return null;
  var y = Number(match[1]), m = Number(match[2]), d = Number(match[3]);
  var t = new Date(Date.UTC(y, m - 1, d));
  if (t.getUTCFullYear() !== y || t.getUTCMonth() !== m - 1 || t.getUTCDate() !== d) return null;
  return { y: y, m: m, d: d };
}

function ymdKey(ymd) {
  return ymd.y + '-' + pad2(ymd.m) + '-' + pad2(ymd.d);
}

function ymdText(ymd) {
  return pad2(ymd.d) + '.' + pad2(ymd.m) + '.' + ymd.y;
}

function pad2(n) {
  return (n < 10 ? '0' : '') + n;
}

/** from -> to oralig'idagi kunlar soni (to keyin bo'lsa musbat). */
function daysBetween(from, to) {
  return Math.round((Date.UTC(to.y, to.m - 1, to.d) - Date.UTC(from.y, from.m - 1, from.d)) / 86400000);
}

/** Reyestrdagi ko'rinish: "12-oktabrga qadar". */
function formatDueText(ymd) {
  return ymd.d + '-' + UZ_MONTHS[ymd.m - 1].toLowerCase() + 'ga qadar';
}

/** Reyestr varag'i nomi: "Oktabr 2026". */
function monthSheetName(ymd) {
  return UZ_MONTHS[ymd.m - 1] + ' ' + ymd.y;
}

function isMonthSheetName(name) {
  return new RegExp('^(' + UZ_MONTHS.join('|') + ') \\d{4}$').test(String(name));
}

/** "Ijro muddati" ustuni: sana bo'lsa "12-oktabrga qadar", aks holda hujjatdagi matn. */
function dueDisplay(dueDate, dueText) {
  if (dueDate) return formatDueText(dueDate);
  return dueText || '';
}

// ---------- Eslatmalar ----------
// Holat reyestrning "Eslatmalar" ustunida saqlanadi: "2026-10-12|R,7,3".
// R — ro'yxatga olish xati, 7/3/1/0 — muddatgacha qolgan kunlar bo'yicha eslatmalar,
// X — muddat o'tgani haqidagi xat.

function parseReminderState(str) {
  var parts = String(str || '').split('|');
  return {
    due: parts.length > 1 ? parts[0] : '',
    tags: (parts.length > 1 ? parts[1] : parts[0]).split(',').filter(Boolean)
  };
}

function serializeReminderState(state) {
  return state.due + '|' + state.tags.join(',');
}

/**
 * Ro'yxatga olish paytidagi holat. Ro'yxatga olish xati shu kunning o'zida
 * borgani uchun bugungi va undan oldingi bosqichlar bajarilgan hisoblanadi
 * (masalan, muddatgacha 5 kun qolgan bo'lsa, "7 kun" eslatmasi yuborilmaydi).
 */
function initialReminderState(dueKey, daysLeft, milestones) {
  var tags = ['R'];
  milestones.forEach(function (m) {
    if (m >= daysLeft) tags.push(String(m));
  });
  if (daysLeft < 0) tags.push('X');
  return serializeReminderState({ due: dueKey, tags: tags });
}

/**
 * Bugun nima yuborish kerakligini aniqlaydi.
 * Natija: {kind: 'none' | 'reminder' | 'overdue', state: '...', changed: bool}.
 * Bir kun o'tkazib yuborilgan bo'lsa ham eng yaqin bosqich bir marta yuboriladi.
 */
function planReminder(stateStr, dueKey, daysLeft, milestones) {
  var st = parseReminderState(stateStr);
  var before = serializeReminderState(st);
  if (st.due !== dueKey) {
    // Muddat o'zgartirilgan (yoki holat yo'q): o'tib ketgan bosqichlarni qayta
    // yubormaymiz, bugungi bosqich esa yangi muddat haqida xabar beradi.
    var tags = st.tags.indexOf('R') >= 0 ? ['R'] : [];
    milestones.forEach(function (m) {
      if (m > daysLeft) tags.push(String(m));
    });
    st = { due: dueKey, tags: tags };
  }
  var kind = 'none';
  if (daysLeft < 0) {
    if (st.tags.indexOf('X') < 0) {
      st.tags.push('X');
      kind = 'overdue';
    }
  } else {
    var due = milestones.filter(function (m) {
      return daysLeft <= m && st.tags.indexOf(String(m)) < 0;
    });
    if (due.length) {
      var current = Math.min.apply(null, due);
      milestones.forEach(function (m) {
        if (m >= current && st.tags.indexOf(String(m)) < 0) st.tags.push(String(m));
      });
      kind = 'reminder';
    }
  }
  var after = serializeReminderState(st);
  return { kind: kind, state: after, changed: after !== before };
}

// ---------- Manzillar va ro'yxatlar ----------

var EMAIL_RE = /^[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+$/;

function isValidEmail(s) {
  return EMAIL_RE.test(String(s || '').trim());
}

/** "a@x.uz, b@y.uz; c@z.uz" -> to'g'ri, takrorlanmagan manzillar. */
function splitEmails(s) {
  var out = [];
  String(s || '').split(/[\s,;]+/).forEach(function (e) {
    e = e.trim().toLowerCase();
    if (isValidEmail(e) && out.indexOf(e) < 0) out.push(e);
  });
  return out;
}

/** Vergul/nuqtali vergul/yangi qator bilan ajratilgan ro'yxat. */
function splitList(s) {
  return String(s || '').split(/[,;\n]+/).map(function (x) { return x.trim(); }).filter(Boolean);
}

// ---------- Kompyuterdagi ilovadan kelgan so'rovni tekshirish ----------

var MAX_TEXT = 5000;

/**
 * doc: {regNo, regDate: 'YYYY-MM-DD', outNo, resolution, dueDate: 'YYYY-MM-DD'|null,
 *       dueText, summary, emails: []}
 * Natija: {errors: [], value: {...}} — value faqat xato bo'lmasa ishlatiladi.
 */
function validateRegistration(doc) {
  doc = doc || {};
  function text(v) {
    return v === null || v === undefined ? '' : String(v).trim().slice(0, MAX_TEXT);
  }
  var errors = [];
  var value = {
    regNo: text(doc.regNo),
    regDate: parseIsoDate(doc.regDate),
    outNo: text(doc.outNo),
    resolution: text(doc.resolution),
    dueDate: doc.dueDate ? parseIsoDate(doc.dueDate) : null,
    dueText: text(doc.dueText),
    summary: text(doc.summary),
    emails: []
  };
  if (!value.regNo) errors.push("Ro'yxat raqami bo'sh");
  if (!value.regDate) errors.push("Ro'yxat sanasi bo'sh yoki noto'g'ri");
  if (!value.resolution) errors.push("Rezolyutsiya bo'sh");
  if (!value.summary) errors.push("Qisqacha mazmun bo'sh");
  if (doc.dueDate && !value.dueDate) errors.push("Muddat sanasi noto'g'ri");
  var rawEmails = Array.isArray(doc.emails) ? doc.emails : [];
  rawEmails.forEach(function (e) {
    var t = String(e || '').trim().toLowerCase();
    if (!isValidEmail(t)) errors.push("Noto'g'ri email: " + t);
    else if (value.emails.indexOf(t) < 0) value.emails.push(t);
  });
  if (!value.emails.length) errors.push("Ijrochilar emaili ko'rsatilmagan");
  return { errors: errors, value: value };
}

// ---------- Xat matnlari ----------

function escapeHtml(s) {
  return String(s === null || s === undefined ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/** entry: {regNo, regDateText, outNo, resolution, dueText, summary} */
function mailDetails(entry) {
  return [
    ["Ro'yxatga olingan raqami", entry.regNo],
    ["Ro'yxatga olingan sana", entry.regDateText],
    ['Chiqish raqami', entry.outNo],
    ['Rezolyutsiya', entry.resolution],
    ['Ijro muddati', entry.dueText],
    ['Hujjatning qisqacha mazmuni', entry.summary]
  ];
}

function renderMail(subject, intro, entry, link, attached) {
  var rows = mailDetails(entry);
  var html = '<p>Assalomu alaykum!</p><p>' + escapeHtml(intro) + '</p>' +
    '<table style="border-collapse:collapse" cellpadding="6">' +
    rows.map(function (r) {
      return '<tr><td style="border:1px solid #ccc;background:#f3f3f3"><b>' + escapeHtml(r[0]) +
        '</b></td><td style="border:1px solid #ccc">' + escapeHtml(r[1] || '—').replace(/\n/g, '<br>') + '</td></tr>';
    }).join('') + '</table>' +
    (attached ? '<p>Hujjat ilova qilingan.</p>' : '') +
    '<p>Ijro natijasini jadvaldagi <b>"Ijrosi haqida qisqacha ma\'lumot"</b> ustuniga yozing: ' +
    '<a href="' + escapeHtml(link) + '">jadvalni ochish</a></p>' +
    '<p style="color:#888">Bu xat avtomatik yuborildi. Savollar bo\'lsa, shu xatga javob yozing.</p>';
  var text = 'Assalomu alaykum!\n\n' + intro + '\n\n' +
    rows.map(function (r) { return r[0] + ': ' + (r[1] || '—'); }).join('\n') + '\n\n' +
    (attached ? 'Hujjat ilova qilingan.\n' : '') +
    "Ijro natijasini jadvaldagi \"Ijrosi haqida qisqacha ma'lumot\" ustuniga yozing: " + link + '\n\n' +
    "Bu xat avtomatik yuborildi. Savollar bo'lsa, shu xatga javob yozing.";
  return { subject: subject, html: html, text: text };
}

function buildRegistrationMail(entry, link, attached) {
  return renderMail(
    'Yangi topshiriq: ' + entry.regNo + (entry.dueText ? ' (muddat: ' + entry.dueText + ')' : ''),
    'Sizga ijro uchun hujjat yuborildi.',
    entry, link, attached);
}

function buildReminderMail(entry, daysLeft, link) {
  var when = daysLeft === 0 ? 'muddat bugun' : daysLeft === 1 ? 'muddat ertaga' : 'muddatga ' + daysLeft + ' kun qoldi';
  return renderMail(
    'Eslatma: ' + entry.regNo + ' — ' + when,
    'Quyidagi hujjat bo\'yicha ijro muddati yaqinlashmoqda (' + when + '). ' +
    'Ijro ta\'minlangan bo\'lsa, jadvalga ma\'lumot kiriting.',
    entry, link, false);
}

function buildOverdueMail(entry, daysLate, link) {
  return renderMail(
    'Muddati o\'tdi: ' + entry.regNo + ' (muddat: ' + entry.dueText + ')',
    'Quyidagi hujjat bo\'yicha ijro muddati ' + daysLate + ' kun oldin o\'tib ketdi. ' +
    'Ijro holati haqida zudlik bilan ma\'lumot kiriting.',
    entry, link, false);
}

/** Token solishtirish (uzunlik va har bir belgi; vaqt bo'yicha farqni kamaytiradi). */
function safeEqual(a, b) {
  a = String(a || '');
  b = String(b || '');
  if (!a || a.length !== b.length) return false;
  var diff = 0;
  for (var i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}
