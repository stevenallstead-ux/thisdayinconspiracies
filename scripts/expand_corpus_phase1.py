#!/usr/bin/env python3
"""
One-shot corpus expansion: +35 events across 5 under-represented domains
(deep history pre-1900, music industry, finance/banking, tech industry
secrecy, medical/pharmaceutical) chosen to bridge current hubs to rare
entities. Adds ~150 new entities to the registry.

Goal per the plan: open up alternate paths through the graph so K-shortest
returns *interesting* alternatives, not just hub-permutations.

This script is idempotent — events with an existing id are skipped, entities
with an existing id are skipped. Safe to re-run.

Run once: python scripts/expand_corpus_phase1.py
Then:     python scripts/derive_edges.py && python scripts/build_autocomplete.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_PATH = ROOT / "data" / "data.json"
ENTITIES_PATH = ROOT / "data" / "entities.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._slug import slugify  # noqa: E402


# ── NEW ENTITIES ──────────────────────────────────────────────────────────
NEW_ENTITIES = [
    # ── persons ──────────────────────────────────────────────────────────
    {"id": "philip-iv-of-france", "type": "person", "name": "King Philip IV of France", "aliases": ["Philip the Fair"]},
    {"id": "pope-clement-v", "type": "person", "name": "Pope Clement V", "aliases": []},
    {"id": "wolfgang-amadeus-mozart", "type": "person", "name": "Wolfgang Amadeus Mozart", "aliases": ["Mozart"]},
    {"id": "antonio-salieri", "type": "person", "name": "Antonio Salieri", "aliases": ["Salieri"]},
    {"id": "abraham-lincoln", "type": "person", "name": "Abraham Lincoln", "aliases": ["Lincoln"]},
    {"id": "john-wilkes-booth", "type": "person", "name": "John Wilkes Booth", "aliases": []},
    {"id": "james-a-garfield", "type": "person", "name": "James A. Garfield", "aliases": ["Garfield"]},
    {"id": "charles-guiteau", "type": "person", "name": "Charles Guiteau", "aliases": []},
    {"id": "jack-the-ripper", "type": "person", "name": "Jack the Ripper", "aliases": ["the Ripper"]},
    {"id": "mary-ann-nichols", "type": "person", "name": "Mary Ann Nichols", "aliases": ["Polly Nichols"]},
    {"id": "william-randolph-hearst", "type": "person", "name": "William Randolph Hearst", "aliases": ["Hearst"]},
    {"id": "warren-g-harding", "type": "person", "name": "Warren G. Harding", "aliases": ["Harding"]},
    {"id": "florence-harding", "type": "person", "name": "Florence Harding", "aliases": []},
    {"id": "buddy-holly", "type": "person", "name": "Buddy Holly", "aliases": []},
    {"id": "ritchie-valens", "type": "person", "name": "Ritchie Valens", "aliases": []},
    {"id": "big-bopper", "type": "person", "name": "The Big Bopper", "aliases": ["J.P. Richardson"]},
    {"id": "brian-jones", "type": "person", "name": "Brian Jones", "aliases": []},
    {"id": "jim-morrison", "type": "person", "name": "Jim Morrison", "aliases": []},
    {"id": "john-lennon", "type": "person", "name": "John Lennon", "aliases": ["Lennon"]},
    {"id": "mark-david-chapman", "type": "person", "name": "Mark David Chapman", "aliases": []},
    {"id": "yoko-ono", "type": "person", "name": "Yoko Ono", "aliases": []},
    {"id": "kurt-cobain", "type": "person", "name": "Kurt Cobain", "aliases": []},
    {"id": "courtney-love", "type": "person", "name": "Courtney Love", "aliases": []},
    {"id": "tom-grant", "type": "person", "name": "Tom Grant", "aliases": []},
    {"id": "notorious-big", "type": "person", "name": "The Notorious B.I.G.", "aliases": ["Biggie Smalls"]},
    {"id": "christopher-wallace", "type": "person", "name": "Christopher Wallace", "aliases": []},
    {"id": "tim-bergling", "type": "person", "name": "Tim Bergling", "aliases": []},
    {"id": "avicii", "type": "person", "name": "Avicii", "aliases": []},
    {"id": "nelson-aldrich", "type": "person", "name": "Nelson Aldrich", "aliases": []},
    {"id": "paul-warburg", "type": "person", "name": "Paul Warburg", "aliases": []},
    {"id": "andrew-mellon", "type": "person", "name": "Andrew Mellon", "aliases": []},
    {"id": "john-maynard-keynes", "type": "person", "name": "John Maynard Keynes", "aliases": ["Keynes"]},
    {"id": "harry-dexter-white", "type": "person", "name": "Harry Dexter White", "aliases": []},
    {"id": "donald-rumsfeld", "type": "person", "name": "Donald Rumsfeld", "aliases": ["Rumsfeld"]},
    {"id": "dick-fuld", "type": "person", "name": "Dick Fuld", "aliases": []},
    {"id": "henry-paulson", "type": "person", "name": "Henry Paulson", "aliases": ["Hank Paulson"]},
    {"id": "sam-bankman-fried", "type": "person", "name": "Sam Bankman-Fried", "aliases": ["SBF"]},
    {"id": "steve-jobs", "type": "person", "name": "Steve Jobs", "aliases": []},
    {"id": "steve-wozniak", "type": "person", "name": "Steve Wozniak", "aliases": ["Woz"]},
    {"id": "george-orwell", "type": "person", "name": "George Orwell", "aliases": ["Eric Blair"]},
    {"id": "ridley-scott", "type": "person", "name": "Ridley Scott", "aliases": []},
    {"id": "edward-snowden", "type": "person", "name": "Edward Snowden", "aliases": ["Snowden"]},
    {"id": "glenn-greenwald", "type": "person", "name": "Glenn Greenwald", "aliases": []},
    {"id": "christopher-wylie", "type": "person", "name": "Christopher Wylie", "aliases": []},
    {"id": "mark-zuckerberg", "type": "person", "name": "Mark Zuckerberg", "aliases": ["Zuck"]},
    {"id": "elon-musk", "type": "person", "name": "Elon Musk", "aliases": []},
    {"id": "jack-dorsey", "type": "person", "name": "Jack Dorsey", "aliases": []},
    {"id": "gerald-ford", "type": "person", "name": "Gerald Ford", "aliases": []},
    {"id": "larry-kramer", "type": "person", "name": "Larry Kramer", "aliases": []},
    {"id": "david-graham", "type": "person", "name": "David Graham", "aliases": []},
    {"id": "anthony-fauci", "type": "person", "name": "Anthony Fauci", "aliases": ["Fauci"]},
    {"id": "harry-truman", "type": "person", "name": "Harry S. Truman", "aliases": ["Truman"]},

    # ── orgs ─────────────────────────────────────────────────────────────
    {"id": "knights-templar", "type": "org", "name": "Knights Templar", "aliases": ["Order of the Temple"]},
    {"id": "freemasons", "type": "org", "name": "Freemasons", "aliases": ["Masonic Order"]},
    {"id": "rolling-stones", "type": "org", "name": "The Rolling Stones", "aliases": []},
    {"id": "the-doors", "type": "org", "name": "The Doors", "aliases": []},
    {"id": "the-beatles", "type": "org", "name": "The Beatles", "aliases": []},
    {"id": "nirvana", "type": "org", "name": "Nirvana", "aliases": []},
    {"id": "bad-boy-records", "type": "org", "name": "Bad Boy Records", "aliases": []},
    {"id": "federal-reserve", "type": "org", "name": "Federal Reserve", "aliases": ["the Fed"]},
    {"id": "lehman-brothers", "type": "org", "name": "Lehman Brothers", "aliases": []},
    {"id": "ftx", "type": "org", "name": "FTX", "aliases": []},
    {"id": "alameda-research", "type": "org", "name": "Alameda Research", "aliases": []},
    {"id": "imf", "type": "org", "name": "International Monetary Fund", "aliases": ["IMF"]},
    {"id": "world-bank", "type": "org", "name": "World Bank", "aliases": []},
    {"id": "apple-inc", "type": "org", "name": "Apple Inc.", "aliases": ["Apple"]},
    {"id": "bp-oil", "type": "org", "name": "BP", "aliases": ["British Petroleum"]},
    {"id": "nsa", "type": "org", "name": "National Security Agency", "aliases": ["NSA"]},
    {"id": "cambridge-analytica", "type": "org", "name": "Cambridge Analytica", "aliases": []},
    {"id": "facebook", "type": "org", "name": "Facebook", "aliases": []},
    {"id": "meta-platforms", "type": "org", "name": "Meta Platforms", "aliases": ["Meta"]},
    {"id": "crowdstrike", "type": "org", "name": "CrowdStrike", "aliases": []},
    {"id": "microsoft-windows", "type": "org", "name": "Microsoft Windows", "aliases": ["Windows"]},
    {"id": "us-public-health-service", "type": "org", "name": "U.S. Public Health Service", "aliases": ["USPHS"]},
    {"id": "cdc", "type": "org", "name": "Centers for Disease Control", "aliases": ["CDC"]},
    {"id": "act-up", "type": "org", "name": "ACT UP", "aliases": []},
    {"id": "merck", "type": "org", "name": "Merck & Co.", "aliases": ["Merck"]},
    {"id": "fda", "type": "org", "name": "Food and Drug Administration", "aliases": ["FDA"]},
    {"id": "purdue-pharma", "type": "org", "name": "Purdue Pharma", "aliases": []},
    {"id": "sackler-family", "type": "org", "name": "Sackler Family", "aliases": ["the Sacklers"]},
    {"id": "wuhan-institute-of-virology", "type": "org", "name": "Wuhan Institute of Virology", "aliases": ["WIV"]},
    {"id": "eco-health-alliance", "type": "org", "name": "EcoHealth Alliance", "aliases": []},
    {"id": "national-security-council", "type": "org", "name": "National Security Council", "aliases": ["NSC"]},

    # ── places ───────────────────────────────────────────────────────────
    {"id": "vienna", "type": "place", "name": "Vienna", "aliases": []},
    {"id": "ford-s-theatre", "type": "place", "name": "Ford's Theatre", "aliases": []},
    {"id": "whitechapel", "type": "place", "name": "Whitechapel, London", "aliases": []},
    {"id": "victorian-london", "type": "place", "name": "Victorian London", "aliases": []},
    {"id": "havana", "type": "place", "name": "Havana, Cuba", "aliases": []},
    {"id": "san-francisco", "type": "place", "name": "San Francisco", "aliases": []},
    {"id": "iowa", "type": "place", "name": "Iowa", "aliases": []},
    {"id": "the-dakota", "type": "place", "name": "The Dakota (NYC)", "aliases": []},
    {"id": "seattle", "type": "place", "name": "Seattle", "aliases": []},
    {"id": "oman", "type": "place", "name": "Oman", "aliases": []},
    {"id": "jekyll-island", "type": "place", "name": "Jekyll Island, Georgia", "aliases": []},
    {"id": "wall-street", "type": "place", "name": "Wall Street", "aliases": []},
    {"id": "bretton-woods", "type": "place", "name": "Bretton Woods, NH", "aliases": []},
    {"id": "cupertino", "type": "place", "name": "Cupertino, California", "aliases": []},
    {"id": "silicon-valley", "type": "place", "name": "Silicon Valley", "aliases": []},
    {"id": "gulf-of-mexico", "type": "place", "name": "Gulf of Mexico", "aliases": []},
    {"id": "hong-kong", "type": "place", "name": "Hong Kong", "aliases": []},
    {"id": "tuskegee-alabama", "type": "place", "name": "Tuskegee, Alabama", "aliases": []},
    {"id": "wuhan", "type": "place", "name": "Wuhan, China", "aliases": []},
    {"id": "fort-detrick", "type": "place", "name": "Fort Detrick, Maryland", "aliases": []},

    # ── programs ─────────────────────────────────────────────────────────
    {"id": "prism-program", "type": "program", "name": "PRISM (NSA)", "aliases": ["PRISM surveillance"]},

    # ── named events / things ────────────────────────────────────────────
    {"id": "the-magic-flute", "type": "event", "name": "The Magic Flute (opera)", "aliases": []},
    {"id": "uss-maine", "type": "event", "name": "USS Maine (battleship)", "aliases": []},
    {"id": "spanish-american-war", "type": "event", "name": "Spanish-American War", "aliases": []},
    {"id": "teapot-dome-scandal", "type": "event", "name": "Teapot Dome Scandal", "aliases": []},
    {"id": "27-club", "type": "event", "name": "The 27 Club", "aliases": []},
    {"id": "nixon-shock", "type": "event", "name": "The Nixon Shock", "aliases": []},
    {"id": "pentagon-accounting-scandal", "type": "event", "name": "Pentagon $2.3T Accounting Scandal", "aliases": []},
    {"id": "2008-financial-crisis", "type": "event", "name": "2008 Financial Crisis", "aliases": ["GFC"]},
    {"id": "macintosh", "type": "event", "name": "Macintosh (1984)", "aliases": ["Mac"]},
    {"id": "1984-novel", "type": "event", "name": "1984 (Orwell novel)", "aliases": ["Nineteen Eighty-Four"]},
    {"id": "deepwater-horizon", "type": "event", "name": "Deepwater Horizon oil rig", "aliases": []},
    {"id": "twitter-files", "type": "event", "name": "The Twitter Files", "aliases": []},
    {"id": "tuskegee-syphilis-study", "type": "event", "name": "Tuskegee Syphilis Study", "aliases": []},
    {"id": "swine-flu-1976", "type": "event", "name": "1976 Swine Flu Vaccine Program", "aliases": []},
    {"id": "mmwr", "type": "event", "name": "MMWR (CDC weekly report)", "aliases": []},
    {"id": "vioxx", "type": "event", "name": "Vioxx (rofecoxib)", "aliases": []},
    {"id": "opioid-crisis", "type": "event", "name": "U.S. Opioid Crisis", "aliases": []},
    {"id": "covid-19", "type": "event", "name": "COVID-19", "aliases": ["SARS-CoV-2"]},
    {"id": "aids-epidemic", "type": "event", "name": "AIDS Epidemic", "aliases": []},
    {"id": "black-tuesday", "type": "event", "name": "Black Tuesday (1929)", "aliases": []},
    {"id": "national-security-act-1947", "type": "event", "name": "National Security Act of 1947", "aliases": []},

    # ── topics (bridging concepts) ───────────────────────────────────────
    {"id": "medieval-secret-society", "type": "topic", "name": "Medieval Secret Society", "aliases": []},
    {"id": "friday-the-13th", "type": "topic", "name": "Friday the 13th Lore", "aliases": []},
    {"id": "confederate-conspiracy", "type": "topic", "name": "Confederate Conspiracy Theories", "aliases": []},
    {"id": "yellow-journalism", "type": "topic", "name": "Yellow Journalism", "aliases": []},
    {"id": "music-industry", "type": "topic", "name": "Music Industry Conspiracies", "aliases": []},
    {"id": "east-coast-west-coast-rivalry", "type": "topic", "name": "East Coast vs West Coast Rap Rivalry", "aliases": []},
    {"id": "electronic-music-industry", "type": "topic", "name": "Electronic Music Industry", "aliases": []},
    {"id": "central-banking", "type": "topic", "name": "Central Banking Conspiracies", "aliases": []},
    {"id": "gold-standard", "type": "topic", "name": "Gold Standard / Hard Money", "aliases": []},
    {"id": "petrodollar", "type": "topic", "name": "Petrodollar System", "aliases": []},
    {"id": "subprime-mortgage", "type": "topic", "name": "Subprime Mortgage Crisis", "aliases": []},
    {"id": "crypto-industry", "type": "topic", "name": "Cryptocurrency Industry", "aliases": []},
    {"id": "effective-altruism", "type": "topic", "name": "Effective Altruism", "aliases": ["EA"]},
    {"id": "surveillance-state", "type": "topic", "name": "Surveillance State", "aliases": []},
    {"id": "data-harvesting", "type": "topic", "name": "Mass Data Harvesting", "aliases": []},
    {"id": "social-media", "type": "topic", "name": "Social Media Manipulation", "aliases": []},
    {"id": "infrastructure-fragility", "type": "topic", "name": "Infrastructure Fragility", "aliases": []},
    {"id": "single-point-of-failure", "type": "topic", "name": "Single Point of Failure", "aliases": []},
    {"id": "medical-experimentation", "type": "topic", "name": "Medical Experimentation on Humans", "aliases": []},
    {"id": "informed-consent-violation", "type": "topic", "name": "Informed Consent Violation", "aliases": []},
    {"id": "vaccine-injury", "type": "topic", "name": "Vaccine Injury", "aliases": []},
    {"id": "pharma-suppression", "type": "topic", "name": "Pharma Suppression", "aliases": []},
    {"id": "hiv-virus", "type": "topic", "name": "HIV / AIDS Origin Theories", "aliases": []},
    {"id": "oxycontin", "type": "topic", "name": "OxyContin", "aliases": []},
    {"id": "gain-of-function-research", "type": "topic", "name": "Gain-of-Function Research", "aliases": []},
    {"id": "oil-industry", "type": "topic", "name": "Oil Industry Cover-ups", "aliases": []},
    {"id": "corexit", "type": "topic", "name": "Corexit (oil dispersant)", "aliases": []},
    {"id": "unsolved-mystery", "type": "topic", "name": "Unsolved Historical Mystery", "aliases": []},
]


# ── NEW EVENTS ────────────────────────────────────────────────────────────
NEW_EVENTS = [
    # ── Domain 1: Deep history pre-1900 ──────────────────────────────────
    {
        "date": "10-13", "year": 1307,
        "title": "Friday the 13th: Knights Templar Arrested Across France",
        "category": "Political",
        "summary": "King Philip IV of France arrested every Knight Templar in his realm in a coordinated dawn raid. The order was tortured into confession, suppressed by Pope Clement V, and its fortune vanished — fueling 700 years of secret-society lore.",
        "theories": [
            "The Templar treasure was secreted to Scotland and seeded the Freemasons",
            "Surviving Templars founded the Bavarian Illuminati centuries later",
            "Friday the 13th's bad-luck association traces directly to this date",
        ],
        "entities": [
            "knights-templar", "philip-iv-of-france", "pope-clement-v",
            "medieval-secret-society", "friday-the-13th", "bavarian-illuminati",
            "occultism", "shadow-government",
        ],
    },
    {
        "date": "12-05", "year": 1791,
        "title": "Mozart Dies Mysteriously at 35",
        "category": "Celebrity",
        "summary": "Wolfgang Amadeus Mozart died after weeks of a wasting illness at age 35, weeks after completing The Magic Flute — an opera packed with explicit Masonic symbolism. He believed he was being poisoned. The cause of death is officially uncertain.",
        "theories": [
            "Antonio Salieri poisoned him out of jealousy",
            "The Freemasons silenced him for revealing initiation rites in The Magic Flute",
            "Mercury poisoning from syphilis treatment, not murder",
        ],
        "entities": [
            "wolfgang-amadeus-mozart", "antonio-salieri", "freemasons",
            "the-magic-flute", "vienna", "occultism", "celebrity-death",
            "political-assassination",
        ],
    },
    {
        "date": "04-14", "year": 1865,
        "title": "Lincoln Assassinated at Ford's Theatre",
        "category": "Political",
        "summary": "President Abraham Lincoln was shot by John Wilkes Booth during a performance of 'Our American Cousin' at Ford's Theatre. The conspiracy involved coordinated attacks on multiple administration officials the same night, suggesting a wider plot than was publicly admitted.",
        "theories": [
            "Confederate intelligence services orchestrated the plot",
            "Edwin Stanton (Secretary of War) had advance knowledge",
            "Booth escaped and a body double was killed in the barn",
        ],
        "entities": [
            "abraham-lincoln", "john-wilkes-booth", "ford-s-theatre",
            "washington-dc", "confederate-conspiracy", "political-assassination",
            "second-shooter", "body-double", "cover-up",
        ],
    },
    {
        "date": "07-02", "year": 1881,
        "title": "President Garfield Shot at Train Station",
        "category": "Political",
        "summary": "James A. Garfield was shot by Charles Guiteau at a Washington train station and lingered for 79 days. Modern analysis suggests his physicians' bloodletting and unsterilized probing killed him more surely than the bullet itself.",
        "theories": [
            "The Stalwart faction within his own party arranged the shooting",
            "Bloodletting medicine was the actual cause of death, not the bullet",
            "Vice President Chester Arthur's Stalwart allies coordinated with Guiteau",
        ],
        "entities": [
            "james-a-garfield", "charles-guiteau", "washington-dc",
            "bloodletting", "political-assassination", "cover-up",
        ],
    },
    {
        "date": "08-31", "year": 1888,
        "title": "First Jack the Ripper Murder in Whitechapel",
        "category": "Unexplained",
        "summary": "Mary Ann Nichols was found murdered in Whitechapel, the first canonical victim of Jack the Ripper. Despite a massive manhunt and decades of investigation, the killer was never identified. Suspects ranged from royal physicians to a member of the royal family.",
        "theories": [
            "Royal physician Sir William Gull committed the murders to protect the Crown",
            "Prince Albert Victor (Queen Victoria's grandson) was the Ripper",
            "The Freemasons covered up the killer's identity to protect a high-ranking member",
        ],
        "entities": [
            "jack-the-ripper", "whitechapel", "mary-ann-nichols",
            "victorian-london", "unsolved-mystery", "royal-family-uk",
            "freemasons", "mi6", "occultism", "cover-up",
        ],
    },
    {
        "date": "02-15", "year": 1898,
        "title": "USS Maine Explodes in Havana Harbor",
        "category": "Government",
        "summary": "The U.S. battleship Maine exploded and sank in Havana Harbor, killing 266 sailors. William Randolph Hearst's newspapers immediately blamed Spain ('Remember the Maine!'), driving public demand for the Spanish-American War. A 1976 Navy study concluded the cause was likely an internal coal-bunker fire.",
        "theories": [
            "U.S. agents sank the Maine to manufacture pretext for war",
            "Hearst's papers manufactured the war for circulation profits",
            "Internal coal-bunker fire (modern consensus)",
        ],
        "entities": [
            "uss-maine", "havana", "cuba", "william-randolph-hearst",
            "yellow-journalism", "spanish-american-war", "false-flag",
            "us-military", "us-navy", "sabotage",
        ],
    },
    {
        "date": "08-02", "year": 1923,
        "title": "President Warren Harding Dies Suddenly in San Francisco",
        "category": "Political",
        "summary": "Warren G. Harding died at age 57 in a San Francisco hotel under disputed circumstances during a cross-country tour. His widow Florence refused an autopsy. Within months, the Teapot Dome scandal broke, revealing massive corruption in his administration.",
        "theories": [
            "Florence Harding poisoned him to end the impending scandal",
            "Teapot Dome conspirators silenced him before he could testify",
            "Cerebral hemorrhage following Bohemian Grove encounter (fringe)",
        ],
        "entities": [
            "warren-g-harding", "florence-harding", "teapot-dome-scandal",
            "san-francisco", "political-assassination", "cover-up",
        ],
    },

    # ── Domain 2: Music industry deaths ───────────────────────────────────
    {
        "date": "02-03", "year": 1959,
        "title": "The Day the Music Died — Buddy Holly Plane Crash",
        "category": "Celebrity",
        "summary": "Buddy Holly, Ritchie Valens, and J.P. 'Big Bopper' Richardson died when their chartered Beechcraft crashed in an Iowa cornfield. Waylon Jennings gave up his seat hours before the flight; the seat went to the Big Bopper instead. Decades of speculation about pilot error, weather, and possible foul play.",
        "theories": [
            "Holly's manager arranged the crash over royalty disputes",
            "The pilot was inexperienced in instrument flying — established",
            "Cover-up of pilot's drug use to protect the charter company",
        ],
        "entities": [
            "buddy-holly", "ritchie-valens", "big-bopper", "iowa",
            "aviation-disaster", "celebrity-death", "music-industry",
            "sabotage", "cover-up",
        ],
    },
    {
        "date": "07-03", "year": 1969,
        "title": "Brian Jones Found Dead in His Swimming Pool",
        "category": "Celebrity",
        "summary": "Rolling Stones founder Brian Jones was found dead in his swimming pool weeks after being fired from the band. The official ruling was 'death by misadventure.' His builder Frank Thorogood made a deathbed confession to murder in 1993.",
        "theories": [
            "Frank Thorogood drowned him over an unpaid bill (his deathbed confession)",
            "Drug overdose covered up to protect the band's image",
            "The Rolling Stones management arranged it to clear the way for Mick Taylor",
        ],
        "entities": [
            "brian-jones", "rolling-stones", "27-club", "music-industry",
            "celebrity-death", "faked-death", "mafia",
        ],
    },
    {
        "date": "07-03", "year": 1971,
        "title": "Jim Morrison Dies in a Paris Bathtub",
        "category": "Celebrity",
        "summary": "The Doors frontman Jim Morrison was found dead in a Paris apartment bathtub at age 27, exactly two years to the day after Brian Jones. No autopsy was performed. Only a handful of people viewed the body before the sealed casket burial. Sightings have continued for decades.",
        "theories": [
            "Heroin overdose at the Rock 'n' Roll Circus, body moved to apartment",
            "He faked his death to escape obscenity charges and live in Africa",
            "CIA Operation CHAOS targeted him as a counterculture leader",
        ],
        "entities": [
            "jim-morrison", "the-doors", "paris", "27-club",
            "music-industry", "celebrity-death", "faked-death", "cia",
        ],
    },
    {
        "date": "12-08", "year": 1980,
        "title": "John Lennon Assassinated Outside The Dakota",
        "category": "Celebrity",
        "summary": "Mark David Chapman shot John Lennon four times outside Lennon's Manhattan apartment building, The Dakota. Chapman remained at the scene reading 'The Catcher in the Rye' until police arrived. His behavior has long been compared to MKUltra-style programmed behavior.",
        "theories": [
            "Chapman was an MKUltra-programmed assassin",
            "FBI files on Lennon (released 2006) prove decade-long surveillance",
            "Yoko Ono had advance knowledge of the plot",
        ],
        "entities": [
            "john-lennon", "mark-david-chapman", "the-dakota", "the-beatles",
            "yoko-ono", "new-york-city", "political-assassination",
            "mind-control", "music-industry", "mkultra", "fbi",
        ],
    },
    {
        "date": "04-08", "year": 1994,
        "title": "Kurt Cobain Found Dead in Seattle Greenhouse",
        "category": "Celebrity",
        "summary": "Nirvana frontman Kurt Cobain was found dead of a shotgun wound at his Seattle home. Officially ruled suicide despite a heroin level three times the lethal dose (which would have rendered him unable to operate the gun). Private investigator Tom Grant has spent 30 years arguing for a homicide reinvestigation.",
        "theories": [
            "Courtney Love arranged the murder — Tom Grant's documented theory",
            "He faked his death and is living in South America",
            "Heroin overdose covered up to look like suicide for insurance reasons",
        ],
        "entities": [
            "kurt-cobain", "nirvana", "courtney-love", "seattle", "tom-grant",
            "27-club", "music-industry", "celebrity-death", "suicide-ruled",
            "faked-death",
        ],
    },
    {
        "date": "03-09", "year": 1997,
        "title": "Notorious B.I.G. Killed in Los Angeles Drive-By",
        "category": "Celebrity",
        "summary": "Christopher Wallace (The Notorious B.I.G.) was shot dead in a drive-by shooting after leaving a Vibe magazine party in Los Angeles, six months after Tupac Shakur was killed in Las Vegas. The case officially remains unsolved.",
        "theories": [
            "Suge Knight ordered both the Tupac and Biggie killings",
            "LAPD officer David Mack was directly involved",
            "FBI / LAPD cover-up of corrupt officer involvement (proven by lawsuits)",
        ],
        "entities": [
            "notorious-big", "christopher-wallace", "bad-boy-records",
            "east-coast-west-coast-rivalry", "los-angeles", "mafia",
            "music-industry", "celebrity-death", "drive-by-shooting",
            "suge-knight", "fbi", "cover-up",
        ],
    },
    {
        "date": "04-20", "year": 2018,
        "title": "Avicii Dies in Oman",
        "category": "Celebrity",
        "summary": "Swedish DJ Tim Bergling (Avicii) was found dead in Muscat, Oman at age 28. Officially ruled suicide following self-inflicted injuries with a broken wine bottle — a method that has struck many as implausible. He had been making a documentary about the dark side of the music industry.",
        "theories": [
            "Music industry executives silenced him over his exposé documentary",
            "He uncovered EDM industry money laundering tied to crypto",
            "Self-inflicted death following years of forced touring (official)",
        ],
        "entities": [
            "tim-bergling", "avicii", "oman", "electronic-music-industry",
            "music-industry", "celebrity-death", "suicide-ruled",
            "faked-death", "crypto-industry",
        ],
    },

    # ── Domain 3: Finance / banking ───────────────────────────────────────
    {
        "date": "11-22", "year": 1910,
        "title": "Jekyll Island Secret Banker Meeting Drafts the Federal Reserve",
        "category": "Government",
        "summary": "Senator Nelson Aldrich and Wall Street representatives including Paul Warburg met in absolute secrecy at the Jekyll Island Club, Georgia, to draft what became the Federal Reserve Act of 1913. Participants traveled under aliases. The meeting was denied for decades before being confirmed.",
        "theories": [
            "The Fed is a private banking cartel disguised as government",
            "J.P. Morgan engineered the 1907 panic to manufacture Fed support",
            "International banking interests captured U.S. monetary sovereignty",
        ],
        "entities": [
            "jekyll-island", "nelson-aldrich", "federal-reserve", "paul-warburg",
            "central-banking", "j-p-morgan", "shadow-government", "cover-up",
        ],
    },
    {
        "date": "10-29", "year": 1929,
        "title": "Black Tuesday Wall Street Crash",
        "category": "Government",
        "summary": "The Wall Street Crash erased $14 billion in a single day, triggering the Great Depression. Andrew Mellon and other 'banker pool' figures had reportedly sold heavily in the months prior. Some historians argue the crash was deliberately engineered to consolidate banking power.",
        "theories": [
            "The Federal Reserve deliberately tightened credit to crash markets",
            "Insider banker pool short-sold while pumping public confidence",
            "Foreign banking interests profited by buying assets at pennies on the dollar",
        ],
        "entities": [
            "wall-street", "black-tuesday", "andrew-mellon", "federal-reserve",
            "central-banking", "j-p-morgan", "shadow-government", "cover-up",
        ],
    },
    {
        "date": "07-22", "year": 1944,
        "title": "Bretton Woods Conference Establishes Dollar Hegemony",
        "category": "Government",
        "summary": "Delegates from 44 Allied nations met at Bretton Woods, New Hampshire to design the post-war monetary system. The dollar became the world's reserve currency, pegged to gold. American delegate Harry Dexter White, who shaped the conference, was later identified as a Soviet intelligence asset.",
        "theories": [
            "Soviet spy Harry Dexter White shaped the IMF to weaken U.S. position",
            "Keynes's superior 'bancor' currency was rejected to entrench dollar power",
            "The conference was rigged to ensure American banking dominance",
        ],
        "entities": [
            "bretton-woods", "john-maynard-keynes", "harry-dexter-white",
            "imf", "world-bank", "central-banking", "soviet-union", "spy-ring",
            "cover-up",
        ],
    },
    {
        "date": "08-15", "year": 1971,
        "title": "Nixon Closes the Gold Window (The Nixon Shock)",
        "category": "Government",
        "summary": "President Nixon ended dollar convertibility to gold, unilaterally collapsing the Bretton Woods system. Within years the petrodollar arrangement with Saudi Arabia replaced gold as the dollar's anchor. The decision was made over a secret weekend at Camp David.",
        "theories": [
            "Move designed to enable unlimited Vietnam War financing",
            "Petrodollar deal locked OPEC into dollar dependency by force",
            "Secret weekend group included unelected banking advisors",
        ],
        "entities": [
            "nixon-shock", "gold-standard", "petrodollar", "richard-nixon",
            "federal-reserve", "central-banking", "shadow-government", "camp-david",
        ],
    },
    {
        "date": "09-10", "year": 2001,
        "title": "Rumsfeld Announces $2.3 Trillion Pentagon Loss",
        "category": "Government",
        "summary": "Defense Secretary Donald Rumsfeld held a press conference acknowledging the Pentagon could not account for $2.3 trillion in transactions. The story disappeared from headlines the next morning when 9/11 struck. The accounting office that was investigating the discrepancy was destroyed in the Pentagon attack.",
        "theories": [
            "The 9/11 attacks were timed to bury the accounting investigation",
            "The missing trillions funded black-budget shadow operations",
            "Rumsfeld's speech was deliberate political cover-out before a known event",
        ],
        "entities": [
            "donald-rumsfeld", "pentagon-accounting-scandal", "pentagon",
            "advance-knowledge", "cover-up", "shadow-government",
            "world-trade-center",
        ],
    },
    {
        "date": "09-15", "year": 2008,
        "title": "Lehman Brothers Files for Bankruptcy",
        "category": "Government",
        "summary": "Lehman Brothers filed for the largest bankruptcy in U.S. history, triggering a global financial cascade. CEO Dick Fuld blamed Treasury Secretary Henry Paulson (formerly of Goldman Sachs, Lehman's chief rival) for engineering the failure while saving Goldman, AIG, and Bear Stearns.",
        "theories": [
            "Paulson deliberately let Lehman fail to benefit Goldman Sachs",
            "The crisis enabled the largest wealth transfer in modern history",
            "Subprime mortgage losses were known and concealed for years",
        ],
        "entities": [
            "lehman-brothers", "dick-fuld", "2008-financial-crisis",
            "henry-paulson", "subprime-mortgage", "federal-reserve",
            "central-banking", "wall-street", "cover-up",
        ],
    },
    {
        "date": "11-11", "year": 2022,
        "title": "FTX Collapses — Sam Bankman-Fried Arrested",
        "category": "Political",
        "summary": "Crypto exchange FTX filed for bankruptcy after a $32 billion valuation collapse. CEO Sam Bankman-Fried, the second-largest Democratic donor in 2022, was charged with massive fraud. FTX customer funds had been routed to his hedge fund Alameda Research and reportedly to political donations.",
        "theories": [
            "FTX was a money-laundering pipeline for Ukraine aid kickbacks",
            "Effective Altruism movement provided cover for political capture",
            "Parents (both Stanford law professors) helped structure the fraud",
        ],
        "entities": [
            "ftx", "sam-bankman-fried", "alameda-research", "crypto-industry",
            "effective-altruism", "dnc", "cover-up", "central-banking",
        ],
    },

    # ── Domain 4: Tech industry secrecy ───────────────────────────────────
    {
        "date": "04-01", "year": 1976,
        "title": "Apple Computer Founded on April Fool's Day",
        "category": "Unexplained",
        "summary": "Steve Jobs, Steve Wozniak, and Ronald Wayne founded Apple Computer in a Cupertino garage on April 1, 1976. The original Apple I sold for $666.66. Jobs's later interest in calligraphy, Eastern mysticism, and reality distortion fueled decades of occult-symbolism claims about the company's branding.",
        "theories": [
            "The $666.66 price was deliberate occult signaling by Wozniak's pricing",
            "Apple's founding was timed by astrological calculation",
            "Jobs's countercultural pose concealed deep ties to military DARPA contracts",
        ],
        "entities": [
            "apple-inc", "steve-jobs", "steve-wozniak", "cupertino",
            "silicon-valley", "occultism", "classified-aerospace",
        ],
    },
    {
        "date": "01-22", "year": 1984,
        "title": "Apple Airs the '1984' Macintosh Super Bowl Ad",
        "category": "Unexplained",
        "summary": "Apple's '1984' Super Bowl ad, directed by Ridley Scott, depicted a woman destroying Big Brother's screen — positioning Macintosh as liberation from IBM's Orwellian control. Forty years on, critics note Apple itself became the surveillance dystopia the ad warned against.",
        "theories": [
            "The ad was pre-emptive misdirection — Apple's true goal was the surveillance role",
            "Steve Jobs personally chose Orwell's date for occult-mathematical reasons",
            "Ridley Scott's Blade Runner / 1984 / Alien trilogy is a coordinated programming arc",
        ],
        "entities": [
            "macintosh", "george-orwell", "1984-novel", "ridley-scott",
            "apple-inc", "steve-jobs", "silicon-valley", "mind-control",
            "surveillance-state",
        ],
    },
    {
        "date": "04-20", "year": 2010,
        "title": "Deepwater Horizon Explodes in the Gulf of Mexico",
        "category": "Government",
        "summary": "BP's Deepwater Horizon oil rig exploded, killing 11 workers and unleashing the largest marine oil spill in U.S. history. The chemical dispersant Corexit, applied at unprecedented scale, was later linked to severe long-term health effects. BP's safety violations were systematic and known.",
        "theories": [
            "Corexit was used to hide oil volume from public satellite imaging",
            "The blowout was caused by deliberate sabotage to spike oil prices",
            "BP knew of the equipment failure for weeks before the explosion",
        ],
        "entities": [
            "deepwater-horizon", "bp-oil", "gulf-of-mexico", "corexit",
            "oil-industry", "sabotage", "cover-up", "classified-aerospace",
        ],
    },
    {
        "date": "06-06", "year": 2013,
        "title": "Edward Snowden NSA Leaks Begin",
        "category": "Government",
        "summary": "The Guardian and Washington Post published the first Snowden leaks revealing PRISM and the NSA's mass collection of American phone metadata. Snowden, an NSA contractor, fled to Hong Kong and ultimately to Russia. The leaks fundamentally changed public understanding of the surveillance state.",
        "theories": [
            "Snowden was a Russian intelligence asset all along",
            "The leaks were a controlled limited hangout — worse programs remain hidden",
            "Glenn Greenwald and Laura Poitras were vetted to filter what got published",
        ],
        "entities": [
            "edward-snowden", "nsa", "prism-program", "glenn-greenwald",
            "surveillance-state", "hong-kong", "whistleblower", "cia",
            "shadow-government",
        ],
    },
    {
        "date": "03-17", "year": 2018,
        "title": "Cambridge Analytica Whistleblower Goes Public",
        "category": "Political",
        "summary": "Christopher Wylie revealed how Cambridge Analytica had harvested data from 87 million Facebook users to micro-target political ads in the 2016 Trump campaign and Brexit referendum. The story exposed the extent of social-media-driven psychological manipulation in democratic processes.",
        "theories": [
            "The exposé itself was a controlled limited hangout to protect bigger players",
            "Facebook knew and approved the data exfiltration in advance",
            "Cambridge Analytica's parent SCL had decades of military psyop contracts",
        ],
        "entities": [
            "cambridge-analytica", "christopher-wylie", "facebook",
            "meta-platforms", "data-harvesting", "mark-zuckerberg",
            "surveillance-state", "mind-control", "whistleblower",
            "social-media",
        ],
    },
    {
        "date": "10-27", "year": 2022,
        "title": "Elon Musk Closes the Twitter Acquisition for $44 Billion",
        "category": "Political",
        "summary": "Elon Musk completed his acquisition of Twitter and immediately fired top executives. The subsequent 'Twitter Files' release of internal communications revealed extensive coordination between the platform, the FBI, and intelligence agencies on content moderation decisions.",
        "theories": [
            "Musk was permitted to buy Twitter to launder intelligence-community equities",
            "The Twitter Files release was a controlled leak protecting the deeper apparatus",
            "Jack Dorsey deliberately sold to Musk to expose the FBI relationship",
        ],
        "entities": [
            "elon-musk", "twitter-files", "jack-dorsey", "social-media",
            "fbi", "cia", "surveillance-state", "shadow-government", "cover-up",
        ],
    },
    {
        "date": "07-19", "year": 2024,
        "title": "CrowdStrike Update Causes Global IT Outage",
        "category": "Unexplained",
        "summary": "A faulty CrowdStrike security update crashed an estimated 8.5 million Windows machines worldwide in hours, grounding airlines, paralyzing hospitals and banks. The single bad update demonstrated how fragile global infrastructure had become to single-point-of-failure cybersecurity vendors.",
        "theories": [
            "The 'accident' was a stress test of nation-state cyberattack response",
            "CrowdStrike's deep ties to U.S. intelligence enabled the deployment privilege",
            "A coordinated Microsoft-CrowdStrike consolidation was the actual goal",
        ],
        "entities": [
            "crowdstrike", "microsoft-windows", "infrastructure-fragility",
            "single-point-of-failure", "sabotage", "cover-up", "nsa",
        ],
    },

    # ── Domain 5: Medical / pharmaceutical ────────────────────────────────
    {
        "date": "10-01", "year": 1932,
        "title": "Tuskegee Syphilis Study Begins",
        "category": "Government",
        "summary": "The U.S. Public Health Service began a 40-year study of untreated syphilis in 399 Black men in Tuskegee, Alabama. The men were never told they had syphilis and were denied penicillin even after it became standard treatment in 1947. The study only ended in 1972 after a press exposé.",
        "theories": [
            "Tuskegee was one of many — most experiments remain classified",
            "MKUltra and Tuskegee shared personnel and methodology",
            "The CDC actively shielded the program from internal whistleblowers",
        ],
        "entities": [
            "tuskegee-syphilis-study", "us-public-health-service",
            "tuskegee-alabama", "medical-experimentation",
            "informed-consent-violation", "mkultra", "cia", "cdc",
            "cover-up", "radiation",
        ],
    },
    {
        "date": "10-01", "year": 1976,
        "title": "Swine Flu Vaccine Panic Begins",
        "category": "Government",
        "summary": "After a single soldier died of swine flu at Fort Dix, President Ford launched a $137 million crash vaccination program for every American. The pandemic never materialized. Hundreds of vaccine recipients developed Guillain-Barré syndrome. The CDC paid $93 million in damages.",
        "theories": [
            "The program was a pharmaceutical-industry trial run for future emergencies",
            "Vaccine injury data was systematically hidden for decades",
            "A test of population-scale rapid-deployment biological response",
        ],
        "entities": [
            "swine-flu-1976", "gerald-ford", "cdc", "vaccine-injury",
            "pharma-suppression", "us-government", "cover-up",
        ],
    },
    {
        "date": "06-05", "year": 1981,
        "title": "First AIDS Cases Reported in CDC's MMWR",
        "category": "Unexplained",
        "summary": "The CDC's Morbidity and Mortality Weekly Report described five cases of pneumonia in previously healthy gay men in Los Angeles — the first official AIDS report. The Reagan administration ignored the epidemic for years. ACT UP eventually forced action; conspiracy theories about HIV's origin persist.",
        "theories": [
            "HIV was engineered as a biological weapon at Fort Detrick",
            "The slow government response was deliberate, targeting marginalized communities",
            "The MMWR delay between first cases and announcement hid earlier deaths",
        ],
        "entities": [
            "aids-epidemic", "hiv-virus", "mmwr", "larry-kramer", "act-up",
            "cdc", "pharma-suppression", "cia", "cover-up", "fort-detrick",
            "los-angeles",
        ],
    },
    {
        "date": "09-30", "year": 2004,
        "title": "Vioxx Withdrawn After Heart Attack Cover-Up",
        "category": "Government",
        "summary": "Merck pulled Vioxx from the market after FDA whistleblower Dr. David Graham testified that the drug had caused an estimated 88,000 to 139,000 heart attacks. Internal Merck documents showed executives had known of the cardiac risk for years before withdrawal.",
        "theories": [
            "FDA leadership actively suppressed Graham's findings under industry pressure",
            "Merck calculated that the lawsuits would cost less than continued sales",
            "Hundreds of thousands more deaths than officially acknowledged",
        ],
        "entities": [
            "vioxx", "merck", "pharma-suppression", "david-graham", "fda",
            "whistleblower", "cover-up",
        ],
    },
    {
        "date": "10-26", "year": 2017,
        "title": "Trump Declares Opioid Crisis a Public Health Emergency",
        "category": "Political",
        "summary": "President Trump declared the opioid epidemic a public health emergency, formally acknowledging a crisis that by then had killed hundreds of thousands. The Sackler family and Purdue Pharma had spent two decades aggressively marketing OxyContin while concealing addiction risks documented in their own internal data.",
        "theories": [
            "DEA was deliberately defanged to allow Purdue's distribution scale",
            "Sackler family extracted billions before the inevitable settlement",
            "FDA approval was secured through systemic regulatory capture",
        ],
        "entities": [
            "opioid-crisis", "purdue-pharma", "sackler-family", "oxycontin",
            "fda", "donald-trump", "pharma-suppression", "cover-up",
        ],
    },
    {
        "date": "12-31", "year": 2019,
        "title": "China Confirms Wuhan Pneumonia Cluster",
        "category": "Government",
        "summary": "Chinese officials notified the WHO of a pneumonia cluster in Wuhan, where the Wuhan Institute of Virology had been conducting coronavirus gain-of-function research with U.S. NIH funding routed through EcoHealth Alliance. The pandemic and its origin became one of the most contested events of the 21st century.",
        "theories": [
            "SARS-CoV-2 leaked from the WIV's gain-of-function research program",
            "EcoHealth Alliance was the cutout enabling banned U.S. funding",
            "Fauci and NIH leadership coordinated the 'natural origin' narrative early",
        ],
        "entities": [
            "covid-19", "wuhan", "wuhan-institute-of-virology",
            "gain-of-function-research", "eco-health-alliance", "anthony-fauci",
            "cdc", "pharma-suppression", "cover-up", "fort-detrick",
        ],
    },

    # ── Bonus: a foundational 35th event ──────────────────────────────────
    {
        "date": "09-18", "year": 1947,
        "title": "The CIA Is Created via the National Security Act",
        "category": "Government",
        "summary": "President Truman signed the National Security Act, creating the Central Intelligence Agency, the National Security Council, and the U.S. Air Force as a separate service. The act also unified the military under a Secretary of Defense. Truman later wrote that the CIA had grown into something he never intended.",
        "theories": [
            "The CIA's original 'Office of Policy Coordination' had no statutory authority",
            "Truman was misled about the scope of covert action authority",
            "The NSC structure was designed to bypass congressional oversight",
        ],
        "entities": [
            "national-security-act-1947", "harry-truman",
            "national-security-council", "cia", "fbi", "us-air-force",
            "shadow-government",
        ],
    },
]


# ── MIGRATION ─────────────────────────────────────────────────────────────
def main() -> int:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    with ENTITIES_PATH.open("r", encoding="utf-8") as f:
        entities = json.load(f)

    existing_entity_ids = {e["id"] for e in entities}
    existing_event_ids = {e["id"] for e in data["events"] if "id" in e}

    # Append new entities (idempotent skip on existing id).
    new_entity_count = 0
    for ent in NEW_ENTITIES:
        if ent["id"] in existing_entity_ids:
            continue
        entities.append({**ent, "quarantined": False})
        existing_entity_ids.add(ent["id"])
        new_entity_count += 1

    # Append new events with stable ids, idempotent skip on existing id.
    new_event_count = 0
    skipped = 0
    for ev in NEW_EVENTS:
        eid = f"{ev['year']}-{slugify(ev['title'], fallback_year=ev['year'])}"
        if eid in existing_event_ids:
            skipped += 1
            continue
        # Validate every referenced entity exists in the registry.
        missing = [t for t in ev.get("entities", []) if t not in existing_entity_ids]
        if missing:
            print(f"[!] event {eid!r} references missing entities: {missing}", file=sys.stderr)
            return 1
        new_entry = {"id": eid, **ev}
        data["events"].append(new_entry)
        existing_event_ids.add(eid)
        new_event_count += 1

    # Bump last_ingest_at — this is an ingest event.
    data["last_ingest_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with ENTITIES_PATH.open("w", encoding="utf-8") as f:
        json.dump(entities, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"[+] entities: +{new_entity_count} new ({len(entities)} total)")
    print(f"[+] events:   +{new_event_count} new ({len(data['events'])} total, {skipped} skipped as duplicates)")
    print(f"[+] last_ingest_at = {data['last_ingest_at']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
