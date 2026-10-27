/**
 * Veb-ilova: xodim kompyuteridagi dastur tasdiqlangan yozuvni shu yerga yuboradi.
 * Deploy → Web app: "Execute as: Me", "Who has access: Anyone". Himoya — maxfiy token.
 *
 * So'rov (POST, JSON):
 *   {token, action: 'ping'}
 *   {token, action: 'register', doc: {...}, file: {name, mimeType, base64} | null}
 * Javob: {ok: true, ...} yoki {ok: false, error: '...'}
 */

function doGet() {
  return ContentService.createTextOutput('Ijro nazorati: ishlayapti');
}

function doPost(e) {
  var res;
  try {
    var req = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    var expected = PropertiesService.getScriptProperties().getProperty(PROP.TOKEN);
    if (!expected || !safeEqual(req.token, expected)) {
      res = { ok: false, error: "Token noto'g'ri" };
    } else if (req.action === 'ping') {
      res = { ok: true, registryUrl: registrySs_().getUrl() };
    } else if (req.action === 'register') {
      res = registerDocument_(req.doc, req.file);
    } else {
      res = { ok: false, error: "Noma'lum amal: " + req.action };
    }
  } catch (err) {
    res = { ok: false, error: String((err && err.message) || err) };
  }
  return ContentService.createTextOutput(JSON.stringify(res)).setMimeType(ContentService.MimeType.JSON);
}

function registerDocument_(doc, file) {
  var checked = validateRegistration(doc);
  if (checked.errors.length) return { ok: false, error: checked.errors.join('; ') };
  var v = checked.value;

  var attachments = [];
  if (file && file.base64) {
    var bytes = Utilities.base64Decode(file.base64);
    if (bytes.length > CFG.MAX_ATTACHMENT_BYTES) return { ok: false, error: 'Fayl juda katta (20 MB dan ortiq)' };
    attachments.push(Utilities.newBlob(bytes, file.mimeType || 'application/pdf', file.name || 'hujjat.pdf'));
  }

  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    var registry = registrySs_();
    var settings = readSettings_(registry);
    if (isDuplicateRegNo_(registry, v.regNo)) {
      return { ok: false, duplicate: true, error: "Bu ro'yxat raqami reyestrda allaqachon bor: " + v.regNo };
    }

    var today = todayYmd_();
    var state = v.dueDate
      ? initialReminderState(ymdKey(v.dueDate), daysBetween(today, v.dueDate), CFG.REMINDER_DAYS)
      : 'R';
    var sheet = getOrCreateMonthSheet_(registry, v.regDate, settings);
    var row = nextRegistryRow_(sheet);
    var link = registryRowLink_(registry, sheet, row);
    var entry = {
      regNo: v.regNo,
      regDateText: ymdText(v.regDate),
      outNo: v.outNo,
      resolution: v.resolution,
      dueText: dueDisplay(v.dueDate, v.dueText),
      summary: v.summary
    };

    // Avval xat: yuborilmasa, reyestrga hech narsa yozilmaydi va kompyuterdagi fayl joyida qoladi.
    sendMail_(settings, v.emails, settings.corpMail,
      buildRegistrationMail(entry, link, attachments.length > 0), attachments);

    try {
      writeRegistryRow_(sheet, row, v, state);
    } catch (err) {
      logEvent_(registry, 'XATO', v.regNo, "Xat yuborildi, lekin reyestrga yozilmadi: " + err.message);
      return { ok: false, error: "Xat yuborildi, lekin reyestrga yozilmadi (qatorni qo'lda kiriting): " + err.message };
    }
    if (settings.autoShare) shareRegistryWith_(registry, v.emails, v.regNo);
    logEvent_(registry, "Ro'yxatga olindi", v.regNo,
      sheet.getName() + ', ' + row + '-qator; xat: ' + v.emails.join(', '));
    return { ok: true, sheet: sheet.getName(), row: row, url: link };
  } finally {
    lock.releaseLock();
  }
}
