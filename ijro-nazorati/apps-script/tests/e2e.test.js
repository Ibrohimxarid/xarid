// Google qismining to'liq oqimi soxta xizmatlar bilan:
// setup → doPost(register) → reyestr qatori + xat → kunma-kun eslatmalar.
process.env.TZ = 'Asia/Tashkent';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { makeEnv } = require('./fakes');

const DIR = path.join(__dirname, '..');

function load() {
  const env = makeEnv();
  const ctx = vm.createContext({ ...env.globals });
  for (const f of fs.readdirSync(DIR).filter(f => f.endsWith('.gs')).sort()) {
    vm.runInContext(fs.readFileSync(path.join(DIR, f), 'utf8'), ctx, { filename: f });
  }
  let today = '2026-10-01';
  ctx.todayYmd_ = () => ctx.parseIsoDate(today);
  ctx.setup();
  const registry = env.spreadsheets.get(env.props.get('REGISTRY_SS_ID'));
  const settings = registry.getSheetByName('Sozlamalar');
  const setSetting = (name, value) => {
    const row = settings.rows.findIndex(r => r && r[0] === name) + 1;
    settings.put(row, 2, value);
  };
  setSetting('Korporativ pochta', 'devonxona@corp.uz');
  setSetting('Rahbar pochtasi', 'rahbar@corp.uz');
  const post = (body) => JSON.parse(ctx.doPost({ postData: { contents: JSON.stringify(body) } }).text);
  const token = env.props.get('API_TOKEN');
  return { env, ctx, registry, post, token, setToday: (d) => { today = d; } };
}

const DOC = {
  regNo: '488-PA', regDate: '2026-10-01', outNo: '26-2850', resolution: 'U.Xoshimova,\nTTPU',
  dueDate: '2026-10-11', dueText: '11-oktabrga qadar', summary: 'Farmon loyihasi kelishish uchun yuborilgan.',
  emails: ['u.xoshimova@corp.uz', 'info@nogoogle.uz']
};

test('setup creates registry with month sheet first, service sheets after, a token and a daily trigger', () => {
  const { env, registry, token } = load();
  assert.deepEqual(registry.getSheets().map(s => s.getName()), ['Oktabr 2026', 'Sozlamalar', 'Jurnal']);
  assert.match(token, /^[0-9a-f]{64}$/);
  assert.deepEqual(env.triggers, ['sendReminders']);
  const month = registry.getSheetByName('Oktabr 2026');
  assert.equal(month.cell(3, 2), "Ro'yxatga olingan raqami");
  assert.match(month.cell(1, 1), /2026-yilda kelib tushgan/);
  const p = month.getProtections()[0];
  assert.equal(p.unprotected[0].getColumn(), 9); // faqat I ustuni ochiq
  assert.equal(p.unprotected[0].getRow(), 4);
});

test('requests without the right token are refused', () => {
  const { post, token } = load();
  assert.deepEqual(post({ token: 'wrong', action: 'ping' }), { ok: false, error: "Token noto'g'ri" });
  assert.equal(post({ token, action: 'ping' }).ok, true);
  assert.equal(post({ token, action: 'nimadir' }).ok, false);
});

