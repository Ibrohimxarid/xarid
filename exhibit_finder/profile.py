"""Tashkent Polytechnic Museum profile: what the museum actually needs.

Everything the relevance check knows about the museum lives in this file, so the
taxonomy can be edited by curators without touching the classification logic.

Each Concept carries:
  * phrases       -- what to look for in a candidate's title/description;
  * demonstrates  -- the concrete thing a visitor learns from such an object,
                     used to write WHY_IT_FITS_TASHKENT_POLYTECHNIC_MUSEUM.

Phrase syntax: plain phrases match whole words, case-insensitively, with any
whitespace/hyphen between words and an optional plural on the last word
("robot arm" matches "Robot-Arms"). Candidate text is normalised so that
"cut-away"/"cut away" read as "cutaway". Other spelling variants must be
listed. A phrase that starts with "re:" is a raw regular expression.
"""

from dataclasses import dataclass, field

MUSEUM_NAME = "Tashkent Polytechnic Museum"

# The museum's core profile (used in WHY_IT_FITS sentences).
PROFILE_AREAS = (
    "automotive technology",
    "transport technology",
    "engineering",
    "mechanics",
    "physics",
    "electricity",
    "optics",
    "robotics",
    "industrial technology",
    "STEM education",
    "interactive science",
    "technology history",
)


@dataclass(frozen=True)
class Concept:
    label: str
    demonstrates: str
    phrases: tuple


@dataclass(frozen=True)
class Category:
    code: str
    group: str  # "A" (high value) or "B" (useful)
    name: str
    areas: tuple  # subset of PROFILE_AREAS
    concepts: tuple = field(default_factory=tuple)


def C(label, demonstrates, *phrases):
    return Concept(label, demonstrates, tuple(phrases) or (label,))


# --------------------------------------------------------------------------
# PRIORITY GROUP A -- HIGH VALUE  (any match => DIRECT_MATCH)
# --------------------------------------------------------------------------

A1_AUTOMOTIVE = Category("A1", "A", "Automotive technology",
    ("automotive technology", "engineering"), (
    C("vehicle cutaway", "the layout of a complete car: engine, drivetrain, chassis and body structure",
      "vehicle cutaway", "car cutaway", "cutaway car", "cutaway vehicle", "sectioned car", "sectioned vehicle"),
    C("engine cutaway", "piston movement, combustion and power transmission inside an internal combustion engine",
      "engine cutaway", "cutaway engine", "sectioned engine", "engine section model", "re:\\bcut[\\s-]?away (?:petrol |diesel |gasoline )?engines?\\b"),
    C("transmission/gearbox demonstrator", "how gear ratios trade speed for torque in a vehicle transmission",
      "transmission cutaway", "gearbox cutaway", "cutaway gearbox", "gearbox demonstrator", "transmission demonstrator",
      "gearbox model", "automatic transmission", "manual gearbox"),
    C("differential demonstrator", "how a differential lets driven wheels turn at different speeds in a corner",
      "differential demonstrator", "differential cutaway", "differential model", "re:\\b(?:car|axle|vehicle) differentials?\\b"),
    C("brake system demonstrator", "how hydraulic pressure and friction stop a vehicle (discs, drums, ABS)",
      "brake demonstrator", "braking system", "brake system", "disc brake", "drum brake", "anti-lock braking", "ABS demonstrator"),
    C("steering system demonstrator", "how steering geometry and rack-and-pinion gearing turn the wheels",
      "steering system", "steering demonstrator", "rack and pinion steering", "power steering"),
    C("suspension demonstrator", "how springs and dampers absorb road shocks and keep tyres in contact with the road",
      "suspension demonstrator", "suspension system", "shock absorber", "re:\\b(?:car|vehicle|wheel) suspension\\b"),
    C("internal combustion engine", "the four-stroke cycle and conversion of fuel energy into motion",
      "internal combustion engine", "four-stroke engine", "two-stroke engine", "diesel engine", "petrol engine",
      "gasoline engine", "engine demonstrator", "car engine", "V8 engine", "rotary engine", "Wankel engine"),
    C("electric drive / EV powertrain", "how an electric motor, inverter and battery drive a vehicle",
      "electric vehicle powertrain", "EV powertrain", "electric powertrain", "EV drivetrain", "electric vehicle cutaway",
      "electric car", "electric vehicle", "electric motor demonstrator"),
    C("hybrid powertrain", "how a hybrid combines a combustion engine, electric motor and energy recovery",
      "hybrid powertrain", "hybrid drivetrain", "hybrid vehicle", "hybrid engine"),
    C("battery technology", "how traction batteries store energy and how cells are assembled into packs",
      "battery pack cutaway", "traction battery", "EV battery", "lithium-ion battery demonstrator", "battery technology"),
    C("fuel injection", "how fuel is metered and atomised for efficient combustion",
      "fuel injection", "fuel injector", "carburettor", "carburetor"),
    C("turbocharger", "how exhaust energy drives a turbine to force more air into an engine",
      "turbocharger", "turbo charger", "supercharger"),
    C("automotive electronics", "how sensors, control units and wiring manage a modern vehicle",
      "automotive electronics", "engine control unit", "vehicle electronics", "CAN bus", "ignition system"),
    C("ADAS / autonomous driving", "how cameras, radar and lidar let a vehicle perceive the road and assist the driver",
      "ADAS", "driver assistance", "autonomous driving", "self-driving", "autonomous vehicle", "lidar"),
    C("vehicle safety / crash test", "how crumple zones, seat belts and airbags manage crash energy",
      "crash test", "crash-test dummy", "crash test dummy", "vehicle safety", "airbag", "seat belt demonstrator", "crumple zone"),
))

