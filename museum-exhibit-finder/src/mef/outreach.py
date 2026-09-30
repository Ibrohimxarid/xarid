"""Outreach opportunity blocks and e-mail drafts.

Drafts are built only from stored facts (research.outreach + evidence). Where
a fact is missing the draft keeps a visible ``[…]`` placeholder instead of
inventing it. Nothing is ever sent automatically.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import UNKNOWN
from .evidence import primary_source
from .models import MuseumFile
from .priority import assess_museum
from .rows import best_contact

SUBJECT = "Potential transfer of retired museum exhibits to Tashkent Polytechnic Museum"

SIGNATURE = """With kind regards,

[Name]
[Position]
Tashkent Polytechnic Museum
Tashkent, Uzbekistan
[E-mail] | [Phone] | [Website]"""


@dataclass
class OutreachDraft:
    museum_id: str
    museum: str
    contact: str
    to: str
    reason: str
    interest: str
    fit: str
    source: str
    next_step: str
    subject: str
    body: str

    def markdown(self) -> str:
        return (
            f"### {self.museum}\n\n"
            f"1. **Museum:** {self.museum}\n"
            f"2. **Contact:** {self.contact}\n"
            f"3. **Reason for contact:** {self.reason}\n"
            f"4. **Exhibits of interest:** {self.interest}\n"
            f"5. **Why it may suit Tashkent Polytechnic Museum:** {self.fit}\n"
            f"6. **Source:** {self.source}\n"
            f"7. **Suggested next step:** {self.next_step}\n\n"
            f"**To:** {self.to}  \n**Subject:** {self.subject}\n\n"
            f"```text\n{self.body}\n```\n"
        )


def source_phrase(src) -> str:
    """How the e-mail refers to the source: 'your website', 'a BBC report (2024)' …"""
    if src is None:
        return "published information"
    when = f" ({src.source_date[:4]})" if src.source_date else ""
    if src.source_type in ("official_site", "press_release", "annual_report", "board_document"):
        return "your published information"
    if src.source_type in ("association", "collection_database"):
        return f"the {src.publisher or 'published'} listing{when}"
    if src.source_type in ("news", "trade_press"):
        if not src.publisher:
            return f"a press report{when}"
        name = src.publisher[4:] if src.publisher.startswith("The ") else src.publisher
        article = "an" if name[:1].upper() in "AEIOU" else "a"
        return f"{article} {name} report{when}"
    if src.source_type == "government":
        return f"{src.publisher or 'government'} information{when}"
    return f"published information{when}"


def _interest(mf: MuseumFile) -> str:
    names = [i.name for ex in mf.exhibitions for i in ex.exhibits
             if i.status not in ("already_transferred", "still_in_use")]
    if mf.research.outreach.interest:
        return mf.research.outreach.interest
    if names:
        return "; ".join(names[:6])
    olds = [ex.old_exhibition or ex.name for ex in mf.exhibitions]
    return f"Exhibits from: {'; '.join(olds)}" if olds else UNKNOWN


def build_draft(mf: MuseumFile) -> OutreachDraft:
    m, o = mf.museum, mf.research.outreach
    src = mf.evidence_by_id().get(o.source or "") or primary_source(mf.evidence)
    contact = best_contact(mf)
    greeting = f"Dear {contact.name}," if contact and contact.name else "Dear Colleagues,"
    to = (contact.email if contact and contact.email else None) or m.general_email or (
        contact.contact_page if contact and contact.contact_page else "[contact to be identified]"
    )
    contact_line = UNKNOWN
    if contact:
        contact_line = ", ".join(x for x in [contact.name, contact.position, contact.email,
                                            contact.phone, contact.contact_page] if x)

    hook = (o.email_hook or "[state the verified fact that prompted this e-mail, citing the source]").rstrip(".")
    src_ref = source_phrase(src)
    interest = _interest(mf).rstrip(".")
    a = assess_museum(mf)
    ask = (
        "whether these items might be available for transfer, donation or purchase"
        if a.priority == "A"
        else "whether any of the retired exhibits are still held and might in future be available "
             "for transfer, donation or purchase"
    )

    body = f"""{greeting}

I am writing on behalf of Tashkent Polytechnic Museum in Tashkent, Uzbekistan — a museum of science, engineering, transport and the history of technology. We are currently developing a modern, hands-on exhibition for school students, families and young engineers.

We understand from {src_ref} that {hook}.

We would be very interested to learn {ask}. Our particular interest is in: {interest}.

If any items could be considered, we would be grateful for basic information on their condition, dimensions and weight, available documentation, and any conditions or procedures for transfer to another institution. We are ready to discuss the practical arrangements for dismantling, packing and international transport, and we would gladly acknowledge {m.name} as the source of the exhibits.

We fully understand that any decision depends on your own collection policies and priorities, and we would be happy to follow whatever process you have in place.

Thank you very much for considering our request.

{SIGNATURE}"""

    return OutreachDraft(
        museum_id=m.id,
        museum=f"{m.name} ({m.city + ', ' if m.city else ''}{m.country})",
        contact=contact_line,
        to=to,
        reason=o.reason or hook,
        interest=interest,
        fit=o.fit or "[explain the fit with the TPM profile: physics, engineering, automotive, transport, STEM]",
        source=(src.url if src else UNKNOWN),
        next_step=mf.research.next_step or "Confirm the contact and send the enquiry.",
        subject=SUBJECT,
        body=body,
    )
