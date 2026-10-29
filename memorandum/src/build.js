// Builds the draft MoU between the Tashkent Polytechnic Museum and Hefei Panshi Intelligent Technology Co., Ltd.
// Usage: node build.js <output.docx>
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Header, Footer, Table, TableRow, TableCell,
  AlignmentType, WidthType, BorderStyle, ShadingType, PageNumber, TabStopType,
  VerticalAlign,
} = require("docx");

const [, , OUT = "MoU_Tashkent_Polytechnic_Museum_Panshi_DRAFT.docx"] = process.argv;

const NAVY = "1F3864";
const GREY = "7F7F7F";
const FONT = "Times New Roman";
const PAGE_W = 11906, PAGE_H = 16838, MARGIN = 1418; // A4, 2.5 cm margins
const TEXT_W = PAGE_W - 2 * MARGIN; // 9070

// Inline markup: **bold**, [placeholder] -> highlighted for filling in.
function runs(text, base = {}) {
  const out = [];
  for (const part of text.split(/(\*\*.+?\*\*|\[[^\]]+\])/)) {
    if (!part) continue;
    if (part.startsWith("**")) out.push(...runs(part.slice(2, -2), { ...base, bold: true }));
    else if (part.startsWith("[")) out.push(new TextRun({ ...base, text: part, highlight: "yellow" }));
    else out.push(new TextRun({ ...base, text: part }));
  }
  return out;
}

const p = (text, opts = {}) =>
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, ...opts, children: runs(text, opts.run) });

const center = (text, opts = {}) => p(text, { alignment: AlignmentType.CENTER, ...opts });

const heading = (text) =>
  new Paragraph({
    keepNext: true,
    spacing: { before: 240, after: 120 },
    children: [new TextRun({ text, bold: true, color: NAVY, size: 22 })],
  });

// "1.1<tab>text" with a hanging indent so wrapped lines align with the text.
const clause = (num, text, opts = {}) =>
  new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    ...opts,
    indent: { left: 709, hanging: 709 },
    tabStops: [{ type: TabStopType.LEFT, position: 709 }],
    children: [new TextRun({ text: num + "\t" }), ...runs(text)],
  });

// "(a)<tab>text" nested under a clause.
const item = (letter, text) =>
  new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: { left: 1276, hanging: 567 },
    tabStops: [{ type: TabStopType.LEFT, position: 1276 }],
    spacing: { after: 60 },
    children: [new TextRun({ text: `(${letter})\t` }), ...runs(text)],
  });

const whereas = (text) =>
  new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    children: [new TextRun({ text: "WHEREAS ", bold: true }), ...runs(text)],
  });

// ---------- tables ----------
const thin = { style: BorderStyle.SINGLE, size: 4, color: "A6A6A6" };
const borders = { top: thin, bottom: thin, left: thin, right: thin };
const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: none, bottom: none, left: none, right: none };

function cell(text, width, { header = false, bold = false, shade, cellBorders = borders, keepNext = false } = {}) {
  const lines = Array.isArray(text) ? text : [text];
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    borders: cellBorders,
    verticalAlign: VerticalAlign.CENTER,
    shading: shade ? { fill: shade, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 110, right: 110 },
    children: lines.map((t) =>
      new Paragraph({
        spacing: { after: 0, line: 252 },
        keepNext,
        children: runs(t, header ? { bold: true, color: "FFFFFF" } : bold ? { bold: true } : {}),
      })
    ),
  });
}

// keepTogether: keep-with-next on every row but the last, so the table does not split across pages.
function grid(widths, headerRow, rows, { firstColBold = false, keepTogether = false } = {}) {
  return new Table({
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headerRow.map((t, i) => cell(t, widths[i], { header: true, shade: NAVY, keepNext: keepTogether })),
      }),
      ...rows.map(
        (r, ri) =>
          new TableRow({
            cantSplit: true,
            children: r.map((t, i) =>
              cell(t, widths[i], {
                bold: firstColBold && i === 0,
                shade: ri % 2 ? "F2F4F8" : undefined,
                keepNext: keepTogether && ri < rows.length - 1,
              })
            ),
          })
      ),
    ],
  });
}

// ---------- header & footer ----------
const header = new Header({
  children: [
    new Paragraph({
      alignment: AlignmentType.RIGHT,
      children: [
        new TextRun({ text: "DRAFT — for discussion purposes only", italics: true, size: 16, color: GREY }),
      ],
    }),
  ],
});

