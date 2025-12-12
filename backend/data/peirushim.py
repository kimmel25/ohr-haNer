import json
import re
from typing import List, Dict, Optional, Set, Tuple

"""
THE GOLD STANDARD TORAH AUTHORS KNOWLEDGE BASE
==============================================
A comprehensive, structured dataset of Rabbinic authority throughout history.
Includes Rishonim, Acharonim, Geonim, and Biblical Commentators.

Features:
- Robust variation handling (quotes, acronyms).
- Categorization by Era and Region.
- Mapping of major works to authors.
"""

# ==============================================================================
#  DATASET: The Master List
# ==============================================================================

AUTHORS_DB = [
    # --------------------------------------------------------------------------
    # BIBLICAL COMMENTATORS (MEFARSHIM)
    # --------------------------------------------------------------------------
    {
        "id": "rashi",
        "primary_name_he": 'רש"י',
        "primary_name_en": "Rashi",
        "full_name_he": "רבי שלמה יצחקי",
        "full_name_en": "Shlomo Yitzchaki",
        "era": "Rishonim",
        "region": "France",
        "variations": ['רש"י', 'רש״י', 'רשי', 'שלמה יצחקי', 'בר יצחק'],
        "works": ["Perush Rashi on Torah", "Perush Rashi on Shas"],
        "category": "Exegesis/Talmud"
    },
    {
        "id": "ibn_ezra",
        "primary_name_he": "אבן עזרא",
        "primary_name_en": "Ibn Ezra",
        "full_name_he": "רבי אברהם אבן עזרא",
        "full_name_en": "Abraham Ibn Ezra",
        "era": "Rishonim",
        "region": "Spain",
        "variations": ['ראב"ע', 'ראב״ע', 'אבן עזרא'],
        "works": ["Sefer HaYashar", "Ibn Ezra on Torah"],
        "category": "Exegesis/Grammar"
    },
    {
        "id": "ramban_torah",
        "primary_name_he": 'רמב"ן',
        "primary_name_en": "Ramban",
        "full_name_he": "רבי משה בן נחמן",
        "full_name_en": "Moshe ben Nachman",
        "era": "Rishonim",
        "region": "Spain/Israel",
        "variations": ['רמב"ן', 'רמב״ן', 'רמבן', 'נחמני', 'בן נחמן'],
        "works": ["Ramban on Torah", "Milchamot HaShem"],
        "category": "Exegesis/Halakha/Kabbalah"
    },
    {
        "id": "rashbam",
        "primary_name_he": 'רשב"ם',
        "primary_name_en": "Rashbam",
        "full_name_he": "רבי שמואל בן מאיר",
        "full_name_en": "Shmuel ben Meir",
        "era": "Rishonim",
        "region": "France",
        "variations": ['רשב"ם', 'רשב״ם', 'רשבם'],
        "works": ["Rashbam on Torah", "Rashbam on Bava Batra"],
        "category": "Exegesis"
    },
    {
        "id": "sforno",
        "primary_name_he": "ספורנו",
        "primary_name_en": "Sforno",
        "full_name_he": "רבי עובדיה ספורנו",
        "full_name_en": "Ovadia Sforno",
        "era": "Rishonim", # Late Rishon/Early Acharon transition
        "region": "Italy",
        "variations": ["ספורנו", "עובדיה ספורנו"],
        "works": ["Sforno on Torah"],
        "category": "Exegesis"
    },
    {
        "id": "radak",
        "primary_name_he": 'רד"ק',
        "primary_name_en": "Radak",
        "full_name_he": "רבי דוד קמחי",
        "full_name_en": "David Kimchi",
        "era": "Rishonim",
        "region": "Provence",
        "variations": ['רד"ק', 'רד״ק', 'רדק', 'קמחי'],
        "works": ["Radak on NaCh", "Sefer HaShorashim"],
        "category": "Exegesis/Grammar"
    },
    {
        "id": "or_hachaim",
        "primary_name_he": "אור החיים",
        "primary_name_en": "Or HaChaim",
        "full_name_he": "רבי חיים בן עטר",
        "full_name_en": "Chaim ibn Attar",
        "era": "Acharonim",
        "region": "Morocco/Israel",
        "variations": ["אור החיים", 'אוה"ח', "אור החיים הקדוש", "בן עטר"],
        "works": ["Or HaChaim"],
        "category": "Exegesis/Kabbalah"
    },
    {
        "id": "kli_yakar",
        "primary_name_he": "כלי יקר",
        "primary_name_en": "Kli Yakar",
        "full_name_he": "רבי שלמה אפרים לונטשיץ",
        "full_name_en": "Shlomo Ephraim Luntschitz",
        "era": "Acharonim",
        "region": "Poland",
        "variations": ["כלי יקר", 'הכלי יקר'],
        "works": ["Kli Yakar"],
        "category": "Exegesis"
    },
    {
        "id": "malbim",
        "primary_name_he": 'מלבי"ם',
        "primary_name_en": "Malbim",
        "full_name_he": "רבי מאיר לייבוש",
        "full_name_en": "Meir Leibush",
        "era": "Acharonim",
        "region": "Eastern Europe",
        "variations": ['מלבי"ם', 'מלבי״ם', 'מלבים'],
        "works": ["HaTorah VeHaMitzvah", "Mikraei Kodesh"],
        "category": "Exegesis/Grammar"
    },
    {
        "id": "abarbanel",
        "primary_name_he": "אברבנאל",
        "primary_name_en": "Abarbanel",
        "full_name_he": "רבי דון יצחק אברבנאל",
        "full_name_en": "Don Isaac Abarbanel",
        "era": "Rishonim", # Late
        "region": "Spain/Italy",
        "variations": ["אברבנאל", "דון יצחק"],
        "works": ["Abarbanel on Torah", "Abarbanel on NaCh"],
        "category": "Exegesis/Philosophy"
    },

    # --------------------------------------------------------------------------
    # TALMUDIC RISHONIM & HALAKHIC CODIFIERS (EARLY)
    # --------------------------------------------------------------------------
    {
        "id": "rif",
        "primary_name_he": 'רי"ף',
        "primary_name_en": "The Rif",
        "full_name_he": "רבי יצחק אלפסי",
        "full_name_en": "Isaac Alfasi",
        "era": "Rishonim",
        "region": "North Africa",
        "variations": ['רי"ף', 'רי״ף', 'הריף', 'אלפסי'],
        "works": ["Sefer HaHalachot"],
        "category": "Halakha"
    },
    {
        "id": "tosafot",
        "primary_name_he": "תוספות",
        "primary_name_en": "Tosafot",
        "full_name_he": "בעלי התוספות",
        "full_name_en": "Baalei HaTosafot",
        "era": "Rishonim",
        "region": "France/Germany",
        "variations": ["תוספות", "תוס'", 'תוס'],
        "works": ["Tosafot on Shas"],
        "category": "Talmud"
    },
    {
        "id": "rambam_halakha",
        "primary_name_he": 'רמב"ם',
        "primary_name_en": "Rambam",
        "full_name_he": "רבי משה בן מימון",
        "full_name_en": "Moshe ben Maimon",
        "era": "Rishonim",
        "region": "Spain/Egypt",
        "variations": ['רמב"ם', 'רמב״ם', 'הרמב"ם', 'מימוני', 'נשר הגדול'],
        "works": ["Mishneh Torah", "Sefer HaMitzvot", "Moreh Nevukhim"],
        "category": "Halakha/Philosophy"
    },
    {
        "id": "rosh",
        "primary_name_he": 'רא"ש',
        "primary_name_en": "The Rosh",
        "full_name_he": "רבי אשר בן יחיאל",
        "full_name_en": "Asher ben Yechiel",
        "era": "Rishonim",
        "region": "Germany/Spain",
        "variations": ['רא"ש', 'רא״ש', 'הרא"ש'],
        "works": ["Piskei HaRosh"],
        "category": "Halakha"
    },
    {
        "id": "rashba",
        "primary_name_he": 'רשב"א',
        "primary_name_en": "Rashba",
        "full_name_he": "רבי שלמה בן אדרת",
        "full_name_en": "Shlomo ben Aderet",
        "era": "Rishonim",
        "region": "Spain",
        "variations": ['רשב"א', 'רשב״א', 'הרשב"א'],
        "works": ["Chiddushei HaRashba", "Teshuvot HaRashba"],
        "category": "Talmud/Halakha"
    },
    {
        "id": "ritva",
        "primary_name_he": 'ריטב"א',
        "primary_name_en": "Ritva",
        "full_name_he": "רבי יום טוב אשווילי",
        "full_name_en": "Yom Tov Asevilli",
        "era": "Rishonim",
        "region": "Spain",
        "variations": ['ריטב"א', 'ריטב״א', 'הריטב"א'],
        "works": ["Chiddushei HaRitva"],
        "category": "Talmud"
    },
    {
        "id": "ran",
        "primary_name_he": 'ר"ן',
        "primary_name_en": "The Ran",
        "full_name_he": "רבי ניסים מגירונא",
        "full_name_en": "Nissim of Gerona",
        "era": "Rishonim",
        "region": "Spain",
        "variations": ['ר"ן', 'ר״ן', 'הר"ן'],
        "works": ["Perush HaRan (Nedarim)", "Chiddushei HaRan"],
        "category": "Talmud"
    },
    {
        "id": "meiri",
        "primary_name_he": "המאירי",
        "primary_name_en": "Meiri",
        "full_name_he": "רבי מנחם המאירי",
        "full_name_en": "Menachem Meiri",
        "era": "Rishonim",
        "region": "Provence",
        "variations": ["מאירי", "המאירי", "בית הבחירה"],
        "works": ["Beit HaBechirah"],
        "category": "Talmud"
    },
    {
        "id": "tur",
        "primary_name_he": "טור",
        "primary_name_en": "Tur",
        "full_name_he": "רבי יעקב בן אשר",
        "full_name_en": "Yaakov ben Asher",
        "era": "Rishonim",
        "region": "Spain",
        "variations": ["טור", "בעל הטורים", "ארבעה טורים"],
        "works": ["Arba'ah Turim", "Baal HaTurim (Torah)"],
        "category": "Halakha"
    },
    {
        "id": "raavad",
        "primary_name_he": 'ראב"ד',
        "primary_name_en": "Raavad",
        "full_name_he": "רבי אברהם בן דוד",
        "full_name_en": "Abraham ben David",
        "era": "Rishonim",
        "region": "Provence",
        "variations": ['ראב"ד', 'ראב״ד', 'הראב"ד'],
        "works": ["Hassagot HaRaavad"],
        "category": "Halakha"
    },
    {
        "id": "chinuch",
        "primary_name_he": "ספר החינוך",
        "primary_name_en": "Sefer HaChinuch",
        "full_name_he": "רבי אהרון הלוי (מיוחס)",
        "full_name_en": "Aharon HaLevi (Attributed)",
        "era": "Rishonim",
        "region": "Spain",
        "variations": ["ספר החינוך", "החינוך"],
        "works": ["Sefer HaChinuch"],
        "category": "Mitzvot"
    },

    # --------------------------------------------------------------------------
    # ACHARONIM: SHULCHAN ARUCH & NOSEI KEILIM (THE "BIG GUNS")
    # --------------------------------------------------------------------------
    {
        "id": "mechaber",
        "primary_name_he": "מחבר",
        "primary_name_en": "The Mechaber",
        "full_name_he": "רבי יוסף קארו",
        "full_name_en": "Yosef Karo",
        "era": "Acharonim",
        "region": "Israel (Safed)",
        "variations": ["מחבר", "מרן", "בית יוסף", "שולחן ערוך", 'שו"ע', 'ב"י'],
        "works": ["Shulchan Aruch", "Beit Yosef", "Kesef Mishneh"],
        "category": "Halakha"
    },
    {
        "id": "rema",
        "primary_name_he": 'רמ"א',
        "primary_name_en": "Rema",
        "full_name_he": "רבי משה איסרליש",
        "full_name_en": "Moshe Isserles",
        "era": "Acharonim",
        "region": "Poland",
        "variations": ['רמ"א', 'רמ״א', 'הרמ"א'],
        "works": ["HaMappah (on Shulchan Aruch)", "Darkei Moshe"],
        "category": "Halakha"
    },
    {
        "id": "shach",
        "primary_name_he": 'ש"ך',
        "primary_name_en": "Shach",
        "full_name_he": "רבי שבתאי הכהן",
        "full_name_en": "Shabbatai HaKohen",
        "era": "Acharonim",
        "region": "Lithuania",
        "variations": ['ש"ך', 'ש״ך', 'שפתי כהן'],
        "works": ["Siftei Kohen"],
        "category": "Halakha (Yoreh Deah/Choshen Mishpat)"
    },
    {
        "id": "taz",
        "primary_name_he": 'ט"ז',
        "primary_name_en": "Taz",
        "full_name_he": "רבי דוד הלוי סגל",
        "full_name_en": "David HaLevi Segal",
        "era": "Acharonim",
        "region": "Poland",
        "variations": ['ט"ז', 'ט״ז', 'טורי זהב'],
        "works": ["Turei Zahav"],
        "category": "Halakha"
    },
    {
        "id": "magen_avraham",
        "primary_name_he": 'מג"א',
        "primary_name_en": "Magen Avraham",
        "full_name_he": "רבי אברהם גומבינר",
        "full_name_en": "Avraham Gombiner",
        "era": "Acharonim",
        "region": "Poland",
        "variations": ['מג"א', 'מגן אברהם'],
        "works": ["Magen Avraham"],
        "category": "Halakha (Orach Chaim)"
    },
    {
        "id": "biur_halacha",
        "primary_name_he": "משנה ברורה",
        "primary_name_en": "Mishnah Berurah",
        "full_name_he": "רבי ישראל מאיר הכהן",
        "full_name_en": "Yisrael Meir Kagan (Chofetz Chaim)",
        "era": "Acharonim",
        "region": "Poland/Belarus",
        "variations": ["משנה ברורה", 'מ"ב', "ביאור הלכה", "חפץ חיים", "שער הציון"],
        "works": ["Mishnah Berurah", "Chofetz Chaim", "Shemirat HaLashon"],
        "category": "Halakha"
    },
    {
        "id": "aruch_hashulchan",
        "primary_name_he": "ערוך השולחן",
        "primary_name_en": "Aruch HaShulchan",
        "full_name_he": "רבי יחיאל מיכל אפשטיין",
        "full_name_en": "Yechiel Michel Epstein",
        "era": "Acharonim",
        "region": "Lithuania",
        "variations": ["ערוך השולחן", 'ערוה"ש'],
        "works": ["Aruch HaShulchan"],
        "category": "Halakha"
    },
    {
        "id": "ben_ish_chai",
        "primary_name_he": "בן איש חי",
        "primary_name_en": "Ben Ish Chai",
        "full_name_he": "רבי יוסף חיים",
        "full_name_en": "Yosef Chaim of Baghdad",
        "era": "Acharonim",
        "region": "Iraq",
        "variations": ["בן איש חי", 'בא"ח', "ריח טוב"],
        "works": ["Ben Ish Chai", "Rav Pealim"],
        "category": "Halakha/Kabbalah"
    },
    {
        "id": "kaf_hachaim",
        "primary_name_he": "כף החיים",
        "primary_name_en": "Kaf HaChaim",
        "full_name_he": "רבי יעקב חיים סופר",
        "full_name_en": "Yaakov Chaim Sofer",
        "era": "Acharonim",
        "region": "Iraq/Israel",
        "variations": ["כף החיים", 'כה"ח'],
        "works": ["Kaf HaChaim"],
        "category": "Halakha"
    },

    # --------------------------------------------------------------------------
    # LOMDUS (ANALYTICAL) & RESPONSA GIANTS
    # --------------------------------------------------------------------------
    {
        "id": "ketzot",
        "primary_name_he": "קצות",
        "primary_name_en": "Ketzot",
        "full_name_he": "רבי אריה לייב הלר",
        "full_name_en": "Aryeh Leib Heller",
        "era": "Acharonim",
        "region": "Galicia",
        "variations": ["קצות", "קצות החושן", 'קה"ח'],
        "works": ["Ketzot HaChoshen", "Shev Shma'tata"],
        "category": "Halakha/Lomdus"
    },
    {
        "id": "netivot",
        "primary_name_he": "נתיבות",
        "primary_name_en": "Netivot",
        "full_name_he": "רבי יעקב לורברבוים",
        "full_name_en": "Yaakov Lorberbaum",
        "era": "Acharonim",
        "region": "Poland",
        "variations": ["נתיבות", "נתיבות המשפט"],
        "works": ["Netivot HaMishpat", "Chavat Daat"],
        "category": "Halakha/Lomdus"
    },
    {
        "id": "noda_biyehuda",
        "primary_name_he": "נודע ביהודה",
        "primary_name_en": "Noda BiYehuda",
        "full_name_he": "רבי יחזקאל לנדא",
        "full_name_en": "Yechezkel Landau",
        "era": "Acharonim",
        "region": "Prague",
        "variations": ["נודע ביהודה", "צל״ח", 'צל"ח'],
        "works": ["Noda BiYehuda", "Tzlach"],
        "category": "Responsa/Talmud"
    },
    {
        "id": "chatam_sofer",
        "primary_name_he": "חתם סופר",
        "primary_name_en": "Chatam Sofer",
        "full_name_he": "רבי משה סופר",
        "full_name_en": "Moshe Sofer",
        "era": "Acharonim",
        "region": "Hungary",
        "variations": ["חתם סופר", 'חת"ס'],
        "works": ["Chatam Sofer (Responsa)", "Torat Moshe"],
        "category": "Responsa/Halakha"
    },
    {
        "id": "gra",
        "primary_name_he": 'הגר"א',
        "primary_name_en": "Vilna Gaon",
        "full_name_he": "רבי אליהו מווילנא",
        "full_name_en": "Elijah of Vilna",
        "era": "Acharonim",
        "region": "Lithuania",
        "variations": ['הגר"א', 'גר"א', 'הגאון מווילנא'],
        "works": ["Biur HaGra", "Shenot Eliyahu"],
        "category": "All"
    },
    {
        "id": "maharsha",
        "primary_name_he": 'מהרש"א',
        "primary_name_en": "Maharsha",
        "full_name_he": "רבי שמואל אליעזר איידלס",
        "full_name_en": "Shmuel Eidels",
        "era": "Acharonim",
        "region": "Poland",
        "variations": ['מהרש"א', 'מהרש״א'],
        "works": ["Chiddushei Halachot", "Chiddushei Aggadot"],
        "category": "Talmud"
    },
    {
        "id": "akiva_eiger",
        "primary_name_he": "רבי עקיבא איגר",
        "primary_name_en": "Rabbi Akiva Eiger",
        "full_name_he": "רבי עקיבא איגר",
        "full_name_en": "Akiva Eiger",
        "era": "Acharonim",
        "region": "Germany/Poland",
        "variations": ["רעKA", "רבי עקיבא איגר", 'רע"א'],
        "works": ["Gilyon HaShas", "Teshuvot R' Akiva Eiger"],
        "category": "Talmud/Halakha"
    },

    # --------------------------------------------------------------------------
    # MODERN POSKIM
    # --------------------------------------------------------------------------
    {
        "id": "igrot_moshe",
        "primary_name_he": "אגרות משה",
        "primary_name_en": "Igrot Moshe",
        "full_name_he": "רבי משה פיינשטיין",
        "full_name_en": "Moshe Feinstein",
        "era": "Acharonim (Modern)",
        "region": "USA",
        "variations": ["אגרות משה", 'אג"מ', "רב משה"],
        "works": ["Igrot Moshe", "Dibrot Moshe"],
        "category": "Halakha"
    },
    {
        "id": "yabia_omer",
        "primary_name_he": "יביע אומר",
        "primary_name_en": "Yabia Omer",
        "full_name_he": "רבי עובדיה יוסף",
        "full_name_en": "Ovadia Yosef",
        "era": "Acharonim (Modern)",
        "region": "Israel",
        "variations": ["יביע אומר", "יחוה דעת", "הרב עובדיה", 'יבי"א'],
        "works": ["Yabia Omer", "Yechaveh Daat", "Chazon Ovadia"],
        "category": "Halakha"
    },
    {
        "id": "chazon_ish",
        "primary_name_he": "חזון איש",
        "primary_name_en": "Chazon Ish",
        "full_name_he": "רבי אברהם ישעיהו קרליץ",
        "full_name_en": "Avraham Yeshayahu Karelitz",
        "era": "Acharonim (Modern)",
        "region": "Israel",
        "variations": ["חזון איש", 'חזו"א'],
        "works": ["Chazon Ish"],
        "category": "Halakha/Talmud"
    },

    # --------------------------------------------------------------------------
    # MUSAR & PHILOSOPHY
    # --------------------------------------------------------------------------
    {
        "id": "ramchal",
        "primary_name_he": 'רמח"ל',
        "primary_name_en": "Ramchal",
        "full_name_he": "רבי משה חיים לוצאטו",
        "full_name_en": "Moshe Chaim Luzzatto",
        "era": "Acharonim",
        "region": "Italy",
        "variations": ['רמח"ל', "מסילת ישרים", "דרך ה'"],
        "works": ["Mesillat Yesharim", "Derech HaShem"],
        "category": "Musar/Kabbalah"
    },
    {
        "id": "chovot_halevavot",
        "primary_name_he": "חובת הלבבות",
        "primary_name_en": "Chovot HaLevavot",
        "full_name_he": "רבי בחיי אבן פקודה",
        "full_name_en": "Bahya ibn Paquda",
        "era": "Rishonim",
        "region": "Spain",
        "variations": ["חובת הלבבות", "רבינו בחיי"],
        "works": ["Chovot HaLevavot", "Rabbeinu Bahya on Torah"],
        "category": "Musar/Philosophy"
    },
    {
        "id": "kuzari",
        "primary_name_he": "הכוזרי",
        "primary_name_en": "The Kuzari",
        "full_name_he": "רבי יהודה הלוי",
        "full_name_en": "Yehuda HaLevi",
        "era": "Rishonim",
        "region": "Spain",
        "variations": ["הכוזרי", "ספר הכוזרי", "ריה״ל"],
        "works": ["Sefer HaKuzari"],
        "category": "Philosophy"
    }
]

