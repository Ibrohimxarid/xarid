/**
 * Bir martalik o'rnatish (skript muharririda, maxsus akkaunt nomidan):
 *   1) setup()         — reyestr, "Sozlamalar", "Jurnal", kunlik trigger va maxfiy token yaratiladi;
 *   2) "Sozlamalar"ni to'ldiring va applySettings() ni ishga tushiring;
 *   3) Deploy → New deployment → Web app (Execute as: Me, Who has access: Anyone);
 *      veb-ilova URL va tokenni kompyuterdagi config.yaml ga yozing.
 * setup() qayta ishga tushirilsa, mavjud narsalar qayta yaratilmaydi.
 */

function setup() {
  var props = PropertiesService.getScriptProperties();
  if (!props.getProperty(PROP.TOKEN)) {
    props.setProperty(PROP.TOKEN, (Utilities.getUuid() + Utilities.getUuid()).replace(/-/g, ''));
  }

  if (!props.getProperty(PROP.REGISTRY_SS_ID)) {
    var registry = SpreadsheetApp.create(CFG.REGISTRY_SS_NAME);
    DriveApp.getFileById(registry.getId()).moveTo(getOrCreateRootFolder_());
    registry.setSpreadsheetTimeZone(CFG.TIMEZONE);

    var settingsSheet = registry.insertSheet(CFG.SHEET_SETTINGS);
    settingsSheet.getRange(1, 1, 1, 3).setValues([['Sozlama', 'Qiymat', 'Izoh']])
      .setFontWeight('bold').setBackground('#d9e1f2');
    settingsSheet.getRange(2, 1, SETTINGS_DEFAULTS.length, 3).setValues(SETTINGS_DEFAULTS)
      .setWrap(true).setVerticalAlignment('top');
    settingsSheet.getRange(2, 1, SETTINGS_DEFAULTS.length, 1).setFontWeight('bold');
    [220, 380, 420].forEach(function (w, i) { settingsSheet.setColumnWidth(i + 1, w); });

    var log = registry.insertSheet(CFG.SHEET_LOG);
    log.getRange(1, 1, 1, 4).setValues([['Vaqt', 'Hodisa', 'Hujjat', 'Tafsilot']])
      .setFontWeight('bold').setBackground('#d9e1f2');
    log.setFrozenRows(1);
    log.getRange(2, 1, log.getMaxRows() - 1, 1).setNumberFormat('dd.mm.yyyy hh:mm:ss');
    [140, 160, 200, 500].forEach(function (w, i) { log.setColumnWidth(i + 1, w); });

    var settings = readSettings_(registry);
    var today = todayYmd_();
    var first = registry.getSheets()[0].setName(monthSheetName(today));
    setupMonthSheet_(first, today.y, settings);
    protectServiceSheet_(settingsSheet, settings);
    protectServiceSheet_(log, settings);
    props.setProperty(PROP.REGISTRY_SS_ID, registry.getId());
  }

  installTriggers_();
  console.log('Reyestr: ' + registrySs_().getUrl());
  showToken();
  console.log('Keyingi qadam: Deploy → New deployment → Web app (Execute as: Me, Who has access: Anyone).');
}

/** config.yaml uchun maxfiy tokenni ko'rsatadi. */
function showToken() {
  console.log('Token (config.yaml → remote.token): ' + prop_(PROP.TOKEN));
}

function getOrCreateRootFolder_() {
  var it = DriveApp.getRootFolder().getFoldersByName(CFG.ROOT_FOLDER_NAME);
  return it.hasNext() ? it.next() : DriveApp.createFolder(CFG.ROOT_FOLDER_NAME);
}

function installTriggers_() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'sendReminders') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('sendReminders').timeBased().everyDays(1).atHour(CFG.REMINDER_HOUR)
    .inTimezone(CFG.TIMEZONE).create();
}

/** "Sozlamalar"dagi o'zgarishlarni qo'llaydi: xodimlarga ruxsat, himoya, "Ijro holati" ro'yxati. */
function applySettings() {
  var registry = registrySs_();
  var settings = readSettings_(registry);
  settings.staff.forEach(function (e) { registry.addEditor(e); });
  registry.getSheets().forEach(function (sh) {
    if (isMonthSheetName(sh.getName())) {
      applyStatusDropdown_(sh, settings);
      protectMonthSheet_(sh, settings);
    } else if (sh.getName() === CFG.SHEET_SETTINGS || sh.getName() === CFG.SHEET_LOG) {
      protectServiceSheet_(sh, settings);
    }
  });
  console.log("Sozlamalar qo'llandi. Xodimlar: " + (settings.staff.join(', ') || "yo'q"));
}
