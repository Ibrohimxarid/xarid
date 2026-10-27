/**
 * Ijro nazorati — Google qismi: reyestr, xatlar va eslatmalar.
 * Hujjatlarni o'qish xodimning kompyuterida bajariladi; bu yerga faqat xodim
 * tasdiqlagan yozuv keladi (WebApp.gs → doPost).
 */

var CFG = {
  TIMEZONE: 'Asia/Tashkent',

  // Eslatmalar: muddatgacha qolgan kunlar. 7 — faqat muddat yetarli bo'lsa.
  REMINDER_DAYS: [7, 3, 1, 0],
  REMINDER_HOUR: 9,

  MAX_ATTACHMENT_BYTES: 20 * 1024 * 1024,

  SHEET_SETTINGS: 'Sozlamalar',
  SHEET_LOG: 'Jurnal',

  ROOT_FOLDER_NAME: 'Ijro nazorati',
  REGISTRY_SS_NAME: 'HUJJATLAR BOYICHA — reyestr'
};

// Script properties kalitlari (setup() to'ldiradi).
var PROP = {
  REGISTRY_SS_ID: 'REGISTRY_SS_ID',
  TOKEN: 'API_TOKEN'
};

// Reyestr (oy varag'i) ustunlari. A–I — mavjud jadval formati, J–M — xizmat ustunlari.
var RG = {
  NUM: 1, REG_NO: 2, REG_DATE: 3, OUT_NO: 4, RESOLUTION: 5, DUE_TEXT: 6, SUMMARY: 7,
  STATUS: 8, REPORT: 9, DUE_DATE: 10, EMAILS: 11, REMINDERS: 12, REGISTERED_AT: 13
};
var RG_HEADERS = ['№', "Ro'yxatga olingan raqami", "Ro'yxatga olingan sana", 'Chiqish raqami',
  'Rezolyutsiya', 'Ijro muddati', 'Hujjatning qisqacha mazmuni', 'Ijro holati',
  "Ijrosi haqida qisqacha ma'lumot", 'Muddat (sana)', 'Ijrochilar email', 'Eslatmalar',
  "Ro'yxatga olingan vaqt"];
var RG_HEADER_ROW = 3;
var RG_FIRST_ROW = 4;

// "Sozlamalar" varag'i: [nomi, standart qiymat, izoh].
var SETTINGS_DEFAULTS = [
  ['Xodimlar', '', "Reyestrni to'liq tahrirlay oladigan xodimlar emaili (vergul bilan). Ijrochilar faqat I ustunini o'zgartiradi."],
  ['Korporativ pochta', '', "Har bir xatning nusxasi (CC) shu manzilga boradi, ijrochilarning javoblari (Reply-To) ham shu manzilga."],
  ['Rahbar pochtasi', '', "Muddat o'tganda xat nusxasi shu manzilga boradi. Bo'sh qoldirilsa — yuborilmaydi."],
  ["Jo'natuvchi nomi", 'Ijro nazorati', "Xatlarda ko'rinadigan jo'natuvchi nomi."],
  ['Ijro holati qiymatlari', 'Ijroda, Bajarildi, Nazoratdan olindi', "\"Ijro holati\" ustunidagi tanlov ro'yxati (vergul bilan)."],
  ['Yakunlangan holatlar', 'Bajarildi, Nazoratdan olindi', "Shu holatdagi hujjatlar bo'yicha eslatma yuborilmaydi."],
  ['Ijrochilarga avtomatik ruxsat', 'Ha', "Ha — ro'yxatga olishda ijrochilarga reyestrni tahrirlash huquqi beriladi (faqat I ustuni)."],
  ['Jadval sarlavhasi', '"O\'zavtosanoat" AJga {yil}-yilda kelib tushgan (***) hujjatlar va ularning ijrosi to\'g\'risida tezkor\nMA\'LUMOT',
    "Oy varag'i sarlavhasi. {yil} o'rniga yil qo'yiladi."]
];
