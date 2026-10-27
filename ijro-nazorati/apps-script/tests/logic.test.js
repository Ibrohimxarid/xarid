// Logic.gs uchun testlar: node --test apps-script/tests/
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ctx = {};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'Logic.gs'), 'utf8'), ctx);
const L = ctx;
const M = [7, 3, 1, 0];

test('parseIsoDate rejects impossible dates', () => {
  assert.deepEqual({ ...L.parseIsoDate('2026-10-12') }, { y: 2026, m: 10, d: 12 });
  assert.equal(L.parseIsoDate('2026-02-30'), null);
  assert.equal(L.parseIsoDate('12.10.2026'), null);
  assert.equal(L.parseIsoDate(null), null);
});

test('due text and month sheet name match the existing register format', () => {
  const d = L.parseIsoDate('2026-10-12');
  assert.equal(L.formatDueText(d), '12-oktabrga qadar');
  assert.equal(L.monthSheetName(d), 'Oktabr 2026');
  assert.ok(L.isMonthSheetName('Oktabr 2026'));
  assert.ok(!L.isMonthSheetName('Sozlamalar'));
  assert.equal(L.dueDisplay(null, 'har chorakda'), 'har chorakda');
});

test('daysBetween crosses month and year', () => {
  assert.equal(L.daysBetween(L.parseIsoDate('2026-12-30'), L.parseIsoDate('2027-01-02')), 3);
  assert.equal(L.daysBetween(L.parseIsoDate('2026-10-12'), L.parseIsoDate('2026-10-11')), -1);
});

// Kunma-kun simulyatsiya: qaysi kunlari xat ketadi.
function simulate(daysLeftAtRegistration) {
  let state = L.initialReminderState('D', daysLeftAtRegistration, M);
  const sent = [];
  for (let left = daysLeftAtRegistration - 1; left >= -3; left--) {
    const plan = L.planReminder(state, 'D', left, M);
    if (plan.kind !== 'none') sent.push(plan.kind === 'overdue' ? 'X' : left);
    state = plan.state;
  }
  return sent;
}

test('long deadline: week, 3 days, 1 day, deadline day, then one overdue notice', () => {
  assert.deepEqual(simulate(20), [7, 3, 1, 0, 'X']);
});

test('deadline under a week: no week reminder', () => {
  assert.deepEqual(simulate(5), [3, 1, 0, 'X']);
});

test('registration on a milestone day does not repeat it', () => {
  assert.deepEqual(simulate(7), [3, 1, 0, 'X']);
  assert.deepEqual(simulate(3), [1, 0, 'X']);
  assert.deepEqual(simulate(0), ['X']);
});

test('registered after the deadline: no reminders at all', () => {
  assert.deepEqual(simulate(-2), []);
});

test('a missed day sends the nearest reminder once', () => {
  const state = L.initialReminderState('D', 10, M);
  let plan = L.planReminder(state, 'D', 5, M); // 7 kunlik ishga tushish o'tkazib yuborilgan
  assert.equal(plan.kind, 'reminder');
  plan = L.planReminder(plan.state, 'D', 4, M);
  assert.equal(plan.kind, 'none');
  plan = L.planReminder(plan.state, 'D', 3, M);
  assert.equal(plan.kind, 'reminder');
});

test('extended deadline restarts the schedule without repeating past steps', () => {
  let plan = L.planReminder(L.initialReminderState('2026-10-12', 1, M), '2026-10-20', 9, M);
  assert.equal(plan.kind, 'none');
  assert.ok(plan.changed);
  assert.equal(plan.state, '2026-10-20|R');
  plan = L.planReminder(plan.state, '2026-10-20', 7, M);
  assert.equal(plan.kind, 'reminder');
  // Muddat bugungi bosqichga o'zgartirilsa — bugun xabar boradi.
  plan = L.planReminder(L.initialReminderState('2026-10-12', 10, M), '2026-10-05', 3, M);
  assert.equal(plan.kind, 'reminder');
});

test('splitEmails keeps only valid unique addresses', () => {
  assert.deepEqual([...L.splitEmails('A@x.uz, a@x.uz; b@y.uz\nnot-an-email')], ['a@x.uz', 'b@y.uz']);
});

test('validateRegistration accepts a complete document', () => {
  const r = L.validateRegistration({
    regNo: ' 488-PA ', regDate: '2026-10-01', outNo: '26-2850', resolution: 'U.Xoshimova,\nTTPU',
    dueDate: '2026-10-12', dueText: '12-oktabrga qadar', summary: 'Loyiha', emails: ['A@x.uz', 'a@x.uz', 'b@y.uz']
  });
  assert.deepEqual([...r.errors], []);
  assert.equal(r.value.regNo, '488-PA');
  assert.deepEqual([...r.value.emails], ['a@x.uz', 'b@y.uz']);
  assert.deepEqual({ ...r.value.dueDate }, { y: 2026, m: 10, d: 12 });
});

test('validateRegistration lists every problem', () => {
  const r = L.validateRegistration({ regDate: '2026-13-01', dueDate: 'ertaga', emails: ['x@'] });
  assert.deepEqual([...r.errors], [
    "Ro'yxat raqami bo'sh", "Ro'yxat sanasi bo'sh yoki noto'g'ri", "Rezolyutsiya bo'sh",
    "Qisqacha mazmun bo'sh", "Muddat sanasi noto'g'ri", "Noto'g'ri email: x@", "Ijrochilar emaili ko'rsatilmagan"
  ]);
  assert.ok(L.validateRegistration(null).errors.length > 0);
});

test('mail templates escape HTML and mention the attachment only when attached', () => {
  const entry = { regNo: '488-PA', regDateText: '01.10.2026', outNo: '26-2850', resolution: 'U.Xoshimova,\nTTPU',
    dueText: '12-oktabrga qadar', summary: '<b>loyiha</b>' };
  const reg = L.buildRegistrationMail(entry, 'https://example.com', true);
  assert.equal(reg.subject, 'Yangi topshiriq: 488-PA (muddat: 12-oktabrga qadar)');
  assert.match(reg.html, /&lt;b&gt;loyiha&lt;\/b&gt;/);
  assert.match(reg.html, /U\.Xoshimova,<br>TTPU/);
  assert.match(reg.text, /Hujjat ilova qilingan/);
  assert.doesNotMatch(L.buildRegistrationMail(entry, 'l', false).text, /ilova/);
  assert.equal(L.buildReminderMail(entry, 1, 'l').subject, 'Eslatma: 488-PA — muddat ertaga');
  assert.equal(L.buildReminderMail(entry, 0, 'l').subject, 'Eslatma: 488-PA — muddat bugun');
  assert.match(L.buildOverdueMail(entry, 2, 'l').subject, /^Muddati o'tdi/);
});

test('safeEqual', () => {
  assert.ok(L.safeEqual('abc', 'abc'));
  assert.ok(!L.safeEqual('abc', 'abd'));
  assert.ok(!L.safeEqual('', ''));
  assert.ok(!L.safeEqual(undefined, 'abc'));
});