A2_TRANSPORT = Category("A2", "A", "Transport technology",
    ("transport technology", "engineering"), (
    C("railway technology", "how locomotives, bogies, couplings and track work together",
      "locomotive component", "locomotive cab", "bogie", "railway technology", "traction motor", "pantograph",
      "steam locomotive", "diesel locomotive", "electric locomotive", "locomotive"),
    C("railway signalling and control", "how signals, interlocking and dispatch keep trains safely separated",
      "railway signalling", "railway signaling", "railroad signal", "railway signal", "signal box", "interlocking frame",
      "interlocking machine", "train control", "railway control system", "signalling demonstrator"),
    C("rail / tram / trolleybus simulator", "how a driver controls acceleration, braking and signals in a rail vehicle",
      "train simulator", "railway simulator", "tram simulator", "metro simulator", "driving cab simulator"),
    C("tram and trolleybus technology", "how electric urban vehicles draw current from overhead lines",
      "tram", "tramcar", "trolleybus", "trolley bus", "streetcar"),
    C("aircraft engine", "how a jet or piston aero-engine compresses air, burns fuel and produces thrust",
      "aircraft engine", "aero engine", "aero-engine", "jet engine", "turbofan", "turbojet", "turboprop",
      "radial engine", "piston aero engine"),
    C("aircraft cutaway / structure", "how wings, fuselage and control surfaces are built and generate lift",
      "aircraft cutaway", "cutaway aircraft", "fuselage section", "cockpit section", "wing section"),
    C("flight simulator", "how pilots use controls and instruments to fly an aircraft",
      "flight simulator", "cockpit simulator", "motion simulator", "aircraft simulator"),
    C("helicopter components", "how a rotor's collective and cyclic pitch produce lift and steering",
      "helicopter rotor", "helicopter component", "rotor head", "swashplate", "helicopter cockpit"),
    C("aircraft control demonstrator", "how ailerons, elevator and rudder change an aircraft's attitude",
      "flight control demonstrator", "aircraft control", "control surface demonstrator"),
    C("ship / boat technology", "how hulls, propellers and marine engines move vessels through water",
      "marine engine", "ship engine", "ship propeller", "boat engine", "outboard motor", "ship model", "hull model"),
    C("traffic engineering / ITS", "how traffic lights, sensors and control systems manage road traffic flow",
      "traffic light", "traffic signal", "traffic control system", "intelligent transport system",
      "traffic engineering", "traffic management system"),
    C("transport simulator", "how operators drive and control vehicles in realistic conditions",
      "driving simulator", "bus simulator", "truck simulator", "ship simulator", "transport simulator"),
))

