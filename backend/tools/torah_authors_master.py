"""
MASTER TORAH AUTHORS KNOWLEDGE BASE - Phase 2 Enhanced (FIXED)
==============================================================
Combines:
- Clean structure from peirushim.py
- Scholarly depth from research document
- Sefaria integration metadata
- Relationship mapping (students, commentaries)
- Acronym disambiguation
- Masechta coverage data

FIXES APPLIED:
- Removed duplicate entries in variations that match primary_name_he
- build_lookup_index now deduplicates to prevent multiple matches for same author
"""

import json
import re
from typing import List, Dict, Optional, Set, Tuple

# ==============================================================================
#  ENHANCED DATASET: The Comprehensive Master List
# ==============================================================================

TORAH_AUTHORS_KB = [
    # ==========================================================================
    # TANNAIM & AMORAIM (For reference - rarely searched by name)
    # ==========================================================================
    {
        "id": "rabi_akiva",
        "primary_name_he": "רבי עקיבא",
        "primary_name_en": "Rabbi Akiva",
        "full_name_he": "רבי עקיבא בן יוסף",
        "full_name_en": "Akiva ben Yosef",
        "era": "Tannaim",
        "period": "50-135 CE",
        "region": "Israel",
        "variations": ["ר' עקיבא", "עקיבא"],  # FIXED: removed duplicate "רבי עקיבא"
        "works": [],
        "category": "Mishnah",
        "sefaria_base": None,
        "commentary_on": [],
        "students": ["Rabbi Meir", "Rabbi Shimon bar Yochai"],
    },
    
    # ==========================================================================
    # BIBLICAL COMMENTATORS (MEFARSHIM)
    # ==========================================================================
    {
        "id": "rashi",
        "primary_name_he": 'רש"י',
        "primary_name_en": "Rashi",
        "full_name_he": "רבי שלמה יצחקי",
        "full_name_en": "Rabbi Shlomo Yitzchaki",
        "era": "Rishonim",
        "period": "1040-1105",
        "region": "France (Troyes)",
        "school": "Ashkenaz",
        "methodology": "Pshat with selective Midrash",
        "variations": ['רש״י', 'רשי', 'שלמה יצחקי', 'בר יצחק'],  # FIXED: removed duplicate 'רש"י'
        "works": ["Perush Rashi on Torah", "Perush Rashi on Shas", "Perush Rashi on Nakh"],
        "category": "Exegesis/Talmud",
        "sefaria_base": "Rashi on",
        "commentary_on": ["Tanakh", "Talmud"],
        "masechta_coverage": "all",
        "standard_position": "Inner margin of Talmud page",
        "students": ["Rashbam", "Rabbeinu Tam", "Ri HaZaken"],
        "super_commentaries": ["Siftei Chachamim", "Maharal on Rashi", "Gur Aryeh"],
        "disambiguation": None,
    },
    {
        "id": "ibn_ezra",
        "primary_name_he": "אבן עזרא",
        "primary_name_en": "Ibn Ezra",
        "full_name_he": "רבי אברהם אבן עזרא",
        "full_name_en": "Abraham Ibn Ezra",
        "era": "Rishonim",
        "period": "1089-1167",
        "region": "Spain/Italy/France",
        "school": "Sefarad",
        "methodology": "Grammatical precision, philosophical rationalism",
        "variations": ['ראב"ע', 'ראב״ע', "ר' אברהם"],  # FIXED: removed duplicate
        "works": ["Ibn Ezra on Torah", "Sefer HaYashar", "Yesod Mora"],
        "category": "Exegesis/Grammar/Astronomy",
        "sefaria_base": "Ibn Ezra on",
        "commentary_on": ["Torah", "Nakh"],
        "masechta_coverage": None,
        "disambiguation": None,
    },
    {
        "id": "ramban",
        "primary_name_he": 'רמב"ן',
        "primary_name_en": "Ramban",
        "full_name_he": "רבי משה בן נחמן",
        "full_name_en": "Moshe ben Nachman (Nachmanides)",
        "era": "Rishonim",
        "period": "1194-1270",
        "region": "Spain/Israel",
        "school": "Sefarad",
        "methodology": "Kabbalistic underpinnings, harmonization",
        "variations": ['רמב״ן', 'רמבן', 'נחמני', 'בן נחמן'],  # FIXED: removed duplicate
        "works": ["Ramban on Torah", "Milchamot HaShem", "Torat HaAdam", "Chiddushim on Gemara"],
        "category": "Exegesis/Halakha/Kabbalah",
        "sefaria_base": "Ramban on",
        "commentary_on": ["Torah", "select Gemara"],
        "primary_masechtot": ["Bava Batra", "Shabbat", "Eruvin"],
        "masechta_coverage": "select",
        "students": ["Rashba", "Ritva"],
        "disambiguation": None,
    },
    {
        "id": "rashbam",
        "primary_name_he": 'רשב"ם',
        "primary_name_en": "Rashbam",
        "full_name_he": "רבי שמואל בן מאיר",
        "full_name_en": "Shmuel ben Meir",
        "era": "Rishonim",
        "period": "1085-1158",
        "region": "France",
        "school": "Ashkenaz",
        "methodology": "Extreme pshat, sometimes contra-Halakhic interpretation",
        "variations": ['רשב״ם', 'רשבם'],  # FIXED
        "works": ["Rashbam on Torah", "Rashbam on Bava Batra"],
        "category": "Exegesis/Talmud",
        "sefaria_base": "Rashbam on",
        "commentary_on": ["Torah", "Bava Batra"],
        "primary_masechtot": ["Bava Batra"],
        "masechta_coverage": "minimal",
        "teacher": "Rashi (grandfather)",
        "disambiguation": None,
    },
    {
        "id": "sforno",
        "primary_name_he": "ספורנו",
        "primary_name_en": "Sforno",
        "full_name_he": "רבי עובדיה ספורנו",
        "full_name_en": "Ovadia Sforno",
        "era": "Rishonim",
        "period": "1475-1550",
        "region": "Italy",
        "variations": ["עובדיה ספורנו"],  # FIXED
        "works": ["Sforno on Torah"],
        "category": "Exegesis",
        "sefaria_base": "Sforno on",
        "commentary_on": ["Torah"],
        "disambiguation": None,
    },
    {
        "id": "radak",
        "primary_name_he": 'רד"ק',
        "primary_name_en": "Radak",
        "full_name_he": "רבי דוד קמחי",
        "full_name_en": "David Kimchi",
        "era": "Rishonim",
        "period": "1160-1235",
        "region": "Provence",
        "school": "Sefarad",
        "variations": ['רד״ק', 'רדק', 'קמחי'],  # FIXED
        "works": ["Radak on Nakh", "Sefer HaShorashim", "Michlol"],
        "category": "Exegesis/Grammar",
        "sefaria_base": "Radak on",
        "commentary_on": ["Nakh"],
        "father": "Rabbi Yosef Kimchi (Radak's father)",
        "disambiguation": None,
    },
    {
        "id": "or_hachaim",
        "primary_name_he": "אור החיים",
        "primary_name_en": "Or HaChaim",
        "full_name_he": "רבי חיים בן עטר",
        "full_name_en": "Chaim ibn Attar",
        "era": "Acharonim",
        "period": "1696-1743",
        "region": "Morocco/Israel",
        "variations": ['אוה"ח', "אור החיים הקדוש", "בן עטר"],  # FIXED
        "works": ["Or HaChaim"],
        "category": "Exegesis/Kabbalah",
        "sefaria_base": "Or HaChaim on",
        "commentary_on": ["Torah"],
        "disambiguation": None,
    },
    {
        "id": "kli_yakar",
        "primary_name_he": "כלי יקר",
        "primary_name_en": "Kli Yakar",
        "full_name_he": "רבי שלמה אפרים לונטשיץ",
        "full_name_en": "Shlomo Ephraim Luntschitz",
        "era": "Acharonim",
        "period": "1550-1619",
        "region": "Poland",
        "variations": ['הכלי יקר'],  # FIXED
        "works": ["Kli Yakar"],
        "category": "Exegesis",
        "sefaria_base": "Kli Yakar on",
        "commentary_on": ["Torah"],
        "disambiguation": None,
    },
    {
        "id": "malbim",
        "primary_name_he": 'מלבי"ם',
        "primary_name_en": "Malbim",
        "full_name_he": "רבי מאיר לייבוש בן יחיאל מיכל",
        "full_name_en": "Meir Leibush ben Yechiel Michel",
        "era": "Acharonim",
        "period": "1809-1879",
        "region": "Eastern Europe",
        "variations": ['מלבי״ם', 'מלבים'],  # FIXED
        "works": ["HaTorah VeHaMitzvah", "Mikraei Kodesh"],
        "category": "Exegesis/Grammar",
        "sefaria_base": "Malbim on",
        "commentary_on": ["Torah", "Nakh"],
        "disambiguation": None,
    },
    {
        "id": "abarbanel",
        "primary_name_he": "אברבנאל",
        "primary_name_en": "Abarbanel",
        "full_name_he": "רבי דון יצחק אברבנאל",
        "full_name_en": "Don Isaac Abarbanel",
        "era": "Rishonim",
        "period": "1437-1508",
        "region": "Spain/Italy/Portugal",
        "variations": ["דון יצחק", "אבי מלך"],  # FIXED
        "works": ["Abarbanel on Torah", "Abarbanel on Nakh"],
        "category": "Exegesis/Philosophy",
        "sefaria_base": "Abarbanel on",
        "commentary_on": ["Torah", "Nakh"],
        "disambiguation": None,
    },

    # ==========================================================================
    # TALMUDIC COMMENTATORS - RISHONIM
    # ==========================================================================
    {
        "id": "rif",
        "primary_name_he": 'רי"ף',
        "primary_name_en": "Rif",
        "full_name_he": "רבי יצחק אלפסי",
        "full_name_en": "Isaac Alfasi",
        "era": "Rishonim",
        "period": "1013-1103",
        "region": "North Africa (Fez)/Spain",
        "school": "Sefarad",
        "methodology": "Halachic extraction, omitting Aggadah",
        "variations": ['רי״ף', 'הריף', 'אלפסי'],  # FIXED
        "works": ["Sefer HaHalachot (Hilchot HaRif)"],
        "category": "Halakha",
        "sefaria_base": "Rif",
        "commentary_on": ["Talmud"],
        "masechta_coverage": "most",
        "standard_position": "Back of Talmud volume",
        "students": ["Ri Migash"],
        "super_commentaries": ["Ran", "Nimukei Yosef"],
        "pillar_status": "First of Three Pillars",
        "disambiguation": None,
    },
    {
        "id": "tosafot",
        "primary_name_he": "תוספות",
        "primary_name_en": "Tosafot",
        "full_name_he": "בעלי התוספות",
        "full_name_en": "Baalei HaTosafot",
        "era": "Rishonim",
        "period": "12th-14th century",
        "region": "France/Germany",
        "school": "Ashkenaz",
        "methodology": "Dialectic analysis, cross-Talmud harmonization",
        "variations": ["תוס'", 'תוס', 'התוספות'],  # FIXED: removed duplicate "תוספות"
        "works": ["Tosafot on Shas"],
        "category": "Talmud",
        "sefaria_base": "Tosafot on",
        "commentary_on": ["Talmud"],
        "masechta_coverage": "most",
        "standard_position": "Outer margin of Talmud page",
        "key_figures": ["Rabbeinu Tam", "Ri HaZaken", "Rashbam", "Ri of Dampierre"],
        "disambiguation": None,
    },
    {
        "id": "rabbeinu_tam",
        "primary_name_he": "רבינו תם",
        "primary_name_en": "Rabbeinu Tam",
        "full_name_he": "רבי יעקב בן מאיר",
        "full_name_en": "Yaakov ben Meir",
        "era": "Rishonim",
        "period": "1100-1171",
        "region": "France",
        "school": "Ashkenaz",
        "methodology": "Leading Tosafist, dialectic master",
        "variations": ['ר"ת', "תם", "יעקב בן מאיר"],  # FIXED
        "works": ["Sefer HaYashar", "Tosafot (primary author)"],
        "category": "Talmud",
        "sefaria_base": None,
        "commentary_on": ["Talmud"],
        "teacher": "Rashi (grandfather)",
        "tefillin_dispute": "Tefillin of Rabbeinu Tam (order dispute with Rashi)",
        "disambiguation": None,
    },
    {
        "id": "rambam",
        "primary_name_he": 'רמב"ם',
        "primary_name_en": "Rambam",
        "full_name_he": "רבי משה בן מימון",
        "full_name_en": "Moshe ben Maimon (Maimonides)",
        "era": "Rishonim",
        "period": "1138-1204",
        "region": "Spain/Egypt",
        "school": "Sefarad",
        "methodology": "Systematic codification, philosophical rationalism",
        "variations": ['רמב״ם', 'הרמב"ם', 'מימוני', 'נשר הגדול'],  # FIXED
        "works": ["Mishneh Torah", "Sefer HaMitzvot", "Moreh Nevukhim", "Perush HaMishnayot"],
        "category": "Halakha/Philosophy",
        "sefaria_base": "Rambam on",
        "commentary_on": ["Mishnah"],
        "halacha_work": "Mishneh Torah",
        "masechta_coverage": "all",
        "super_commentaries": ["Maggid Mishneh", "Kesef Mishneh", "Raavad Hassagot", "Lechem Mishneh"],
        "pillar_status": "Second of Three Pillars",
        "controversy": "Maimonidean Controversy (philosophy vs tradition)",
        "disambiguation": None,
    },
    {
        "id": "raavad",
        "primary_name_he": 'ראב"ד',
        "primary_name_en": "Raavad",
        "full_name_he": "רבי אברהם בן דוד",
        "full_name_en": "Abraham ben David of Posquières",
        "era": "Rishonim",
        "period": "1125-1198",
        "region": "Provence",
        "variations": ['ראב״ד', 'הראב"ד'],  # FIXED
        "works": ["Hassagot on Mishneh Torah", "Baalei HaNefesh"],
        "category": "Halakha",
        "sefaria_base": "Raavad on",
        "commentary_on": ["Mishneh Torah"],
        "standard_position": "Printed on page of Mishneh Torah",
        "disambiguation": "Raavad III (most famous)",
    },
    {
        "id": "rosh",
        "primary_name_he": 'רא"ש',
        "primary_name_en": "Rosh",
        "full_name_he": "רבי אשר בן יחיאל",
        "full_name_en": "Asher ben Yechiel",
        "era": "Rishonim",
        "period": "1250-1327",
        "region": "Germany/Spain",
        "school": "Ashkenaz transplanted to Sefarad",
        "variations": ['רא״ש', 'הרא"ש', 'אשרי'],  # FIXED
        "works": ["Piskei HaRosh", "Teshuvot HaRosh"],
        "category": "Halakha/Talmud",
        "sefaria_base": "Rosh on",
        "commentary_on": ["Talmud"],
        "masechta_coverage": "most",
        "teacher": "Maharam of Rothenburg",
        "students": ["Tur (son)"],
        "pillar_status": "Third of Three Pillars",
        "disambiguation": None,
    },
    {
        "id": "rashba",
        "primary_name_he": 'רשב"א',
        "primary_name_en": "Rashba",
        "full_name_he": "רבי שלמה בן אדרת",
        "full_name_en": "Shlomo ben Aderet",
        "era": "Rishonim",
        "period": "1235-1310",
        "region": "Spain (Barcelona)",
        "school": "Sefarad",
        "variations": ['רשב״א', 'הרשב"א'],  # FIXED
        "works": ["Chiddushei HaRashba", "Teshuvot HaRashba"],
        "category": "Talmud/Halakha",
        "sefaria_base": "Rashba on",
        "commentary_on": ["Talmud"],
        "masechta_coverage": "extensive",
        "teacher": "Ramban",
        "students": ["Ritva"],
        "disambiguation": None,
    },
    {
        "id": "ritva",
        "primary_name_he": 'ריטב"א',
        "primary_name_en": "Ritva",
        "full_name_he": "רבי יום טוב אשווילי",
        "full_name_en": "Yom Tov Asevilli",
        "era": "Rishonim",
        "period": "1250-1330",
        "region": "Spain (Seville)",
        "school": "Sefarad",
        "variations": ['ריטב״א', 'הריטב"א'],  # FIXED
        "works": ["Chiddushei HaRitva"],
        "category": "Talmud",
        "sefaria_base": "Ritva on",
        "commentary_on": ["Talmud"],
        "masechta_coverage": "many",
        "teacher": "Rashba",
        "disambiguation": None,
    },
    {
        "id": "ran",
        "primary_name_he": "רן",
        "primary_name_en": "Ran",
        "full_name_he": "רבי נסים גירונדי",
        "full_name_en": "Nissim Gerondi",
        "era": "Rishonim",
        "period": "1290-1375",
        "region": "Spain (Gerona)",
        "school": "Sefarad",
        "variations": ['ר"ן', "הרן", "נסים גירונדי"],  # FIXED: removed duplicate "רן"
        "works": ["Ran on Rif", "Chiddushei HaRan"],
        "category": "Talmud",
        "sefaria_base": "Ran on",
        "commentary_on": ["Rif", "select Talmud"],
        "primary_masechtot": ["Nedarim", "Pesachim", "Rosh Hashanah", "Taanit", "Megillah"],
        "masechta_coverage": "select",
        "standard_position": "Commentary on Rif (back of Talmud)",
        "super_commentaries": [],
        "disambiguation": None,
    },
    {
        "id": "nimukei_yosef",
        "primary_name_he": "נימוקי יוסף",
        "primary_name_en": "Nimukei Yosef",
        "full_name_he": "רבי יוסף חביבא",
        "full_name_en": "Yosef Haviva",
        "era": "Rishonim",
        "period": "15th century",
        "region": "Spain",
        "variations": ['נ"י'],  # FIXED
        "works": ["Nimukei Yosef on Rif"],
        "category": "Talmud",
        "sefaria_base": "Nimukei Yosef on",
        "commentary_on": ["Rif"],
        "standard_position": "Alongside Ran on Rif",
        "disambiguation": None,
    },
    {
        "id": "meiri",
        "primary_name_he": "מאירי",
        "primary_name_en": "Meiri",
        "full_name_he": "רבי מנחם המאירי",
        "full_name_en": "Menachem HaMeiri",
        "era": "Rishonim",
        "period": "1249-1310",
        "region": "Provence",
        "variations": ["המאירי", "בית הבחירה"],  # FIXED
        "works": ["Beit HaBechira"],
        "category": "Talmud",
        "sefaria_base": "Meiri on",
        "commentary_on": ["Talmud"],
        "masechta_coverage": "extensive",
        "unique_feature": "Manuscripts only discovered 20th century",
        "disambiguation": None,
    },
    {
        "id": "maharam_rothenburg",
        "primary_name_he": 'מהר"ם',
        "primary_name_en": "Maharam of Rothenburg",
        "full_name_he": "רבי מאיר בן ברוך מרוטנבורג",
        "full_name_en": "Meir ben Baruch of Rothenburg",
        "era": "Rishonim",
        "period": "1215-1293",
        "region": "Germany",
        "school": "Ashkenaz",
        "variations": ['מהר״ם', 'מהר"ם מרוטנבורג'],  # FIXED
        "works": ["Teshuvot Maharam", "Hagahot Maimoniot"],
        "category": "Halakha/Responsa",
        "sefaria_base": "Maharam of Rothenburg on",
        "commentary_on": [],
        "students": ["Rosh", "Mordechai"],
        "disambiguation": "Maharam of Rothenburg (most famous, 13th century)",
    },
    {
        "id": "mordechai",
        "primary_name_he": "מרדכי",
        "primary_name_en": "Mordechai",
        "full_name_he": "רבי מרדכי בן הלל",
        "full_name_en": "Mordechai ben Hillel",
        "era": "Rishonim",
        "period": "1250-1298",
        "region": "Germany",
        "school": "Ashkenaz",
        "variations": ["המרדכי"],  # FIXED
        "works": ["Sefer HaMordechai"],
        "category": "Halakha/Talmud",
        "sefaria_base": "Mordechai on",
        "commentary_on": ["Talmud"],
        "teacher": "Maharam of Rothenburg",
        "standard_position": "Back of Talmud volume",
        "disambiguation": None,
    },

    # ==========================================================================
    # SHULCHAN ARUCH & CODIFIERS
    # ==========================================================================
    {
        "id": "tur",
        "primary_name_he": "טור",
        "primary_name_en": "Tur",
        "full_name_he": "רבי יעקב בן אשר",
        "full_name_en": "Yaakov ben Asher",
        "era": "Rishonim",
        "period": "1269-1343",
        "region": "Spain",
        "variations": ["בעל הטורים", "יעקב בעל הטורים"],  # FIXED
        "works": ["Arba'ah Turim", "Baal HaTurim on Torah"],
        "category": "Halakha/Exegesis",
        "sefaria_base": "Tur",
        "commentary_on": [],
        "father": "Rosh",
        "super_commentaries": ["Beit Yosef", "Darkei Moshe", "Bach", "Drisha"],
        "four_sections": ["Orach Chaim", "Yoreh Deah", "Even HaEzer", "Choshen Mishpat"],
        "disambiguation": None,
    },
    {
        "id": "beit_yosef",
        "primary_name_he": "בית יוסף",
        "primary_name_en": "Beit Yosef",
        "full_name_he": "רבי יוסף קארו",
        "full_name_en": "Yosef Karo",
        "era": "Acharonim",
        "period": "1488-1575",
        "region": "Spain/Turkey/Israel",
        "variations": ["מרן", "יוסף קארו"],  # FIXED
        "works": ["Beit Yosef", "Shulchan Aruch", "Kesef Mishneh"],
        "category": "Halakha",
        "sefaria_base": "Beit Yosef on",
        "commentary_on": ["Tur"],
        "standard_position": "Alongside Tur",
        "codified_work": "Shulchan Aruch",
        "disambiguation": None,
    },
    {
        "id": "shulchan_aruch",
        "primary_name_he": "שולחן ערוך",
        "primary_name_en": "Shulchan Aruch",
        "full_name_he": "רבי יוסף קארו",
        "full_name_en": "Yosef Karo",
        "era": "Acharonim",
        "period": "1488-1575",
        "region": "Israel (Safed)",
        "variations": ['שו"ע'],  # FIXED: removed duplicate
        "works": ["Shulchan Aruch"],
        "category": "Halakha",
        "sefaria_base": "Shulchan Arukh",
        "commentary_on": [],
        "super_commentaries": ["Rema", "Taz", "Shach", "Magen Avraham", "Mishnah Berurah"],
        "nosei_keilim": ["Taz", "Shach", "Magen Avraham", "Pri Megadim"],
        "standard_position": "Central text with commentaries around",
        "four_sections": ["Orach Chaim", "Yoreh Deah", "Even HaEzer", "Choshen Mishpat"],
        "disambiguation": None,
    },
    {
        "id": "rema",
        "primary_name_he": 'רמ"א',
        "primary_name_en": "Rema",
        "full_name_he": "רבי משה איסרליש",
        "full_name_en": "Moshe Isserles",
        "era": "Acharonim",
        "period": "1530-1572",
        "region": "Poland (Krakow)",
        "school": "Ashkenaz",
        "variations": ['רמ״א', 'הרמ"א', 'איסרליש'],  # FIXED
        "works": ["Mapah (glosses on Shulchan Aruch)", "Darkei Moshe"],
        "category": "Halakha",
        "sefaria_base": "Rema on",
        "commentary_on": ["Shulchan Aruch"],
        "standard_position": "Integrated into Shulchan Aruch text",
        "represents": "Ashkenazic custom vs Sephardic (Shulchan Aruch)",
        "disambiguation": None,
    },
    {
        "id": "taz",
        "primary_name_he": 'ט"ז',
        "primary_name_en": "Taz",
        "full_name_he": "רבי דוד הלוי",
        "full_name_en": "David HaLevi Segal",
        "era": "Acharonim",
        "period": "1586-1667",
        "region": "Poland",
        "variations": ['ט״ז', 'טז', 'דוד הלוי'],  # FIXED
        "works": ["Turei Zahav"],
        "category": "Halakha",
        "sefaria_base": "Turei Zahav on",
        "commentary_on": ["Shulchan Aruch"],
        "standard_position": "Nosei Keilim on Shulchan Aruch",
        "disambiguation": None,
    },
    {
        "id": "shach",
        "primary_name_he": 'ש"ך',
        "primary_name_en": "Shach",
        "full_name_he": "רבי שבתי כהן",
        "full_name_en": "Shabtai Kohen",
        "era": "Acharonim",
        "period": "1622-1663",
        "region": "Lithuania/Poland",
        "variations": ['ש״ך', 'שך'],  # FIXED
        "works": ["Siftei Kohen"],
        "category": "Halakha",
        "sefaria_base": "Shach on",
        "commentary_on": ["Shulchan Aruch"],
        "standard_position": "Nosei Keilim on Shulchan Aruch (Yoreh Deah)",
        "primary_sections": ["Yoreh Deah", "Choshen Mishpat"],
        "disambiguation": None,
    },
    {
        "id": "magen_avraham",
        "primary_name_he": "מגן אברהם",
        "primary_name_en": "Magen Avraham",
        "full_name_he": "רבי אברהם אבלי גומבינר",
        "full_name_en": "Avraham Gombiner",
        "era": "Acharonim",
        "period": "1637-1683",
        "region": "Poland",
        "variations": ['מג"א', "גומבינר"],  # FIXED
        "works": ["Magen Avraham"],
        "category": "Halakha",
        "sefaria_base": "Magen Avraham on",
        "commentary_on": ["Shulchan Aruch Orach Chaim"],
        "standard_position": "Nosei Keilim on Orach Chaim",
        "primary_sections": ["Orach Chaim"],
        "disambiguation": None,
    },
    {
        "id": "mishna_berura",
        "primary_name_he": "משנה ברורה",
        "primary_name_en": "Mishnah Berurah",
        "full_name_he": "רבי ישראל מאיר הכהן",
        "full_name_en": "Yisrael Meir Kagan (Chofetz Chaim)",
        "era": "Acharonim",
        "period": "1838-1933",
        "region": "Poland/Lithuania",
        "variations": ['מ"ב', "חפץ חיים"],  # FIXED
        "works": ["Mishnah Berurah", "Chofetz Chaim", "Biur Halacha"],
        "category": "Halakha",
        "sefaria_base": "Mishnah Berurah",
        "commentary_on": ["Shulchan Aruch Orach Chaim"],
        "standard_position": "Standard commentary on Orach Chaim",
        "primary_sections": ["Orach Chaim"],
        "super_commentaries": ["Biur Halacha (own work)"],
        "disambiguation": None,
    },
    {
        "id": "aruch_hashulchan",
        "primary_name_he": "ערוך השולחן",
        "primary_name_en": "Aruch HaShulchan",
        "full_name_he": "רבי יחיאל מיכל עפשטיין",
        "full_name_en": "Yechiel Michel Epstein",
        "era": "Acharonim",
        "period": "1829-1908",
        "region": "Belarus",
        "variations": ["עה״ש"],  # FIXED
        "works": ["Aruch HaShulchan"],
        "category": "Halakha",
        "sefaria_base": "Arukh HaShulchan",
        "commentary_on": [],
        "all_four_sections": True,
        "disambiguation": None,
    },

    # ==========================================================================
    # CHOSHEN MISHPAT SPECIALISTS
    # ==========================================================================
    {
        "id": "ketzot_hachoshen",
        "primary_name_he": "קצות החושן",
        "primary_name_en": "Ketzot HaChoshen",
        "full_name_he": "רבי אריה ליב הכהן",
        "full_name_en": "Aryeh Leib Heller",
        "era": "Acharonim",
        "period": "1754-1813",
        "region": "Galicia",
        "variations": ["קצות", "קה״ח"],  # FIXED
        "works": ["Ketzot HaChoshen"],
        "category": "Halakha",
        "sefaria_base": "Ketzot HaChoshen on",
        "commentary_on": ["Shulchan Aruch Choshen Mishpat"],
        "standard_position": "Nosei Keilim on Choshen Mishpat",
        "primary_sections": ["Choshen Mishpat"],
        "pilpul_style": "Deep analytical approach",
        "disambiguation": None,
    },
    {
        "id": "netivot_hamishpat",
        "primary_name_he": "נתיבות המשפט",
        "primary_name_en": "Netivot HaMishpat",
        "full_name_he": "רבי יעקב ליסה",
        "full_name_en": "Yaakov Lissa",
        "era": "Acharonim",
        "period": "1760-1832",
        "region": "Poland",
        "variations": ["נתיבות"],  # FIXED
        "works": ["Netivot HaMishpat"],
        "category": "Halakha",
        "sefaria_base": "Netivot HaMishpat on",
        "commentary_on": ["Shulchan Aruch Choshen Mishpat"],
        "standard_position": "Nosei Keilim on Choshen Mishpat (alongside Ketzot)",
        "primary_sections": ["Choshen Mishpat"],
        "disambiguation": None,
    },

    # ==========================================================================
    # TALMUD COMMENTATORS - ACHARONIM
    # ==========================================================================
    {
        "id": "maharsha",
        "primary_name_he": 'מהרש"א',
        "primary_name_en": "Maharsha",
        "full_name_he": "רבי שמואל אליעזר איידלס",
        "full_name_en": "Shmuel Eidels",
        "era": "Acharonim",
        "period": "1555-1631",
        "region": "Poland",
        "variations": ['מהרש״א'],  # FIXED
        "works": ["Chiddushei Halachot", "Chiddushei Aggadot"],
        "category": "Talmud",
        "sefaria_base": "Maharsha on",
        "commentary_on": ["Talmud"],
        "masechta_coverage": "extensive",
        "standard_position": "Back of Talmud volume",
        "disambiguation": "Maharsha (not Maharshal)",
    },
    {
        "id": "maharshal",
        "primary_name_he": 'מהרש"ל',
        "primary_name_en": "Maharshal",
        "full_name_he": "רבי שלמה לוריא",
        "full_name_en": "Shlomo Luria",
        "era": "Acharonim",
        "period": "1510-1574",
        "region": "Poland",
        "variations": ['מהרש״ל'],  # FIXED
        "works": ["Yam Shel Shlomo", "Chochmat Shlomo"],
        "category": "Talmud/Halakha",
        "sefaria_base": "Maharshal on",
        "commentary_on": ["Talmud"],
        "disambiguation": "Maharshal (Shlomo, not Shmuel=Maharsha)",
    },
    {
        "id": "pnei_yehoshua",
        "primary_name_he": "פני יהושע",
        "primary_name_en": "Pnei Yehoshua",
        "full_name_he": "רבי יעקב יהושע פאלק",
        "full_name_en": "Yaakov Yehoshua Falk",
        "era": "Acharonim",
        "period": "1680-1756",
        "region": "Poland/Germany",
        "variations": ['פנ"י', "יעקב יהושע"],  # FIXED
        "works": ["Pnei Yehoshua"],
        "category": "Talmud",
        "sefaria_base": "Pnei Yehoshua on",
        "commentary_on": ["Talmud"],
        "masechta_coverage": "select",
        "standard_position": "Back of Talmud volume",
        "disambiguation": None,
    },
    {
        "id": "akiva_eiger",
        "primary_name_he": "רבי עקיבא איגר",
        "primary_name_en": "Rabbi Akiva Eiger",
        "full_name_he": "רבי עקיבא איגר",
        "full_name_en": "Akiva Eiger",
        "era": "Acharonim",
        "period": "1761-1837",
        "region": "Germany/Poland (Posen)",
        "variations": ['רע"א', "איגר"],  # FIXED
        "works": ["Gilyon HaShas", "Teshuvot R' Akiva Eiger"],
        "category": "Talmud/Halakha",
        "sefaria_base": "Rabbi Akiva Eiger on",
        "commentary_on": ["Talmud", "Shulchan Aruch"],
        "standard_position": "Margin glosses on Talmud",
        "disambiguation": None,
    },

    # ==========================================================================
    # MODERN POSKIM
    # ==========================================================================
    {
        "id": "igrot_moshe",
        "primary_name_he": "אגרות משה",
        "primary_name_en": "Igrot Moshe",
        "full_name_he": "רבי משה פיינשטיין",
        "full_name_en": "Moshe Feinstein",
        "era": "Acharonim (Contemporary)",
        "period": "1895-1986",
        "region": "USA (New York)",
        "variations": ['אג"מ', "רב משה", "פיינשטיין"],  # FIXED
        "works": ["Igrot Moshe", "Dibrot Moshe"],
        "category": "Halakha/Responsa",
        "sefaria_base": "Igrot Moshe",
        "commentary_on": [],
        "modern_posek": True,
        "disambiguation": None,
    },
    {
        "id": "yabia_omer",
        "primary_name_he": "יביע אומר",
        "primary_name_en": "Yabia Omer",
        "full_name_he": "רבי עובדיה יוסף",
        "full_name_en": "Ovadia Yosef",
        "era": "Acharonim (Contemporary)",
        "period": "1920-2013",
        "region": "Israel",
        "school": "Sefarad",
        "variations": ["יחוה דעת", "הרב עובדיה", 'יבי"א'],  # FIXED
        "works": ["Yabia Omer", "Yechaveh Daat", "Chazon Ovadia"],
        "category": "Halakha/Responsa",
        "sefaria_base": "Yabia Omer",
        "commentary_on": [],
        "modern_posek": True,
        "former_chief_rabbi": "Sephardic Chief Rabbi of Israel",
        "disambiguation": None,
    },
    {
        "id": "chazon_ish",
        "primary_name_he": "חזון איש",
        "primary_name_en": "Chazon Ish",
        "full_name_he": "רבי אברהם ישעיהו קרליץ",
        "full_name_en": "Avraham Yeshayahu Karelitz",
        "era": "Acharonim (Contemporary)",
        "period": "1878-1953",
        "region": "Lithuania/Israel",
        "variations": ['חזו"א'],  # FIXED
        "works": ["Chazon Ish"],
        "category": "Halakha/Talmud",
        "sefaria_base": "Chazon Ish on",
        "commentary_on": ["Shulchan Aruch", "select Talmud"],
        "modern_posek": True,
        "disambiguation": None,
    },

    # ==========================================================================
    # MUSAR & PHILOSOPHY & KABBALAH
    # ==========================================================================
    {
        "id": "ramchal",
        "primary_name_he": 'רמח"ל',
        "primary_name_en": "Ramchal",
        "full_name_he": "רבי משה חיים לוצאטו",
        "full_name_en": "Moshe Chaim Luzzatto",
        "era": "Acharonim",
        "period": "1707-1746",
        "region": "Italy/Amsterdam",
        "variations": ['רמח״ל', "לוצאטו"],  # FIXED
        "works": ["Mesillat Yesharim", "Derech HaShem", "Daat Tevunot"],
        "category": "Musar/Kabbalah/Philosophy",
        "sefaria_base": "Ramchal",
        "commentary_on": [],
        "disambiguation": None,
    },
    {
        "id": "chovot_halevavot",
        "primary_name_he": "חובת הלבבות",
        "primary_name_en": "Chovot HaLevavot",
        "full_name_he": "רבי בחיי אבן פקודה",
        "full_name_en": "Bahya ibn Paquda",
        "era": "Rishonim",
        "period": "11th century",
        "region": "Spain",
        "variations": ["רבינו בחיי", "בחיי"],  # FIXED
        "works": ["Chovot HaLevavot"],
        "category": "Musar/Philosophy",
        "sefaria_base": "Chovot HaLevavot",
        "commentary_on": [],
        "disambiguation": None,
    },
    {
        "id": "kuzari",
        "primary_name_he": "הכוזרי",
        "primary_name_en": "The Kuzari",
        "full_name_he": "רבי יהודה הלוי",
        "full_name_en": "Yehuda HaLevi",
        "era": "Rishonim",
        "period": "1075-1141",
        "region": "Spain",
        "variations": ["ספר הכוזרי", 'ריה"ל'],  # FIXED
        "works": ["Sefer HaKuzari"],
        "category": "Philosophy",
        "sefaria_base": "Kuzari",
        "commentary_on": [],
        "disambiguation": None,
    },

    # ==========================================================================
    # ACRONYM DISAMBIGUATION EXAMPLES
    # ==========================================================================
    {
        "id": "maharam_lublin",
        "primary_name_he": 'מהר"ם',
        "primary_name_en": "Maharam of Lublin",
        "full_name_he": "רבי מאיר בן גדליה מלובלין",
        "full_name_en": "Meir ben Gedaliah of Lublin",
        "era": "Acharonim",
        "period": "1558-1616",
        "region": "Poland (Lublin)",
        "variations": ['מהר"ם מלובלין'],  # FIXED: removed duplicate
        "works": ["Meir Einei Chachamim"],
        "category": "Talmud/Halakha",
        "sefaria_base": "Maharam of Lublin on",
        "commentary_on": ["Talmud"],
        "disambiguation": "Maharam of Lublin (16th century, NOT Rothenburg)",
    },
    {
        "id": "maharam_schick",
        "primary_name_he": 'מהר"ם',
        "primary_name_en": "Maharam Schick",
        "full_name_he": "רבי משה שיק",
        "full_name_en": "Moshe Schick",
        "era": "Acharonim",
        "period": "1807-1879",
        "region": "Hungary",
        "variations": ['מהר"ם שיק'],  # FIXED: removed duplicate
        "works": ["Teshuvot Maharam Schick"],
        "category": "Halakha/Responsa",
        "sefaria_base": "Maharam Schick",
        "commentary_on": [],
        "disambiguation": "Maharam Schick (19th century Hungary)",
    },
]