# ==============================================================================
#  UTILITY FUNCTIONS
# ==============================================================================

def normalize_text(text: str) -> str:
    """
    Normalizes Hebrew text for comparison.
    1. Replaces fancy quotes (gershayim) with standard quotes.
    2. Strips whitespace.
    
    Args:
        text (str): The Hebrew string to normalize.
        
    Returns:
        str: Normalized string.
    """
    if not text:
        return ""
    
    # Replace unicode variants of quotes/apostrophes
    text = text.replace('״', '"').replace('׳', "'")
    # Replace common quote variants used in Torah databases
    text = text.replace('”', '"').replace('’', "'")
    return text.strip()

def get_all_search_terms() -> Set[str]:
    """
    Generates a set of ALL valid Hebrew search terms for authors.
    Useful for building a quick lookup index.
    """
    terms = set()
    for author in AUTHORS_DB:
        # Add primary name
        terms.add(normalize_text(author['primary_name_he']))
        # Add all variations
        for var in author['variations']:
            terms.add(normalize_text(var))
    return terms

def detect_references(text: str) -> List[Dict]:
    """
    Scans a block of text (e.g., a sentence or paragraph) and identifies
    any authors mentioned within it.
    
    Args:
        text (str): The input text to scan.
        
    Returns:
        List[Dict]: A list of author objects found in the text.
    """
    normalized_input = normalize_text(text)
    found_authors = []
    
    # We iterate through the DB. 
    # Note: For very large texts, an Aho-Corasick algorithm or Trie would be faster.
    # For typical use cases, this loop is sufficient.
    
    for author in AUTHORS_DB:
        # Check all variations for this author
        variations = [normalize_text(v) for v in author['variations']]
        variations.append(normalize_text(author['primary_name_he']))
        
        # Check if any variation exists in the input text
        # We use regex word boundaries to avoid partial matches (e.g., matching 'Ran' inside 'Raanana')
        # However, Hebrew word boundaries are tricky. 
        # Simple inclusion check is often safer for acronyms, but we must be careful.
        
        for variant in variations:
            # Escape regex characters in the variant name
            escaped_variant = re.escape(variant)
            
            # Look for the variant in the text
            if re.search(f"{escaped_variant}", normalized_input):
                found_authors.append(author)
                break # Found this author, move to next author
                
    return found_authors