A3_MECHANICS = Category("A3-M", "A", "Interactive physics: mechanics",
    ("physics", "mechanics", "interactive science"), (
    C("Newton's laws / inertia / momentum", "Newton's laws of motion, inertia and conservation of momentum",
      "Newton's laws", "newtons laws", "Newton's cradle", "newtons cradle", "inertia", "conservation of momentum", "momentum exhibit", "collision cart"),
    C("circular motion", "centripetal and centrifugal effects in rotating systems",
      "centrifugal", "centripetal", "rotating platform", "rotating chair", "spinning chair", "turntable experiment"),
    C("simple machines", "how levers, pulleys and gears give mechanical advantage",
      "lever", "pulley", "block and tackle", "mechanical advantage", "simple machine", "gear train", "gear wall",
      "gears exhibit", "lift yourself"),
    C("angular momentum / gyroscope", "conservation of angular momentum and gyroscopic stability",
      "angular momentum", "gyroscope", "gyroscopic", "bicycle wheel gyroscope"),
    C("energy conservation", "conversion between potential and kinetic energy",
      "conservation of energy", "energy conversion", "ball run", "marble run", "loop the loop", "rolling ball sculpture"),
    C("friction", "how surface materials and normal force change friction",
      "friction"),
    C("gravity", "gravitational acceleration, free fall and orbital motion",
      "gravity well", "free fall", "falling objects", "gravity demonstrator", "gravity exhibit"),
    C("pendulums and oscillations", "periodic motion, resonance and the physics of pendulums",
      "Foucault pendulum", "pendulum wave", "pendulum", "harmonograph", "oscillation", "coupled oscillator"),
))

A3_FLUIDS = Category("A3-F", "A", "Interactive physics: fluid mechanics",
    ("physics", "engineering", "interactive science"), (
    C("Bernoulli effect", "how fast-moving air lowers pressure (the principle behind lift)",
      "Bernoulli", "floating ball", "air table"),
    C("air and water flow", "laminar and turbulent flow, pressure and fluid dynamics",
      "air flow", "airflow", "water flow", "fluid dynamics", "laminar flow", "turbulence", "flow visualisation",
      "flow visualization", "water table", "hydraulic table"),
    C("pressure", "hydrostatic and air pressure and how they do work",
      "air pressure", "water pressure", "hydrostatic", "Magdeburg hemispheres", "vacuum chamber", "Archimedes screw"),
    C("vortex", "how rotating fluids form stable vortices",
      "vortex", "tornado machine", "fog tornado", "smoke ring"),
    C("wind tunnel / aerodynamics", "how shape changes drag and lift in moving air",
      "wind tunnel", "aerodynamic", "aerodynamics", "airfoil", "aerofoil"),
))

A3_WAVES = Category("A3-W", "A", "Interactive physics: waves and sound",
    ("physics", "interactive science"), (
    C("sound waves", "how sound travels as pressure waves and how pitch relates to frequency",
      "sound wave", "acoustic", "acoustics", "whisper dish", "echo tube", "parabolic dish", "oscilloscope sound"),
    C("resonance and vibration", "resonance, standing waves and vibration modes",
      "resonance", "Chladni", "standing wave", "vibration", "Rubens tube", "wave machine", "wave generator"),
    C("Doppler effect", "how relative motion shifts perceived frequency",
      "Doppler"),
))

