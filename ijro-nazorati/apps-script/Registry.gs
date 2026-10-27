/**
 * Reyestr: har oy uchun alohida varaq ("Oktabr 2026"), mavjud jadval formatida.
 * Varaq himoyalangan: xodimlar hammasini, ijrochilar faqat I ustunini o'zgartiradi.
 */

function getOrCreateMonthSheet_(registry, ymd, settings) {
  var name = monthSheetName(ymd);
  var sh = registry.getSheetByName(name);
  if (sh) return sh;
  // Oy varaqlari boshida, "Sozlamalar" va "Jurnal" oxirida turadi.
  var monthCount = registry.getSheets().filter(function (x) { return isMonthSheetName(x.getName()); }).length;
  sh = registry.insertSheet(name, monthCount);
  setupMonthSheet_(sh, ymd.y, settings);
  return sh;
}

function setupMonthSheet_(sh, year, settings) {
  var cols = RG_HEADERS.length;
  sh.getRange(1, 1, 2, RG.REPORT).merge()
    .setValue(settings.title.replace('{yil}', year))
    .setWrap(true).setFontWeight('bold').setFontSize(12)
    .setHorizontalAlignment('center').setVerticalAlignment('middle');
  sh.getRange(RG_HEADER_ROW, 1, 1, cols).setValues([RG_HEADERS])
    .setFontWeight('bold').setWrap(true).setBackground('#d9e1f2')
    .setHorizontalAlignment('center').setVerticalAlignment('middle');
  sh.getRange(RG_HEADER_ROW, RG.DUE_DATE, 1, cols - RG.DUE_DATE + 1)
    .setBackground('#eeeeee').setFontColor('#666666');
  sh.setFrozenRows(RG_HEADER_ROW);

  var widths = [40, 120, 100, 110, 160, 120, 360, 110, 300, 100, 200, 120, 140];
  widths.forEach(function (w, i) { sh.setColumnWidth(i + 1, w); });

  var rows = sh.getMaxRows() - RG_FIRST_ROW + 1;
  // Raqamlar matn sifatida saqlanadi (aks holda "26-2850" sana bo'lib qolishi mumkin).
  [RG.REG_NO, RG.OUT_NO, RG.DUE_TEXT].forEach(function (c) {
    sh.getRange(RG_FIRST_ROW, c, rows, 1).setNumberFormat('@');
  });
  [RG.REG_DATE, RG.DUE_DATE].forEach(function (c) {
    sh.getRange(RG_FIRST_ROW, c, rows, 1).setNumberFormat('dd.mm.yyyy');
  });
  sh.getRange(RG_FIRST_ROW, RG.REGISTERED_AT, rows, 1).setNumberFormat('dd.mm.yyyy hh:mm');
  sh.getRange(RG_FIRST_ROW, 1, rows, cols).setVerticalAlignment('top').setWrap(true);
  applyStatusDropdown_(sh, settings);
  sh.hideColumns(RG.REMINDERS, 2);
  protectMonthSheet_(sh, settings);
}

function applyStatusDropdown_(sh, settings) {
  if (!settings.statusValues.length) return;
  var rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(settings.statusValues, true)
    .setAllowInvalid(true)
    .build();
  sh.getRange(RG_FIRST_ROW, RG.STATUS, sh.getMaxRows() - RG_FIRST_ROW + 1, 1).setDataValidation(rule);
}

/** Varaq himoyasi: egasi + xodimlar; I ustuni (ma'lumot qatorlari) — hamma tahrirlovchilar uchun ochiq. */
function protectMonthSheet_(sh, settings) {
  sh.getProtections(SpreadsheetApp.ProtectionType.SHEET).forEach(function (p) { p.remove(); });
  var p = sh.protect().setDescription("Ijrochilar faqat \"Ijrosi haqida qisqacha ma'lumot\" ustunini o'zgartiradi");
  p.setUnprotectedRanges([sh.getRange(RG_FIRST_ROW, RG.REPORT, sh.getMaxRows() - RG_FIRST_ROW + 1, 1)]);
  p.addEditor(Session.getEffectiveUser());
  p.removeEditors(p.getEditors());
  if (p.canDomainEdit()) p.setDomainEdit(false);
  if (settings.staff.length) p.addEditors(settings.staff);
}

/** "Sozlamalar" va "Jurnal": faqat egasi va xodimlar o'zgartiradi. */
function protectServiceSheet_(sh, settings) {
  sh.getProtections(SpreadsheetApp.ProtectionType.SHEET).forEach(function (p) { p.remove(); });
  var p = sh.protect().setDescription('Faqat xodimlar');
  p.addEditor(Session.getEffectiveUser());
  p.removeEditors(p.getEditors());
  if (p.canDomainEdit()) p.setDomainEdit(false);
  if (settings.staff.length) p.addEditors(settings.staff);
}

function isDuplicateRegNo_(registry, regNo) {
  var target = String(regNo).trim().toLowerCase();
  return registry.getSheets().some(function (sh) {
    if (!isMonthSheetName(sh.getName()) || sh.getLastRow() < RG_FIRST_ROW) return false;
    return sh.getRange(RG_FIRST_ROW, RG.REG_NO, sh.getLastRow() - RG_FIRST_ROW + 1, 1).getValues()
      .some(function (r) { return String(r[0]).trim().toLowerCase() === target; });
  });
}

function nextRegistryRow_(sh) {
  return Math.max(sh.getLastRow() + 1, RG_FIRST_ROW);
}

/** v — tekshirilgan qator (readReviewRow_), state — eslatmalar holati. */
function writeRegistryRow_(sh, row, v, state) {
  var values = [
    row - RG_HEADER_ROW,
    v.regNo,
    ymdToDate_(v.regDate),
    v.outNo,
    v.resolution,
    dueDisplay(v.dueDate, v.dueText),
    v.summary,
    '',
    '',
    ymdToDate_(v.dueDate),
    v.emails.join(', '),
    state,
    new Date()
  ];
  sh.getRange(row, 1, 1, values.length).setValues([values]);
  sh.getRange(row, 1, 1, RG.REPORT).setBorder(true, true, true, true, true, true);
}

/** Reyestr qatoridan xat uchun ma'lumot. */
function entryFromRegistryRow_(r) {
  var regDate = cellToYmd_(r[RG.REG_DATE - 1]);
  return {
    regNo: String(r[RG.REG_NO - 1]).trim(),
    regDateText: regDate ? ymdText(regDate) : '',
    outNo: String(r[RG.OUT_NO - 1]).trim(),
    resolution: String(r[RG.RESOLUTION - 1]).trim(),
    dueText: String(r[RG.DUE_TEXT - 1]).trim(),
    summary: String(r[RG.SUMMARY - 1]).trim()
  };
}

/** Ijrochilarga reyestrni tahrirlash huquqi (himoya tufayli faqat I ustuni). */
function shareRegistryWith_(registry, emails, regNo) {
  var current = registry.getEditors().map(function (u) { return u.getEmail().toLowerCase(); });
  emails.forEach(function (e) {
    if (current.indexOf(e) >= 0) return;
    try {
      registry.addEditor(e);
    } catch (err) {
      logEvent_(registry, 'Ruxsat berilmadi', regNo, e + ': ' + err.message +
        ' (bu manzilga Google akkaunt ochilmagan bo\'lishi mumkin)');
    }
  });
}
