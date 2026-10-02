"""One-off annotation of existing research files for the TPM relevance check (2026-10-02)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from yaml_patch import exhibit, exhibition, load, save  # noqa: E402

EXHIBITS = {
    ("american-museum-and-gardens", "singer-treadle"): dict(
        object_type="household", transport="standard",
        fit_for_tpm="Treadle drive turns the foot pedal's reciprocating motion into rotary motion via a crank and belt — "
                    "a small mechanics example, but ordinary household equipment (low priority in the brief)."),
    ("cambridge-museum-of-technology", "kleischograph"): dict(
        object_type="machine", category=["industrial", "mechanics", "electricity", "optics"], transport="standard",
        fit_for_tpm="Klischograph-type photo-engraving machine: the photograph is scanned optically and the printing "
                    "plate engraved automatically — shows optical scanning, electrical control and mechanical "
                    "automation in the printing industry."),
    ("cambridge-museum-of-technology", "engineering-books"): dict(object_type="book_document"),
    ("coventry-transport-museum", "approved-disposals-2026"): dict(object_type="mixed_collection"),
    ("illinois-railway-museum", "cnw-tender"): dict(
        object_type="rolling_stock", transport="oversize",
        fit_for_tpm="Steam-locomotive tender (coal and water carrier) — shows how a steam locomotive was supplied "
                    "with fuel and water; a large railway-technology object."),
    ("montana-science-center", "hands-on-exhibits"): dict(
        object_type="interactive_station", former_exhibit=True,
        fit_for_tpm="Hands-on exhibits from a closed interactive science centre — visitors carry out the experiments "
                    "themselves, the interactive STEM format TPM already uses; the exact exhibit list must be requested."),
    ("museum-speelklok", "adb-objects"): dict(object_type="mixed_collection"),
    ("nasm-washington", "transfer-list"): dict(object_type="mixed_collection"),
    ("national-museum-of-flight", "bac-111-g-avmo"): dict(object_type="aircraft", transport="oversize"),
    ("national-railway-museum", "t3-563"): dict(object_type="rolling_stock"),
    ("national-railway-museum", "4vep"): dict(object_type="rolling_stock"),
    ("nederlands-transport-museum", "collection-contents"): dict(object_type="mixed_collection"),
    ("omsi-portland", "shake-house"): dict(
        object_type="simulator", category=["engineering", "physics", "stem"], former_exhibit=True,
        fit_for_tpm="Walk-in earthquake simulator: visitors feel recorded ground motion and learn how buildings "
                    "respond — the brief's earthquake-simulator item, and locally meaningful in seismically active "
                    "Tashkent (1966 earthquake)."),
    ("petersen-automotive-museum", "hot-rods-mecum-2026"): dict(
        object_type="vehicle", transport="standard",
        fit_for_tpm="Historic hot rods show engine tuning, chassis modification and the evolution of American "
                    "automotive engineering — complete cars for an automotive-technology display."),
    ("petersen-automotive-museum", "alfa-giulia-tz"): dict(
        object_type="vehicle", transport="standard",
        fit_for_tpm="1964 Alfa Romeo Giulia TZ — lightweight tubular space-frame racing car showing chassis and "
                    "aerodynamic engineering."),
    ("raf-museum", "sr53-xd145"): dict(
        object_type="aircraft", transport="oversize", former_exhibit=True,
        fit_for_tpm="Mixed-power interceptor prototype (rocket engine plus jet engine, 1957) — shows rocket and jet "
                    "propulsion and high-speed aerodynamics in one aircraft."),
    ("raf-museum", "h126-xn714"): dict(
        object_type="aircraft", transport="oversize", former_exhibit=True,
        fit_for_tpm="Research aircraft that tested jet-blown flaps for short take-off and landing — demonstrates lift "
                    "augmentation and aerodynamic research."),
    ("raf-museum", "sea-balliol-wl732"): dict(
        object_type="aircraft", transport="oversize",
        fit_for_tpm="1950s naval advanced trainer with a Rolls-Royce Merlin piston engine — a complete piston-engine "
                    "aircraft for an aviation-technology display."),
    ("royal-engineers-museum", "iee-proceedings"): dict(object_type="book_document"),
    ("saint-louis-science-center", "zeiss-universarium-ix"): dict(
        object_type="instrument",
        fit_for_tpm="Opto-mechanical Zeiss star projector (fibre-optic star field, lens projection, precision drives) "
                    "— a showpiece for optics and projection systems, or reusable in a small dome."),
    ("science-museum-group", "altair"): dict(object_type="computer"),
    ("science-museum-group", "electricity-gallery-1950s"): dict(object_type="household"),
    ("spoorwegmuseum", "surplus-rolling-stock"): dict(
        object_type="rolling_stock", transport="oversize",
        fit_for_tpm="Locomotives and carriages (duplicates and parts donors) — real railway vehicles showing traction, "
                    "bogies, couplings and braking; railways are a major transport sector in Uzbekistan."),
    ("universiteitsmuseum-utrecht", "vitrines-8-door"): dict(object_type="display_furniture"),
    ("universiteitsmuseum-utrecht", "vitrines-4-door"): dict(object_type="display_furniture"),
    ("villach-vehicle-museum", "villach-vehicles"): dict(
        object_type="vehicle", transport="standard",
        fit_for_tpm="Historic motorcycles, mopeds and cars incl. an early electric car — complete vehicles showing the "
                    "evolution of engines and automotive technology."),
    ("witney-and-district-museum", "prestcold-fridge"): dict(
        object_type="household", transport="hazardous",
        fit_for_tpm="1950s compressor refrigerator — shows the refrigeration cycle (compressor, condenser, evaporator), "
                    "i.e. thermodynamics in everyday life; ordinary household equipment that may still contain coolant."),
    ("zaans-museum", "machine-parts"): dict(
        object_type="component", transport="standard",
        fit_for_tpm="Iron wheels from old industrial machines — could illustrate wheel and gear transmission in a "
                    "mechanics corner, but they are loose parts, not exhibits."),
}

GALLERIES = {
    ("hong-kong-science-museum", "permanent-renewal"): dict(
        object_type="interactive_station", category=["optics", "physics", "stem"],
        fit_for_tpm="Ageing interactive exhibits from the renewed permanent galleries, incl. the World of Mirrors optics "
                    "gallery due for renewal in 2026–27 — hands-on mirror and reflection experiments fit TPM's optics "
                    "and interactive-physics areas."),
    ("kamin-science-center", "makeover-2025-2027"): dict(
        object_type="interactive_station", category=["physics", "stem"],
        fit_for_tpm="Interactive exhibits retired during the nine-exhibition makeover (incl. the old SportsWorks "
                    "building, which becomes a Science of Speed auto-racing exhibit) — hands-on motion and force "
                    "stations fit TPM's interactive mechanics area."),
    ("franklin-institute", "bicentennial-master-plan"): dict(
        object_type="interactive_station", category=["physics", "engineering", "stem"],
        fit_for_tpm="Twelve subject exhibitions of a classic physics-and-engineering science museum are being "
                    "consolidated into six; retired hands-on stations on forces, electricity and machines would fit "
                    "TPM's interactive physics and engineering areas — ask which are retired."),
    ("palais-de-la-decouverte", "renovation-2020-2027"): dict(
        object_type="demonstrator", category=["physics", "electricity", "optics"],
        fit_for_tpm="The pre-2020 demonstration rooms (live physics demonstrations) are replaced by a new museography; "
                    "retired demonstration apparatus for electricity, optics and mechanics fits TPM's interactive "
                    "physics area."),
    ("phaeno", "redesign-2025"): dict(
        object_type="interactive_station", category=["physics", "stem"],
        fit_for_tpm="phaeno's 2025 redesign revised 200 and added 50 hands-on exhibits; stations taken off the floor are "
                    "interactive physics experiments of the kind TPM already uses — ask which left the floor."),
    ("queensland-museum-kurilpa", "sparklab"): dict(
        object_type="interactive_station", category=["physics", "stem"],
        fit_for_tpm="Hands-on exhibits of the former Sciencentre, replaced by SparkLab — interactive science stations "
                    "fitting TPM's STEM area; ask whether any were kept in store."),
    ("science-north", "floors-3-4-renewal"): dict(
        object_type="interactive_station", category=["stem"],
        fit_for_tpm="Third- and fourth-floor hands-on exhibits are being renewed ($1.9m; Woven by Water to 2028); "
                    "retired interactive science stations would fit TPM's STEM area — ask what leaves the floor."),
    ("shanghai-science-technology-museum", "upgrade-2023-2026"): dict(
        object_type="interactive_station", category=["robotics", "stem", "computing"],
        fit_for_tpm="The 2001-era halls 'Robot World' and 'Information Age' were entirely replaced in the 2023–2026 "
                    "upgrade — retired robot and information-technology exhibits fit TPM's robotics and automation area."),
    ("tech-interactive", "renewal"): dict(
        object_type="interactive_station", category=["engineering", "stem"],
        fit_for_tpm="More than half of The Tech Interactive's exhibits were replaced; retired technology and engineering "
                    "interactives fit TPM's STEM and engineering areas — ask what is in store."),
    ("technopolis-mechelen", "main-expo-2022"): dict(
        object_type="interactive_station", category=["physics", "stem"],
        fit_for_tpm="Technopolis replaced part of its main exhibition in 2022 (classics such as the bicycle on a cable "
                    "and the bed of nails were kept); the retired hands-on physics installations fit TPM's "
                    "interactive-physics format."),
    ("universum-bremen", "permanent-rebuild-2026"): dict(
        object_type="interactive_station", category=["physics", "mechanics", "stem"],
        fit_for_tpm="Universum's 4,000 m² hands-on exhibition is rebuilt from 16 Nov 2026; highlights (earthquake sofa, "
                    "tilted room, plasma sphere) stay, other interactive stations leave the floor — hands-on physics "
                    "experiments fit TPM directly. Ask before November 2026."),
    ("vitm-bengaluru", "fun-science"): dict(
        object_type="interactive_station", category=["physics", "mechanics", "optics", "acoustics"],
        fit_for_tpm="The previous Fun Science gallery was replaced in July 2025 by ~50 new hands-on exhibits on "
                    "mechanics, optics and sound; the retired hands-on physics exhibits match TPM's interactive format."),
    ("miraikan", "renewal-2023"): dict(
        object_type="interactive_station", category=["stem"],
        fit_for_tpm="Miraikan replaced its previous permanent zones in November 2023 with four new exhibitions (incl. "
                    "Robots) — retired interactive science-and-technology exhibits fit TPM's STEM area; ask what was kept."),
    ("national-science-museum-daejeon", "creativity-hall"): dict(
        object_type="interactive_station", category=["stem"],
        fit_for_tpm="The Creativity Hall (hands-on science zone) is being remodelled; Korean national science museums "
                    "transfer retired exhibits to other institutions (see Gwacheon) — retired interactive stations fit "
                    "TPM's STEM area."),
    ("noesis-thessaloniki", "planetarium-upgrade"): dict(
        object_type="instrument", category=["optics", "space"],
        fit_for_tpm="The previous planetarium projection system was replaced — projector hardware shows optics and "
                    "projection technology, fitting TPM's optics area (or reusable in a small dome)."),
    ("maryland-science-center", "our-place-in-space"): dict(
        object_type="interactive_station", category=["space", "stem"],
        fit_for_tpm="The former 'Our Place in Space' exhibition was replaced by a new space-exploration exhibit in late "
                    "2025 — retired space-science interactives fit TPM's aviation/space and STEM areas."),
    ("ontario-science-centre", "don-mills-building"): dict(
        object_type="interactive_station", category=["physics", "stem"],
        fit_for_tpm="Hands-on exhibits of the closed Don Mills building (one of the first interactive science centres, "
                    "1969) have been in storage since 2024 — classic interactive physics and technology stations that "
                    "match TPM's format directly."),
    ("southern-air-heritage", "wind-down"): dict(object_type="mixed_collection", category=["aviation"]),
}

RESEARCH = {
    "american-museum-and-gardens": dict(international_transfer="unknown"),
    "coventry-transport-museum": dict(international_transfer="domestic_first",
                                      transfer_programme="Collections Review Project — approved disposals (Feb 2026)"),
    "illinois-railway-museum": dict(international_transfer="yes"),
    "museum-speelklok": dict(international_transfer="domestic_first"),
    "nasm-washington": dict(transfer_programme="Collection Items for Transfer (periodic transfer list)"),
    "nederlands-transport-museum": dict(international_transfer="yes",
                                        transfer_programme="Sale of the collection after closure (2025)"),
    "petersen-automotive-museum": dict(international_transfer="yes"),
    "raf-museum": dict(international_transfer="domestic_first",
                       transfer_programme="Objects Transfer Programme (to late 2027)"),
    "spoorwegmuseum": dict(international_transfer="domestic_first",
                           transfer_programme="Rolling-stock deaccession via the Afstotingsdatabase"),
    "universiteitsmuseum-utrecht": dict(international_transfer="yes"),
    "zaans-museum": dict(international_transfer="yes"),
    "villach-vehicle-museum": dict(international_transfer="yes"),
    "science-museum-group": dict(transfer_programme="Collection transfers to public museums (via Find an Object)"),
    "southern-air-heritage": dict(transfer_programme="Artifact disposition in 2027 (to families and partner institutions)"),
}


def main():
    touched = {}
    for (mid, iid), fields in EXHIBITS.items():
        d = touched.setdefault(mid, load(mid))
        exhibit(d, iid).update(fields)
    for (mid, eid), fields in GALLERIES.items():
        d = touched.setdefault(mid, load(mid))
        exhibition(d, eid).update(fields)
    for mid, fields in RESEARCH.items():
        d = touched.setdefault(mid, load(mid))
        d["research"].update(fields)
    for mid, d in touched.items():
        save(mid, d)
    print(f"annotated {len(touched)} files")


if __name__ == "__main__":
    main()