# ==============================================================================
#  ENHANCED UTILITY FUNCTIONS (FIXED)
# ==============================================================================

def normalize_text(text: str) -> str:
    """
    Normalizes Hebrew text for comparison.
    Handles quote variations, whitespace, final letters.
    """
    if not text:
        return ""
    
    # Replace unicode variants
    text = text.replace('״', '"').replace('׳', "'")
    # Normalize common stylized quotes to plain ASCII quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")

    return text.strip()


def build_lookup_index() -> Dict[str, List[Dict]]:
    """
    Builds a fast lookup index: normalized_name → [list of matching authors]
    Handles the case where multiple authors share an acronym (e.g., multiple Maharams)
    
    FIXED: Now deduplicates entries to prevent same author appearing multiple times
    """
    index = {}
    
    for author in TORAH_AUTHORS_KB:
        author_id = author['id']
        
        # Collect all names/variations for this author
        all_names = set()
        
        # Add primary name
        primary = normalize_text(author['primary_name_he'])
        all_names.add(primary)
        
        # Add all variations
        for var in author.get('variations', []):
            normalized = normalize_text(var)
            all_names.add(normalized)
        
        # Now add to index, checking for duplicates
        for name in all_names:
            if name not in index:
                index[name] = []
            
            # Check if this author is already in the list (by id)
            already_present = any(a['id'] == author_id for a in index[name])
            if not already_present:
                index[name].append(author)
    
    return index