test('register writes the row in the existing format and mails all executors', () => {
  const { env, registry, post, token } = load();
  const res = post({ token, action: 'register', doc: DOC,
    file: { name: 'hujjat.pdf', mimeType: 'application/pdf', base64: Buffer.from('%PDF-1.4').toString('base64') } });
  assert.equal(res.ok, true, res.error);
  assert.equal(res.sheet, 'Oktabr 2026');
  assert.equal(res.row, 4);

  const sh = registry.getSheetByName('Oktabr 2026');
  const row = sh.getRange(4, 1, 1, 13).getValues()[0];
  assert.equal(row[0], 1);
  assert.equal(row[1], '488-PA');
  assert.equal(row[3], '26-2850');
  assert.equal(row[4], 'U.Xoshimova,\nTTPU');
  assert.equal(row[5], '11-oktabrga qadar');
  assert.equal(row[7], '');
  assert.equal(row[8], '');
  assert.equal(row[10], 'u.xoshimova@corp.uz, info@nogoogle.uz');
  assert.equal(row[11], '2026-10-11|R');

  assert.equal(env.sent.length, 1);
  const m = env.sent[0];
  assert.equal(m.to, 'u.xoshimova@corp.uz,info@nogoogle.uz');
  assert.equal(m.cc, 'devonxona@corp.uz');
  assert.equal(m.replyTo, 'devonxona@corp.uz');
  assert.equal(m.attachments.length, 1);
  assert.match(m.subject, /^Yangi topshiriq: 488-PA/);
  assert.match(m.htmlBody, /#gid=\d+&amp;range=I4/);

  // Google akkaunti yo'q manzilga ruxsat berilmadi — jurnalda qayd bor.
  assert.deepEqual(registry.editors, ['u.xoshimova@corp.uz']);
  const log = registry.getSheetByName('Jurnal');
  assert.ok(log.rows.some(r => r && r[1] === 'Ruxsat berilmadi'));
  assert.ok(log.rows.some(r => r && r[1] === "Ro'yxatga olindi"));
});

test('duplicates, invalid data and exhausted mail quota write nothing', () => {
  const { env, registry, post, token } = load();
  assert.equal(post({ token, action: 'register', doc: DOC }).ok, true);
  const dup = post({ token, action: 'register', doc: { ...DOC, regNo: ' 488-pa ' } });
  assert.equal(dup.ok, false);
  assert.equal(dup.duplicate, true);

  const bad = post({ token, action: 'register', doc: { ...DOC, regNo: '', emails: [] } });
  assert.match(bad.error, /Ro'yxat raqami bo'sh/);

  env.setQuota(1);
  const noMail = post({ token, action: 'register', doc: { ...DOC, regNo: '489-PA' } });
  assert.match(noMail.error, /limiti/);
  assert.equal(registry.getSheetByName('Oktabr 2026').getLastRow(), 4);
});

test('a document from another month gets its own sheet before the service sheets', () => {
  const { registry, post, token } = load();
  assert.equal(post({ token, action: 'register', doc: { ...DOC, regNo: '12-PA', regDate: '2026-11-03', dueDate: null, dueText: '' } }).ok, true);
  assert.deepEqual(registry.getSheets().map(s => s.getName()), ['Oktabr 2026', 'Noyabr 2026', 'Sozlamalar', 'Jurnal']);
  const row = registry.getSheetByName('Noyabr 2026').getRange(4, 1, 1, 13).getValues()[0];
  assert.equal(row[0], 1);
  assert.equal(row[5], '');
  assert.equal(row[11], 'R');
});

test('reminders: week, 3 days, 1 day, deadline day, one overdue copy to the manager; none after "Bajarildi"', () => {
  const { env, ctx, registry, post, token, setToday } = load();
  assert.equal(post({ token, action: 'register', doc: DOC }).ok, true);
  assert.equal(post({ token, action: 'register', doc: { ...DOC, regNo: '490-PA' } }).ok, true);
  const sh = registry.getSheetByName('Oktabr 2026');
  sh.put(5, 8, 'Bajarildi'); // ikkinchi hujjat bajarilgan
  env.sent.length = 0;

  const byDay = {};
  for (let d = 2; d <= 14; d++) {
    const day = `2026-10-${String(d).padStart(2, '0')}`;
    setToday(day);
    ctx.sendReminders();
    const mails = env.sent.splice(0);
    if (mails.length) byDay[day] = mails;
  }
  assert.deepEqual(Object.keys(byDay), ['2026-10-04', '2026-10-08', '2026-10-10', '2026-10-11', '2026-10-12']);
  assert.match(byDay['2026-10-04'][0].subject, /muddatga 7 kun qoldi/);
  assert.match(byDay['2026-10-08'][0].subject, /muddatga 3 kun qoldi/);
  assert.match(byDay['2026-10-10'][0].subject, /muddat ertaga/);
  assert.match(byDay['2026-10-11'][0].subject, /muddat bugun/);
  const overdue = byDay['2026-10-12'][0];
  assert.match(overdue.subject, /^Muddati o'tdi: 488-PA/);
  assert.equal(overdue.cc, 'devonxona@corp.uz,rahbar@corp.uz');
  for (const mails of Object.values(byDay)) assert.equal(mails.length, 1);
});

test('moving the deadline in column J restarts reminders from the new date', () => {
  const { env, ctx, registry, post, token, setToday } = load();
  assert.equal(post({ token, action: 'register', doc: DOC }).ok, true);
  const sh = registry.getSheetByName('Oktabr 2026');
  setToday('2026-10-10');
  ctx.sendReminders(); // "ertaga" eslatmasi
  env.sent.length = 0;
  sh.put(4, 10, vm.runInContext('new Date(2026, 9, 25)', ctx)); // muddat 25-oktabrga uzaytirildi
  setToday('2026-10-11');
  ctx.sendReminders();
  assert.equal(env.sent.length, 0); // eski muddat bo'yicha "bugun" xati ketmaydi
  setToday('2026-10-18');
  ctx.sendReminders();
  assert.equal(env.sent.length, 1);
  assert.match(env.sent[0].subject, /7 kun qoldi/);
  assert.match(env.sent[0].htmlBody, /25-oktabrga qadar/);
});

test('a failed reminder is retried the next day', () => {
  const { env, ctx, post, token, setToday } = load();
  assert.equal(post({ token, action: 'register', doc: DOC }).ok, true);
  env.sent.length = 0;
  env.setQuota(0);
  setToday('2026-10-04');
  ctx.sendReminders();
  assert.equal(env.sent.length, 0);
  env.setQuota(100);
  setToday('2026-10-05');
  ctx.sendReminders();
  assert.equal(env.sent.length, 1);
  assert.match(env.sent[0].subject, /6 kun qoldi/);
});
