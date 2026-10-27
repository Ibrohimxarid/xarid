/**
 * Har kuni ertalab: muddatgacha 7 (agar muddat yetarli bo'lsa), 3, 1 kun qolganda va
 * muddat kuni ijrochilarga eslatma; muddat o'tgach — bir marta xat (nusxasi rahbarga).
 * "Ijro holati" yakunlangan bo'lsa yoki muddat sanasi yo'q bo'lsa — eslatma yuborilmaydi.
 */

function sendReminders() {
  var lock = LockService.getScriptLock();
  lock.waitLock(60000);
  try {
    var registry = registrySs_();
    var settings = readSettings_(registry);
    var today = todayYmd_();
    registry.getSheets().forEach(function (sh) {
      if (!isMonthSheetName(sh.getName()) || sh.getLastRow() < RG_FIRST_ROW) return;
      var values = sh.getRange(RG_FIRST_ROW, 1, sh.getLastRow() - RG_FIRST_ROW + 1, RG_HEADERS.length).getValues();
      values.forEach(function (r, i) {
        remindRow_(settings, registry, sh, RG_FIRST_ROW + i, r, today);
      });
    });
  } finally {
    lock.releaseLock();
  }
}

function remindRow_(settings, registry, sh, row, r, today) {
  var entry = entryFromRegistryRow_(r);
  if (!entry.regNo) return;
  if (settings.doneStatuses.indexOf(String(r[RG.STATUS - 1]).trim().toLowerCase()) >= 0) return;
  var due = cellToYmd_(r[RG.DUE_DATE - 1]);
  var emails = splitEmails(r[RG.EMAILS - 1]);
  if (!due || !emails.length) return;

  var daysLeft = daysBetween(today, due);
  var plan = planReminder(String(r[RG.REMINDERS - 1]), ymdKey(due), daysLeft, CFG.REMINDER_DAYS);
  if (plan.kind !== 'none') {
    // "Muddat (sana)" o'zgartirilgan bo'lsa ham xatda joriy muddat ko'rinsin.
    entry.dueText = formatDueText(due);
    var link = registryRowLink_(registry, sh, row);
    try {
      if (plan.kind === 'overdue') {
        sendMail_(settings, emails, settings.corpMail.concat(settings.managerMail),
          buildOverdueMail(entry, -daysLeft, link), []);
      } else {
        sendMail_(settings, emails, settings.corpMail, buildReminderMail(entry, daysLeft, link), []);
      }
    } catch (err) {
      // Holat yozilmaydi — ertaga qayta urinadi.
      logEvent_(registry, 'Eslatma yuborilmadi', entry.regNo, err.message);
      return;
    }
    logEvent_(registry, plan.kind === 'overdue' ? "Muddati o'tdi" : 'Eslatma', entry.regNo,
      'qoldi: ' + daysLeft + ' kun; ' + emails.join(', '));
  }
  if (plan.changed) sh.getRange(row, RG.REMINDERS).setValue(plan.state);
}