const footer = new Footer({
  children: [
    new Paragraph({
      style: "Footer",
      border: { top: { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF", space: 4 } },
      tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }],
      children: [
        new TextRun({ text: "Memorandum of Understanding — Tashkent Polytechnic Museum and Hefei Panshi Intelligent Technology Co., Ltd.", size: 16, color: GREY }),
        new TextRun({ text: "\tPage ", size: 16, color: GREY }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, color: GREY }),
        new TextRun({ text: " of ", size: 16, color: GREY }),
        new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 16, color: GREY }),
      ],
    }),
  ],
});

// ---------- content ----------
const body = [];
const add = (...xs) => body.push(...xs);

// Title block
add(
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 240, after: 120 },
    children: [new TextRun({ text: "MEMORANDUM OF UNDERSTANDING", bold: true, size: 34, color: NAVY })],
  }),
  center("between", { run: { italics: true }, spacing: { after: 60 } }),
  center("**TASHKENT POLYTECHNIC MUSEUM**", { spacing: { after: 60 }, run: { size: 24 } }),
  center("and", { run: { italics: true }, spacing: { after: 60 } }),
  center("**HEFEI PANSHI INTELLIGENT TECHNOLOGY CO., LTD.**", { spacing: { after: 160 }, run: { size: 24 } }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: NAVY, space: 8 } },
    children: [
      new TextRun({
        text: "on Cooperation in Museum Exhibition Development, Interactive Technologies, and Science and Cultural Education",
        italics: true,
      }),
    ],
  }),
  new Paragraph({
    spacing: { after: 240 },
    tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }],
    children: [...runs("Tashkent, Republic of Uzbekistan"), new TextRun({ text: "\t" }), ...runs("[__ ____________ 2026]")],
  })
);

// Parties
add(
  p("This Memorandum of Understanding (hereinafter the “**MoU**”) is made by and between:"),
  clause(
    "(1)",
    "**Tashkent Polytechnic Museum**, established under the laws of the Republic of Uzbekistan, having its address at 13 Amir Temur Avenue, Mirabad District, Tashkent, Republic of Uzbekistan, represented by its Director, Mr. Sherzod Ulugbekovich Bekmatov, acting on the basis of the Charter of the Museum (hereinafter the “**Museum**”); and"
  ),
  new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: { left: 709, hanging: 709 },
    tabStops: [{ type: TabStopType.LEFT, position: 709 }],
    children: [
      new TextRun({ text: "(2)\t" }),
      new TextRun({ text: "Hefei Panshi Intelligent Technology Co., Ltd.", bold: true }),
      new TextRun({ text: " (" }),
      new TextRun({ text: "合肥磐石智能科技股份有限公司", font: { ascii: FONT, hAnsi: FONT, eastAsia: "SimSun" } }),
      new TextRun({ text: "), a company incorporated under the laws of the People’s Republic of China, having its address at Panshi Industrial Park, southwest of the intersection of Yunhu Road and Jixian Road, Feixi Economic Development Zone, Hefei, Anhui Province, People’s Republic of China, represented by " }),
      ...runs("[full name], [title], acting on the basis of [the Articles of Association / Power of Attorney No. ___]"),
      new TextRun({ text: " (hereinafter “" }),
      new TextRun({ text: "Panshi", bold: true }),
      new TextRun({ text: "”)." }),
    ],
  }),
  p("The Museum and Panshi are hereinafter referred to collectively as the “**Parties**” and individually as a “**Party**”.")
);

// Recitals
add(
  heading("PREAMBLE"),
  whereas(
    "the Museum, established in 2015 on the initiative of JSC “Uzavtosanoat”, presents the history of the automobile, engineering and technology, and operates an interactive science exhibition dedicated to popularising science and engineering among children, young people and the general public;"
  ),
  whereas(
    "Panshi, founded in 2012, specialises in the content development, design, fabrication, installation and operational management of science centres, museums and other cultural venues, and has delivered interactive exhibition projects in the People’s Republic of China and internationally;"
  ),
  whereas(
    "the Parties recognise that combining museum collections and curatorial expertise with modern interactive, multimedia and digital technologies makes heritage and science more accessible, engaging and educational for visitors of all ages;"
  ),
  whereas(
    "the Parties wish to establish a framework for long-term and mutually beneficial cooperation on the basis of equality, mutual respect and the laws of their respective countries;"
  ),
  p("**NOW, THEREFORE,** the Parties have reached the following understanding:")
);