A3_OPTICS = Category("A3-O", "A", "Interactive physics: optics",
    ("optics", "physics", "interactive science"), (
    C("mirrors and lenses", "reflection, refraction and image formation by mirrors and lenses",
      "infinity mirror", "mirror maze", "concave mirror", "convex mirror", "kaleidoscope", "lens", "optical bench",
      "camera obscura", "periscope", "mirror room", "hall of mirrors", "distorting mirror",
      "funhouse mirror", "mirror exhibit"),
    C("lasers", "how lasers produce coherent light and how light travels in straight lines",
      "laser"),
    C("polarization", "how polarising filters select the orientation of light waves",
      "polarization", "polarisation", "polarizing", "polarising", "polarized light", "polarised light"),
    C("diffraction and interference", "the wave nature of light through diffraction and interference patterns",
      "diffraction", "interference pattern", "spectroscope", "prism", "light spectrum", "colour mixing", "color mixing"),
    C("optical illusions", "how the eye and brain interpret light, colour and perspective",
      "optical illusion", "Ames room", "anamorphic", "persistence of vision", "zoetrope", "praxinoscope"),
    C("holography and projection", "how holograms and projectors record and reconstruct images",
      "hologram", "holography", "holographic", "Pepper's ghost", "projection system", "projector"),
))

A3_ELECTRICITY = Category("A3-E", "A", "Interactive physics: electricity and magnetism",
    ("electricity", "physics", "interactive science"), (
    C("Tesla coil", "high-voltage resonant transformers and electrical discharge",
      "Tesla coil", "singing Tesla coil"),
    C("Van de Graaff generator", "static electricity and charge separation",
      "Van de Graaff", "Wimshurst", "electrostatic generator", "static electricity", "electrostatic"),
    C("plasma", "ionised gas as the fourth state of matter",
      "plasma ball", "plasma globe", "plasma tube", "plasma lamp", "plasma exhibit"),
    C("electromagnetism", "how electric currents create magnetic fields and forces",
      "electromagnet", "electromagnetism", "electromagnetic", "magnetic field", "magnetic levitation", "maglev",
      "jumping ring", "Thomson ring", "Lenz", "eddy current", "magnet exhibit", "magnetism"),
    C("electric circuits", "how current, voltage and resistance behave in circuits",
      "electric circuit", "circuit board exhibit", "circuit wall", "series and parallel", "Ohm's law", "hand battery",
      "human battery"),
    C("induction, generators and motors", "electromagnetic induction and conversion between mechanical and electrical energy",
      "electromagnetic induction", "induction coil", "dynamo", "hand-crank generator", "hand crank generator", "pedal generator", "pedal power",
      "electric motor", "motor demonstrator", "generator demonstrator"),
    C("transformers", "how transformers change voltage for power transmission",
      "transformer"),
))

A4_ROBOTICS = Category("A4", "A", "Robotics and automation",
    ("robotics", "industrial technology", "engineering"), (
    C("robotic arm", "how a multi-axis robot arm is programmed to move precisely and repeatably",
      "robotic arm", "robot arm", "industrial robot", "KUKA", "FANUC", "ABB robot", "Yaskawa", "six-axis robot",
      "6-axis robot", "articulated robot", "SCARA"),
    C("collaborative robot", "how cobots work safely alongside people using force sensing",
      "collaborative robot", "cobot", "Universal Robots", "UR5", "UR10"),
    C("robot programming station", "how visitors program and sequence robot movements",
      "robot programming", "programmable robot", "robotics training", "robotics workstation", "teach pendant"),
    C("educational robot", "basic robotics, sensors and control for learners",
      "educational robot", "humanoid robot", "robot exhibit", "robot", "robotics"),
    C("factory automation", "how sensors, PLCs and actuators automate a production line",
      "factory automation", "automation demonstrator", "PLC", "programmable logic controller", "Industry 4.0",
      "mechatronics", "conveyor", "pick-and-place", "pick and place", "sorting system", "robotic sorting"),
    C("machine vision", "how cameras and software inspect, recognise and sort objects",
      "machine vision", "computer vision", "vision system"),
    C("autonomous robot", "how mobile robots navigate and avoid obstacles autonomously",
      "autonomous robot", "mobile robot", "AGV", "automated guided vehicle"),
))

