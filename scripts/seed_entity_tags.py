#!/usr/bin/env python3
"""
One-shot entity tagger for the seeded 103-event corpus.

Reads data/data.json, applies the TAG_MAP below (event_id → [entity_ids]),
writes entities: [...] per event. Also writes data/entities.json with the
flat entity registry.

This is the "weekend of hand-tagging" deliverable from the plan, generated
in one pass with per-event reasoning baked in. The user should audit
data/entities.json after the first run — entity names, aliases, and types
are the highest-value surface to review.

Re-running is safe but overwrites any hand edits to the `entities:` field
on an event. For ongoing new daily entries, generate_entry.py's Stage-1
entity auto-tag path (with ≥2-occurrence quarantine per OV-7) takes over.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_PATH = ROOT / "data" / "data.json"
ENTITIES_PATH = ROOT / "data" / "entities.json"


# ──────────────────────────────────────────────────────────────────────────
# ENTITY REGISTRY — flat array, hand-curated
# ──────────────────────────────────────────────────────────────────────────
# Types: person | org | place | program | event | topic
#
# Curation rules:
# - IDs are stable slugs. Never renamed after tagging.
# - `aliases` list lets the autocomplete match common variants users type.
# - Topics are abstract categories ("nuclear-testing", "mass-ufo-sighting")
#   that let the graph connect events with no shared person/org/place.
# - A rare entity mentioned by only 1 event still belongs in the registry;
#   at graph-build time the hub-cap + weight-prune decides what lands on
#   an edge. Quarantine (OV-7) only applies to NEW entities from ongoing
#   auto-tagging, not the seed.

ENTITIES: list[dict] = [
    # ─── people ─────────────────────────────────────────────────────────
    {"id": "dwight-eisenhower", "type": "person", "name": "Dwight D. Eisenhower", "aliases": ["Eisenhower", "Ike"]},
    {"id": "gus-grissom", "type": "person", "name": "Gus Grissom", "aliases": ["Virgil Grissom"]},
    {"id": "ed-white", "type": "person", "name": "Ed White", "aliases": ["Edward White II"]},
    {"id": "roger-chaffee", "type": "person", "name": "Roger Chaffee", "aliases": []},
    {"id": "fife-symington", "type": "person", "name": "Fife Symington", "aliases": ["Governor Symington"]},
    {"id": "robert-kenneth-wilson", "type": "person", "name": "Robert Kenneth Wilson", "aliases": ["the surgeon"]},
    {"id": "steven-greer", "type": "person", "name": "Steven Greer", "aliases": ["Dr. Greer"]},
    {"id": "richard-nixon", "type": "person", "name": "Richard Nixon", "aliases": ["Nixon"]},
    {"id": "amelia-earhart", "type": "person", "name": "Amelia Earhart", "aliases": []},
    {"id": "fred-noonan", "type": "person", "name": "Fred Noonan", "aliases": []},
    {"id": "neil-armstrong", "type": "person", "name": "Neil Armstrong", "aliases": []},
    {"id": "buzz-aldrin", "type": "person", "name": "Buzz Aldrin", "aliases": ["Edwin Aldrin"]},
    {"id": "stanley-kubrick", "type": "person", "name": "Stanley Kubrick", "aliases": []},
    {"id": "marilyn-monroe", "type": "person", "name": "Marilyn Monroe", "aliases": []},
    {"id": "jfk", "type": "person", "name": "John F. Kennedy", "aliases": ["JFK", "Kennedy", "President Kennedy"]},
    {"id": "rfk", "type": "person", "name": "Robert F. Kennedy", "aliases": ["RFK", "Bobby Kennedy"]},
    {"id": "jfk-jr", "type": "person", "name": "John F. Kennedy Jr.", "aliases": ["JFK Jr.", "John Kennedy Jr."]},
    {"id": "jeffrey-epstein", "type": "person", "name": "Jeffrey Epstein", "aliases": ["Epstein"]},
    {"id": "princess-diana", "type": "person", "name": "Princess Diana", "aliases": ["Diana Spencer", "Diana, Princess of Wales"]},
    {"id": "lee-harvey-oswald", "type": "person", "name": "Lee Harvey Oswald", "aliases": ["Oswald"]},
    {"id": "mlk", "type": "person", "name": "Martin Luther King Jr.", "aliases": ["MLK", "King"]},
    {"id": "james-earl-ray", "type": "person", "name": "James Earl Ray", "aliases": []},
    {"id": "sirhan-sirhan", "type": "person", "name": "Sirhan Sirhan", "aliases": []},
    {"id": "thane-eugene-cesar", "type": "person", "name": "Thane Eugene Cesar", "aliases": []},
    {"id": "orson-welles", "type": "person", "name": "Orson Welles", "aliases": []},
    {"id": "hg-wells", "type": "person", "name": "H.G. Wells", "aliases": ["H. G. Wells"]},
    {"id": "charles-halt", "type": "person", "name": "Charles Halt", "aliases": ["Lt. Col. Halt"]},
    {"id": "grigori-rasputin", "type": "person", "name": "Grigori Rasputin", "aliases": ["Rasputin"]},
    {"id": "james-bedford", "type": "person", "name": "James Bedford", "aliases": []},
    {"id": "al-capone", "type": "person", "name": "Al Capone", "aliases": ["Capone"]},
    {"id": "fdr", "type": "person", "name": "Franklin D. Roosevelt", "aliases": ["FDR", "Roosevelt"]},
    {"id": "betty-hill", "type": "person", "name": "Betty Hill", "aliases": []},
    {"id": "barney-hill", "type": "person", "name": "Barney Hill", "aliases": []},
    {"id": "roger-patterson", "type": "person", "name": "Roger Patterson", "aliases": []},
    {"id": "bob-gimlin", "type": "person", "name": "Bob Gimlin", "aliases": []},
    {"id": "travis-walton", "type": "person", "name": "Travis Walton", "aliases": []},
    {"id": "christa-mcauliffe", "type": "person", "name": "Christa McAuliffe", "aliases": []},
    {"id": "ilan-ramon", "type": "person", "name": "Ilan Ramon", "aliases": []},
    {"id": "pope-benedict-xvi", "type": "person", "name": "Pope Benedict XVI", "aliases": ["Benedict XVI", "Joseph Ratzinger"]},
    {"id": "mahatma-gandhi", "type": "person", "name": "Mahatma Gandhi", "aliases": ["Gandhi"]},
    {"id": "nathuram-godse", "type": "person", "name": "Nathuram Godse", "aliases": []},
    {"id": "olof-palme", "type": "person", "name": "Olof Palme", "aliases": []},
    {"id": "julius-caesar", "type": "person", "name": "Julius Caesar", "aliases": ["Caesar"]},
    {"id": "marc-antony", "type": "person", "name": "Marc Antony", "aliases": ["Mark Antony"]},
    {"id": "augustus", "type": "person", "name": "Augustus", "aliases": ["Octavian", "Caesar Augustus"]},
    {"id": "marshall-applewhite", "type": "person", "name": "Marshall Applewhite", "aliases": []},
    {"id": "ronald-reagan", "type": "person", "name": "Ronald Reagan", "aliases": ["Reagan"]},
    {"id": "john-hinckley-jr", "type": "person", "name": "John Hinckley Jr.", "aliases": ["Hinckley"]},
    {"id": "george-h-w-bush", "type": "person", "name": "George H. W. Bush", "aliases": ["Bush Sr.", "GHW Bush"]},
    {"id": "jesse-james", "type": "person", "name": "Jesse James", "aliases": []},
    {"id": "robert-ford", "type": "person", "name": "Robert Ford", "aliases": []},
    {"id": "j-p-morgan", "type": "person", "name": "J.P. Morgan", "aliases": ["John Pierpont Morgan"]},
    {"id": "adolf-hitler", "type": "person", "name": "Adolf Hitler", "aliases": ["Hitler"]},
    {"id": "adam-weishaupt", "type": "person", "name": "Adam Weishaupt", "aliases": []},
    {"id": "osama-bin-laden", "type": "person", "name": "Osama bin Laden", "aliases": ["bin Laden"]},
    {"id": "anwar-sadat", "type": "person", "name": "Anwar Sadat", "aliases": ["Sadat"]},
    {"id": "menachem-begin", "type": "person", "name": "Menachem Begin", "aliases": ["Begin"]},
    {"id": "jimmy-carter", "type": "person", "name": "Jimmy Carter", "aliases": ["Carter", "President Carter"]},
    {"id": "stanislav-petrov", "type": "person", "name": "Stanislav Petrov", "aliases": []},
    {"id": "vasili-arkhipov", "type": "person", "name": "Vasili Arkhipov", "aliases": []},
    {"id": "barack-obama", "type": "person", "name": "Barack Obama", "aliases": ["Obama"]},
    {"id": "larry-mcdonald", "type": "person", "name": "Larry McDonald", "aliases": []},
    {"id": "charles-manson", "type": "person", "name": "Charles Manson", "aliases": ["Manson"]},
    {"id": "sharon-tate", "type": "person", "name": "Sharon Tate", "aliases": []},
    {"id": "elvis-presley", "type": "person", "name": "Elvis Presley", "aliases": ["Elvis", "The King"]},
    {"id": "tom-parker", "type": "person", "name": "Tom Parker", "aliases": ["Colonel Tom Parker"]},
    {"id": "michael-jackson", "type": "person", "name": "Michael Jackson", "aliases": []},
    {"id": "conrad-murray", "type": "person", "name": "Conrad Murray", "aliases": []},
    {"id": "tupac-shakur", "type": "person", "name": "Tupac Shakur", "aliases": ["Tupac", "2Pac"]},
    {"id": "suge-knight", "type": "person", "name": "Suge Knight", "aliases": []},
    {"id": "donald-trump", "type": "person", "name": "Donald Trump", "aliases": ["Trump"]},
    {"id": "hillary-clinton", "type": "person", "name": "Hillary Clinton", "aliases": []},
    {"id": "kenneth-arnold", "type": "person", "name": "Kenneth Arnold", "aliases": []},
    {"id": "harold-dahl", "type": "person", "name": "Harold Dahl", "aliases": []},
    {"id": "fred-crisman", "type": "person", "name": "Fred Crisman", "aliases": []},
    {"id": "nicholas-ii", "type": "person", "name": "Tsar Nicholas II", "aliases": ["Nicholas II"]},
    {"id": "anastasia-romanov", "type": "person", "name": "Anastasia Romanov", "aliases": ["Anastasia", "Anna Anderson"]},
    {"id": "lenin", "type": "person", "name": "Vladimir Lenin", "aliases": ["Lenin"]},
    {"id": "warren-anderson", "type": "person", "name": "Warren Anderson", "aliases": []},
    {"id": "timothy-mcveigh", "type": "person", "name": "Timothy McVeigh", "aliases": ["McVeigh"]},
    {"id": "george-washington", "type": "person", "name": "George Washington", "aliases": ["Washington"]},
    {"id": "mikhail-gorbachev", "type": "person", "name": "Mikhail Gorbachev", "aliases": ["Gorbachev"]},
    {"id": "klaus-fuchs", "type": "person", "name": "Klaus Fuchs", "aliases": []},
    {"id": "david-johnston", "type": "person", "name": "David Johnston", "aliases": []},
    {"id": "emad-salem", "type": "person", "name": "Emad Salem", "aliases": []},
    {"id": "carl-allen", "type": "person", "name": "Carl Allen", "aliases": []},
    {"id": "d-b-cooper", "type": "person", "name": "D.B. Cooper", "aliases": ["Dan Cooper"]},
    {"id": "robert-rackstraw", "type": "person", "name": "Robert Rackstraw", "aliases": []},

    # ─── orgs ──────────────────────────────────────────────────────────
    {"id": "cia", "type": "org", "name": "Central Intelligence Agency", "aliases": ["CIA", "The Agency", "Central Intelligence"]},
    {"id": "fbi", "type": "org", "name": "Federal Bureau of Investigation", "aliases": ["FBI", "The Bureau"]},
    {"id": "mi6", "type": "org", "name": "MI6", "aliases": ["Secret Intelligence Service", "SIS", "British MI6"]},
    {"id": "kgb", "type": "org", "name": "KGB", "aliases": ["Soviet intelligence"]},
    {"id": "mossad", "type": "org", "name": "Mossad", "aliases": ["Israeli intelligence"]},
    {"id": "isi", "type": "org", "name": "ISI (Pakistan)", "aliases": ["Inter-Services Intelligence", "Pakistani ISI"]},
    {"id": "nasa", "type": "org", "name": "NASA", "aliases": ["National Aeronautics and Space Administration"]},
    {"id": "us-military", "type": "org", "name": "U.S. Military", "aliases": ["United States military", "US Armed Forces"]},
    {"id": "us-army", "type": "org", "name": "U.S. Army", "aliases": ["United States Army"]},
    {"id": "us-navy", "type": "org", "name": "U.S. Navy", "aliases": ["United States Navy"]},
    {"id": "us-air-force", "type": "org", "name": "U.S. Air Force", "aliases": ["USAF", "United States Air Force"]},
    {"id": "royal-canadian-navy", "type": "org", "name": "Royal Canadian Navy", "aliases": ["RCN"]},
    {"id": "belgian-air-force", "type": "org", "name": "Belgian Air Force", "aliases": []},
    {"id": "us-government", "type": "org", "name": "U.S. Government", "aliases": ["United States government", "federal government"]},
    {"id": "pentagon", "type": "org", "name": "The Pentagon", "aliases": ["Department of Defense", "DoD"]},
    {"id": "soviet-union", "type": "org", "name": "Soviet Union", "aliases": ["USSR", "the Soviets"]},
    {"id": "soviet-military", "type": "org", "name": "Soviet Military", "aliases": ["Red Army", "Soviet armed forces"]},
    {"id": "soviet-navy", "type": "org", "name": "Soviet Navy", "aliases": []},
    {"id": "nazi-regime", "type": "org", "name": "Nazi Regime", "aliases": ["Third Reich", "Nazi Germany"]},
    {"id": "branch-davidians", "type": "org", "name": "Branch Davidians", "aliases": []},
    {"id": "peoples-temple", "type": "org", "name": "Peoples Temple", "aliases": ["Jim Jones cult"]},
    {"id": "heavens-gate", "type": "org", "name": "Heaven's Gate", "aliases": []},
    {"id": "aum-shinrikyo", "type": "org", "name": "Aum Shinrikyo", "aliases": ["Aum cult"]},
    {"id": "manson-family", "type": "org", "name": "Manson Family", "aliases": []},
    {"id": "mafia", "type": "org", "name": "Mafia", "aliases": ["Cosa Nostra", "mob"]},
    {"id": "warren-commission", "type": "org", "name": "Warren Commission", "aliases": []},
    {"id": "atf", "type": "org", "name": "ATF", "aliases": ["Bureau of Alcohol, Tobacco, Firearms and Explosives"]},
    {"id": "black-september", "type": "org", "name": "Black September", "aliases": []},
    {"id": "pkk", "type": "org", "name": "PKK", "aliases": ["Kurdistan Workers' Party"]},
    {"id": "ira", "type": "org", "name": "IRA", "aliases": ["Irish Republican Army"]},
    {"id": "bavarian-illuminati", "type": "org", "name": "Bavarian Illuminati", "aliases": ["Illuminati", "Order of the Illuminati"]},
    {"id": "union-carbide", "type": "org", "name": "Union Carbide", "aliases": []},
    {"id": "tepco", "type": "org", "name": "TEPCO", "aliases": ["Tokyo Electric Power Company"]},
    {"id": "alcor", "type": "org", "name": "Alcor Life Extension Foundation", "aliases": ["Alcor"]},
    {"id": "royal-family-uk", "type": "org", "name": "British Royal Family", "aliases": ["Royal Family", "House of Windsor"]},
    {"id": "vatican", "type": "org", "name": "The Vatican", "aliases": ["Roman Curia", "Catholic Church"]},
    {"id": "dnc", "type": "org", "name": "Democratic National Committee", "aliases": ["DNC"]},
    {"id": "national-press-club", "type": "org", "name": "National Press Club", "aliases": []},
    {"id": "oh-national-guard", "type": "org", "name": "Ohio National Guard", "aliases": []},
    {"id": "delta-force", "type": "org", "name": "Delta Force", "aliases": []},
    {"id": "us-army-rangers", "type": "org", "name": "U.S. Army Rangers", "aliases": ["Rangers"]},
    {"id": "navy-seals", "type": "org", "name": "U.S. Navy SEALs", "aliases": ["SEALs", "Navy SEALs"]},
    {"id": "7th-cavalry", "type": "org", "name": "U.S. 7th Cavalry", "aliases": []},

    # ─── places ────────────────────────────────────────────────────────
    {"id": "ural-mountains", "type": "place", "name": "Ural Mountains", "aliases": ["Urals"]},
    {"id": "los-angeles", "type": "place", "name": "Los Angeles", "aliases": ["LA"]},
    {"id": "phoenix-arizona", "type": "place", "name": "Phoenix, Arizona", "aliases": ["Phoenix"]},
    {"id": "loch-ness", "type": "place", "name": "Loch Ness", "aliases": []},
    {"id": "chernobyl", "type": "place", "name": "Chernobyl", "aliases": ["Chornobyl"]},
    {"id": "lakehurst-new-jersey", "type": "place", "name": "Lakehurst, New Jersey", "aliases": ["Lakehurst NJ"]},
    {"id": "roswell-nm", "type": "place", "name": "Roswell, New Mexico", "aliases": ["Roswell"]},
    {"id": "dealey-plaza", "type": "place", "name": "Dealey Plaza", "aliases": []},
    {"id": "dallas", "type": "place", "name": "Dallas, Texas", "aliases": ["Dallas"]},
    {"id": "memphis", "type": "place", "name": "Memphis, Tennessee", "aliases": ["Memphis"]},
    {"id": "bermuda-triangle", "type": "place", "name": "Bermuda Triangle", "aliases": []},
    {"id": "kecksburg-pa", "type": "place", "name": "Kecksburg, Pennsylvania", "aliases": ["Kecksburg"]},
    {"id": "rendlesham-forest", "type": "place", "name": "Rendlesham Forest", "aliases": []},
    {"id": "point-pleasant-wv", "type": "place", "name": "Point Pleasant, West Virginia", "aliases": ["Point Pleasant"]},
    {"id": "tunguska", "type": "place", "name": "Tunguska", "aliases": []},
    {"id": "washington-dc", "type": "place", "name": "Washington, D.C.", "aliases": ["D.C.", "Washington"]},
    {"id": "moscow", "type": "place", "name": "Moscow", "aliases": []},
    {"id": "berlin", "type": "place", "name": "Berlin", "aliases": []},
    {"id": "pearl-harbor", "type": "place", "name": "Pearl Harbor", "aliases": []},
    {"id": "new-mexico-desert", "type": "place", "name": "New Mexico Desert", "aliases": ["Jornada del Muerto"]},
    {"id": "hiroshima", "type": "place", "name": "Hiroshima", "aliases": []},
    {"id": "marshall-islands", "type": "place", "name": "Marshall Islands", "aliases": []},
    {"id": "novaya-zemlya", "type": "place", "name": "Novaya Zemlya", "aliases": []},
    {"id": "cuba", "type": "place", "name": "Cuba", "aliases": []},
    {"id": "nova-scotia", "type": "place", "name": "Nova Scotia", "aliases": ["Shag Harbour area"]},
    {"id": "shag-harbour", "type": "place", "name": "Shag Harbour", "aliases": []},
    {"id": "kentucky", "type": "place", "name": "Kentucky", "aliases": []},
    {"id": "kelly-hopkinsville", "type": "place", "name": "Kelly-Hopkinsville, Kentucky", "aliases": ["Hopkinsville"]},
    {"id": "paris", "type": "place", "name": "Paris", "aliases": []},
    {"id": "new-york-city", "type": "place", "name": "New York City", "aliases": ["NYC", "Manhattan"]},
    {"id": "empire-state-building", "type": "place", "name": "Empire State Building", "aliases": []},
    {"id": "world-trade-center", "type": "place", "name": "World Trade Center", "aliases": ["WTC", "Twin Towers"]},
    {"id": "capitol-building", "type": "place", "name": "U.S. Capitol Building", "aliases": ["The Capitol", "Capitol Hill"]},
    {"id": "siberia", "type": "place", "name": "Siberia", "aliases": []},
    {"id": "bluff-creek", "type": "place", "name": "Bluff Creek, California", "aliases": ["Bluff Creek"]},
    {"id": "san-diego", "type": "place", "name": "San Diego", "aliases": []},
    {"id": "las-vegas", "type": "place", "name": "Las Vegas", "aliases": []},
    {"id": "mount-rainier", "type": "place", "name": "Mount Rainier", "aliases": []},
    {"id": "puget-sound", "type": "place", "name": "Puget Sound", "aliases": []},
    {"id": "yekaterinburg", "type": "place", "name": "Yekaterinburg", "aliases": ["Ekaterinburg"]},
    {"id": "halifax", "type": "place", "name": "Halifax, Nova Scotia", "aliases": ["Halifax"]},
    {"id": "abbottabad", "type": "place", "name": "Abbottabad, Pakistan", "aliases": ["Abbottabad"]},
    {"id": "camp-david", "type": "place", "name": "Camp David", "aliases": []},
    {"id": "munich", "type": "place", "name": "Munich", "aliases": []},
    {"id": "bhopal", "type": "place", "name": "Bhopal, India", "aliases": ["Bhopal"]},
    {"id": "waco", "type": "place", "name": "Waco, Texas", "aliases": ["Waco"]},
    {"id": "oklahoma-city", "type": "place", "name": "Oklahoma City", "aliases": []},
    {"id": "brazil", "type": "place", "name": "Brazil", "aliases": []},
    {"id": "varginha", "type": "place", "name": "Varginha, Brazil", "aliases": ["Varginha"]},
    {"id": "stockholm", "type": "place", "name": "Stockholm", "aliases": []},
    {"id": "martha-s-vineyard", "type": "place", "name": "Martha's Vineyard", "aliases": []},
    {"id": "tokyo", "type": "place", "name": "Tokyo", "aliases": []},
    {"id": "kent-state", "type": "place", "name": "Kent State University", "aliases": ["Kent State"]},
    {"id": "mount-st-helens", "type": "place", "name": "Mount St. Helens", "aliases": []},
    {"id": "fukushima", "type": "place", "name": "Fukushima", "aliases": ["Fukushima Daiichi"]},
    {"id": "rome", "type": "place", "name": "Rome (Ancient)", "aliases": ["Roman Senate", "Ancient Rome"]},
    {"id": "boston", "type": "place", "name": "Boston", "aliases": []},
    {"id": "wounded-knee", "type": "place", "name": "Wounded Knee, South Dakota", "aliases": ["Wounded Knee Creek"]},
    {"id": "graceland", "type": "place", "name": "Graceland", "aliases": []},
    {"id": "mogadishu", "type": "place", "name": "Mogadishu, Somalia", "aliases": ["Mogadishu"]},
    {"id": "ingolstadt", "type": "place", "name": "Ingolstadt", "aliases": []},
    {"id": "lake-superior", "type": "place", "name": "Lake Superior", "aliases": []},
    {"id": "mount-vernon", "type": "place", "name": "Mount Vernon", "aliases": []},
    {"id": "great-plains", "type": "place", "name": "Great Plains", "aliases": []},
    {"id": "lorraine-motel", "type": "place", "name": "Lorraine Motel", "aliases": []},
    {"id": "ambassador-hotel", "type": "place", "name": "Ambassador Hotel", "aliases": []},
    {"id": "wannsee", "type": "place", "name": "Wannsee (Berlin)", "aliases": ["Wannsee Villa"]},

    # ─── programs / named ops ──────────────────────────────────────────
    {"id": "mkultra", "type": "program", "name": "MKUltra", "aliases": ["Project MKUltra", "MK-Ultra", "mind control program"]},
    {"id": "operation-paperclip", "type": "program", "name": "Operation Paperclip", "aliases": ["Paperclip"]},
    {"id": "project-mogul", "type": "program", "name": "Project Mogul", "aliases": []},
    {"id": "aatip", "type": "program", "name": "AATIP", "aliases": ["Advanced Aerospace Threat Identification Program", "Pentagon UFO Program"]},
    {"id": "apollo-program", "type": "program", "name": "Apollo Program", "aliases": ["NASA Apollo"]},
    {"id": "apollo-11", "type": "program", "name": "Apollo 11", "aliases": []},
    {"id": "apollo-13", "type": "program", "name": "Apollo 13", "aliases": []},
    {"id": "manhattan-project", "type": "program", "name": "Manhattan Project", "aliases": []},
    {"id": "operation-wrath-of-god", "type": "program", "name": "Operation Wrath of God", "aliases": []},
    {"id": "bay-of-pigs", "type": "program", "name": "Bay of Pigs", "aliases": ["Bay of Pigs invasion"]},
    {"id": "voyager-program", "type": "program", "name": "Voyager Program", "aliases": ["NASA Voyager"]},
    {"id": "cointelpro", "type": "program", "name": "COINTELPRO", "aliases": ["FBI COINTELPRO"]},

    # ─── named events / things ─────────────────────────────────────────
    {"id": "hindenburg", "type": "event", "name": "Hindenburg (LZ 129)", "aliases": ["LZ 129", "Hindenburg airship"]},
    {"id": "ss-edmund-fitzgerald", "type": "event", "name": "SS Edmund Fitzgerald", "aliases": ["Edmund Fitzgerald"]},
    {"id": "uss-eldridge", "type": "event", "name": "USS Eldridge", "aliases": []},
    {"id": "uss-liberty", "type": "event", "name": "USS Liberty", "aliases": []},
    {"id": "uss-vincennes", "type": "event", "name": "USS Vincennes", "aliases": []},
    {"id": "titanic", "type": "event", "name": "RMS Titanic", "aliases": ["Titanic"]},
    {"id": "mh370", "type": "event", "name": "Malaysia Airlines Flight MH370", "aliases": ["MH370", "Flight 370"]},
    {"id": "kal007", "type": "event", "name": "Korean Air Lines Flight 007", "aliases": ["KAL 007", "KAL007"]},
    {"id": "iran-air-655", "type": "event", "name": "Iran Air Flight 655", "aliases": []},
    {"id": "flight-19", "type": "event", "name": "Flight 19", "aliases": []},
    {"id": "flight-305", "type": "event", "name": "Northwest Orient Flight 305", "aliases": ["Flight 305"]},
    {"id": "challenger", "type": "event", "name": "Space Shuttle Challenger", "aliases": ["Challenger"]},
    {"id": "columbia-shuttle", "type": "event", "name": "Space Shuttle Columbia", "aliases": ["Columbia"]},
    {"id": "voyager-1", "type": "event", "name": "Voyager 1", "aliases": []},
    {"id": "nessie", "type": "event", "name": "Loch Ness Monster", "aliases": ["Nessie"]},
    {"id": "bigfoot", "type": "event", "name": "Bigfoot / Sasquatch", "aliases": ["Sasquatch", "Bigfoot"]},
    {"id": "mothman", "type": "event", "name": "Mothman", "aliases": []},
    {"id": "yeti", "type": "event", "name": "Yeti", "aliases": ["Abominable Snowman"]},
    {"id": "chupacabra", "type": "event", "name": "Chupacabra", "aliases": []},
    {"id": "silver-bridge", "type": "event", "name": "Silver Bridge", "aliases": []},
    {"id": "hale-bopp", "type": "event", "name": "Comet Hale-Bopp", "aliases": ["Hale-Bopp"]},
    {"id": "reichstag", "type": "event", "name": "Reichstag Building", "aliases": ["Reichstag"]},
    {"id": "tsar-bomba", "type": "event", "name": "Tsar Bomba", "aliases": []},
    {"id": "castle-bravo", "type": "event", "name": "Castle Bravo", "aliases": []},
    {"id": "trinity-test", "type": "event", "name": "Trinity (nuclear test)", "aliases": ["Trinity test"]},
    {"id": "isabella-stewart-gardner-museum", "type": "event", "name": "Isabella Stewart Gardner Museum", "aliases": ["Gardner Museum"]},
    {"id": "alfred-p-murrah-building", "type": "event", "name": "Alfred P. Murrah Federal Building", "aliases": ["Murrah Building"]},
    {"id": "b-25-bomber", "type": "event", "name": "B-25 Mitchell (bomber)", "aliases": ["B-25"]},

    # ─── topics ─────────────────────────────────────────────────────────
    {"id": "military-industrial-complex", "type": "topic", "name": "Military-Industrial Complex", "aliases": []},
    {"id": "shadow-government", "type": "topic", "name": "Shadow Government", "aliases": ["deep state"]},
    {"id": "spacecraft-fire", "type": "topic", "name": "Spacecraft Fire", "aliases": []},
    {"id": "radiation", "type": "topic", "name": "Radiation Exposure", "aliases": ["radioactive"]},
    {"id": "nuclear-testing", "type": "topic", "name": "Nuclear Weapons Testing", "aliases": ["atomic testing"]},
    {"id": "nuclear-disaster", "type": "topic", "name": "Nuclear Disaster", "aliases": ["reactor meltdown"]},
    {"id": "weather-balloon-cover-story", "type": "topic", "name": "Weather Balloon Cover Story", "aliases": []},
    {"id": "anti-aircraft", "type": "topic", "name": "Anti-Aircraft Fire", "aliases": []},
    {"id": "aviation-disappearance", "type": "topic", "name": "Aviation Disappearance", "aliases": []},
    {"id": "aviation-disaster", "type": "topic", "name": "Aviation Disaster", "aliases": []},
    {"id": "classified-cargo", "type": "topic", "name": "Classified Cargo", "aliases": []},
    {"id": "mass-ufo-sighting", "type": "topic", "name": "Mass UFO Sighting", "aliases": []},
    {"id": "v-shaped-craft", "type": "topic", "name": "V-Shaped Craft", "aliases": []},
    {"id": "triangular-craft", "type": "topic", "name": "Triangular Craft", "aliases": []},
    {"id": "lunar-mission", "type": "topic", "name": "Lunar Mission", "aliases": []},
    {"id": "cryptid-hoax", "type": "topic", "name": "Cryptid Hoax", "aliases": []},
    {"id": "photographic-evidence", "type": "topic", "name": "Photographic Evidence", "aliases": ["photograph analysis"]},
    {"id": "cover-up", "type": "topic", "name": "Cover-up", "aliases": ["coverup"]},
    {"id": "airship", "type": "topic", "name": "Airship", "aliases": ["dirigible", "zeppelin"]},
    {"id": "whistleblower", "type": "topic", "name": "Whistleblower Testimony", "aliases": ["whistleblowing"]},
    {"id": "disinformation-psyop", "type": "topic", "name": "Disinformation Psyop", "aliases": ["psyop"]},
    {"id": "deep-throat", "type": "topic", "name": "Deep Throat (Watergate source)", "aliases": []},
    {"id": "missing-18-minutes", "type": "topic", "name": "Missing 18 Minutes (Nixon tapes)", "aliases": []},
    {"id": "airburst-explosion", "type": "topic", "name": "Airburst Explosion", "aliases": []},
    {"id": "crashed-ufo-retrieval", "type": "topic", "name": "Crashed UFO Retrieval", "aliases": ["craft recovery"]},
    {"id": "assassination", "type": "topic", "name": "Assassination", "aliases": []},
    {"id": "political-assassination", "type": "topic", "name": "Political Assassination", "aliases": []},
    {"id": "celebrity-death", "type": "topic", "name": "Celebrity Death", "aliases": []},
    {"id": "kennedy-curse", "type": "topic", "name": "Kennedy Family Deaths", "aliases": ["Kennedy curse"]},
    {"id": "faked-death", "type": "topic", "name": "Faked Death (staged death)", "aliases": ["staged death"]},
    {"id": "body-double", "type": "topic", "name": "Body Double", "aliases": []},
    {"id": "alien-abduction", "type": "topic", "name": "Alien Abduction", "aliases": []},
    {"id": "first-contact-claim", "type": "topic", "name": "First Contact / Close Encounter", "aliases": []},
    {"id": "glowing-red-eyes", "type": "topic", "name": "Glowing Red Eyes (cryptid)", "aliases": []},
    {"id": "harbinger-of-disaster", "type": "topic", "name": "Harbinger of Disaster", "aliases": []},
    {"id": "cult-mass-death", "type": "topic", "name": "Cult Mass Death", "aliases": ["mass suicide", "cult suicide"]},
    {"id": "second-shooter", "type": "topic", "name": "Second Shooter Theory", "aliases": []},
    {"id": "false-flag", "type": "topic", "name": "False Flag", "aliases": []},
    {"id": "advance-knowledge", "type": "topic", "name": "Advance Knowledge / Stand Down", "aliases": ["stand down order"]},
    {"id": "controlled-demolition", "type": "topic", "name": "Controlled Demolition", "aliases": []},
    {"id": "power-grid-failure", "type": "topic", "name": "Power Grid Failure", "aliases": ["blackout"]},
    {"id": "nuclear-near-miss", "type": "topic", "name": "Nuclear Near-Miss", "aliases": ["nuclear close call"]},
    {"id": "classified-aerospace", "type": "topic", "name": "Classified Aerospace Program", "aliases": []},
    {"id": "lighthouse-explanation", "type": "topic", "name": "Lighthouse / Mundane Explanation", "aliases": []},
    {"id": "teleportation", "type": "topic", "name": "Teleportation / Invisibility", "aliases": []},
    {"id": "polygraph-testimony", "type": "topic", "name": "Polygraph-Verified Testimony", "aliases": []},
    {"id": "cult-suicide", "type": "topic", "name": "Cult Suicide", "aliases": []},
    {"id": "emp", "type": "topic", "name": "Electromagnetic Pulse (EMP)", "aliases": ["EMP weapon"]},
    {"id": "apocalyptic-prediction", "type": "topic", "name": "Apocalyptic Prediction", "aliases": []},
    {"id": "provocateur-theory", "type": "topic", "name": "Provocateur / Fed Infiltration", "aliases": []},
    {"id": "final-solution", "type": "topic", "name": "Final Solution (Holocaust)", "aliases": []},
    {"id": "o-ring-failure", "type": "topic", "name": "O-Ring Failure", "aliases": []},
    {"id": "foam-strike", "type": "topic", "name": "Foam Strike (Columbia)", "aliases": []},
    {"id": "pope-abdication", "type": "topic", "name": "Papal Abdication", "aliases": []},
    {"id": "internment", "type": "topic", "name": "Internment / Forced Relocation", "aliases": []},
    {"id": "truck-bombing", "type": "topic", "name": "Truck Bombing", "aliases": []},
    {"id": "drive-by-shooting", "type": "topic", "name": "Drive-By Shooting", "aliases": []},
    {"id": "propofol-overdose", "type": "topic", "name": "Propofol Overdose", "aliases": []},
    {"id": "barbiturate-overdose", "type": "topic", "name": "Barbiturate Overdose", "aliases": []},
    {"id": "suicide-ruled", "type": "topic", "name": "Officially Ruled Suicide", "aliases": []},
    {"id": "sabotage", "type": "topic", "name": "Sabotage (alleged)", "aliases": []},
    {"id": "spy-ring", "type": "topic", "name": "Espionage / Spy Ring", "aliases": ["espionage"]},
    {"id": "birther-conspiracy", "type": "topic", "name": "Birther Conspiracy", "aliases": []},
    {"id": "golden-record", "type": "topic", "name": "Voyager Golden Record", "aliases": []},
    {"id": "interdimensional-entity", "type": "topic", "name": "Interdimensional Entity", "aliases": []},
    {"id": "ghost-dance", "type": "topic", "name": "Ghost Dance Movement", "aliases": []},
    {"id": "cryonics", "type": "topic", "name": "Cryonics / Cryopreservation", "aliases": []},
    {"id": "bloodletting", "type": "topic", "name": "Bloodletting Medicine", "aliases": []},
    {"id": "bermuda-triangle-anomaly", "type": "topic", "name": "Bermuda Triangle Anomaly", "aliases": []},
    {"id": "nazi-escape", "type": "topic", "name": "Nazi Escape Theories (ratlines)", "aliases": ["ratlines"]},
    {"id": "dna-forensic", "type": "topic", "name": "DNA Forensic Evidence", "aliases": []},
    {"id": "civil-rights-movement", "type": "topic", "name": "Civil Rights Movement", "aliases": []},
    {"id": "disclosure-movement", "type": "topic", "name": "UFO Disclosure Movement", "aliases": []},
    {"id": "occultism", "type": "topic", "name": "Occultism / Ritual", "aliases": []},
    {"id": "mind-control", "type": "topic", "name": "Mind Control", "aliases": ["hypnosis conspiracy"]},
    {"id": "great-depression-era-crime", "type": "topic", "name": "Prohibition-Era Organized Crime", "aliases": []},
    {"id": "hijacking", "type": "topic", "name": "Aircraft Hijacking", "aliases": []},
    {"id": "submarine-incident", "type": "topic", "name": "Submarine Incident", "aliases": []},
    {"id": "soviet-collapse", "type": "topic", "name": "Soviet Collapse", "aliases": []},
    {"id": "art-heist", "type": "topic", "name": "Art Heist", "aliases": []},
    {"id": "pentagon-videos", "type": "topic", "name": "Pentagon UFO Videos", "aliases": ["Navy UAP videos"]},
    {"id": "mayan-calendar", "type": "topic", "name": "Mayan Long Count Calendar", "aliases": []},
    {"id": "watergate", "type": "topic", "name": "Watergate Scandal", "aliases": []},
    {"id": "holocaust", "type": "topic", "name": "Holocaust", "aliases": ["Shoah"]},
    {"id": "balkanization", "type": "topic", "name": "Peace Accord (Middle East)", "aliases": []},
    {"id": "prophecy-visions", "type": "topic", "name": "Prophecy / Visions", "aliases": []},
    {"id": "surveillance-balloon", "type": "topic", "name": "Surveillance Balloon", "aliases": []},
    {"id": "black-hawk", "type": "topic", "name": "Black Hawk Helicopter", "aliases": []},
    {"id": "civilian-aircraft-shootdown", "type": "topic", "name": "Civilian Aircraft Shootdown", "aliases": []},
]


# ──────────────────────────────────────────────────────────────────────────
# EVENT → ENTITY TAGS
# ──────────────────────────────────────────────────────────────────────────
# Each event_id maps to a list of entity_ids. 3-7 tags per event, mixing
# specific entities (people, orgs, places) with topic tags so the graph
# has both rare (for signal) and broad (for bridging) edges.

TAG_MAP: dict[str, list[str]] = {
    "1961-eisenhower-warns-of-the-military-industrial-complex": [
        "dwight-eisenhower", "us-government", "pentagon", "military-industrial-complex", "shadow-government"
    ],
    "1967-apollo-1-fire-kills-three-astronauts": [
        "nasa", "apollo-program", "gus-grissom", "ed-white", "roger-chaffee", "spacecraft-fire", "sabotage"
    ],
    "1959-dyatlov-pass-incident-begins": [
        "ural-mountains", "soviet-union", "soviet-military", "radiation", "yeti"
    ],
    "1942-battle-of-los-angeles": [
        "los-angeles", "us-military", "us-army", "anti-aircraft", "weather-balloon-cover-story", "mass-ufo-sighting"
    ],
    "2014-malaysia-airlines-flight-mh370-disappears": [
        "mh370", "aviation-disappearance", "classified-cargo", "civilian-aircraft-shootdown"
    ],
    "1997-the-phoenix-lights": [
        "phoenix-arizona", "fife-symington", "mass-ufo-sighting", "v-shaped-craft", "classified-aerospace"
    ],
    "1970-apollo-13-oxygen-tank-explodes": [
        "nasa", "apollo-program", "apollo-13", "lunar-mission", "sabotage", "cover-up"
    ],
    "1934-the-surgeon-s-photograph-of-the-loch-ness-monster": [
        "loch-ness", "nessie", "robert-kenneth-wilson", "cryptid-hoax", "photographic-evidence"
    ],
    "1986-chernobyl-reactor-4-explodes": [
        "chernobyl", "soviet-union", "nuclear-disaster", "radiation", "cover-up"
    ],
    "1937-the-hindenburg-disaster": [
        "hindenburg", "lakehurst-new-jersey", "airship", "nazi-regime", "sabotage"
    ],
    "2001-the-disclosure-project-press-conference": [
        "steven-greer", "national-press-club", "washington-dc", "disclosure-movement", "whistleblower", "disinformation-psyop"
    ],
    "1972-watergate-break-in": [
        "richard-nixon", "dnc", "cia", "watergate", "washington-dc", "deep-throat", "missing-18-minutes", "cover-up"
    ],
    "1908-the-tunguska-event": [
        "tunguska", "siberia", "airburst-explosion", "crashed-ufo-retrieval"
    ],
    "1937-amelia-earhart-vanishes": [
        "amelia-earhart", "fred-noonan", "aviation-disappearance", "spy-ring"
    ],
    "1947-the-roswell-incident": [
        "roswell-nm", "us-air-force", "us-military", "project-mogul", "crashed-ufo-retrieval", "weather-balloon-cover-story", "surveillance-balloon"
    ],
    "1969-apollo-11-moon-landing": [
        "nasa", "apollo-program", "apollo-11", "neil-armstrong", "buzz-aldrin", "stanley-kubrick", "lunar-mission", "cover-up"
    ],
    "1962-marilyn-monroe-found-dead": [
        "marilyn-monroe", "los-angeles", "jfk", "rfk", "cia", "mafia", "celebrity-death", "barbiturate-overdose", "suicide-ruled"
    ],
    "2019-jeffrey-epstein-found-dead-in-cell": [
        "jeffrey-epstein", "new-york-city", "suicide-ruled", "body-double", "cover-up", "assassination"
    ],
    "1955-the-kelly-hopkinsville-encounter": [
        "kelly-hopkinsville", "kentucky", "first-contact-claim", "alien-abduction"
    ],
    "1997-death-of-princess-diana": [
        "princess-diana", "paris", "mi6", "royal-family-uk", "celebrity-death", "faked-death", "assassination"
    ],
    "2001-the-september-11-attacks": [
        "world-trade-center", "new-york-city", "pentagon", "controlled-demolition", "advance-knowledge", "false-flag"
    ],
    "1961-the-betty-and-barney-hill-abduction": [
        "betty-hill", "barney-hill", "alien-abduction", "first-contact-claim", "mind-control"
    ],
    "1967-the-shag-harbour-ufo-incident": [
        "shag-harbour", "nova-scotia", "royal-canadian-navy", "crashed-ufo-retrieval", "cover-up"
    ],
    "1967-the-patterson-gimlin-film": [
        "bluff-creek", "roger-patterson", "bob-gimlin", "bigfoot", "photographic-evidence", "cryptid-hoax"
    ],
    "1943-the-philadelphia-experiment": [
        "uss-eldridge", "us-navy", "teleportation", "carl-allen", "cover-up"
    ],
    "1975-the-travis-walton-abduction": [
        "travis-walton", "phoenix-arizona", "alien-abduction", "polygraph-testimony", "first-contact-claim"
    ],
    "1966-first-mothman-sighting-in-point-pleasant": [
        "point-pleasant-wv", "mothman", "glowing-red-eyes", "silver-bridge", "harbinger-of-disaster", "interdimensional-entity", "cryptid-hoax"
    ],
    "1978-jonestown-massacre": [
        "peoples-temple", "cia", "mkultra", "cult-mass-death", "cult-suicide", "mind-control"
    ],
    "1963-jfk-assassinated-in-dallas": [
        "jfk", "dealey-plaza", "dallas", "lee-harvey-oswald", "warren-commission", "cia", "bay-of-pigs", "mafia", "second-shooter", "political-assassination"
    ],
    "1989-the-belgian-ufo-wave-begins": [
        "belgian-air-force", "triangular-craft", "classified-aerospace", "mass-ufo-sighting"
    ],
    "1945-flight-19-disappears-in-the-bermuda-triangle": [
        "flight-19", "us-navy", "bermuda-triangle", "bermuda-triangle-anomaly", "aviation-disappearance"
    ],
    "1965-the-kecksburg-ufo-incident": [
        "kecksburg-pa", "us-military", "crashed-ufo-retrieval", "cover-up"
    ],
    "2017-the-pentagon-ufo-program-revealed": [
        "pentagon", "aatip", "us-navy", "pentagon-videos", "disclosure-movement", "whistleblower"
    ],
    "1980-rendlesham-forest-incident-begins": [
        "rendlesham-forest", "us-air-force", "charles-halt", "crashed-ufo-retrieval", "lighthouse-explanation", "classified-aerospace"
    ],
    "1916-the-murder-of-rasputin": [
        "grigori-rasputin", "mi6", "occultism", "political-assassination"
    ],
    "1967-james-bedford-becomes-first-human-cryonically-preserved": [
        "james-bedford", "alcor", "cryonics", "shadow-government"
    ],
    "1929-the-st-valentine-s-day-massacre": [
        "al-capone", "mafia", "great-depression-era-crime", "political-assassination"
    ],
    "1954-castle-bravo-nuclear-test": [
        "castle-bravo", "marshall-islands", "us-military", "nuclear-testing", "radiation", "cover-up"
    ],
    "1968-assassination-of-martin-luther-king-jr": [
        "mlk", "memphis", "lorraine-motel", "james-earl-ray", "fbi", "civil-rights-movement", "political-assassination", "cointelpro"
    ],
    "1968-assassination-of-robert-f-kennedy": [
        "rfk", "los-angeles", "ambassador-hotel", "sirhan-sirhan", "thane-eugene-cesar", "mkultra", "mind-control", "second-shooter", "political-assassination", "kennedy-curse"
    ],
    "1945-the-trinity-test": [
        "trinity-test", "manhattan-project", "new-mexico-desert", "nuclear-testing", "radiation", "cover-up"
    ],
    "1945-hiroshima-bombing": [
        "hiroshima", "manhattan-project", "us-military", "nuclear-testing", "soviet-union", "cover-up"
    ],
    "1977-voyager-1-launched": [
        "voyager-1", "voyager-program", "nasa", "golden-record", "cia"
    ],
    "1938-war-of-the-worlds-broadcast": [
        "orson-welles", "hg-wells", "cia", "mind-control", "disinformation-psyop"
    ],
    "1965-the-northeast-blackout": [
        "power-grid-failure", "mass-ufo-sighting", "soviet-union", "emp"
    ],
    "2012-the-mayan-calendar-end-date": [
        "mayan-calendar", "nasa", "apocalyptic-prediction", "prophecy-visions"
    ],
    "2021-attack-on-the-u-s-capitol": [
        "donald-trump", "capitol-building", "washington-dc", "fbi", "provocateur-theory", "false-flag"
    ],
    "1942-the-wannsee-conference": [
        "wannsee", "berlin", "nazi-regime", "final-solution", "holocaust", "operation-paperclip", "cover-up"
    ],
    "1986-space-shuttle-challenger-explodes": [
        "challenger", "nasa", "christa-mcauliffe", "o-ring-failure", "cover-up"
    ],
    "1996-the-varginha-ufo-incident": [
        "varginha", "brazil", "crashed-ufo-retrieval", "chupacabra", "first-contact-claim"
    ],
    "1948-mahatma-gandhi-assassinated": [
        "mahatma-gandhi", "nathuram-godse", "mi6", "political-assassination"
    ],
    "2003-space-shuttle-columbia-disintegrates": [
        "columbia-shuttle", "nasa", "ilan-ramon", "foam-strike", "cover-up"
    ],
    "2013-pope-benedict-xvi-abdicates": [
        "pope-benedict-xvi", "vatican", "pope-abdication", "cover-up"
    ],
    "1942-executive-order-9066-signed": [
        "fdr", "us-government", "fbi", "internment"
    ],
    "1993-first-world-trade-center-bombing": [
        "world-trade-center", "new-york-city", "fbi", "emad-salem", "truck-bombing", "advance-knowledge", "false-flag"
    ],
    "1933-the-reichstag-fire": [
        "reichstag", "berlin", "nazi-regime", "false-flag", "cover-up"
    ],
    "1986-prime-minister-olof-palme-assassinated": [
        "olof-palme", "stockholm", "pkk", "political-assassination", "cover-up"
    ],
    "2011-fukushima-nuclear-disaster": [
        "fukushima", "tepco", "nuclear-disaster", "radiation", "cover-up"
    ],
    "-44-the-ides-of-march": [
        "julius-caesar", "marc-antony", "augustus", "rome", "political-assassination"
    ],
    "1990-the-isabella-stewart-gardner-museum-heist": [
        "isabella-stewart-gardner-museum", "boston", "mafia", "ira", "art-heist"
    ],
    "1995-tokyo-subway-sarin-attack": [
        "aum-shinrikyo", "tokyo", "cult-mass-death"
    ],
    "1997-heaven-s-gate-mass-suicide": [
        "heavens-gate", "marshall-applewhite", "hale-bopp", "san-diego", "cult-suicide", "apocalyptic-prediction"
    ],
    "1981-reagan-assassination-attempt": [
        "ronald-reagan", "john-hinckley-jr", "george-h-w-bush", "washington-dc", "mkultra", "mind-control", "second-shooter", "political-assassination"
    ],
    "1882-jesse-james-killed": [
        "jesse-james", "robert-ford", "faked-death", "body-double"
    ],
    "1970-apollo-13-launches-toward-the-moon": [
        "nasa", "apollo-program", "apollo-13", "lunar-mission", "occultism"
    ],
    "1912-the-titanic-sinks": [
        "titanic", "j-p-morgan", "body-double", "sabotage"
    ],
    "1993-waco-siege-ends": [
        "branch-davidians", "waco", "fbi", "atf", "cover-up", "sabotage"
    ],
    "1995-oklahoma-city-bombing": [
        "alfred-p-murrah-building", "oklahoma-city", "timothy-mcveigh", "waco", "truck-bombing", "false-flag"
    ],
    "1945-adolf-hitler-dies-in-the-berlin-bunker": [
        "adolf-hitler", "berlin", "nazi-regime", "operation-paperclip", "nazi-escape", "faked-death", "body-double", "dna-forensic"
    ],
    "1776-the-bavarian-illuminati-founded": [
        "adam-weishaupt", "bavarian-illuminati", "ingolstadt", "shadow-government", "occultism"
    ],
    "2011-osama-bin-laden-killed-in-abbottabad": [
        "osama-bin-laden", "abbottabad", "navy-seals", "isi", "cover-up", "body-double"
    ],
    "1970-kent-state-shootings": [
        "kent-state", "oh-national-guard", "fbi", "provocateur-theory", "political-assassination"
    ],
    "1980-mount-st-helens-erupts": [
        "mount-st-helens", "david-johnston", "classified-aerospace", "cover-up"
    ],
    "1967-the-uss-liberty-incident": [
        "uss-liberty", "us-navy", "mossad", "cover-up"
    ],
    "1947-the-maury-island-incident": [
        "harold-dahl", "fred-crisman", "puget-sound", "us-air-force", "crashed-ufo-retrieval", "cryptid-hoax", "cover-up"
    ],
    "1947-kenneth-arnold-sees-flying-saucers": [
        "kenneth-arnold", "mount-rainier", "mass-ufo-sighting", "classified-aerospace", "first-contact-claim"
    ],
    "2009-michael-jackson-dies": [
        "michael-jackson", "los-angeles", "conrad-murray", "celebrity-death", "propofol-overdose"
    ],
    "1988-uss-vincennes-shoots-down-iran-air-flight-655": [
        "uss-vincennes", "iran-air-655", "us-navy", "civilian-aircraft-shootdown", "cover-up"
    ],
    "1999-jfk-jr-plane-crash": [
        "jfk-jr", "hillary-clinton", "martha-s-vineyard", "aviation-disaster", "kennedy-curse", "political-assassination"
    ],
    "1918-the-romanov-family-executed": [
        "nicholas-ii", "anastasia-romanov", "lenin", "yekaterinburg", "dna-forensic", "body-double"
    ],
    "1945-b-25-bomber-crashes-into-the-empire-state-building": [
        "b-25-bomber", "empire-state-building", "new-york-city", "us-army", "aviation-disaster", "false-flag"
    ],
    "1969-the-tate-labianca-murders": [
        "charles-manson", "manson-family", "sharon-tate", "los-angeles", "mkultra", "mind-control", "celebrity-death"
    ],
    "2003-the-northeast-blackout-of-2003": [
        "power-grid-failure", "mass-ufo-sighting", "spy-ring"
    ],
    "1977-elvis-presley-dies-at-graceland": [
        "elvis-presley", "tom-parker", "graceland", "memphis", "celebrity-death", "faked-death", "mafia"
    ],
    "1949-the-soviet-union-tests-its-first-atomic-bomb": [
        "soviet-union", "manhattan-project", "klaus-fuchs", "nuclear-testing", "spy-ring"
    ],
    "1983-korean-air-lines-flight-007-shot-down": [
        "kal007", "larry-mcdonald", "soviet-military", "civilian-aircraft-shootdown", "cover-up"
    ],
    "1972-the-munich-olympics-massacre": [
        "black-september", "munich", "mossad", "operation-wrath-of-god", "political-assassination"
    ],
    "1996-tupac-shakur-dies": [
        "tupac-shakur", "suge-knight", "las-vegas", "celebrity-death", "drive-by-shooting", "faked-death"
    ],
    "1978-the-camp-david-accords": [
        "anwar-sadat", "menachem-begin", "jimmy-carter", "camp-david", "balkanization", "political-assassination"
    ],
    "1983-stanislav-petrov-prevents-nuclear-war": [
        "stanislav-petrov", "soviet-military", "nuclear-near-miss"
    ],
    "1993-the-battle-of-mogadishu": [
        "mogadishu", "delta-force", "us-army-rangers", "black-hawk", "cover-up"
    ],
    "1962-cuban-missile-crisis-announced": [
        "jfk", "cuba", "soviet-union", "nuclear-near-miss", "cover-up"
    ],
    "1962-vasili-arkhipov-refuses-to-launch": [
        "vasili-arkhipov", "soviet-navy", "nuclear-near-miss", "submarine-incident", "cuba"
    ],
    "1961-the-tsar-bomba-detonates": [
        "tsar-bomba", "novaya-zemlya", "soviet-union", "nuclear-testing", "cover-up"
    ],
    "2008-barack-obama-elected-president": [
        "barack-obama", "cia", "birther-conspiracy"
    ],
    "1975-ss-edmund-fitzgerald-sinks": [
        "ss-edmund-fitzgerald", "lake-superior", "aviation-disaster"
    ],
    "1971-d-b-cooper-hijacks-flight-305": [
        "d-b-cooper", "robert-rackstraw", "flight-305", "fbi", "hijacking", "faked-death"
    ],
    "1984-the-bhopal-gas-disaster": [
        "union-carbide", "warren-anderson", "bhopal", "us-government", "cover-up", "sabotage"
    ],
    "1917-the-halifax-explosion": [
        "halifax", "nova-scotia", "airburst-explosion", "nazi-regime", "sabotage"
    ],
    "1941-the-attack-on-pearl-harbor": [
        "pearl-harbor", "fdr", "us-navy", "advance-knowledge", "false-flag", "cover-up"
    ],
    "1799-george-washington-dies": [
        "george-washington", "mount-vernon", "bloodletting", "political-assassination"
    ],
    "1991-the-soviet-union-dissolves": [
        "mikhail-gorbachev", "george-h-w-bush", "moscow", "soviet-union", "kgb", "soviet-collapse"
    ],
    "1890-the-wounded-knee-massacre": [
        "wounded-knee", "7th-cavalry", "great-plains", "ghost-dance", "cover-up"
    ],
}


# ──────────────────────────────────────────────────────────────────────────
# MIGRATION LOGIC
# ──────────────────────────────────────────────────────────────────────────
def load_data() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict) -> None:
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def save_entities() -> None:
    ENTITIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Add quarantined: false (all seed entities are trusted per OV-7)
    registry = [{**e, "quarantined": False} for e in ENTITIES]
    with ENTITIES_PATH.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
        f.write("\n")


def verify_consistency() -> list[str]:
    """Return a list of issues (empty if all clean)."""
    issues: list[str] = []
    entity_ids = {e["id"] for e in ENTITIES}
    tag_ids_used: set[str] = set()

    for event_id, tags in TAG_MAP.items():
        for t in tags:
            tag_ids_used.add(t)
            if t not in entity_ids:
                issues.append(
                    f"event {event_id!r} references missing entity {t!r}"
                )

    unused = entity_ids - tag_ids_used
    for u in sorted(unused):
        issues.append(f"entity {u!r} is defined but referenced by no event")

    return issues


def main() -> int:
    issues = verify_consistency()
    if issues:
        print("[!] consistency issues:", file=sys.stderr)
        for msg in issues:
            print(f"  - {msg}", file=sys.stderr)
        print(f"[!] {len(issues)} issue(s); aborting. Fix above.", file=sys.stderr)
        return 1

    data = load_data()
    events = data["events"]

    tagged = 0
    missing_in_map = 0

    for entry in events:
        eid = entry["id"]
        if eid in TAG_MAP:
            entry["entities"] = TAG_MAP[eid]
            tagged += 1
        else:
            missing_in_map += 1
            print(f"[!] no tags for event id: {eid}", file=sys.stderr)

    save_data(data)
    save_entities()

    print(f"[+] entities registered: {len(ENTITIES)}")
    print(f"[+] events tagged:       {tagged}")
    if missing_in_map:
        print(f"[!] events missing tags: {missing_in_map}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