// Article 1
add(
  heading("ARTICLE 1. PURPOSE"),
  clause(
    "1.1",
    "The purpose of this MoU is to establish a general framework for cooperation between the Parties in the development, modernisation and operation of museum exhibitions, the introduction of interactive and digital technologies, educational activities and professional exchange."
  ),
  clause(
    "1.2",
    "This MoU records the intentions of the Parties. Specific projects shall be implemented on the basis of separate agreements or contracts concluded in accordance with Article 6."
  )
);

// Article 2
add(
  heading("ARTICLE 2. AREAS OF COOPERATION"),
  p("The Parties intend to cooperate in, without limitation, the following areas:"),
  clause(
    "2.1",
    "**Exhibition concept and design:** joint development of concepts, storylines, content, and spatial and graphic design for the permanent and temporary exhibitions of the Museum, including the modernisation of existing exhibition halls."
  ),
  clause(
    "2.2",
    "**Interactive and digital exhibits:** design, fabrication, installation and commissioning of interactive, multimedia, immersive (AR/VR, projection mapping) and hands-on exhibits, as well as digital reconstructions and 3D presentations of objects from the Museum’s collection."
  ),
  clause(
    "2.3",
    "**Temporary and travelling exhibitions:** organisation of joint temporary exhibitions, hosting of travelling science and cultural exhibitions at the Museum, and presentation of the Museum’s heritage (in digital form or as replicas) in the People’s Republic of China and other countries."
  ),
  clause(
    "2.4",
    "**Education and public programmes:** development of educational programmes, workshops and STEAM activities for schoolchildren, students and families based on the Museum’s exhibitions."
  ),
  clause(
    "2.5",
    "**Training and knowledge exchange:** training of the Museum’s staff in exhibition design and in the operation and maintenance of interactive equipment; internships, study visits, seminars and the exchange of best practices."
  ),
  clause(
    "2.6",
    "**Technical support:** consultation, maintenance, upgrading and after-sales support of exhibits and equipment supplied under joint projects."
  ),
  clause(
    "2.7",
    "**Research and promotion:** joint participation in conferences, forums and exhibitions, joint publications, and promotion of the cooperation in the media."
  ),
  clause("2.8", "**Other areas** of mutual interest agreed by the Parties in writing.")
);

// Article 3
add(
  heading("ARTICLE 3. FORMS OF COOPERATION"),
  clause("3.1", "Cooperation under this MoU may take the following forms:"),
  item("a", "exchange of information, materials and expertise;"),
  item("b", "working meetings and visits of delegations and experts;"),
  item("c", "preparation of feasibility studies, concepts, technical proposals and cost estimates for specific projects;"),
  item("d", "implementation of joint projects under separate agreements;"),
  item("e", "any other forms agreed by the Parties.")
);

// Article 4
add(
  heading("ARTICLE 4. COMMITMENTS OF THE PARTIES"),
  clause("4.1", "The Museum intends to:"),
  item(
    "a",
    "provide Panshi with the historical, scientific and curatorial information reasonably necessary for the preparation of proposals, subject to the Museum’s internal rules and applicable law;"
  ),
  item("b", "provide curatorial guidance and approve the content of all exhibits relating to its collections;"),
  item("c", "facilitate site visits, surveys and access to the premises required for joint projects;"),
  item("d", "assist, within its competence, in obtaining the permits and approvals required in the Republic of Uzbekistan."),
  clause("4.2", "Panshi intends to:"),
  item("a", "provide professional expertise in exhibition planning, design and interactive technologies;"),
  item(
    "b",
    "prepare, at the Museum’s request, concepts, technical proposals and indicative cost estimates at no cost to the Museum, unless otherwise agreed in writing;"
  ),
  item(
    "c",
    "comply with the Museum’s requirements for the safety and conservation of museum objects, visitor safety and the applicable technical standards;"
  ),
  item(
    "d",
    "provide training to the Museum’s staff and technical support for the exhibits it supplies, under the terms of the relevant agreements."
  )
);

// Article 5
add(
  heading("ARTICLE 5. JOINT WORKING GROUP"),
  clause(
    "5.1",
    "The Parties may establish a Joint Working Group, which shall meet at least once a year, in person or online, to review progress and agree on an annual plan of activities."
  )
);