A5_ENGINEERING = Category("A5", "A", "Engineering",
    ("engineering", "mechanics", "industrial technology"), (
    C("structural engineering", "how arches, trusses and cables carry load in buildings and bridges",
      "bridge model", "build a bridge", "bridge building", "arch bridge", "truss", "structural engineering",
      "load testing", "load test", "tension and compression"),
    C("earthquake simulator", "how buildings respond to seismic shaking and how engineers make them resist it",
      "earthquake simulator", "earthquake table", "shake table", "seismic"),
    C("materials testing", "how materials are tested for strength, hardness and fatigue",
      "materials testing", "tensile test", "tensile testing", "hardness tester", "strength of materials"),
    C("hydraulics and pneumatics", "how fluid power multiplies force in machines",
      "hydraulic", "hydraulics", "pneumatic", "pneumatics", "hydraulic press"),
    C("machine tools and CNC", "how lathes, mills and CNC machines shape metal",
      "CNC", "machine tool", "lathe", "milling machine", "drill press"),
    C("3D printing / additive manufacturing", "how parts are built layer by layer from digital models",
      "3D printer", "3D printing", "additive manufacturing"),
    C("mechanical engineering demonstrator", "mechanisms such as cams, linkages and cranks that convert motion",
      "mechanism model", "mechanisms exhibit", "cam and follower", "crankshaft", "mechanical model", "kinematic model", "clockwork"),
))

A6_ENERGY = Category("A6", "A", "Energy technology",
    ("engineering", "electricity", "industrial technology"), (
    C("steam engine", "how heat is turned into mechanical work by steam pressure",
      "steam engine", "beam engine", "stationary engine", "Stirling engine", "steam turbine"),
    C("turbines", "how turbines extract energy from moving fluids to generate power",
      "gas turbine", "turbine", "water wheel", "hydroelectric"),
    C("wind energy", "how wind turbines convert moving air into electricity",
      "wind turbine", "wind energy", "wind power", "windmill"),
    C("solar energy", "how photovoltaic cells and solar collectors convert sunlight",
      "solar panel", "solar energy", "solar power", "photovoltaic", "solar cell"),
    C("hydrogen and fuel cells", "how fuel cells produce electricity from hydrogen",
      "fuel cell", "hydrogen", "electrolysis", "electrolyser", "electrolyzer"),
    C("energy storage", "how energy is stored in batteries, flywheels and other systems",
      "energy storage", "battery system", "flywheel"),
    C("power grid and transmission", "how electricity is generated, transmitted and distributed",
      "electrical grid", "power grid", "power transmission", "power station", "substation", "smart grid",
      "generator", "alternator"),
    C("renewable energy exhibit", "how renewable sources compare and combine in an energy system",
      "renewable energy", "energy exhibit", "energy station"),
))

A7_STEM = Category("A7", "A", "STEM interactive stations",
    ("STEM education", "interactive science"), (
    C("interactive physics station", "a physical phenomenon that visitors explore by hand",
      "physics table", "physics station", "science table", "experiment station", "hands-on physics", "interactive physics"),
    C("engineering challenge / building station", "design, build and test thinking through hands-on construction",
      "engineering challenge", "building station", "build and test", "design challenge", "construction station",
      "tinkering", "makerspace", "maker space"),
    C("mechanical puzzle", "spatial reasoning and mechanical logic",
      "mechanical puzzle", "tangram", "Tower of Hanoi"),
    C("reaction time / human performance", "measurement of human reaction time and motion",
      "reaction time", "reaction-time", "reaction timer", "reaction wall", "speed of sound and light", "motion station"),
    C("water experiments", "flow, pressure, waves and buoyancy at a water table",
      "water play", "water experiment", "water lab", "dam building"),
    C("measurement", "how physical quantities are measured and compared",
      "measuring station", "measurement exhibit"),
))

A8_DIGITAL = Category("A8", "A", "Digital and immersive technology",
    ("STEM education", "interactive science"), (
    C("projection mapping", "how projected images are mapped onto physical surfaces",
      "projection mapping", "interactive projection", "floor projection", "wall projection"),
    C("immersive room", "how immersive audiovisual spaces present scientific content",
      "immersive room", "immersive environment", "immersive installation", "dome projection", "planetarium projector"),
    C("touch interfaces", "how multi-touch interfaces let visitors explore digital content",
      "multi-touch table", "multitouch table", "touch table", "touchscreen exhibit", "touchscreen kiosk",
      "interactive wall", "touch wall", "interactive kiosk"),
    C("AR/VR", "how augmented and virtual reality create interactive simulations",
      "augmented reality", "virtual reality", "VR station", "VR simulator", "AR exhibit", "AR sandbox",
      "augmented reality sandbox"),
    C("motion tracking", "how cameras and sensors track body movement for gesture control",
      "motion tracking", "gesture control", "gesture-controlled", "Kinect", "motion capture"),
))

