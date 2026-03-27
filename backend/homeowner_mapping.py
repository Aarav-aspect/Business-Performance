# Postcode to region mapping
# Priority: 4-char prefix > 3-char prefix > 2-char prefix > 1-char prefix

_MAP_4 = {
    "NR33": "East", "NR34": "East", "NR35": "East", "NR32": "East",
    "SW1A": "Central", "SW1E": "Central", "SW1H": "Central", "SW1P": "Central",
    "SW1B": "Central", "SW1W": "Central", "SW1X": "Central", "SW1Y": "Central",
    "SW1V": "Central",
    "LE16": "North West",
    "NW10": "North West", "NW11": "North West",
    "UB10": "North West",
    "BH24": "South West", "BH25": "South West",
    "SW20": "South West", "SW10": "South West", "SW11": "South West",
    "SW18": "South West", "SW12": "South West",
    "TN22": "South West", "TN20": "South West", "TN21": "South West",
    "TN19": "South West", "TN31": "South West", "TN32": "South West",
    "TN33": "South West", "TN34": "South West", "TN35": "South West",
    "TN36": "South West", "TN37": "South West", "TN38": "South West",
    "TN39": "South West", "TN40": "South West",
}

_MAP_3 = {
    "NW1": "North West", "NW2": "North West", "NW3": "North West",
    "NW4": "North West", "NW5": "North West", "NW6": "North West",
    "NW7": "North West", "NW8": "North West", "NW9": "North West",
    "N1C": "North West",
    "N10": "North West", "N11": "North West", "N12": "North West",
    "N13": "North West", "N14": "North West", "N15": "North West",
    "N16": "North West", "N17": "North West", "N18": "North West",
    "N19": "North West", "N20": "North West", "N21": "North West",
    "N22": "North West",
    "W10": "North West", "W11": "North West", "W12": "North West",
    "W13": "North West", "W14": "North West",
    "UB5": "North West", "UB6": "North West", "UB9": "North West",
    "SL7": "North West", "SL8": "North West", "SL9": "North West",
    "PE8": "North West", "RG8": "North West", "RG9": "North West",
    "SN7": "North West",
    "EN9": "East", "SG8": "East",
    "WC1": "Central", "WC2": "Central",
    "SW2": "South West", "SW3": "South West", "SW4": "South West",
    "SW5": "South West", "SW6": "South West", "SW7": "South West",
    "SW8": "South West", "SW9": "South West",
    "TN5": "South West", "TN6": "South West", "TN7": "South West",
}

_MAP_2 = {
    "BR": "East", "CB": "East", "CM": "East", "CO": "East", "CT": "East",
    "DA": "East", "IG": "East", "IP": "East", "ME": "East", "PE": "East",
    "RM": "East", "SE": "East", "SS": "East",
    "N1": "North West",
    "N2": "North West", "N3": "North West", "N4": "North West",
    "N5": "North West", "N6": "North West", "N7": "North West",
    "N8": "North West", "N9": "North West",
    "NE": "North West", "HU": "North West", "YO": "North West",
    "LS": "North West", "HG": "North West", "TS": "North West",
    "DL": "North West", "CA": "North West", "LA": "North West",
    "PR": "North West", "FY": "North West", "HX": "North West",
    "DH": "North West", "OL": "North West", "HD": "North West",
    "W2": "North West", "W3": "North West", "W4": "North West",
    "W5": "North West", "W6": "North West", "W7": "North West",
    "W8": "North West", "W9": "North West",
    "AL": "North West", "EN": "North West", "HA": "North West",
    "HP": "North West", "LU": "North West", "MK": "North West",
    "NN": "North West", "OX": "North West", "SG": "North West",
    "WD": "North West", "NP": "North West", "NG": "North West",
    "GL": "North West", "HR": "North West", "LE": "North West",
    "CV": "North West", "WR": "North West", "DY": "North West",
    "ST": "North West", "TF": "North West", "LL": "North West",
    "CW": "North West", "SK": "North West", "WA": "North West",
    "WN": "North West", "LN": "North West", "DN": "North West",
    "SY": "North West", "CH": "North West", "DE": "North West",
    "WS": "North West", "WV": "North West", "BL": "North West",
    "WF": "North West",
    "EC": "Central", "W1": "Central",
    "BN": "South West", "CR": "South West", "GU": "South West",
    "KT": "South West", "PO": "South West", "RG": "South West",
    "RH": "South West", "SL": "South West", "SN": "South West",
    "SO": "South West", "SW": "South West", "TN": "South West",
    "TW": "South West", "UB": "South West", "SM": "South West",
    "EX": "South West", "TQ": "South West", "PL": "South West",
    "DT": "South West", "BA": "South West", "BH": "South West",
    "SP": "South West", "BS": "South West", "CF": "South West",
    "SA": "South West", "TA": "South West", "TR": "South West",
}

_MAP_1 = {
    "E": "East",
    "N": "East",
    "B": "North West",
    "S": "North West",
    "M": "North West",
    "L": "North West",
    "W": "South West",
}


def postcode_to_region(postcode) -> str:
    """Map a UK postcode to its region. Returns 'Other' if no match found."""
    if postcode is None or (not isinstance(postcode, str)):
        # Handles NaN, pd.NA, float, int, etc.
        return "Other"
    if not postcode:
        return "Other"
    pc = postcode.strip().upper().replace(" ", "")
    if len(pc) >= 4 and pc[:4] in _MAP_4:
        return _MAP_4[pc[:4]]
    if len(pc) >= 3 and pc[:3] in _MAP_3:
        return _MAP_3[pc[:3]]
    if len(pc) >= 2 and pc[:2] in _MAP_2:
        return _MAP_2[pc[:2]]
    if len(pc) >= 1 and pc[:1] in _MAP_1:
        return _MAP_1[pc[:1]]
    return "Other"