// Article 6
add(
  heading("ARTICLE 6. FINANCIAL PROVISIONS"),
  clause(
    "6.1",
    "This MoU does not create any financial obligations for either Party. Each Party shall bear its own costs related to activities under this MoU, unless otherwise agreed in writing."
  ),
  clause(
    "6.2",
    "The scope, budget, timeline, payment terms, delivery conditions, warranties and liability for each specific project shall be set out in separate agreements or contracts."
  ),
  clause(
    "6.3",
    "Any procurement of goods, works or services by the Museum shall be carried out in strict compliance with the procurement legislation of the Republic of Uzbekistan applicable to the Museum and with the Museum’s internal procedures. Nothing in this MoU grants Panshi any exclusivity, priority or preferential right in any procurement procedure."
  )
);

// Article 7
add(
  heading("ARTICLE 7. INTELLECTUAL PROPERTY"),
  clause(
    "7.1",
    "Each Party retains all rights to its intellectual property existing before, or developed independently of, this MoU."
  ),
  clause(
    "7.2",
    "All rights to the Museum’s collections, objects, archives, images, photographs, 3D scans and related data remain with the Museum. Panshi may use such materials solely for agreed joint projects and only with the Museum’s prior written consent."
  ),
  clause(
    "7.3",
    "The ownership and use of intellectual property created in the course of joint projects shall be governed by the separate agreements referred to in Article 6."
  )
);

// Article 8
add(
  heading("ARTICLE 8. CONFIDENTIALITY"),
  clause(
    "8.1",
    "Each Party shall keep confidential any information received from the other Party that is marked as confidential or would reasonably be understood to be confidential, and shall not disclose it to third parties without the other Party’s prior written consent, except as required by law."
  ),
  clause("8.2", "This obligation shall survive for three (3) years after the expiry or termination of this MoU.")
);

// Article 9
add(
  heading("ARTICLE 9. USE OF NAMES AND LOGOS"),
  clause(
    "9.1",
    "Neither Party shall use the name, logo or trademarks of the other Party in any publicity, advertising or other public materials without that Party’s prior written approval."
  ),
  clause("9.2", "The Parties may announce the signing of this MoU using jointly agreed wording.")
);

// Article 10
add(
  heading("ARTICLE 10. ANTI-CORRUPTION AND COMPLIANCE"),
  clause(
    "10.1",
    "The Parties shall comply with the anti-corruption laws applicable to them and shall not offer, give, request or accept any undue payment or advantage in connection with this MoU or any project under it."
  ),
  clause(
    "10.2",
    "Each Party shall act in accordance with the laws of its own country and applicable international norms, including legislation on the protection of cultural heritage, export and import controls, and customs."
  )
);

// Article 11
add(
  heading("ARTICLE 11. LEGAL NATURE OF THE MoU"),
  clause(
    "11.1",
    "This MoU is a declaration of intent and does not create legally binding obligations for the Parties, with the exception of Articles 6, 7, 8 and 9, which shall be binding."
  ),
  clause(
    "11.2",
    "This MoU does not establish a partnership, joint venture, agency or employment relationship between the Parties, and neither Party may act on behalf of or bind the other."
  ),
  clause("11.3", "This MoU does not restrict either Party from cooperating with third parties.")
);

// Article 12
add(
  heading("ARTICLE 12. SETTLEMENT OF DIFFERENCES"),
  clause(
    "12.1",
    "Any differences arising from the interpretation or implementation of this MoU shall be resolved amicably through consultations and negotiations between the Parties."
  )
);

// Article 13
add(
  heading("ARTICLE 13. ENTRY INTO FORCE, DURATION AND TERMINATION"),
  clause(
    "13.1",
    "This MoU shall enter into force on the date of its signature by both Parties and shall remain in force for a period of [three (3)] years."
  ),
  clause(
    "13.2",
    "Thereafter, this MoU shall be automatically extended for successive periods of one (1) year unless either Party notifies the other in writing of its intention not to extend it at least ninety (90) days before the expiry of the current period."
  ),
  clause("13.3", "Either Party may terminate this MoU at any time by giving the other Party ninety (90) days’ prior written notice."),
  clause(
    "13.4",
    "The expiry or termination of this MoU shall not affect agreements concluded or projects commenced during its term, unless the Parties agree otherwise."
  ),
  clause(
    "13.5",
    "Any amendments or additions to this MoU shall be made in writing in the form of addenda signed by both Parties, which shall form an integral part of this MoU."
  )
);