A9_AUTO_MANUFACTURING = Category("A9", "A", "Automotive manufacturing",
    ("automotive technology", "industrial technology", "robotics"), (
    C("assembly line", "how cars are assembled step by step on a production line",
      "assembly line", "production line", "car assembly", "vehicle assembly", "engine assembly"),
    C("robotic welding / painting", "how robots weld and paint car bodies",
      "robotic welding", "welding robot", "spot welding", "painting robot", "paint robot", "body shop"),
    C("stamping", "how sheet steel is pressed into body panels",
      "stamping press", "metal stamping", "body panel press"),
    C("quality control", "how vehicles and parts are inspected for defects",
      "quality control", "quality inspection", "end-of-line test"),
    C("production logistics", "how parts flow to the line just in time",
      "production logistics", "just-in-time", "kanban"),
))

# --------------------------------------------------------------------------
# PRIORITY GROUP B -- USEFUL  (best match => STRONG_MATCH)
# --------------------------------------------------------------------------

B_USEFUL = (
    Category("B-AV", "B", "Aviation", ("transport technology", "technology history"), (
        C("aviation exhibit", "the development of flight and aircraft technology",
          "aircraft", "aeroplane", "airplane", "glider", "propeller", "cockpit", "aviation"),)),
    Category("B-RW", "B", "Railway", ("transport technology", "technology history"), (
        C("railway exhibit", "the development of rail transport",
          "railway", "railroad", "rolling stock", "carriage bogie", "rail car", "railcar", "wagon"),)),
    Category("B-IM", "B", "Industrial machinery", ("industrial technology", "technology history"), (
        C("industrial machine", "how industrial machinery transformed production",
          "industrial machine", "industrial machinery", "loom", "printing press", "machine shop", "workshop machine"),)),
    Category("B-AG", "B", "Agricultural machinery", ("industrial technology", "technology history"), (
        C("agricultural machine", "the mechanisation of agriculture",
          "tractor", "combine harvester", "agricultural machinery", "cotton harvester", "harvester", "plough engine"),)),
    Category("B-TC", "B", "Telecommunications", ("electricity", "technology history"), (
        C("telecommunications", "how signals carry voice and data over distance",
          "telegraph", "telephone exchange", "switchboard", "radio transmitter", "radio receiver", "telecommunication",
          "telecommunications", "fibre optic", "fiber optic", "antenna", "satellite dish", "telephone"),)),
    Category("B-EL", "B", "Electronics", ("electricity", "technology history"), (
        C("electronics", "how components such as valves, transistors and chips process signals",
          "electronics", "vacuum tube", "valve amplifier", "transistor", "semiconductor", "integrated circuit",
          "oscilloscope", "radio set"),)),
    Category("B-CH", "B", "Computing history", ("technology history", "STEM education"), (
        C("computing", "how computers evolved and process information",
          "computer", "mainframe", "calculating machine", "mechanical calculator", "punch card", "difference engine",
          "supercomputer", "microcomputer"),)),
    Category("B-MS", "B", "Materials science", ("engineering", "STEM education"), (
        C("materials science", "how material structure determines properties",
          "materials science", "composite material", "crystal structure", "metallurgy", "alloy"),)),
    Category("B-EN", "B", "Environmental technology", ("engineering", "STEM education"), (
        C("environmental technology", "how technology monitors and protects the environment",
          "water treatment", "recycling technology", "air quality monitor", "environmental technology",
          "weather station"),)),
    Category("B-SP", "B", "Space technology", ("technology history", "engineering", "physics"), (
        C("space technology", "how rockets, satellites and spacecraft work",
          "rocket engine", "rocket", "satellite", "spacecraft", "space capsule", "lunar module", "space station",
          "spacesuit", "space suit", "space shuttle", "heat shield"),)),
)