# Build the index once on module load
AUTHOR_LOOKUP_INDEX = build_lookup_index()


def is_author(hebrew_term: str) -> bool:
    """Check if a Hebrew term is a known author."""
    normalized = normalize_text(hebrew_term)
    return normalized in AUTHOR_LOOKUP_INDEX


def get_author_matches(hebrew_term: str) -> List[Dict]:
    """
    Get all authors matching a Hebrew term.
    Returns list because some acronyms are ambiguous (e.g., multiple Maharams).
    """
    normalized = normalize_text(hebrew_term)
    return AUTHOR_LOOKUP_INDEX.get(normalized, [])


def disambiguate_author(hebrew_term: str, context: str = None, period: str = None) -> Optional[Dict]:
    """
    Disambiguate between multiple authors with same acronym.
    
    Args:
        hebrew_term: The Hebrew name/acronym
        context: Optional context (e.g., "13th century", "Rothenburg")
        period: Optional period hint
    
    Returns:
        Single best-matching author or None
    """
    matches = get_author_matches(hebrew_term)
    
    if not matches:
        return None
    
    if len(matches) == 1:
        return matches[0]
    
    # Multiple matches - need disambiguation
    if context:
        context_lower = context.lower()
        
        # Try matching by period
        for match in matches:
            if match.get('period', '').lower() in context_lower:
                return match
            
            # Try matching by region
            if match.get('region', '').lower() in context_lower:
                return match
            
            # Try matching by disambiguation string
            disambig = match.get('disambiguation', '')
            if disambig and any(word in context_lower for word in disambig.lower().split()):
                return match
    
    if period:
        # Try to match by period
        for match in matches:
            if period in match.get('period', ''):
                return match
    
    # If still ambiguous, return the most famous one (usually earliest or has disambiguation=None)
    for match in matches:
        if match.get('disambiguation') is None:
            return match
    
    # Last resort: return first match
    return matches[0]