// Article 14
add(
  heading("ARTICLE 14. NOTICES AND CONTACTS"),
  clause(
    "14.1",
    "All notices under this MoU shall be made in writing and sent to the contacts below, or to such other contacts as a Party may notify in writing:",
    { keepNext: true }
  ),
  new Paragraph({ spacing: { after: 60 }, keepNext: true, children: [] }),
  grid(
    [2000, 3535, 3535],
    ["", "The Museum", "Panshi"],
    [
      ["Address", "13 Amir Temur Avenue, Mirabad District, Tashkent, Republic of Uzbekistan", "Panshi Industrial Park, Yunhu Road and Jixian Road, Feixi Economic Development Zone, Hefei, Anhui Province, PRC"],
      ["Telephone", "+998 70 523 10 10", "+86 400-135-1080"],
      ["E-mail", "[e-mail]", "[e-mail]"],
      ["Website", "politomuseum.uz", "www.panshiexhibit.com"],
    ],
    { firstColBold: true, keepTogether: true }
  ),
  new Paragraph({ spacing: { after: 60 }, children: [] })
);

// Article 15
add(
  heading("ARTICLE 15. FINAL PROVISIONS"),
  clause(
    "15.1",
    "This MoU is signed in [Tashkent] on [date] in two (2) original copies in the English language, one for each Party, both being equally authentic. Translations into Uzbek and Chinese may be prepared for convenience; in the event of any discrepancy, the English text shall prevail."
  ),
  clause(
    "15.2",
    "This MoU may be signed in counterparts, including by the exchange of scanned signed copies, each of which shall be deemed an original."
  ),
  clause(
    "15.3",
    "Annex 1 (Indicative Initial Activities) is attached for reference only and may be updated by mutual agreement of the Parties in writing without a formal amendment of this MoU."
  ),
  p("**IN WITNESS WHEREOF**, the undersigned, being duly authorised by their respective organisations, have signed this MoU.", {
    spacing: { before: 200, after: 240 },
    keepNext: true,
  })
);

// Signature block
const half = TEXT_W / 2;
const sig = (lines) => cell(lines, half, { cellBorders: noBorders });
add(
  new Table({
    width: { size: TEXT_W, type: WidthType.DXA },
    columnWidths: [half, half],
    rows: [
      new TableRow({
        cantSplit: true,
        children: [
          sig(["**FOR THE MUSEUM**", "Tashkent Polytechnic Museum", "", "", "", "______________________________", "Name: Sherzod U. Bekmatov", "Title: Director", "Date: [__ / __ / 2026]", "", "L.S."]),
          sig(["**FOR PANSHI**", "Hefei Panshi Intelligent Technology Co., Ltd.", "", "", "", "______________________________", "Name: [full name]", "Title: [title]", "Date: [__ / __ / 2026]", "", "L.S."]),
        ],
      }),
    ],
  })
);

// Annex 1
add(
  new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "Annex 1 to the MoU", italics: true })] }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 60 },
    children: [new TextRun({ text: "INDICATIVE INITIAL ACTIVITIES", bold: true, size: 26, color: NAVY })],
  }),
  center("(for reference; non-binding)", { run: { italics: true }, spacing: { after: 200 } }),
  grid(
    [600, 4270, 2200, 2000],
    ["No.", "Activity", "Responsible", "Timeframe"],
    [
      ["1", "Visit of Panshi specialists to the Museum; assessment of exhibition spaces and needs", "Panshi, with the Museum’s support", "[month, year]"],
      ["2", "Preparation of a concept and technical proposal for [the modernisation of the Museum’s interactive science exhibition]", "Panshi", "[__ weeks after the visit]"],
      ["3", "Study visit of Museum staff to Panshi’s production facilities and reference projects in China", "Both Parties", "[month, year]"],
      ["4", "Training workshop for Museum staff on interactive exhibits and museum education", "Panshi", "[month, year]"],
      ["5", "First meeting of the Joint Working Group; approval of the annual plan of activities", "Both Parties", "[month, year]"],
    ]
  )
);

// ---------- document ----------
const doc = new Document({
  creator: "Tashkent Polytechnic Museum",
  title: "Memorandum of Understanding — Tashkent Polytechnic Museum and Hefei Panshi Intelligent Technology Co., Ltd. (Draft)",
  styles: {
    default: {
      document: {
        run: { font: FONT, size: 22 },
        paragraph: { spacing: { after: 120, line: 276 } },
      },
    },
    paragraphStyles: [
      { id: "Footer", name: "footer", basedOn: "Normal", run: { size: 16, color: GREY }, paragraph: { spacing: { after: 0 } } },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: PAGE_W, height: PAGE_H },
          margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN, header: 709, footer: 709 },
        },
      },
      headers: { default: header },
      footers: { default: footer },
      children: body,
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log("wrote", OUT);
});