GROUP_A = (A1_AUTOMOTIVE, A2_TRANSPORT, A3_MECHANICS, A3_FLUIDS, A3_WAVES, A3_OPTICS, A3_ELECTRICITY,
           A4_ROBOTICS, A5_ENGINEERING, A6_ENERGY, A7_STEM, A8_DIGITAL, A9_AUTO_MANUFACTURING)
GROUP_B = B_USEFUL
ALL_CATEGORIES = GROUP_A + GROUP_B

# --------------------------------------------------------------------------
# Object TYPE vocabularies (checked against object_type, or the title).
# --------------------------------------------------------------------------

# EXCLUDE: never recommend, whatever the subject.
EXCLUDED_TYPES = (
    "painting", "oil painting", "watercolour", "watercolor", "drawing", "sketch", "etching", "engraving",
    "lithograph", "sculpture", "statue", "bust", "artwork", "work of art", "fine art", "tapestry",
    "archaeological", "archaeology", "excavated", "antiquity", "antiquities", "pottery shard", "potsherd",
    "ethnographic", "fossil", "taxidermy", "natural history specimen", "jewellery", "jewelry", "coin", "coins",
)

# GROUP C: low priority. NOT_RELEVANT unless the object has a strong
# technology-history connection, in which case it can at most be WEAK_MATCH.
LOW_PRIORITY_TYPES = (
    "book", "books", "volume", "volumes", "instruction manual", "service manual", "workshop manual",
    "owner's manual", "user manual", "catalogue", "catalog", "journal", "magazine", "newspaper",
    "document", "documents", "archive", "archival", "manuscript", "letter", "letters", "certificate", "map",
    "poster", "posters", "photograph", "photographs", "photo", "photos", "postcard", "slide collection",
    "art print", "print collection", "clothing", "uniform", "costume", "textile", "garment", "hat", "furniture", "chair",
    "display cabinet", "wardrobe", "sofa", "desk", "decorative", "ornament", "vase", "figurine", "household", "kitchen", "kitchenware",
    "utensil", "tableware", "medal", "badge", "stamp", "stamps", "timetable", "ticket", "nameplate", "plaque", "collectible", "collectibles", "memorabilia",
    "souvenir", "toy", "die-cast", "diecast",
)

# Technology objects that are toys/souvenirs are capped at WEAK_MATCH.
NOVELTY_MARKERS = ("toy", "souvenir", "figurine", "die-cast", "diecast", "memorabilia", "collectible",
                   "keyring", "key ring", "ornament", "decorative model")

# General technology vocabulary that is not in any category => RELATED.
GENERAL_TECH_TERMS = (
    "machine", "machinery", "apparatus", "scientific instrument", "instrument", "laboratory equipment",
    "measuring instrument", "engineering", "technology", "technical", "device", "mechanical", "engine",
    "motor", "industrial", "invention", "prototype", "electrical", "physics", "science",
)

# Exhibit-form markers (facts about how the object is presented to visitors).
INTERACTIVE_MARKERS = ("interactive", "hands-on", "hands on", "visitor-operated", "visitor operated",
                       "push-button", "push button", "crank", "visitors can", "visitors control", "playable",
                       "try it", "minds-on")
DEMONSTRATOR_MARKERS = ("demonstrator", "demonstration", "demo unit", "cutaway", "cut-away", "sectioned",
                        "working model", "simulator", "training rig", "trainer", "test bench", "exhibit station",
                        "teaching model", "educational model", "functional model", "operational model")
EXHIBIT_MARKERS = ("exhibit", "exhibition", "installation", "gallery", "display", "science centre",
                   "science center", "museum")

# Phrases that make a WHY_IT_FITS text generic and therefore unacceptable.
GENERIC_WHY_PHRASES = (
    "interesting for the museum", "interesting object", "could be interesting", "nice object", "good object",
    "useful for the museum", "relevant to the museum", "might be useful", "would be nice",
    "valuable object", "good addition",
)