def get_sefaria_ref(author_hebrew: str, sugya_ref: str) -> Optional[str]:
    """
    Construct a Sefaria reference for an author's commentary on a sugya.
    
    Args:
        author_hebrew: Hebrew name like "רן"
        sugya_ref: Base sugya like "Pesachim 4b"
    
    Returns:
        Constructed reference like "Ran on Pesachim 4b"
    """
    matches = get_author_matches(author_hebrew)
    
    if not matches:
        return None
    
    # Take first match (or disambiguate if needed)
    author = matches[0]
    
    sefaria_base = author.get('sefaria_base')
    if not sefaria_base:
        return None
    
    # Handle special cases (like Rif which doesn't use "on")
    if sefaria_base == "Rif":
        return f"Rif {sugya_ref}"
    
    # Standard format
    return f"{sefaria_base} {sugya_ref}"


def detect_authors_in_text(text: str) -> List[Dict]:
    """
    Scan text and identify all authors mentioned.
    Returns list of unique author objects found.
    """
    normalized_input = normalize_text(text)
    found_authors = []
    seen_ids = set()
    
    for author in TORAH_AUTHORS_KB:
        if author['id'] in seen_ids:
            continue
        
        # Check all variations
        variations = [normalize_text(v) for v in author.get('variations', [])]
        variations.append(normalize_text(author['primary_name_he']))
        
        for variant in variations:
            escaped_variant = re.escape(variant)
            if re.search(f"{escaped_variant}", normalized_input):
                found_authors.append(author)
                seen_ids.add(author['id'])
                break
    
    return found_authors