def export_to_json(filename: str = "torah_authors_kb.json"):
    """
    Exports the entire Knowledge Base to a clean JSON file.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(AUTHORS_DB, f, indent=4, ensure_ascii=False)
        print(f"Successfully exported {len(AUTHORS_DB)} authors to {filename}")
    except Exception as e:
        print(f"Error exporting JSON: {e}")

# ==============================================================================
#  MAIN EXECUTION
# ==============================================================================

if __name__ == "__main__":
    print("--- TORAH AUTHORS KNOWLEDGE BASE ---")
    print(f"Total Authors Loaded: {len(AUTHORS_DB)}")
    
    # 1. Export the JSON as requested
    export_to_json()
    
    # 2. Test Detection Logic
    test_phrase = 'כמו שכתב הרמב"ם בהלכות תשובה וגם הראב"ד השיג עליו, וכן פסק השולחן ערוך'
    print(f"\nTesting detection on phrase: '{test_phrase}'")
    
    detected = detect_references(test_phrase)
    
    print(f"Found {len(detected)} authors:")
    for author in detected:
        print(f" - {author['primary_name_en']} ({author['era']})")
        
    # 3. Test Variation Handling
    print("\nTesting Variation Normalization:")
    rashi_var1 = 'רש"י'
    rashi_var2 = 'רש״י' # Hebrew gershayim
    
    print(f"Normalizing '{rashi_var1}': {normalize_text(rashi_var1)}")
    print(f"Normalizing '{rashi_var2}': {normalize_text(rashi_var2)}")
    print(f"Match? {normalize_text(rashi_var1) == normalize_text(rashi_var2)}")