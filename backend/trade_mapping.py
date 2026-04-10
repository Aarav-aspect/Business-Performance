# Trade group phase & region mapping
#
# Phase 3: 3 regions (East, North West, South West)
# Phase 2: 2 regions (North, South)
# Phase 1: No regions

TRADE_GROUP_PHASES = {
    'Leak, Damp & Restoration': 3,
    'Plumbing & Drainage': 3,
    'HVac & Electrical': 2,
    'Building Fabric': 2,
    'Fire Safety': 2,
    'Environmental Services': 1,
}

TRADE_GROUP_REGIONS = {
    3: ['East', 'North West', 'South West'],
    2: ['North', 'South'],
    1: [],
}


def get_trade_group_phase(trade_group: str) -> int:
    """Return the phase number (1-3) for a trade group."""
    return TRADE_GROUP_PHASES.get(trade_group, 1)


def get_trade_group_regions(trade_group: str) -> list:
    """Return the available regions for a trade group based on its phase."""
    phase = get_trade_group_phase(trade_group)
    return TRADE_GROUP_REGIONS[phase]


# ---------------------------------------------------------------------------
# Phase 2 postcode → region (North / South)
# ---------------------------------------------------------------------------

_P2_MAP_4 = {"UB11": "South"}

_P2_MAP_3_NORTH = {"SL9", "SL8", "SL7", "RG9", "RG8", "SN7"}
_P2_MAP_3_SOUTH = {"UB2", "UB4", "UB8", "UB7", "UB3"}

_P2_MAP_2_NORTH = {
    "RM", "IG", "EN", "WD", "HA", "UB", "NW", "WC", "EC", "WV", "WR", "WA",
    "WF", "WS", "WN",
}
_P2_MAP_2_SOUTH = {
    "SL", "SE", "SW", "TW", "KT", "SM", "CR", "BR", "DA", "ME", "TN", "BN",
    "RH", "GU", "SO", "BH", "SP", "CT", "PO", "RG", "BA", "EX", "TA", "BS",
    "DT", "SN", "PL", "TQ", "TR",
}

_P2_MAP_1_NORTH = {
    "N", "E", "L", "B", "G", "C", "S", "P", "H", "A", "M", "I", "D", "T",
    "Y", "F", "O", "W",
}


def postcode_to_region_phase2(postcode: str) -> str:
    """Map postcode to North/South region for Phase 2 trade groups."""
    if not isinstance(postcode, str) or len(postcode.strip()) < 1:
        return "Leads Without Postcode"

    pc = postcode.strip().upper()

    if pc[:4] in _P2_MAP_4:
        return _P2_MAP_4[pc[:4]]
    if pc[:3] in _P2_MAP_3_NORTH:
        return "North"
    if pc[:3] in _P2_MAP_3_SOUTH:
        return "South"
    if pc[:2] in _P2_MAP_2_NORTH:
        return "North"
    if pc[:2] in _P2_MAP_2_SOUTH:
        return "South"
    if pc[:1] in _P2_MAP_1_NORTH:
        return "North"

    return "Other"


# ---------------------------------------------------------------------------
# Phase 3 postcode → region (East / North West / South West)
# ---------------------------------------------------------------------------

_P3_MAP_4_EAST = {
    "NR33", "NR34", "NR35", "NR32", "SW1A", "SW1E", "SW1H", "SW1P",
    "SW1B", "SW1W", "SW1X", "SW1Y", "SW1V",
}
_P3_MAP_4_NW = {"LE16", "NW10", "NW11", "UB10"}
_P3_MAP_4_SW = {
    "BH24", "BH25", "SW20", "SW10", "SW11", "SW18", "SW12",
    "TN22", "TN20", "TN21", "TN19", "TN31", "TN32", "TN33", "TN34", "TN35",
    "TN36", "TN37", "TN38", "TN39", "TN40",
}

_P3_MAP_3_EAST = {"NW1", "EN9", "SG8", "WC1", "WC2", "N1C", "PE8"}
_P3_MAP_3_NW = {
    "N10", "N11", "N12", "N13", "N14", "N17", "N18", "N20", "N21", "N22",
    "NW2", "NW4", "NW7", "NW9", "RG8", "RG9", "UB9", "SN7", "NW3", "NW5",
    "NW6", "NW8", "W14", "W11", "W10", "N19", "N15", "N16", "UB6", "UB5",
    "SL9", "SL8", "SL7", "W12", "W13",
}
_P3_MAP_3_SW = {
    "SW4", "SW5", "SW2", "SW3", "SW6", "SW7", "SW8", "SW9", "TN7", "TN6", "TN5",
}

_P3_MAP_2_EAST = {
    "BR", "CB", "CM", "CO", "CT", "DA", "EC", "IG", "IP", "ME", "PE", "RM",
    "SE", "SS", "TN", "N1", "W1",
}
_P3_MAP_2_NW = {
    "NE", "HU", "YO", "LS", "HG", "TS", "DL", "CA", "LA", "PR", "FY", "HX",
    "DH", "OL", "HD", "W2", "W9", "W8", "AL", "EN", "HA", "HP", "LU", "MK",
    "N2", "N3", "N9", "NN", "OX", "SG", "WD", "NP", "NG", "GL", "HR", "LE",
    "CV", "WR", "DY", "ST", "TF", "LL", "CW", "SK", "WA", "WN", "LN", "DN",
    "N6", "N7", "N5", "N4", "N8", "SY", "CH", "DE", "WS", "WV", "BL", "W6",
    "W3", "W4", "W5", "WF", "W7",
}
_P3_MAP_2_SW = {
    "BN", "CR", "GU", "KT", "PO", "RG", "RH", "SL", "SN", "SO", "SW", "TW",
    "UB", "SM", "EX", "TQ", "PL", "DT", "BA", "BH", "SP", "BS", "CF", "SA",
    "TA", "TR",
}

_P3_MAP_1 = {"E": "East", "N": "East", "B": "North West", "S": "North West",
             "M": "North West", "L": "North West", "W": "South West"}


def postcode_to_region_phase3(postcode: str) -> str:
    """Map postcode to East/North West/South West region for Phase 3 trade groups."""
    if not isinstance(postcode, str) or len(postcode.strip()) < 1:
        return "Leads Without Postcode"

    pc = postcode.strip().upper()

    p4 = pc[:4]
    if p4 in _P3_MAP_4_EAST:
        return "East"
    if p4 in _P3_MAP_4_NW:
        return "North West"
    if p4 in _P3_MAP_4_SW:
        return "South West"

    p3 = pc[:3]
    if p3 in _P3_MAP_3_EAST:
        return "East"
    if p3 in _P3_MAP_3_NW:
        return "North West"
    if p3 in _P3_MAP_3_SW:
        return "South West"

    p2 = pc[:2]
    if p2 in _P3_MAP_2_EAST:
        return "East"
    if p2 in _P3_MAP_2_NW:
        return "North West"
    if p2 in _P3_MAP_2_SW:
        return "South West"

    p1 = pc[:1]
    if p1 in _P3_MAP_1:
        return _P3_MAP_1[p1]

    return "Other"