def export_to_json(filename: str = "torah_authors_master_kb.json"):
    """Export the entire KB to JSON."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(TORAH_AUTHORS_KB, f, indent=2, ensure_ascii=False)
        print(f"✓ Exported {len(TORAH_AUTHORS_KB)} authors to {filename}")
    except Exception as e:
        print(f"✗ Error exporting: {e}")


def get_stats() -> Dict:
    """Get statistics about the knowledge base."""
    stats = {
        'total_authors': len(TORAH_AUTHORS_KB),
        'rishonim': len([a for a in TORAH_AUTHORS_KB if 'Rishonim' in a.get('era', '')]),
        'acharonim': len([a for a in TORAH_AUTHORS_KB if 'Acharonim' in a.get('era', '')]),
        'tannaim_amoraim': len([a for a in TORAH_AUTHORS_KB if a.get('era') in ['Tannaim', 'Amoraim']]),
        'with_sefaria_base': len([a for a in TORAH_AUTHORS_KB if a.get('sefaria_base')]),
        'talmud_commentators': len([a for a in TORAH_AUTHORS_KB if 'Talmud' in a.get('category', '')]),
        'halakhic_authorities': len([a for a in TORAH_AUTHORS_KB if 'Halakha' in a.get('category', '')]),
        'biblical_commentators': len([a for a in TORAH_AUTHORS_KB if 'Exegesis' in a.get('category', '')]),
        'ambiguous_acronyms': len([k for k, v in AUTHOR_LOOKUP_INDEX.items() if len(v) > 1]),
    }
    return stats


# ==============================================================================
#  TESTING
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MASTER TORAH AUTHORS KNOWLEDGE BASE - PHASE 2 (FIXED)")
    print("=" * 70)
    
    stats = get_stats()
    print("\nKNOWLEDGE BASE STATISTICS:")
    for key, value in stats.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    
    print("\n" + "=" * 70)
    print("TESTING DUPLICATE FIX")
    print("=" * 70)
    
    # Test that Ran and Tosafot no longer have duplicates
    test_terms = ['רן', 'תוספות', 'רש"י']
    for term in test_terms:
        matches = get_author_matches(term)
        print(f"\n'{term}': {len(matches)} match(es)")
        for m in matches:
            print(f"  - {m['primary_name_en']} ({m['period']})")
    
    print("\n" + "=" * 70)
    print("TESTING SEFARIA REFERENCE CONSTRUCTION")
    print("=" * 70)
    
    test_cases = [
        ('רן', 'Pesachim 4b'),
        ('תוספות', 'Bava Metzia 10a'),
        ('רש"י', 'Ketubot 7b'),
    ]
    
    for author, sugya in test_cases:
        ref = get_sefaria_ref(author, sugya)
        print(f"  {author} + {sugya} → {ref}")