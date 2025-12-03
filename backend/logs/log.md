2025-12-02 09:27:52 | INFO     | root:setup_logging:47 | ================================================================================
2025-12-02 09:27:52 | INFO     | root:setup_logging:48 | Marei Mekomos V5 - Flexible Thinking - Logging initialized
2025-12-02 09:27:52 | INFO     | root:setup_logging:49 | Log file: C:\Projects\marei-mekomos\backend\logs\marei_mekomos_20251202.log
2025-12-02 09:27:52 | INFO     | root:setup_logging:50 | ================================================================================
2025-12-02 09:27:52 | CRITICAL | main:<module>:118 | ANTHROPIC_API_KEY not found in environment variables!
2025-12-02 09:33:43 | INFO     | root:setup_logging:47 | ================================================================================
2025-12-02 09:33:43 | INFO     | root:setup_logging:48 | Marei Mekomos V5 - Flexible Thinking - Logging initialized
2025-12-02 09:33:43 | INFO     | root:setup_logging:49 | Log file: c:\Projects\marei-mekomos\backend\logs\marei_mekomos_20251202.log
2025-12-02 09:33:43 | INFO     | root:setup_logging:50 | ================================================================================
2025-12-02 09:33:43 | INFO     | __main__:<module>:121 | ✓ Anthropic client initialized successfully
2025-12-02 09:33:43 | INFO     | vector_search:__init__:55 | VectorSearchEngine initializing...
2025-12-02 09:33:43 | INFO     | vector_search:__init__:56 |   Embeddings directory: c:\Projects\marei-mekomos\backend\embeddings
2025-12-02 09:33:43 | INFO     | vector_search:__init__:66 |   ✓ BEREL dependencies available
2025-12-02 09:33:43 | INFO     | vector_search:__init__:67 |   Note: Embeddings will be loaded on first search
2025-12-02 09:33:43 | INFO     | __main__:<module>:126 | ✓ Vector search engine ready
2025-12-02 09:33:43 | INFO     | __main__:<module>:1027 | 🚀 Starting Marei Mekomos API v5.0 (Hybrid Search)
2025-12-02 09:33:43 | INFO     | __main__:<module>:1028 |    New: Intelligent transliteration resolution
2025-12-02 09:33:43 | INFO     | __main__:<module>:1029 |    Vector search ready: YES ✓
2025-12-02 09:33:43 | INFO     | __main__:<module>:1030 |    Listening on http://0.0.0.0:8000
2025-12-02 09:33:43 | DEBUG    | asyncio:__init__:623 | Using proactor: IocpProactor
2025-12-02 09:34:06 | INFO     | __main__:search_sources:833 | ====================================================================================================
2025-12-02 09:34:06 | INFO     | __main__:search_sources:834 | NEW SEARCH REQUEST: 'beheima chezkas issur omedes'
2025-12-02 09:34:06 | INFO     | __main__:search_sources:837 | ====================================================================================================
2025-12-02 09:34:06 | INFO     | __main__:search_sources:847 | 
🔍 Attempting hybrid transliteration resolution...
2025-12-02 09:34:06 | INFO     | hybrid_resolver:resolve:96 | ================================================================================
2025-12-02 09:34:06 | INFO     | hybrid_resolver:resolve:97 | HYBRID RESOLUTION: Starting
2025-12-02 09:34:06 | INFO     | hybrid_resolver:resolve:98 | ================================================================================
2025-12-02 09:34:06 | INFO     | hybrid_resolver:resolve:99 |   Original query: 'beheima chezkas issur omedes'
2025-12-02 09:34:06 | DEBUG    | hybrid_resolver:needs_resolution:74 | Query: 'beheima chezkas issur omedes' | Hebrew ratio: 0.00 | Needs resolution: True
2025-12-02 09:34:06 | INFO     | hybrid_resolver:resolve:118 | 
[STAGE 1] Vector Search - Finding Candidates
2025-12-02 09:34:06 | INFO     | hybrid_resolver:resolve:119 | ------------------------------------------------------------
2025-12-02 09:34:06 | INFO     | hybrid_resolver:_get_vector_candidates:157 |   Searching vector index for: 'beheima chezkas issur omedes'
2025-12-02 09:34:06 | DEBUG    | vector_search:search:185 | Vector search for: 'beheima chezkas issur omedes' (top_k=20)
2025-12-02 09:34:06 | INFO     | vector_search:_load_berel_model:74 | Loading BEREL model...
2025-12-02 09:34:06 | DEBUG    | requests.packages.urllib3.connectionpool:_new_conn:817 | Starting new HTTPS connection (1): huggingface.co
2025-12-02 09:34:06 | DEBUG    | requests.packages.urllib3.connectionpool:_make_request:393 | https://huggingface.co:443 "HEAD /dicta-il/BEREL/resolve/main/tokenizer_config.json HTTP/1.1" 307 0
2025-12-02 09:34:06 | DEBUG    | requests.packages.urllib3.connectionpool:_make_request:393 | https://huggingface.co:443 "HEAD /api/resolve-cache/models/dicta-il/BEREL/029fa610debddd0cd798f8babc33e41388fb2bac/tokenizer_config.json HTTP/1.1" 200 0
2025-12-02 09:34:07 | DEBUG    | requests.packages.urllib3.connectionpool:_make_request:393 | https://huggingface.co:443 "GET /api/models/dicta-il/BEREL/tree/main/additional_chat_templates?recursive=False&expand=False HTTP/1.1" 404 64
2025-12-02 09:34:07 | DEBUG    | requests.packages.urllib3.connectionpool:_make_request:393 | https://huggingface.co:443 "GET /api/models/dicta-il/BEREL/tree/main?recursive=True&expand=False HTTP/1.1" 200 1208
2025-12-02 09:34:07 | DEBUG    | requests.packages.urllib3.connectionpool:_make_request:393 | https://huggingface.co:443 "GET /api/models/dicta-il/BEREL HTTP/1.1" 200 1324
2025-12-02 09:34:07 | DEBUG    | requests.packages.urllib3.connectionpool:_make_request:393 | https://huggingface.co:443 "HEAD /dicta-il/BEREL/resolve/main/config.json HTTP/1.1" 307 0
2025-12-02 09:34:07 | DEBUG    | requests.packages.urllib3.connectionpool:_make_request:393 | https://huggingface.co:443 "HEAD /api/resolve-cache/models/dicta-il/BEREL/029fa610debddd0cd798f8babc33e41388fb2bac/config.json HTTP/1.1" 200 0
2025-12-02 09:34:08 | INFO     | vector_search:_load_berel_model:81 |   ✓ BEREL model loaded successfully
2025-12-02 09:34:08 | INFO     | vector_search:_load_embeddings:92 | Loading pre-computed embeddings...
2025-12-02 09:34:08 | INFO     | vector_search:_load_embeddings:120 |   ✓ Loaded 5616 text embeddings
2025-12-02 09:34:08 | INFO     | vector_search:_load_embeddings:121 |   ✓ Embedding dimension: 768
2025-12-02 09:34:09 | DEBUG    | vector_search:search:207 |   Query embedded (shape: (768,))
2025-12-02 09:34:10 | DEBUG    | vector_search:search:242 |   Top 3 matches:
2025-12-02 09:34:10 | DEBUG    | vector_search:search:244 |     [1] Zevachim 121b (score: 0.701)
2025-12-02 09:34:10 | DEBUG    | vector_search:search:244 |     [2] Chiddushei HaRambam on Rosh Hashanah 24b (score: 0.674)
2025-12-02 09:34:10 | DEBUG    | vector_search:search:244 |     [3] Menachot 68b (score: 0.584)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [1] Zevachim 121b (score: 0.701)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [2] Chiddushei HaRambam on Rosh Hashanah 24b (score: 0.674)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [3] Menachot 68b (score: 0.584)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [4] Chullin 90b (score: 0.583)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [5] Tractate Mezuzah 2a (score: 0.571)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [6] Tosafot Chad Mikamei on Yevamot 56b (score: 0.563)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [7] Menachot 14a (score: 0.562)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [8] Nedarim 46a (score: 0.559)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [9] Tosafot Chad Mikamei on Yevamot 18a (score: 0.558)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [10] Chullin 84b (score: 0.558)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [11] Tractate Tzitzit 2a (score: 0.557)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [12] Tosafot Chad Mikamei on Yevamot 102b (score: 0.553)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [13] Zevachim 44a (score: 0.551)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [14] Tosafot Chad Mikamei on Yevamot 26b (score: 0.550)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [15] Tosafot Chad Mikamei on Yevamot 35b (score: 0.543)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [16] Tractate Soferim 4b (score: 0.541)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [17] Bava Batra 177b (score: 0.540)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [18] Tractate Gerim 3a (score: 0.540)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [19] Shabbat 158b (score: 0.539)
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_get_vector_candidates:182 |     [20] Chullin 79a (score: 0.538)
2025-12-02 09:34:10 | INFO     | hybrid_resolver:_get_vector_candidates:184 |   ✓ Retrieved 20 candidates
2025-12-02 09:34:10 | INFO     | hybrid_resolver:resolve:131 |   ✓ Found 20 candidates for Claude to review
2025-12-02 09:34:10 | INFO     | hybrid_resolver:resolve:134 | 
[STAGE 2] Claude Verification - Picking Best Match
2025-12-02 09:34:10 | INFO     | hybrid_resolver:resolve:135 | ------------------------------------------------------------
2025-12-02 09:34:10 | DEBUG    | hybrid_resolver:_claude_verify:248 |   Sending 20 candidates to Claude...
2025-12-02 09:34:10 | DEBUG    | anthropic._base_client:_build_request:493 | Request options: {'method': 'post', 'url': '/v1/messages', 'timeout': Timeout(connect=5.0, read=600, write=600, pool=600), 'files': None, 'idempotency_key': 'stainless-python-retry-411396ff-f41e-47c9-bf12-3041c4660346', 'json_data': {'max_tokens': 1000, 'messages': [{'role': 'user', 'content': 'User\'s query: "beheima chezkas issur omedes"\n\nHere are the top 20 potential matches from our vector search:\n\n\n[Candidate #1] (similarity: 0.701)\nSource: Zevachim 121b\nHebrew: מה עופות שאין המום פוסל בהן זמן פוסל בהן קדשי במה קטנה שהמום פוסל בהן אינו דין שזמן פוסל בהן מה לעופות שכן אין הזר כשר בהן תאמר בבמה קטנה שהזר כשר בה לא יהא זמן פסול בה ת"ל (ויקרא ז, יא) וזאת תורת זבח השלמים לעשות זמן במה קטנה כזמן במה גדולה: <br><br><big><strong>הדרן עלך פרת חטאת וסליקא לה מסכת זבח\nEnglish: <b>If bird</b> offerings, whose <i>halakhot</i> are more lenient in <b>that a blemish does not disqualify them, are</b> nevertheless <b>disqualified by time,</b> then with regard to <b>sacrificial</b> animals <b>of a small</b> private <b>altar, which are disqualified by a blemish, is it not logical \n--------------------------------------------------\n\n[Candidate #2] (similarity: 0.674)\nSource: Chiddushei HaRambam on Rosh Hashanah 24b\nHebrew: <b>היינו לפני החמה היינו לצפונה היינו לאחר החמה היינו לדרומה.</b> פירוש כבר פירשנו למעלה שהירח קודם המולד הוא אחר השמש שעדיין לא נקבץ עמה ואחר המולד הוא לפני השמש שכבר נקבץ עמה והלך לפניה. ועל זה הקשינו היינו לפני החמה היינו לצפונה כלומר וכי בארבע רוחות מהלך אינו מהלך אלא בשני רוחות או לפני החמה כגו\n--------------------------------------------------\n\n[Candidate #3] (similarity: 0.584)\nSource: Menachot 68b\nHebrew: אי הכי אפילו חלה נמי אפשר דאפי לה פחות מחמשת רבעים קמח ועוד תרומה נמי אפשר דעביד לה כדר\' אושעיא דאמר רבי אושעיא מערים אדם על תבואתו ומכניסה במוץ שלה כדי שתהא בהמתו אוכלת ופטורה מן המעשר אי נמי דעייל לה דרך גגות ודרך קרפיפות התם בפרהסיא זילא ביה מילתא הכא בצינעא לא זילא ביה מילתא: <big><strong>מתני׳<\nEnglish: The Gemara asks: <b>If so,</b> then <b><i>ḥalla</i></b> should be subject to the same rabbinic decree <b>as well,</b> to prevent someone from circumventing their obligation to separate <i>ḥalla</i> by temporarily selling their dough to a gentile who will knead it and return it to them. Why then does\n--------------------------------------------------\n\n[Candidate #4] (similarity: 0.583)\nSource: Chullin 90b\nHebrew: שיעורא בעינן ועבודת כוכבים כתותי מכתת שיעורא הכא כל מה דמכתת מעלי לכסוי: <br><br><big><strong>הדרן עלך כסוי הדם</strong></big><br><br> מתני׳ <big><strong>גיד</strong></big> הנשה נוהג בארץ ובחוצה לארץ בפני הבית ושלא בפני הבית בחולין ובמוקדשין ונוהג בבהמה ובחיה בירך של ימין ובירך של שמאל ואינו נוהג בע\nEnglish: <b>we require</b> a minimum <b>measure</b> in order to fulfill these mitzvot. A shofar must be large enough that, when grasped, part of it protrudes from both sides of one’s hand, and a <i>lulav</i> must be at least four handbreadths long. <b>And</b> since an object of <b>idol worship</b> and its ef\n--------------------------------------------------\n\n[Candidate #5] (similarity: 0.571)\nSource: Tractate Mezuzah 2a\nHebrew: אין כותבין מזוזות <i data-commentator="Mesorat HaShas" data-order="1"></i>לא על גבי עורות בהמה טמאה ולא על גבי עורות חיה טמאה אבל כותבין על עורות נבלות ועל עורות טרפות <i data-commentator="Mesorat HaShas" data-order="2"></i>ואין חוששין שמא עורות לבובין הם <i data-commentator="Mesorat HaShas" data-or\nEnglish: It is not permitted to write <i>mezuzoth</i> on the skins of ritually unclean cattle or on skins of ritually unclean wild animals. It is permitted, however, to write them on skins of <i>nebeloth</i> and <i>ṭerefoth</i>, and there is no need to consider the possibility of their having been pierced at\n--------------------------------------------------\n\n[Candidate #6] (similarity: 0.563)\nSource: Tosafot Chad Mikamei on Yevamot 56b\nHebrew: אמר רבה שכבת זרע דכתב גבי שפחה חרופה למעט מינה דכל חייבי לאוין בהעראה דא"כ לישתוק קרא מיניה דשפחה חרופה. שכבת זרע דאשת איש למ"ד משמש מת בעריות חייב פרט למשמש מתה. שכבת זרע דסוטה לאו למעקרה קינא לה שלא כדרכה דהא משכבי אשה [כתיב]. אלא פרט שקנא לה דרך אבריה ואע"ג דפריצות בעלמא איצטריך ס"ד בקפידא דבעל ת\n--------------------------------------------------\n\n[Candidate #7] (similarity: 0.562)\nSource: Menachot 14a\nHebrew: הא תו למה לי אי לאכול ולאכול דבר שאין דרכו לאכול קמ"ל דמצטרף מרישא (דסיפא) שמעת מינה (דקתני כחצי זית בחוץ כחצי זית למחר פסול הא כחצי זית למחר וכחצי זית למחר פיגול) אי לאכול ולהקטיר (דהיא גופא קמ"ל) מדיוקא דרישא שמעת מינה דהשתא מה לאכול ולאכול דבר שאין דרכו לאכול אמרת לא מצטרף לאכול ולהקטיר מיבעיא אי\nEnglish: According to Abaye, <b>why do I also</b> need <b>this</b> mishna here? <b>If</b> you will suggest that this mishna is necessary, as one can infer from it that if one intended <b>to partake</b> of half an olive-bulk the next day <b>and</b> then intended <b>to partake of</b> another half an olive-bulk\n--------------------------------------------------\n\n[Candidate #8] (similarity: 0.559)\nSource: Nedarim 46a\nHebrew: אִיבָּעֵית אֵימָא: הָא דְּאַפְקְרֵיהּ בְּאַנְפֵּי תְרֵין, וְהָא דְּאַפְקְרֵיהּ בְּאַפֵּי תְלָתָא. דְּאָמַר רַבִּי יוֹחָנָן מִשּׁוּם רַבִּי שִׁמְעוֹן בֶּן יְהוֹצָדָק: כׇּל הַמַּפְקִיר בִּפְנֵי שְׁלֹשָׁה — הָוֵי הֶפְקֵר, בִּפְנֵי שְׁנַיִם — לָא הָוֵי הֶפְקֵר. וְרַבִּי יְהוֹשֻׁעַ בֶּן לֵוִי אָמַר: דְּב\nEnglish: <b>If you wish, say</b> instead: <b>That</b> <i>baraita</i>, in which it is taught that the item does not leave the possession of the owner until it enters the possession of another, is referring to a case <b>where</b> one declared it ownerless <b>before two</b> people; <b>and this</b> <i>baraita</i\n--------------------------------------------------\n\n[Candidate #9] (similarity: 0.558)\nSource: Tosafot Chad Mikamei on Yevamot 18a\nHebrew: הא דתנן עשה בה מאמר ומת חולצת ולא מתיבמת ה"ה אע"ג דלא עבד בה מאמר שניה מחלץ חלצה יבומי לא מיבמה דקי"ל כשמואל דאמר יש זיקה אפי\' בתרי אחי וה"ל צרת א)אחות אשה בזיקה. והא דקתני עשה בה מאמר לאפוקי מב"ש דאמרי מאמר קונה קנין גמור קמ"ל:\n--------------------------------------------------\n\n[Candidate #10] (similarity: 0.558)\nSource: Chullin 84b\nHebrew: רבי אומר יום אחד יום המיוחד טעון כרוז מכאן אמרו בארבעה פרקים בשנה המוכר בהמה לחבירו צריך להודיעו: <br><br><big><strong>הדרן עלך אותו ואת בנו</strong></big><br><br> מתני׳ <big><strong>כסוי</strong></big> הדם נוהג בארץ ובחוצה לארץ בפני הבית ושלא בפני הבית בחולין אבל לא במוקדשין ונוהג בחיה ובעוף במזומן\nEnglish: § <b>Rabbi</b> Yehuda HaNasi <b>says:</b> The verse: “You shall not slaughter it and its offspring both in <b>one day”</b> (Leviticus 22:28), is referring to a special day, and it indicates that <b>a special day requires a proclamation</b> to prevent buyers from slaughtering an animal together with \n--------------------------------------------------\n\n[Candidate #11] (similarity: 0.557)\nSource: Tractate Tzitzit 2a\nHebrew: <i data-commentator="Mesorat HaShas" data-order="1"></i>הכל חייבים בציצית רבי שמעון פוטר בנשים מפני שהזמן גרמא <i data-commentator="Mesorat HaShas" data-order="2"></i>כל קטן שהוא יודע להתעטף בציצית אביו עושה לו ציצית <i data-commentator="Mesorat HaShas" data-order="3"></i>טלית שהוא <i data-commentat\nEnglish: All<sup class="footnote-marker">1</sup><i class="footnote">Even women.</i> are subject to the obligation of <i>zizith</i>. R. Simeon exempts women since [the commandment of <i>zizith</i>] is a positive commandment which is dependent on a fixed time.<sup class="footnote-marker">2</sup><i class="footn\n--------------------------------------------------\n\n[Candidate #12] (similarity: 0.553)\nSource: Tosafot Chad Mikamei on Yevamot 102b\nHebrew: מאי דכתב ה"ר אלפס ולענין חליצה עד שתהא אביו ואמו מישראל מ"ט תרי בישראל כתיב הכי פי\' תרי בישראל כתיבי חד לענות חלוץ הנעל ג\' פעמי\' כדר\' יהודה משו\' ר"ט ואמרי\' מונקרא שמו נפקא ומוקים בישראל כיון שחלץ לה הותרה לכל ישראל כדאיתא בפ"ק דקדושין וחד בישראל למעוטי אמו מישראל מקרב אחיך נפקא. ואית ספרים שכתוב בהם\n--------------------------------------------------\n\n[Candidate #13] (similarity: 0.551)\nSource: Zevachim 44a\nHebrew: ומנחת כהנים ומנחת כהן משיח והדם והנסכים הבאין בפני עצמן דברי רבי מאיר וחכמים אומרים אף הבאין עם הבהמה לוג שמן של מצורע ר\' שמעון אומר אין חייבין עליו משום פיגול ורבי מאיר אומר חייבין עליו משום פיגול שדם האשם מתירו וכל שיש לו מתירין בין לאדם בין למזבח חייבין עליו משום פיגול העולה דמה מתיר את בשרה למזב\nEnglish: <b>the meal offering of priests,</b> from which no handful of flour is removed and which is burned in its entirety (see Leviticus 6:16); <b>the meal offering of</b> the <b>anointed priest,</b> which is sacrificed by the High Priest each day, half in the morning and half in the evening; <b>the blood,\n--------------------------------------------------\n\n[Candidate #14] (similarity: 0.550)\nSource: Tosafot Chad Mikamei on Yevamot 26b\nHebrew: אמר רב מנשה גזלן דדבריהם כשר לעדות הא דדברי תורה פסול לעדות אשה:\n הא דתנן החכם שאסר את האשה בנדר לא ישאנה וקי"ל ביחיד מומחה ולפום הכי אם התירה ישאנה אבל בתלתא אפילו אסרו ישאנה משום שהם ב"ד ובבכורות פרק כל פסולי המוקדשים דכי אמרי\' הפרת נדרים בשלשה הדיוטות במקום שאין שם מומחה ורבי יהודה ס"ל התם ואחד מ\n--------------------------------------------------\n\n[Candidate #15] (similarity: 0.543)\nSource: Tosafot Chad Mikamei on Yevamot 35b\nHebrew: אמר רב נחמן אמר שמואל כל שנשתהה עשר שנים אחר בעלה ונשאת שוב אין נתעברת. ולא אמרן אלא שאין דעתה להנשא אבל דעתה להנשא מתעברת:\n\n--------------------------------------------------\n\n[Candidate #16] (similarity: 0.541)\nSource: Tractate Soferim 4b\nHebrew: הכותב <i data-commentator="Haggahot R\' Yeshaya Berlin" data-order="1"></i>צריך לעשות <i data-commentator="Gra\'s Nuschah" data-order="1"></i>שיעור בפתיחה של (במדבר י׳:ל״ה) ויהי בנסוע הארון <i data-commentator="Haggahot R\' Yeshaya Berlin" data-order="2"></i>מלמעלה ומלמטה שהוא ספר בפני עצמו וי"א שמקומו\nEnglish: A scribe must provide a distinguishing mark<sup class="footnote-marker">1</sup><i class="footnote">The traditional mark is an inverted <i>nun</i>.</i> for the section<sup class="footnote-marker">2</sup><i class="footnote">So GRA. V reads ‘a prescribed space at the opening’.</i> beginning <i>And it c\n--------------------------------------------------\n\n[Candidate #17] (similarity: 0.540)\nSource: Bava Batra 177b\nHebrew: עָרֵב דְּבֵית דִּין הוּא דְּלָא בָּעֵי קִנְיָן, הָא בְּעָלְמָא בָּעֵי קִנְיָן. וְהִלְכְתָא: עָרֵב בִּשְׁעַת מַתַּן מָעוֹת – לֹא בָּעֵי קִנְיָן, אַחַר מַתַּן מָעוֹת – בָּעֵי קִנְיָן. עָרֵב דְּבֵית דִּין – לָא בָּעֵי קִנְיָן; דִּבְהָהִיא הֲנָאָה דִּמְהֵימַן לֵיהּ – גָּמַר וּמְשַׁעְבֵּד לֵיהּ. <br><br>\nEnglish: <b>It is</b> only <b>a guarantor</b> who undertakes a loan guarantee <b>in</b> the presence of <b>a court who does not require an act of acquisition; this</b> indicates that <b>generally,</b> a guarantor <b>requires an act of acquisition</b> in order to be obligated to pay. The Gemara concludes: <b>\n--------------------------------------------------\n\n[Candidate #18] (similarity: 0.540)\nSource: Tractate Gerim 3a\nHebrew: <i data-commentator="Haggahot R\' Yeshaya Berlin" data-order="1"></i>איזהו גר תושב כל שקבל עליו שלא לעבוד ע"ז דברי רבי מאיר רבי יהודה אומר כל שקבל עליו שלא להיות אוכל נבילות: רוקו ומושבו ומשכבו ומי רגליו טמאין <i data-commentator="New Nuschah" data-order="1"></i>עיסתו ושמנו ויינו טהורים <i data-comme\nEnglish: What is a ‘resident proselyte’?<sup class="footnote-marker">1</sup><i class="footnote">Heb. <i>ger toshab</i> as distinguished from <i>ger ẓedeḳ</i>, ‘a righteous proselyte’.</i> Whoever undertakes to abstain from idolatry, in the view of R. Meir; R. Judah said: Whoever undertakes not to eat flesh t\n--------------------------------------------------\n\n[Candidate #19] (similarity: 0.539)\nSource: Shabbat 158b\nHebrew: וְגִיגִית סְדוּקָה מוּנַּחַת עַל גַּבָּן. וּפָקְקוּ אֶת הַמָּאוֹר בַּטָּפִיחַ, וְקָשְׁרוּ אֶת הַמְּקִידָּה בְּגֶמִי לֵידַע אִם יֵשׁ שָׁם בְּגִיגִית פּוֹתֵחַ טֶפַח אִם לָאו. וּמִדִּבְרֵיהֶם לָמַדְנוּ שֶׁפּוֹקְקִין וּמוֹדְדִין וְקוֹשְׁרִין בְּשַׁבָּת. עוּלָּא אִיקְּלַע לְבֵי רֵישׁ גָּלוּתָא. חַזְיֵיהּ\nEnglish: <b>and</b> there was <b>a cracked roofing placed atop</b> the two houses. If the roofing was intact it would have the legal status of a tent over a corpse, rendering everything in the alleyway, and, through the windows, everything in the houses, ritually impure. However, since the roofing was cracke\n--------------------------------------------------\n\n[Candidate #20] (similarity: 0.538)\nSource: Chullin 79a\nHebrew: דניכחוש חיליה אלא סוקרו בסיקרא אמאי כי היכי דליחזיוה אינשי וליבעי רחמי עילויה כדתניא (ויקרא יג, מה) וטמא טמא יקרא צריך להודיע לרבים ורבים מבקשים עליו רחמים וכן מי שאירע בו דבר צריך להודיע לרבים ורבים מבקשים עליו רחמים אמר רבינא כמאן תלינן כובסא בדיקלא כמאן כי האי תנא: <br><br><big><strong>הדרן עלך ב\nEnglish: <b>that</b> the tree’s <b>strength will lessen.</b> It is possible that the tree shed its fruits prematurely due to excessive blossoming. It taxes the tree to sustain these blossoms, and this may render the tree incapable of sustaining the fruits that subsequently grow from the blossoms. Stones were\n--------------------------------------------------\n\nWhich candidate best matches the user\'s query? Consider:\n- Phonetic similarity between transliteration and Hebrew\n- Context and meaning\n- Source location\n\nProvide your answer in JSON format.'}], 'model': 'claude-sonnet-4-20250514', 'system': 'You are a Torah scholar assistant specializing in identifying Hebrew and Aramaic terms from transliterations.\n\nYour task: Given a user\'s transliterated query and a list of potential Hebrew/Aramaic matches from Sefaria, identify which match best corresponds to the user\'s query.\n\nIMPORTANT GUIDELINES:\n1. Compare the TRANSLITERATION to the HEBREW TEXT carefully\n2. Consider phonetic similarity (ch=ח, sh=ש, tz=צ, v=ב, etc.)\n3. Use your knowledge of Torah terminology to assess context\n4. Yeshivish transliterations use "sav" instead of "tav" (s=ת)\n5. Be confident when you find a clear match\n6. Admit uncertainty if no good match exists\n\nReturn JSON:\n{\n  "matched": true/false,\n  "hebrew_term": "The actual Hebrew/Aramaic term",\n  "source_ref": "Where this term appears (e.g., \'Chullin 10a\')",\n  "confidence": "high/medium/low",\n  "explanation": "Why this is the best match (explain the transliteration mapping)",\n  "hebrew_context": "The full Hebrew text from that source (for context)"\n}\n\nIf no good match exists, return:\n{\n  "matched": false,\n  "confidence": "none",\n  "explanation": "Why no match was found"\n}'}}
2025-12-02 09:34:10 | DEBUG    | anthropic._base_client:request:1045 | Sending HTTP Request: POST https://api.anthropic.com/v1/messages
2025-12-02 09:34:10 | DEBUG    | httpcore.connection:trace:47 | connect_tcp.started host='api.anthropic.com' port=443 local_address=None timeout=5.0 socket_options=[(65535, 8, True), (6, 17, 60), (6, 16, 5), (6, 3, 60)]
2025-12-02 09:34:10 | DEBUG    | httpcore.connection:trace:47 | connect_tcp.complete return_value=<httpcore._backends.sync.SyncStream object at 0x000001F81B4800D0>
2025-12-02 09:34:10 | DEBUG    | httpcore.connection:trace:47 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F819ACBCC0> server_hostname='api.anthropic.com' timeout=5.0
2025-12-02 09:34:10 | DEBUG    | httpcore.connection:trace:47 | start_tls.complete return_value=<httpcore._backends.sync.SyncStream object at 0x000001F81B4801C0>
2025-12-02 09:34:10 | DEBUG    | httpcore.http11:trace:47 | send_request_headers.started request=<Request [b'POST']>
2025-12-02 09:34:10 | DEBUG    | httpcore.http11:trace:47 | send_request_headers.complete
2025-12-02 09:34:10 | DEBUG    | httpcore.http11:trace:47 | send_request_body.started request=<Request [b'POST']>
2025-12-02 09:34:10 | DEBUG    | httpcore.http11:trace:47 | send_request_body.complete
2025-12-02 09:34:10 | DEBUG    | httpcore.http11:trace:47 | receive_response_headers.started request=<Request [b'POST']>
2025-12-02 09:34:22 | DEBUG    | httpcore.http11:trace:47 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:22 GMT'), (b'Content-Type', b'application/json'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Content-Encoding', b'gzip'), (b'anthropic-ratelimit-input-tokens-limit', b'30000'), (b'anthropic-ratelimit-input-tokens-remaining', b'24000'), (b'anthropic-ratelimit-input-tokens-reset', b'2025-12-02T14:34:23Z'), (b'anthropic-ratelimit-output-tokens-limit', b'8000'), (b'anthropic-ratelimit-output-tokens-remaining', b'8000'), (b'anthropic-ratelimit-output-tokens-reset', b'2025-12-02T14:34:26Z'), (b'anthropic-ratelimit-requests-limit', b'50'), (b'anthropic-ratelimit-requests-remaining', b'49'), (b'anthropic-ratelimit-requests-reset', b'2025-12-02T14:34:11Z'), (b'retry-after', b'52'), (b'anthropic-ratelimit-tokens-limit', b'38000'), (b'anthropic-ratelimit-tokens-remaining', b'32000'), (b'anthropic-ratelimit-tokens-reset', b'2025-12-02T14:34:23Z'), (b'request-id', b'req_011CVi2T2Vi1h3aze8gdAnrN'), (b'strict-transport-security', b'max-age=31536000; includeSubDomains; preload'), (b'anthropic-organization-id', b'73a09491-cda3-40b4-8544-d00ca1bc9331'), (b'x-envoy-upstream-service-time', b'12218'), (b'cf-cache-status', b'DYNAMIC'), (b'X-Robots-Tag', b'none'), (b'Server', b'cloudflare'), (b'CF-RAY', b'9a7b8b265ba20edf-EWR')])
2025-12-02 09:34:22 | INFO     | httpx:_send_single_request:1025 | HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"
2025-12-02 09:34:22 | DEBUG    | httpcore.http11:trace:47 | receive_response_body.started request=<Request [b'POST']>
2025-12-02 09:34:22 | DEBUG    | httpcore.http11:trace:47 | receive_response_body.complete
2025-12-02 09:34:22 | DEBUG    | httpcore.http11:trace:47 | response_closed.started
2025-12-02 09:34:22 | DEBUG    | httpcore.http11:trace:47 | response_closed.complete
2025-12-02 09:34:22 | DEBUG    | anthropic._base_client:request:1083 | HTTP Response: POST https://api.anthropic.com/v1/messages "200 OK" Headers({'date': 'Tue, 02 Dec 2025 14:34:22 GMT', 'content-type': 'application/json', 'transfer-encoding': 'chunked', 'connection': 'keep-alive', 'content-encoding': 'gzip', 'anthropic-ratelimit-input-tokens-limit': '30000', 'anthropic-ratelimit-input-tokens-remaining': '24000', 'anthropic-ratelimit-input-tokens-reset': '2025-12-02T14:34:23Z', 'anthropic-ratelimit-output-tokens-limit': '8000', 'anthropic-ratelimit-output-tokens-remaining': '8000', 'anthropic-ratelimit-output-tokens-reset': '2025-12-02T14:34:26Z', 'anthropic-ratelimit-requests-limit': '50', 'anthropic-ratelimit-requests-remaining': '49', 'anthropic-ratelimit-requests-reset': '2025-12-02T14:34:11Z', 'retry-after': '52', 'anthropic-ratelimit-tokens-limit': '38000', 'anthropic-ratelimit-tokens-remaining': '32000', 'anthropic-ratelimit-tokens-reset': '2025-12-02T14:34:23Z', 'request-id': 'req_011CVi2T2Vi1h3aze8gdAnrN', 'strict-transport-security': 'max-age=31536000; includeSubDomains; preload', 'anthropic-organization-id': '73a09491-cda3-40b4-8544-d00ca1bc9331', 'x-envoy-upstream-service-time': '12218', 'cf-cache-status': 'DYNAMIC', 'x-robots-tag': 'none', 'server': 'cloudflare', 'cf-ray': '9a7b8b265ba20edf-EWR'})
2025-12-02 09:34:22 | DEBUG    | anthropic._base_client:request:1091 | request_id: req_011CVi2T2Vi1h3aze8gdAnrN
2025-12-02 09:34:22 | DEBUG    | hybrid_resolver:_claude_verify:258 |   Claude response: Looking at the transliterated query "beheima chezkas issur omedes" and analyzing the Hebrew candidates, I need to find terms that match:

- "beheima" = בהמה (animal/beast)
- "chezkas" = חזקת (presumpt...
2025-12-02 09:34:22 | WARNING  | hybrid_resolver:_claude_verify:275 |   ✗ No match found
2025-12-02 09:34:22 | WARNING  | hybrid_resolver:_claude_verify:276 |     Reason: While several candidates contain the word 'beheima' (בהמה), none contain the complete phrase or concept of 'chezkas issur omedes' (חזקת איסור עומדת) that would correspond to this specific transliteration. The query appears to refer to a technical halakhic concept about an animal with presumptive forbidden status, but this exact terminology is not found in any of the provided matches.
2025-12-02 09:34:22 | INFO     | hybrid_resolver:resolve:144 | ================================================================================
2025-12-02 09:34:22 | INFO     | __main__:search_sources:866 | → No resolution needed or possible - proceeding normally
2025-12-02 09:34:22 | INFO     | __main__:interpret_query:523 | ================================================================================
2025-12-02 09:34:22 | INFO     | __main__:interpret_query:524 | STAGE 0: QUERY INTERPRETATION
2025-12-02 09:34:22 | INFO     | __main__:interpret_query:525 | ================================================================================
2025-12-02 09:34:22 | INFO     | __main__:interpret_query:526 |   Topic: beheima chezkas issur omedes
2025-12-02 09:34:22 | DEBUG    | __main__:interpret_query:583 |   Sending to Claude...
2025-12-02 09:34:22 | DEBUG    | anthropic._base_client:_build_request:493 | Request options: {'method': 'post', 'url': '/v1/messages', 'timeout': Timeout(connect=5.0, read=600, write=600, pool=600), 'files': None, 'idempotency_key': 'stainless-python-retry-39489b7b-80df-4fce-ac33-1a5c3676be82', 'json_data': {'max_tokens': 800, 'messages': [{'role': 'user', 'content': 'User\'s query: "beheima chezkas issur omedes"\n\nInterpret this query, handling any spelling variations or transliterations. Determine if clarification is needed.'}], 'model': 'claude-sonnet-4-20250514', 'system': 'You are a Torah scholar assistant that interprets user queries about Jewish texts.\n\nYour job is to:\n1. Understand what the user is asking (handling spelling variations, transliterations, Hebrew, etc.)\n2. Map their query to standard halachic/Torah concepts\n3. Determine if clarification is needed\n\nIMPORTANT: If the query has been RESOLVED via hybrid search (you\'ll see resolved Hebrew terms in context),\nuse that resolution as authoritative. Don\'t second-guess the vector search + verification process.\n\nHANDLING SPELLING VARIATIONS (use these examples but apply the logic to any possible query):\n- "chuppa" / "chuppah" / "chupa" / "huppa" / "חופה" → All mean "chuppah"\n- "niddah" / "nida" / "nidah" / "נדה" → All mean "niddah"\n- "rambam" / "Rambam" / "maimonides" / "רמב״ם" → All mean "Rambam"\n- "shulchan aruch" / "shulchan arukh" / "SA" / "שולחן ערוך" → All mean "Shulchan Aruch"\n\nYour output should normalize these into standard English terms that Sefaria uses.\n\nCONFIDENCE CHECK:\nOnly ask for clarification if the query is GENUINELY UNCLEAR or could mean completely different things.\n\nExamples where clarification IS needed:\n- "niddah" (alone - could be laws, tum\'ah, or mikvah)\n- "chuppah" (alone - could be construction, laws, or blessings)\n- "chometz" (alone - could be ba\'al yiraeh, bittul chametz, or bedikas chametz)\n\nExamples where clarification is NOT needed:\n- "machlokes rishonim chuppas niddah rambam" (specific enough - proceed!)\n- "bitul chametz" (clear topic - proceed!)\n- "bedikas chometz derabbanan or deoraisa" (clear topic - proceed!)\n- "chezkas haguf vs chezkas mamon" (clear topic - proceed!)\n- "kibbud av v\'em" (clear topic - proceed!)\n\nIf you can reasonably determine what they\'re asking about, DON\'T ask for clarification - just proceed!\n\nReturn JSON:\n{\n  "needs_clarification": true/false,\n  "clarifying_questions": ["Question 1?", "Question 2?"],  // Max 2 questions, ONLY if genuinely unclear\n  "interpreted_query": "The normalized query in standard terminology",\n  "confidence": "high/medium/low"\n}\n\nIf needs_clarification is false, clarifying_questions should be empty.'}}
2025-12-02 09:34:22 | DEBUG    | anthropic._base_client:request:1045 | Sending HTTP Request: POST https://api.anthropic.com/v1/messages
2025-12-02 09:34:22 | DEBUG    | httpcore.connection:trace:47 | connect_tcp.started host='api.anthropic.com' port=443 local_address=None timeout=5.0 socket_options=[(65535, 8, True), (6, 17, 60), (6, 16, 5), (6, 3, 60)]
2025-12-02 09:34:22 | DEBUG    | httpcore.connection:trace:47 | connect_tcp.complete return_value=<httpcore._backends.sync.SyncStream object at 0x000001F81B7F5070>
2025-12-02 09:34:22 | DEBUG    | httpcore.connection:trace:47 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F819E9CBC0> server_hostname='api.anthropic.com' timeout=5.0
2025-12-02 09:34:22 | DEBUG    | httpcore.connection:trace:47 | start_tls.complete return_value=<httpcore._backends.sync.SyncStream object at 0x000001F81B7F5040>
2025-12-02 09:34:22 | DEBUG    | httpcore.http11:trace:47 | send_request_headers.started request=<Request [b'POST']>
2025-12-02 09:34:22 | DEBUG    | httpcore.http11:trace:47 | send_request_headers.complete
2025-12-02 09:34:22 | DEBUG    | httpcore.http11:trace:47 | send_request_body.started request=<Request [b'POST']>
2025-12-02 09:34:22 | DEBUG    | httpcore.http11:trace:47 | send_request_body.complete
2025-12-02 09:34:22 | DEBUG    | httpcore.http11:trace:47 | receive_response_headers.started request=<Request [b'POST']>
2025-12-02 09:34:25 | DEBUG    | httpcore.http11:trace:47 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:25 GMT'), (b'Content-Type', b'application/json'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Content-Encoding', b'gzip'), (b'anthropic-ratelimit-input-tokens-limit', b'30000'), (b'anthropic-ratelimit-input-tokens-remaining', b'30000'), (b'anthropic-ratelimit-input-tokens-reset', b'2025-12-02T14:34:25Z'), (b'anthropic-ratelimit-output-tokens-limit', b'8000'), (b'anthropic-ratelimit-output-tokens-remaining', b'8000'), (b'anthropic-ratelimit-output-tokens-reset', b'2025-12-02T14:34:26Z'), (b'anthropic-ratelimit-requests-limit', b'50'), (b'anthropic-ratelimit-requests-remaining', b'49'), (b'anthropic-ratelimit-requests-reset', b'2025-12-02T14:34:24Z'), (b'retry-after', b'36'), (b'anthropic-ratelimit-tokens-limit', b'38000'), (b'anthropic-ratelimit-tokens-remaining', b'38000'), (b'anthropic-ratelimit-tokens-reset', b'2025-12-02T14:34:25Z'), (b'request-id', b'req_011CVi2TwcnxhpMfaiWKueVG'), (b'strict-transport-security', b'max-age=31536000; includeSubDomains; preload'), (b'anthropic-organization-id', b'73a09491-cda3-40b4-8544-d00ca1bc9331'), (b'x-envoy-upstream-service-time', b'3011'), (b'cf-cache-status', b'DYNAMIC'), (b'X-Robots-Tag', b'none'), (b'Server', b'cloudflare'), (b'CF-RAY', b'9a7b8b74fe6b8c06-EWR')])
2025-12-02 09:34:25 | INFO     | httpx:_send_single_request:1025 | HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"
2025-12-02 09:34:25 | DEBUG    | httpcore.http11:trace:47 | receive_response_body.started request=<Request [b'POST']>
2025-12-02 09:34:25 | DEBUG    | httpcore.http11:trace:47 | receive_response_body.complete
2025-12-02 09:34:25 | DEBUG    | httpcore.http11:trace:47 | response_closed.started
2025-12-02 09:34:25 | DEBUG    | httpcore.http11:trace:47 | response_closed.complete
2025-12-02 09:34:25 | DEBUG    | anthropic._base_client:request:1083 | HTTP Response: POST https://api.anthropic.com/v1/messages "200 OK" Headers({'date': 'Tue, 02 Dec 2025 14:34:25 GMT', 'content-type': 'application/json', 'transfer-encoding': 'chunked', 'connection': 'keep-alive', 'content-encoding': 'gzip', 'anthropic-ratelimit-input-tokens-limit': '30000', 'anthropic-ratelimit-input-tokens-remaining': '30000', 'anthropic-ratelimit-input-tokens-reset': '2025-12-02T14:34:25Z', 'anthropic-ratelimit-output-tokens-limit': '8000', 'anthropic-ratelimit-output-tokens-remaining': '8000', 'anthropic-ratelimit-output-tokens-reset': '2025-12-02T14:34:26Z', 'anthropic-ratelimit-requests-limit': '50', 'anthropic-ratelimit-requests-remaining': '49', 'anthropic-ratelimit-requests-reset': '2025-12-02T14:34:24Z', 'retry-after': '36', 'anthropic-ratelimit-tokens-limit': '38000', 'anthropic-ratelimit-tokens-remaining': '38000', 'anthropic-ratelimit-tokens-reset': '2025-12-02T14:34:25Z', 'request-id': 'req_011CVi2TwcnxhpMfaiWKueVG', 'strict-transport-security': 'max-age=31536000; includeSubDomains; preload', 'anthropic-organization-id': '73a09491-cda3-40b4-8544-d00ca1bc9331', 'x-envoy-upstream-service-time': '3011', 'cf-cache-status': 'DYNAMIC', 'x-robots-tag': 'none', 'server': 'cloudflare', 'cf-ray': '9a7b8b74fe6b8c06-EWR'})
2025-12-02 09:34:25 | DEBUG    | anthropic._base_client:request:1091 | request_id: req_011CVi2TwcnxhpMfaiWKueVG
2025-12-02 09:34:25 | DEBUG    | __main__:interpret_query:594 |   Claude response: {
  "needs_clarification": false,
  "clarifying_questions": [],
  "interpreted_query": "behemah chezkat issur omedes - the presumption that an animal stands in a state of prohibition",
  "confidence":
2025-12-02 09:34:25 | DEBUG    | __main__:parse_claude_json:311 | ✓ Successfully parsed JSON
2025-12-02 09:34:25 | INFO     | __main__:interpret_query:602 |   ✓ Interpretation: behemah chezkat issur omedes - the presumption that an animal stands in a state of prohibition
2025-12-02 09:34:25 | INFO     | __main__:interpret_query:603 |   Needs clarification: False
2025-12-02 09:34:25 | INFO     | __main__:search_sources:894 | → Interpreted query: behemah chezkat issur omedes - the presumption that an animal stands in a state of prohibition
2025-12-02 09:34:25 | INFO     | __main__:identify_base_texts:621 | ================================================================================
2025-12-02 09:34:25 | INFO     | __main__:identify_base_texts:622 | STAGE 1: IDENTIFY BASE TEXT SECTIONS
2025-12-02 09:34:25 | INFO     | __main__:identify_base_texts:623 | ================================================================================
2025-12-02 09:34:25 | INFO     | __main__:identify_base_texts:624 |   Query: behemah chezkat issur omedes - the presumption that an animal stands in a state of prohibition
2025-12-02 09:34:25 | DEBUG    | __main__:identify_base_texts:646 |   Sending to Claude...
2025-12-02 09:34:25 | DEBUG    | anthropic._base_client:_build_request:493 | Request options: {'method': 'post', 'url': '/v1/messages', 'timeout': Timeout(connect=5.0, read=600, write=600, pool=600), 'files': None, 'idempotency_key': 'stainless-python-retry-1e47c9fb-b4af-4255-b717-bb0f02c232ee', 'json_data': {'max_tokens': 1000, 'messages': [{'role': 'user', 'content': "Query: behemah chezkat issur omedes - the presumption that an animal stands in a state of prohibition\n\nIdentify 2-4 BASE TEXT sections (chapters/simanim, not specific halachos) that discuss this topic.\nUse Sefaria's English names and general section references."}], 'model': 'claude-sonnet-4-20250514', 'system': 'You are a Torah scholar assistant that identifies which BASE TEXT sections discuss a given topic.\n\nGiven a user\'s query, identify which GENERAL SECTIONS of foundational texts discuss this topic.\n\nIMPORTANT RULES:\n1. Return BASE TEXTS ONLY (Torah, Mishna, Gemara, Rambam, Ramban, Rashba, Ritva, Tur, Shulchan Aruch)\n2. Use GENERAL SECTION REFERENCES (e.g., "Marriage chapter 10" not "Marriage 10:11 specifically")\n3. Use SEFARIA\'S ENGLISH NAMES:\n   - "Mishneh Torah, Marriage" NOT "Ishut"\n   - "Mishneh Torah, Forbidden Intercourse" NOT "Issurei Biah"\n   - "Shulchan Arukh, Even HaEzer" NOT just "Even HaEzer"\n4. Include chapter/section but NOT specific halachos\n5. Return 2-4 base texts maximum\n\nEXAMPLES:\n\nQuery: "chuppas niddah"\nGood output:\n{\n  "base_texts": [\n    {"ref": "Mishneh Torah, Marriage 10", "reason": "Discusses chuppah and its validity with niddah"},\n    {"ref": "Shulchan Arukh, Even HaEzer 61", "reason": "Laws of chuppah when woman is niddah"},\n    {"ref": "Ketubot 57b", "reason": "Gemara discussing timing of nisuin relative to niddah"}\n  ]\n}\n\nBad output (TOO SPECIFIC):\n{"base_texts": [{"ref": "Mishneh Torah, Marriage 10:11"}]}  ❌ Too specific!\n\nBad output (COMMENTARY):\n{"base_texts": [{"ref": "Kesef Mishneh on Marriage 10"}]}  ❌ We want base text!\n\nQuery: "bitul chametz"\nGood output:\n{\n  "base_texts": [\n    {"ref": "Mishneh Torah, Leavened and Unleavened Bread 2", "reason": "Laws of nullifying chametz"},\n    {"ref": "Shulchan Arukh, Orach Chayim 434", "reason": "Laws of bitul chametz"},\n    {"ref": "Pesachim 6b", "reason": "Gemara on bitul chametz"}\n  ]\n}\n\nReturn JSON in this exact format.'}}
2025-12-02 09:34:25 | DEBUG    | anthropic._base_client:request:1045 | Sending HTTP Request: POST https://api.anthropic.com/v1/messages
2025-12-02 09:34:25 | DEBUG    | httpcore.http11:trace:47 | send_request_headers.started request=<Request [b'POST']>
2025-12-02 09:34:25 | DEBUG    | httpcore.http11:trace:47 | send_request_headers.complete
2025-12-02 09:34:25 | DEBUG    | httpcore.http11:trace:47 | send_request_body.started request=<Request [b'POST']>
2025-12-02 09:34:25 | DEBUG    | httpcore.http11:trace:47 | send_request_body.complete
2025-12-02 09:34:25 | DEBUG    | httpcore.http11:trace:47 | receive_response_headers.started request=<Request [b'POST']>
2025-12-02 09:34:30 | DEBUG    | httpcore.http11:trace:47 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:30 GMT'), (b'Content-Type', b'application/json'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Content-Encoding', b'gzip'), (b'anthropic-ratelimit-input-tokens-limit', b'30000'), (b'anthropic-ratelimit-input-tokens-remaining', b'30000'), (b'anthropic-ratelimit-input-tokens-reset', b'2025-12-02T14:34:28Z'), (b'anthropic-ratelimit-output-tokens-limit', b'8000'), (b'anthropic-ratelimit-output-tokens-remaining', b'8000'), (b'anthropic-ratelimit-output-tokens-reset', b'2025-12-02T14:34:32Z'), (b'anthropic-ratelimit-requests-limit', b'50'), (b'anthropic-ratelimit-requests-remaining', b'49'), (b'anthropic-ratelimit-requests-reset', b'2025-12-02T14:34:27Z'), (b'retry-after', b'35'), (b'anthropic-ratelimit-tokens-limit', b'38000'), (b'anthropic-ratelimit-tokens-remaining', b'38000'), (b'anthropic-ratelimit-tokens-reset', b'2025-12-02T14:34:28Z'), (b'request-id', b'req_011CVi2UAt1oTdjjzkYh8BXL'), (b'strict-transport-security', b'max-age=31536000; includeSubDomains; preload'), (b'anthropic-organization-id', b'73a09491-cda3-40b4-8544-d00ca1bc9331'), (b'x-envoy-upstream-service-time', b'4836'), (b'cf-cache-status', b'DYNAMIC'), (b'X-Robots-Tag', b'none'), (b'Server', b'cloudflare'), (b'CF-RAY', b'9a7b8b886fe08c06-EWR')])
2025-12-02 09:34:30 | INFO     | httpx:_send_single_request:1025 | HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"
2025-12-02 09:34:30 | DEBUG    | httpcore.http11:trace:47 | receive_response_body.started request=<Request [b'POST']>
2025-12-02 09:34:30 | DEBUG    | httpcore.http11:trace:47 | receive_response_body.complete
2025-12-02 09:34:30 | DEBUG    | httpcore.http11:trace:47 | response_closed.started
2025-12-02 09:34:30 | DEBUG    | httpcore.http11:trace:47 | response_closed.complete
2025-12-02 09:34:30 | DEBUG    | anthropic._base_client:request:1083 | HTTP Response: POST https://api.anthropic.com/v1/messages "200 OK" Headers({'date': 'Tue, 02 Dec 2025 14:34:30 GMT', 'content-type': 'application/json', 'transfer-encoding': 'chunked', 'connection': 'keep-alive', 'content-encoding': 'gzip', 'anthropic-ratelimit-input-tokens-limit': '30000', 'anthropic-ratelimit-input-tokens-remaining': '30000', 'anthropic-ratelimit-input-tokens-reset': '2025-12-02T14:34:28Z', 'anthropic-ratelimit-output-tokens-limit': '8000', 'anthropic-ratelimit-output-tokens-remaining': '8000', 'anthropic-ratelimit-output-tokens-reset': '2025-12-02T14:34:32Z', 'anthropic-ratelimit-requests-limit': '50', 'anthropic-ratelimit-requests-remaining': '49', 'anthropic-ratelimit-requests-reset': '2025-12-02T14:34:27Z', 'retry-after': '35', 'anthropic-ratelimit-tokens-limit': '38000', 'anthropic-ratelimit-tokens-remaining': '38000', 'anthropic-ratelimit-tokens-reset': '2025-12-02T14:34:28Z', 'request-id': 'req_011CVi2UAt1oTdjjzkYh8BXL', 'strict-transport-security': 'max-age=31536000; includeSubDomains; preload', 'anthropic-organization-id': '73a09491-cda3-40b4-8544-d00ca1bc9331', 'x-envoy-upstream-service-time': '4836', 'cf-cache-status': 'DYNAMIC', 'x-robots-tag': 'none', 'server': 'cloudflare', 'cf-ray': '9a7b8b886fe08c06-EWR'})
2025-12-02 09:34:30 | DEBUG    | anthropic._base_client:request:1091 | request_id: req_011CVi2UAt1oTdjjzkYh8BXL
2025-12-02 09:34:30 | DEBUG    | __main__:identify_base_texts:657 |   Claude response: ```json
{
  "base_texts": [
    {"ref": "Mishneh Torah, Ritual Slaughter 1", "reason": "Discusses the fundamental presumption that animals are forbidden until properly slaughtered"},
    {"ref": "Shulchan Arukh, Yoreh De'ah 1", "reason": "Laws establishing the presumptive prohibition of animals and 
2025-12-02 09:34:30 | DEBUG    | __main__:parse_claude_json:311 | ✓ Successfully parsed JSON
2025-12-02 09:34:30 | INFO     | __main__:identify_base_texts:662 |   ✓ Identified 4 base text sections:
2025-12-02 09:34:30 | INFO     | __main__:identify_base_texts:664 |     - Mishneh Torah, Ritual Slaughter 1: Discusses the fundamental presumption that animals are forbi
2025-12-02 09:34:30 | INFO     | __main__:identify_base_texts:664 |     - Shulchan Arukh, Yoreh De'ah 1: Laws establishing the presumptive prohibition of animals and
2025-12-02 09:34:30 | INFO     | __main__:identify_base_texts:664 |     - Chullin 9a: Gemara establishing the principle that animals have a presum
2025-12-02 09:34:30 | INFO     | __main__:identify_base_texts:664 |     - Mishneh Torah, Forbidden Foods 4: Discusses presumptions regarding the status of animals and m
2025-12-02 09:34:30 | INFO     | __main__:fetch_commentaries_for_base_texts:683 | ================================================================================
2025-12-02 09:34:30 | INFO     | __main__:fetch_commentaries_for_base_texts:684 | STAGE 2: FETCH COMMENTARIES VIA RELATED API
2025-12-02 09:34:30 | INFO     | __main__:fetch_commentaries_for_base_texts:685 | ================================================================================
2025-12-02 09:34:30 | INFO     | __main__:fetch_commentaries_for_base_texts:691 | 
📖 Processing base text: Mishneh Torah, Ritual Slaughter 1
2025-12-02 09:34:30 | INFO     | __main__:get_related_texts:449 | 🔗 Getting related texts for: Mishneh Torah, Ritual Slaughter 1
2025-12-02 09:34:30 | DEBUG    | __main__:get_related_texts:460 |   URL: https://www.sefaria.org/api/related/Mishneh%20Torah%2C%20Ritual%20Slaughter%201
2025-12-02 09:34:30 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:30 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B022BB0>
2025-12-02 09:34:30 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B44CE40> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:31 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B831970>
2025-12-02 09:34:31 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:31 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:31 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:31 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:31 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:33 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:33 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/related/Mishneh%20Torah%2C%20Ritual%20Slaughter%201'), (b'x-varnish', b'406861813'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=W2DR4v2xJ5rzXh87E26VKJafOhMQ%2FvQDrzfm%2Bh7iqH6EbrPOrzfJPrHRfD3UTbB9wrG6X8ZCui%2FCFB%2BtavcF5kBzQjdOxiCDhYUjnkmq"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8ba89a9c25d8-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:33 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/related/Mishneh%20Torah%2C%20Ritual%20Slaughter%201 "HTTP/1.1 200 OK"
2025-12-02 09:34:33 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:33 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:33 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:33 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:33 | DEBUG    | __main__:get_related_texts:473 |   Found 494 total links
2025-12-02 09:34:33 | INFO     | __main__:get_related_texts:487 |   ✓ Found 277 commentaries
2025-12-02 09:34:33 | DEBUG    | __main__:get_related_texts:491 |   Commentaries found:
2025-12-02 09:34:33 | DEBUG    | __main__:get_related_texts:493 |     - Yad Eitan on Mishneh Torah, Ritual Slaughter 1:1:1
2025-12-02 09:34:33 | DEBUG    | __main__:get_related_texts:493 |     - Ohr Sameach on Mishneh Torah, Ritual Slaughter 1:1:1
2025-12-02 09:34:33 | DEBUG    | __main__:get_related_texts:493 |     - Tzafnat Pa'neach on Mishneh Torah, Ritual Slaughter 1:1:1
2025-12-02 09:34:33 | DEBUG    | __main__:get_related_texts:493 |     - Tzafnat Pa'neach on Mishneh Torah, Ritual Slaughter 1:1:2
2025-12-02 09:34:33 | DEBUG    | __main__:get_related_texts:493 |     - Steinsaltz on Mishneh Torah, Ritual Slaughter 1:1:1
2025-12-02 09:34:33 | DEBUG    | __main__:get_related_texts:495 |     ... and 272 more
2025-12-02 09:34:33 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:33 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:33 | INFO     | __main__:fetch_commentaries_for_base_texts:700 |   Found 277 commentaries, fetching texts...
2025-12-02 09:34:33 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [1/10] Fetching: Yad Eitan on Mishneh Torah, Ritual Slaughter 1:1:1
2025-12-02 09:34:33 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Yad Eitan on Mishneh Torah, Ritual Slaughter 1:1:1
2025-12-02 09:34:33 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Yad%20Eitan%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:1
2025-12-02 09:34:33 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:33 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B938040>
2025-12-02 09:34:33 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B44CF40> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B849D90>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:34 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Yad%20Eitan%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:1'), (b'x-varnish', b'410589986'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=iVCIiXpf0PjT9ZAchgOCW4G7y2ei6pG9jno56atq49c3VSeV9N9sdjqQ469InEEm8ppJPHn5yop0aCSpJL2oxv8S74m5gm8hoOpGantU"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bbb6ed33453-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:34 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Yad%20Eitan%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:34 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:34 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Yad Eitan on Mishneh Torah, Ritual Slaughter 1:1:1 (he=True, en=False)
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:34 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (811 chars)
2025-12-02 09:34:34 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [2/10] Fetching: Ohr Sameach on Mishneh Torah, Ritual Slaughter 1:1:1
2025-12-02 09:34:34 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Ohr Sameach on Mishneh Torah, Ritual Slaughter 1:1:1
2025-12-02 09:34:34 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Ohr%20Sameach%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:1
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B9216D0>
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B0291C0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B938F40>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:34 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Ohr%20Sameach%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:1'), (b'x-varnish', b'406544314'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=yHXRHVRtijlZOt7tP3XBuAYKPyk%2F8cLb%2FNDVzWC2NEsrtlXRWzbGDfwExRulLX2xMDEdG9IypGwoUJWaA9w5vsJOHATcYIb%2F1Q73%2FAPw"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bbd8a122f06-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:34 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Ohr%20Sameach%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:34 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:34 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Ohr Sameach on Mishneh Torah, Ritual Slaughter 1:1:1 (he=True, en=False)
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:34 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (1000 chars)
2025-12-02 09:34:34 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [3/10] Fetching: Tzafnat Pa'neach on Mishneh Torah, Ritual Slaughter 1:1:1
2025-12-02 09:34:34 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Tzafnat Pa'neach on Mishneh Torah, Ritual Slaughter 1:1:1
2025-12-02 09:34:34 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Tzafnat%20Pa'neach%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:1
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B925D60>
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B0299C0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B925AF0>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:34 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Tzafnat%20Pa'neach%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:1"), (b'x-varnish', b'410589992'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=B71GyBXgu%2Bl8TsxaxwtpRxmoMMOLIWTwSSFiFzZl7S7V1pbqGIOiIsN3e8W1PoXPyLmGlZ1ShxsXexBokppY00P3UlG%2B2kR0vNtw8A%3D%3D"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bbf4e309608-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:34 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Tzafnat%20Pa'neach%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:34 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:34 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Tzafnat Pa'neach on Mishneh Torah, Ritual Slaughter 1:1:1 (he=True, en=False)
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:34 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (1000 chars)
2025-12-02 09:34:34 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [4/10] Fetching: Tzafnat Pa'neach on Mishneh Torah, Ritual Slaughter 1:1:2
2025-12-02 09:34:34 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Tzafnat Pa'neach on Mishneh Torah, Ritual Slaughter 1:1:2
2025-12-02 09:34:34 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Tzafnat%20Pa'neach%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:2
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B92E430>
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B829CC0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:34 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B933070>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:34 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:35 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Tzafnat%20Pa'neach%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:2"), (b'x-varnish', b'410783567'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=OVSkjfk2%2FDeBQj18Kl%2BGWJwkCr3JBApXZX7eF3Ahh01r0w2TgQ%2F1nno0MihzDtsP2sGBeQo6MTMeFfrF%2FU82FUxqF4luT55FnqwBRpNV"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bc12fc037a9-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:35 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Tzafnat%20Pa'neach%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:2 "HTTP/1.1 200 OK"
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:35 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:35 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Tzafnat Pa'neach on Mishneh Torah, Ritual Slaughter 1:1:2 (he=True, en=False)
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:35 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (1000 chars)
2025-12-02 09:34:35 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [5/10] Fetching: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:1:1
2025-12-02 09:34:35 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:1:1
2025-12-02 09:34:35 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:1
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B935AC0>
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B829BC0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B935850>
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:35 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:1'), (b'x-varnish', b'411341503'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=x4kLC%2BnYGz%2FyqdF8Frg%2FxwVC%2FVpq2XJ3vOimnQNmjKVvvPGJCV4mDUbhT8P34qkw3RYYL%2BItTX4ckXahnDfz2J94O6BLyg3fvSwpnF6L"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bc32fda0f61-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:35 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:35 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:35 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:1:1 (he=True, en=False)
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:35 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (59 chars)
2025-12-02 09:34:35 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [6/10] Fetching: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:1:2
2025-12-02 09:34:35 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:1:2
2025-12-02 09:34:35 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:2
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B9365E0>
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B829940> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B936970>
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:35 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:2'), (b'x-varnish', b'395296319'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=BgBrjlVv4oABQnU8C7XQRkSkPfIvignqu5aume36aPaciwDJ6THDek25tuw5srDVLIrd6IIWu0CoXclDEvKGTKByPXDpusofGrS8LQ%3D%3D"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bc55d0b3d08-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:35 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:2 "HTTP/1.1 200 OK"
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:35 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:35 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:1:2 (he=True, en=False)
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:35 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (119 chars)
2025-12-02 09:34:35 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [7/10] Fetching: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:1:3
2025-12-02 09:34:35 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:1:3
2025-12-02 09:34:35 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:3
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B92EFD0>
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B44CF40> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:35 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B935190>
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:35 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:36 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:3'), (b'x-varnish', b'395296333'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=jJxK2tC%2BXq%2BwAjGq4mLveS1GTOuJ%2BiKb%2B40hny5QB5vRwv9jBr2Bu1kh9re8wK3v5MQFSzVc%2FXMe39ykPLhIezm5k3R8LAxqBSJNfd5o"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bc71c0206a1-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:36 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:1:3 "HTTP/1.1 200 OK"
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:36 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:36 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:1:3 (he=True, en=False)
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:36 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (92 chars)
2025-12-02 09:34:36 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [8/10] Fetching: Tzafnat Pa'neach on Mishneh Torah, Ritual Slaughter 1:10:1
2025-12-02 09:34:36 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Tzafnat Pa'neach on Mishneh Torah, Ritual Slaughter 1:10:1
2025-12-02 09:34:36 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Tzafnat%20Pa'neach%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:10:1
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B925850>
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B44CEC0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B925BB0>
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:36 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Tzafnat%20Pa'neach%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:10:1"), (b'x-varnish', b'395296339'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=qhHSxCL%2BQC3E4IivvKBZJ6CPb0FoO9Si3AuC6KzUyA8D5BrRgiLd5xb4YLcF5oGkPZqpQH0M%2FGeFHl7skjvSSQwdawl4aDLzkiZ84KIE"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bc90e0bf799-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:36 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Tzafnat%20Pa'neach%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:10:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:36 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:36 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Tzafnat Pa'neach on Mishneh Torah, Ritual Slaughter 1:10:1 (he=True, en=False)
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:36 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (279 chars)
2025-12-02 09:34:36 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [9/10] Fetching: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:10:1
2025-12-02 09:34:36 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:10:1
2025-12-02 09:34:36 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:10:1
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B9370A0>
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B846D40> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B849E50>
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:36 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:10:1'), (b'x-varnish', b'409120434'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=ZWkY3fwdZtm%2B%2Fmogvon9vtgZh7mspw7Y4c8WI%2B%2BnIty%2FHaWFMSfh18kgKyY8%2FMZl12%2BVt3XfkLBjNhfi639u3UXlVOMRKQLYuIOyaGv3"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bcb0c1643d4-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:36 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:10:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:36 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:36 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:10:1 (he=True, en=False)
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:36 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (44 chars)
2025-12-02 09:34:36 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [10/10] Fetching: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:11:1
2025-12-02 09:34:36 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:11:1
2025-12-02 09:34:36 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:11:1
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B928BB0>
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B0291C0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:36 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B928940>
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:36 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:37 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:37 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:11:1'), (b'x-varnish', b'410726790'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=XTY7WiiNr9UAKROpAAifl1ZX8dfoFggD1g0jFQumFC%2BSFbkYh4WVupYKCx50JHdiqcGtts%2BOSk1mIyuELQeZ%2BloAcKcHD%2FA%2Fyw7dOQ%3D%3D"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bccbdeb51ba-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:37 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Ritual%20Slaughter%201:11:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:37 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:37 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:37 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:37 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:37 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:37 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:11:1 (he=True, en=False)
2025-12-02 09:34:37 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:37 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:37 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (95 chars)
2025-12-02 09:34:37 | INFO     | __main__:fetch_commentaries_for_base_texts:691 | 
📖 Processing base text: Shulchan Arukh, Yoreh De'ah 1
2025-12-02 09:34:37 | INFO     | __main__:get_related_texts:449 | 🔗 Getting related texts for: Shulchan Arukh, Yoreh De'ah 1
2025-12-02 09:34:37 | DEBUG    | __main__:get_related_texts:460 |   URL: https://www.sefaria.org/api/related/Shulchan%20Arukh%2C%20Yoreh%20De'ah%201
2025-12-02 09:34:37 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:37 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B938280>
2025-12-02 09:34:37 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B846F40> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:37 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B921B20>
2025-12-02 09:34:37 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:37 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:37 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:37 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:37 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:37 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:37 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/related/Shulchan%20Arukh%2C%20Yoreh%20De'ah%201"), (b'x-varnish', b'407356063'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=1JtLjGsmOz%2Fdv%2F9TCZxLxvxEd6TwHGt42Hx5mB0mHJtZtVHvclbp3d76oCm1CKEVYm4B3K0SH8TI9JOZTSty4PQv%2BywJLxAb0Yv%2FKQ%3D%3D"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bcebf26d953-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:37 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/related/Shulchan%20Arukh%2C%20Yoreh%20De'ah%201 "HTTP/1.1 200 OK"
2025-12-02 09:34:37 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:37 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:37 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:37 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:37 | DEBUG    | __main__:get_related_texts:473 |   Found 715 total links
2025-12-02 09:34:37 | INFO     | __main__:get_related_texts:487 |   ✓ Found 565 commentaries
2025-12-02 09:34:37 | DEBUG    | __main__:get_related_texts:491 |   Commentaries found:
2025-12-02 09:34:37 | DEBUG    | __main__:get_related_texts:493 |     - Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:1
2025-12-02 09:34:37 | DEBUG    | __main__:get_related_texts:493 |     - Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:2
2025-12-02 09:34:37 | DEBUG    | __main__:get_related_texts:493 |     - Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:3
2025-12-02 09:34:37 | DEBUG    | __main__:get_related_texts:493 |     - Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:4
2025-12-02 09:34:37 | DEBUG    | __main__:get_related_texts:493 |     - Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:5
2025-12-02 09:34:37 | DEBUG    | __main__:get_related_texts:495 |     ... and 560 more
2025-12-02 09:34:37 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:37 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:37 | INFO     | __main__:fetch_commentaries_for_base_texts:700 |   Found 565 commentaries, fetching texts...
2025-12-02 09:34:37 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [1/10] Fetching: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:1
2025-12-02 09:34:37 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:1
2025-12-02 09:34:37 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:1
2025-12-02 09:34:37 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:37 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B480520>
2025-12-02 09:34:37 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B0291C0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:38 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B7CB3A0>
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:38 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:1"), (b'x-varnish', b'409380924'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=w7W%2B1430P20qq99uIB3NByURa8f%2BZfUICDdUgS1iwctQ5CVi8bjsGkvvYGjLlbyJ%2FMSjXCpKE5tOO25EVBXTs2SfOusdUQYstagmcfpc"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bd48fdf7cb2-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:38 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:38 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:38 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:1 (he=True, en=False)
2025-12-02 09:34:38 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:38 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:38 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (1000 chars)
2025-12-02 09:34:38 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [2/10] Fetching: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:2
2025-12-02 09:34:38 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:2
2025-12-02 09:34:38 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:2
2025-12-02 09:34:38 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:38 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B7F5CD0>
2025-12-02 09:34:38 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B04CD40> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:38 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B921580>
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:38 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:2"), (b'x-varnish', b'410726826'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=BXMdebSJCb6HfoQi8%2FGe%2Fcu8g6u1YigjAb0NYR5qBYScmMoBJhDvT2YT09f2AjFaNk22OwCoj2kwpAxjQ3YrIe1RZ68DT0lK8eG%2FxB%2Fq"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bd68e6bc463-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:38 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:2 "HTTP/1.1 200 OK"
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:38 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:38 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:2 (he=True, en=False)
2025-12-02 09:34:38 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:38 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:38 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (368 chars)
2025-12-02 09:34:38 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [3/10] Fetching: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:3
2025-12-02 09:34:38 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:3
2025-12-02 09:34:38 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:3
2025-12-02 09:34:38 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:38 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B9258E0>
2025-12-02 09:34:38 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B44CEC0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:38 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B849D30>
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:38 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:39 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:3"), (b'x-varnish', b'407681558'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=NM19kyZMMis1gTQHxv8jb6n3yocTNZ41Gra%2BPFOj0ATWNEWnfblu41wHk5gE6D2Bqar%2FnPQb4ZKepjsTDZSzhnlnLvQ9HXxgEuagYvAx"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bd85d34d2b1-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:39 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:3 "HTTP/1.1 200 OK"
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:39 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:39 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:3 (he=True, en=False)
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:39 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (1000 chars)
2025-12-02 09:34:39 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [4/10] Fetching: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:4
2025-12-02 09:34:39 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:4
2025-12-02 09:34:39 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:4
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B935850>
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B44CF40> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B935C70>
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:39 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:4"), (b'x-varnish', b'411044211'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=H1Mhw9S1gyzzXKibozaZnWZmK7KN734m0PhT5KQCVNbpVEW2Q52PdyuDXrHTdfBSj%2BRHtsFe4PiVVG%2Ftvn21VheVUzCG97JU5OaZ1dif"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bdd5b00c64a-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:39 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:4 "HTTP/1.1 200 OK"
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:39 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:39 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:4 (he=True, en=False)
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:39 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (234 chars)
2025-12-02 09:34:39 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [5/10] Fetching: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:5
2025-12-02 09:34:39 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:5
2025-12-02 09:34:39 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:5
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B937A60>
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B44CE40> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B937A30>
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:39 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:5"), (b'x-varnish', b'409479390'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=NCf2nL1E%2F7pcW606YZPQH0RKIBj8Nj3XqNvBg4uHEq%2BK5XRIf1UH84zyIJa9oyU%2Bo%2BhcuwgFlnzAOXfKLLgcej0vAojvvzX%2F%2B0GcC2y%2F"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bdf2f96cd8b-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:39 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:5 "HTTP/1.1 200 OK"
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:39 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:39 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:39 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:5 (he=True, en=False)
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:39 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (371 chars)
2025-12-02 09:34:39 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [6/10] Fetching: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:6
2025-12-02 09:34:39 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:6
2025-12-02 09:34:39 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:6
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81BAB0190>
2025-12-02 09:34:39 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B829240> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:40 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B94A970>
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:40 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:6"), (b'x-varnish', b'407781538'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=%2FY9NK0l9e1vwFZH1H0wxAyDtGID4JRCJJvnv0pQ6N49QE5UKezHAVe5AhUqh0uBkNUarJ3uBZp5q%2B1ohVtmVdj6jpCBdPqyliQ4rXhIE"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8be0df69729b-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:40 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Turei%20Zahav%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:6 "HTTP/1.1 200 OK"
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:40 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:40 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Turei Zahav on Shulchan Arukh, Yoreh De'ah 1:6 (he=True, en=False)
2025-12-02 09:34:40 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:40 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:40 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (1000 chars)
2025-12-02 09:34:40 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [7/10] Fetching: Tur, Yoreh De'ah 1:1
2025-12-02 09:34:40 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Tur, Yoreh De'ah 1:1
2025-12-02 09:34:40 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Tur%2C%20Yoreh%20De'ah%201:1
2025-12-02 09:34:40 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:40 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81BAB0DC0>
2025-12-02 09:34:40 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B8291C0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:40 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81BAB03D0>
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:40 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Tur%2C%20Yoreh%20De'ah%201:1"), (b'x-varnish', b'410232143'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=6FQOuN1jJesoRqXpUMdyaLair1LIGNreDTmF8%2FSDsN7D7mifKrBYZzyI3UMgSquJSxmuqTtZf9KW5F%2BQp1d%2F%2BjohbcEB05meUIiqNk7Z"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8be3b982f812-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:40 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Tur%2C%20Yoreh%20De'ah%201:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:40 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:40 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Tur, Yoreh De'ah 1:1 (he=True, en=False)
2025-12-02 09:34:40 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:40 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:40 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (1000 chars)
2025-12-02 09:34:40 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [8/10] Fetching: Yad Ephraim on Shulchan Arukh, Yoreh De'ah 1:1
2025-12-02 09:34:40 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Yad Ephraim on Shulchan Arukh, Yoreh De'ah 1:1
2025-12-02 09:34:40 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Yad%20Ephraim%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:1
2025-12-02 09:34:40 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:40 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B938520>
2025-12-02 09:34:40 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B846CC0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:40 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B94A7F0>
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:40 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:41 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Yad%20Ephraim%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:1"), (b'x-varnish', b'404969660'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=qDpgiNMsPocqrIW2Gibmw6SKVL8Kid0mjqdtEotbQ5ZZR%2B%2FIjun6BCR3niYb5AlFOWq%2Fpg%2FLfkBiF%2FxXfjZEvBrctd3z2%2BvZ5xki%2Fg%3D%3D"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8be5f8cf6d50-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:41 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Yad%20Ephraim%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:41 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:41 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Yad Ephraim on Shulchan Arukh, Yoreh De'ah 1:1 (he=True, en=False)
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:41 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (198 chars)
2025-12-02 09:34:41 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [9/10] Fetching: Yad Ephraim on Shulchan Arukh, Yoreh De'ah 1:2
2025-12-02 09:34:41 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Yad Ephraim on Shulchan Arukh, Yoreh De'ah 1:2
2025-12-02 09:34:41 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Yad%20Ephraim%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:2
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B8316A0>
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B846EC0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B937730>
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:41 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Yad%20Ephraim%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:2"), (b'x-varnish', b'408261234'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=MwrNHj5ILC1Xw98KfA3Qk3i7P568iLpeIRGeqMRAUmLu5SWm6OkFxzRDeiwykDOH1f3haXKFxg3cUl21xe4xP7EcqM5qEkAc2D0t8OuA"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8be828f9b29e-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:41 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Yad%20Ephraim%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:2 "HTTP/1.1 200 OK"
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:41 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:41 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Yad Ephraim on Shulchan Arukh, Yoreh De'ah 1:2 (he=True, en=False)
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:41 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (849 chars)
2025-12-02 09:34:41 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [10/10] Fetching: Yad Ephraim on Shulchan Arukh, Yoreh De'ah 1:3
2025-12-02 09:34:41 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Yad Ephraim on Shulchan Arukh, Yoreh De'ah 1:3
2025-12-02 09:34:41 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Yad%20Ephraim%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:3
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B925430>
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B846D40> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B022BB0>
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:41 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Yad%20Ephraim%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:3"), (b'x-varnish', b'407062122'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=2aRqystKafJIKo5VX%2Fso3WiUxC0boSXTlKJfUFJcadt4%2Fu87TuEtoePYZu8JkzGKXlS%2FSzhFxF%2FIYQfMFbgBFh%2FwgTGzfX7O5kkd9ryD"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bea0d23c440-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:41 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Yad%20Ephraim%20on%20Shulchan%20Arukh%2C%20Yoreh%20De'ah%201:3 "HTTP/1.1 200 OK"
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:41 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:41 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Yad Ephraim on Shulchan Arukh, Yoreh De'ah 1:3 (he=True, en=False)
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:41 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (1000 chars)
2025-12-02 09:34:41 | INFO     | __main__:fetch_commentaries_for_base_texts:691 | 
📖 Processing base text: Chullin 9a
2025-12-02 09:34:41 | INFO     | __main__:get_related_texts:449 | 🔗 Getting related texts for: Chullin 9a
2025-12-02 09:34:41 | DEBUG    | __main__:get_related_texts:460 |   URL: https://www.sefaria.org/api/related/Chullin%209a
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B849E80>
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B846E40> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:41 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B849580>
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:41 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:42 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:42 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/related/Chullin%209a'), (b'x-varnish', b'407781555'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=qrADiR0gQVBPPJJ2iUGJvhvHlBVhVq20gYRuNS2WEUwASfIsXiQW8pnIg7rpiJv3E9NxIEUV3WPJLwGoQTesnSqHdsGEcepoZYScqVbo"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bebdd380edf-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:42 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/related/Chullin%209a "HTTP/1.1 200 OK"
2025-12-02 09:34:42 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:42 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:42 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:42 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:42 | DEBUG    | __main__:get_related_texts:473 |   Found 190 total links
2025-12-02 09:34:42 | INFO     | __main__:get_related_texts:487 |   ✓ Found 100 commentaries
2025-12-02 09:34:42 | DEBUG    | __main__:get_related_texts:491 |   Commentaries found:
2025-12-02 09:34:42 | DEBUG    | __main__:get_related_texts:493 |     - Rosh on Chullin 1:11:1
2025-12-02 09:34:42 | DEBUG    | __main__:get_related_texts:493 |     - Rashi on Chullin 9a:1:1
2025-12-02 09:34:42 | DEBUG    | __main__:get_related_texts:493 |     - Rashi on Chullin 9a:1:2
2025-12-02 09:34:42 | DEBUG    | __main__:get_related_texts:493 |     - Rashi on Chullin 9a:1:3
2025-12-02 09:34:42 | DEBUG    | __main__:get_related_texts:493 |     - Steinsaltz on Chullin 9a:1
2025-12-02 09:34:42 | DEBUG    | __main__:get_related_texts:495 |     ... and 95 more
2025-12-02 09:34:42 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:42 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:42 | INFO     | __main__:fetch_commentaries_for_base_texts:700 |   Found 100 commentaries, fetching texts...
2025-12-02 09:34:42 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [1/10] Fetching: Rosh on Chullin 1:11:1
2025-12-02 09:34:42 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Rosh on Chullin 1:11:1
2025-12-02 09:34:42 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Rosh%20on%20Chullin%201:11:1
2025-12-02 09:34:42 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:42 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B9370D0>
2025-12-02 09:34:42 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B44CF40> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:42 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B937AF0>
2025-12-02 09:34:42 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:42 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:42 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:42 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:42 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:42 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:42 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Rosh%20on%20Chullin%201:11:1'), (b'x-varnish', b'410232203'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=ZKoobxFINo%2FWNAzC9VpyXdSIP1s9nbhzpz4gX86zznTfISvpZG5TbvHDG6%2FOrcP86K21lxK8Kksi8wl%2Blydu%2B4JSFVPmYN9ZrayVb6ZI"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bf16c4b429a-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:42 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Rosh%20on%20Chullin%201:11:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:42 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:42 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:42 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:42 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:42 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:42 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Rosh on Chullin 1:11:1 (he=True, en=False)
2025-12-02 09:34:42 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:42 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:42 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (1000 chars)
2025-12-02 09:34:42 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [2/10] Fetching: Rashi on Chullin 9a:1:1
2025-12-02 09:34:42 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Rashi on Chullin 9a:1:1
2025-12-02 09:34:42 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Rashi%20on%20Chullin%209a:1:1
2025-12-02 09:34:42 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:42 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B94A490>
2025-12-02 09:34:42 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B0291C0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B935310>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:43 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Rashi%20on%20Chullin%209a:1:1'), (b'x-varnish', b'405043394'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=Vc9QO8GejfFNMEVQEzmw0%2By7Fts%2FxMdUc%2FqMMY2hxK72q4qfKofIW7ZwdDD2Kvk%2B4Z8a8sGaPWsA%2B4pEKE5pRDJjmQMld8OkcWgEdVH0"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bf32c332223-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:43 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Rashi%20on%20Chullin%209a:1:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:43 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:43 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Rashi on Chullin 9a:1:1 (he=True, en=False)
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:43 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (84 chars)
2025-12-02 09:34:43 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [3/10] Fetching: Rashi on Chullin 9a:1:2
2025-12-02 09:34:43 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Rashi on Chullin 9a:1:2
2025-12-02 09:34:43 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Rashi%20on%20Chullin%209a:1:2
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B9251C0>
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B0299C0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B925E80>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:43 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Rashi%20on%20Chullin%209a:1:2'), (b'x-varnish', b'411631979'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=xMk3MQASLAcdymX15ARuwhcHGYUOEb9fcrpoyBw4UY6%2FDjUmhBqqmbYcnhBj7kYA9Dy%2F7bODtkKUxMWEon39beH0LfBNuPMj7aSZXAJM"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bf51f6381e7-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:43 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Rashi%20on%20Chullin%209a:1:2 "HTTP/1.1 200 OK"
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:43 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:43 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Rashi on Chullin 9a:1:2 (he=True, en=False)
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:43 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (16 chars)
2025-12-02 09:34:43 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [4/10] Fetching: Rashi on Chullin 9a:1:3
2025-12-02 09:34:43 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Rashi on Chullin 9a:1:3
2025-12-02 09:34:43 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Rashi%20on%20Chullin%209a:1:3
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B37B280>
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B846840> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B9217F0>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:43 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Rashi%20on%20Chullin%209a:1:3'), (b'x-varnish', b'407030860'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=IOyoFwAv8h8O%2FOXVv42oKOc5AE5a9CUJE1E9popNKNKziQuWQq%2BGIvz9y0FpaPjZW1YKjA6tt3m5e8f6Ifo6giOtM5tjlele0yxzZeu%2F"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bf6fcdf6dc6-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:43 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Rashi%20on%20Chullin%209a:1:3 "HTTP/1.1 200 OK"
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:43 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:43 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Rashi on Chullin 9a:1:3 (he=True, en=False)
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:43 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (37 chars)
2025-12-02 09:34:43 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [5/10] Fetching: Steinsaltz on Chullin 9a:1
2025-12-02 09:34:43 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Steinsaltz on Chullin 9a:1
2025-12-02 09:34:43 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Chullin%209a:1
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B88B370>
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B846BC0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:43 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B78F2E0>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:43 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:44 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Steinsaltz%20on%20Chullin%209a:1'), (b'x-varnish', b'404773880'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=RS9pZ6usyzMHyRDYvpibr2w7HohuTVqtIq2FPyfP7IWYoTtKSdmiVe5wu%2FlLq5v9LPz9NEGYiZtXy%2FWrPxOBlp0BA6W7oxpHkaY4Lw%3D%3D"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bf8d965c324-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:44 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Chullin%209a:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:44 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:44 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Steinsaltz on Chullin 9a:1 (he=True, en=False)
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:44 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (263 chars)
2025-12-02 09:34:44 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [6/10] Fetching: Rabbeinu Gershom on Chullin 9a:1
2025-12-02 09:34:44 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Rabbeinu Gershom on Chullin 9a:1
2025-12-02 09:34:44 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Rabbeinu%20Gershom%20on%20Chullin%209a:1
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B898A30>
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B846EC0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B8987C0>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:44 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Rabbeinu%20Gershom%20on%20Chullin%209a:1'), (b'x-varnish', b'407030891'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=Ya%2B48hBk3vJvzqJlj597CYjn5HnAiy7ZQyICCvRjNAs6snhXSzyGjTZhmokP3nwcEeoAHWt3wk0bNOxZj5MPLBXN86tejYfB5uoQICfc"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bfabba4c54a-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:44 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Rabbeinu%20Gershom%20on%20Chullin%209a:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:44 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:44 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Rabbeinu Gershom on Chullin 9a:1 (he=True, en=False)
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:44 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (69 chars)
2025-12-02 09:34:44 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [7/10] Fetching: Otzar La'azei Rashi, Talmud, Chullin 9
2025-12-02 09:34:44 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Otzar La'azei Rashi, Talmud, Chullin 9
2025-12-02 09:34:44 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Otzar%20La'azei%20Rashi%2C%20Talmud%2C%20Chullin%209
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B8960D0>
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B44CE40> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B896E50>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:44 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Otzar%20La'azei%20Rashi%2C%20Talmud%2C%20Chullin%209"), (b'x-varnish', b'409016797'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=Oyk%2BfYZMGrb5aPvEiwcqhkK0OikGLu5NwkRfl2hoemWWcnXHJA9FkjivfgxHtfnPTOICEF7kp4x4399tyj8IY0JvkNemlZFAbHmLEH1I"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bfc7f05432b-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:44 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Otzar%20La'azei%20Rashi%2C%20Talmud%2C%20Chullin%209 "HTTP/1.1 200 OK"
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:44 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:44 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Otzar La'azei Rashi, Talmud, Chullin 9 (he=True, en=False)
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:44 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (103 chars)
2025-12-02 09:34:44 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [8/10] Fetching: Rif Chullin 2b:2
2025-12-02 09:34:44 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Rif Chullin 2b:2
2025-12-02 09:34:44 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Rif%20Chullin%202b:2
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B78F0D0>
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B44CF40> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B898730>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:44 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Rif%20Chullin%202b:2'), (b'x-varnish', b'411697666'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=rStxcLSmZavF0081bMEN3B%2Fy2foSWZ7bEZsr6ZomKnZhuZeR%2Fs4m6slKd%2FyhxAEZ0SQOsTWKKpElguJSWaJJGpGA%2BJix3S8JnvXg7CuD"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8bfe5f255e71-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:44 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Rif%20Chullin%202b:2 "HTTP/1.1 200 OK"
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:44 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:44 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:44 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Rif Chullin 2b:2 (he=True, en=False)
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:44 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (573 chars)
2025-12-02 09:34:44 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [9/10] Fetching: Rashi on Chullin 9a:10:1
2025-12-02 09:34:44 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Rashi on Chullin 9a:10:1
2025-12-02 09:34:44 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Rashi%20on%20Chullin%209a:10:1
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B9217C0>
2025-12-02 09:34:44 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B829740> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:45 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B37B280>
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:45 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Rashi%20on%20Chullin%209a:10:1'), (b'x-varnish', b'404059083'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=ATkc21KyqcCvDBSOs50i3UG%2FeS3D2NIDnWwUEA0FmrU2bQevt6dpcl6tv66IqjhLd3RCQxIqIdn8QWpip3MVmEnKyCNdOw4J0VljDY1Q"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8c000dcd425f-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:45 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Rashi%20on%20Chullin%209a:10:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:45 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:45 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Rashi on Chullin 9a:10:1 (he=True, en=False)
2025-12-02 09:34:45 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:45 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:45 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (76 chars)
2025-12-02 09:34:45 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [10/10] Fetching: Rashi on Chullin 9a:10:2
2025-12-02 09:34:45 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Rashi on Chullin 9a:10:2
2025-12-02 09:34:45 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Rashi%20on%20Chullin%209a:10:2
2025-12-02 09:34:45 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:45 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B925F40>
2025-12-02 09:34:45 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B8299C0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:45 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B925940>
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:45 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Rashi%20on%20Chullin%209a:10:2'), (b'x-varnish', b'401832356'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=5eRqoc32nsEQ9dVRokgHRv2dnoZfynSfk0ANieVBAQnZdAoYWJeH718FVAUb735DWWWOa0LeSCoUTPaK44Zk7%2Fiv4ogZogz%2BJTERCXRz"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8c01fe8227f6-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:45 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Rashi%20on%20Chullin%209a:10:2 "HTTP/1.1 200 OK"
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:45 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:45 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Rashi on Chullin 9a:10:2 (he=True, en=False)
2025-12-02 09:34:45 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:45 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:45 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (159 chars)
2025-12-02 09:34:45 | INFO     | __main__:fetch_commentaries_for_base_texts:691 | 
📖 Processing base text: Mishneh Torah, Forbidden Foods 4
2025-12-02 09:34:45 | INFO     | __main__:get_related_texts:449 | 🔗 Getting related texts for: Mishneh Torah, Forbidden Foods 4
2025-12-02 09:34:45 | DEBUG    | __main__:get_related_texts:460 |   URL: https://www.sefaria.org/api/related/Mishneh%20Torah%2C%20Forbidden%20Foods%204
2025-12-02 09:34:45 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:45 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B935520>
2025-12-02 09:34:45 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B829040> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:45 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B94A280>
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:45 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:45 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/related/Mishneh%20Torah%2C%20Forbidden%20Foods%204'), (b'x-varnish', b'407781656'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=rBicP6gRvuRmUOWAFYpa5CYLqUVfbDUqOyEFJZ%2Fj%2FQbn2b9LG7czW2qWRknomop6ATDbFMhpATK2hG917c38pmXKV%2B%2Fg9o1UONxRCYqG"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8c03cfafd96d-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:46 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/related/Mishneh%20Torah%2C%20Forbidden%20Foods%204 "HTTP/1.1 200 OK"
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:46 | DEBUG    | __main__:get_related_texts:473 |   Found 296 total links
2025-12-02 09:34:46 | INFO     | __main__:get_related_texts:487 |   ✓ Found 192 commentaries
2025-12-02 09:34:46 | DEBUG    | __main__:get_related_texts:491 |   Commentaries found:
2025-12-02 09:34:46 | DEBUG    | __main__:get_related_texts:493 |     - Tzafnat Pa'neach on Mishneh Torah, Forbidden Foods 4:1:1
2025-12-02 09:34:46 | DEBUG    | __main__:get_related_texts:493 |     - Steinsaltz on Mishneh Torah, Forbidden Foods 4:1:1
2025-12-02 09:34:46 | DEBUG    | __main__:get_related_texts:493 |     - Steinsaltz on Mishneh Torah, Forbidden Foods 4:1:2
2025-12-02 09:34:46 | DEBUG    | __main__:get_related_texts:493 |     - Steinsaltz on Mishneh Torah, Forbidden Foods 4:10:1
2025-12-02 09:34:46 | DEBUG    | __main__:get_related_texts:493 |     - Steinsaltz on Mishneh Torah, Forbidden Foods 4:10:2
2025-12-02 09:34:46 | DEBUG    | __main__:get_related_texts:495 |     ... and 187 more
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:46 | INFO     | __main__:fetch_commentaries_for_base_texts:700 |   Found 192 commentaries, fetching texts...
2025-12-02 09:34:46 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [1/10] Fetching: Tzafnat Pa'neach on Mishneh Torah, Forbidden Foods 4:1:1
2025-12-02 09:34:46 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Tzafnat Pa'neach on Mishneh Torah, Forbidden Foods 4:1:1
2025-12-02 09:34:46 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Tzafnat%20Pa'neach%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:1:1
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B849670>
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B029040> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B8494C0>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:46 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Tzafnat%20Pa'neach%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:1:1"), (b'x-varnish', b'411796147'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=%2FKJi%2FAhBft4ZW%2FnFGdVxEfRLNM0TP75r2FGUJ5yPykGHJbgJuggwsBy6KR6RF3JntSg5u9pdH4JERTvx%2F6oZOqHtXlkioclhQTyQMoX5"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8c0778854286-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:46 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Tzafnat%20Pa'neach%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:1:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:46 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:46 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Tzafnat Pa'neach on Mishneh Torah, Forbidden Foods 4:1:1 (he=True, en=False)
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:46 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (832 chars)
2025-12-02 09:34:46 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [2/10] Fetching: Steinsaltz on Mishneh Torah, Forbidden Foods 4:1:1
2025-12-02 09:34:46 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Steinsaltz on Mishneh Torah, Forbidden Foods 4:1:1
2025-12-02 09:34:46 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:1:1
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B480EB0>
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B8291C0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B78F430>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:46 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:1:1'), (b'x-varnish', b'407356211'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=9DpJoKBtg0s3oMb2EtzE0OH61XerruJQGmGavCRt%2B%2Bs5w%2F7wB%2Fo1ELxkCFJsgw51Kh%2FUIaVrRKnvdRxPrAc2Th2wCzs7anybqyVtroMi"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8c093eeb069b-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:46 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:1:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:46 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:46 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Steinsaltz on Mishneh Torah, Forbidden Foods 4:1:1 (he=True, en=False)
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:46 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (87 chars)
2025-12-02 09:34:46 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [3/10] Fetching: Steinsaltz on Mishneh Torah, Forbidden Foods 4:1:2
2025-12-02 09:34:46 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Steinsaltz on Mishneh Torah, Forbidden Foods 4:1:2
2025-12-02 09:34:46 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:1:2
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B022A30>
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B829AC0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B898DF0>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:46 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:1:2'), (b'x-varnish', b'410590123'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=97mTj1RzJQ%2Bp%2BTlzmJKxnnlI89tWbpJGurJJiQ7UQxa9u9A2yFqSxsHx24iXTfAp25BpARiKjGY5HTu3F1NLZVCyF2RUARteFK8W1FAO"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8c0afeb6be83-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:46 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:1:2 "HTTP/1.1 200 OK"
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:46 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:46 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:46 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Steinsaltz on Mishneh Torah, Forbidden Foods 4:1:2 (he=True, en=False)
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:46 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (45 chars)
2025-12-02 09:34:46 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [4/10] Fetching: Steinsaltz on Mishneh Torah, Forbidden Foods 4:10:1
2025-12-02 09:34:46 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Steinsaltz on Mishneh Torah, Forbidden Foods 4:10:1
2025-12-02 09:34:46 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:10:1
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B937B20>
2025-12-02 09:34:46 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B829140> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:47 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B831910>
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:47 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:10:1'), (b'x-varnish', b'405134261'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=WBMvcan8yU8vPD114Jw4SDIpMR8qfMqE0hWWUixGxn4MRPEgbYZba82f1MBhrLZUyvaOMgwn2KJzIk2ZIi33CWHJG%2Fg6ALGmk8hUiuS4"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8c0cca2b4282-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:47 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:10:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:47 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:47 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Steinsaltz on Mishneh Torah, Forbidden Foods 4:10:1 (he=True, en=False)
2025-12-02 09:34:47 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:47 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:47 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (102 chars)
2025-12-02 09:34:47 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [5/10] Fetching: Steinsaltz on Mishneh Torah, Forbidden Foods 4:10:2
2025-12-02 09:34:47 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Steinsaltz on Mishneh Torah, Forbidden Foods 4:10:2
2025-12-02 09:34:47 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:10:2
2025-12-02 09:34:47 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:47 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B982CD0>
2025-12-02 09:34:47 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B8292C0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:47 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B982A60>
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:47 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:10:2'), (b'x-varnish', b'407134407'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=%2BkS3%2Fhmkb2rwh0xO%2FRyz6ryqj23vH1m%2F%2BjNeQWUer49TDswDgrdtv5SwnSV%2BvCwoLhTwknQlm9k01DxvpTfTlYyDu0zntos%2BF3SnDZcr"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8c0e9ede8c6d-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:47 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:10:2 "HTTP/1.1 200 OK"
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:47 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:47 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Steinsaltz on Mishneh Torah, Forbidden Foods 4:10:2 (he=True, en=False)
2025-12-02 09:34:47 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:47 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:47 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (88 chars)
2025-12-02 09:34:47 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [6/10] Fetching: Steinsaltz on Mishneh Torah, Forbidden Foods 4:11:1
2025-12-02 09:34:47 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Steinsaltz on Mishneh Torah, Forbidden Foods 4:11:1
2025-12-02 09:34:47 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:11:1
2025-12-02 09:34:47 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:47 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B9893A0>
2025-12-02 09:34:47 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B829940> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:47 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B987C10>
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:47 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:48 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:11:1'), (b'x-varnish', b'406442104'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=FW6uccVbfMe76yBDYAOD2kGDGth1JL1Zkr2C2XDWC5Oql%2FjDr2kS0VU88OcQ7sdqvk4cJlhCmhNGpyPuomjKUQhChPLC9upYIYHRkTMZ"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8c11cf3cccb6-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:48 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:11:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:48 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:48 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Steinsaltz on Mishneh Torah, Forbidden Foods 4:11:1 (he=True, en=False)
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:48 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (94 chars)
2025-12-02 09:34:48 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [7/10] Fetching: Tzafnat Pa'neach on Mishneh Torah, Forbidden Foods 4:12:1
2025-12-02 09:34:48 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Tzafnat Pa'neach on Mishneh Torah, Forbidden Foods 4:12:1
2025-12-02 09:34:48 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Tzafnat%20Pa'neach%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:12:1
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B989FA0>
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B8299C0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B989AC0>
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:48 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b"/api/v3/texts/Tzafnat%20Pa'neach%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:12:1"), (b'x-varnish', b'410914860'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=qYQHhc7tIjWz03fanDPTG7Oi4wbzMjfCEJT%2BhMKv6CvOi2LqIbNdXrEnP6%2FaFKEnUEIqJIYf%2BSM5uMRCelDBlUJNCdxHr89Z0QFvtyWw"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8c138fc78dd6-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:48 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Tzafnat%20Pa'neach%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:12:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:48 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:48 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Tzafnat Pa'neach on Mishneh Torah, Forbidden Foods 4:12:1 (he=True, en=False)
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:48 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (55 chars)
2025-12-02 09:34:48 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [8/10] Fetching: Steinsaltz on Mishneh Torah, Forbidden Foods 4:12:1
2025-12-02 09:34:48 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Steinsaltz on Mishneh Torah, Forbidden Foods 4:12:1
2025-12-02 09:34:48 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:12:1
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B935100>
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B0299C0> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B987640>
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:48 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:12:1'), (b'x-varnish', b'411404257'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=j0YSqk1B2C5anwIU8JkXxdtVvmDpMa9lzcOFzXJqqv1%2BamysWmg3EqIWlEGW9uFb2u4lDgswEsGCAq%2B3zDKnf3sTDpHB5CXcDuf96kLd"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8c15b989ee23-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:48 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:12:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:48 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:48 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Steinsaltz on Mishneh Torah, Forbidden Foods 4:12:1 (he=True, en=False)
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:48 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (80 chars)
2025-12-02 09:34:48 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [9/10] Fetching: Steinsaltz on Mishneh Torah, Forbidden Foods 4:12:2
2025-12-02 09:34:48 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Steinsaltz on Mishneh Torah, Forbidden Foods 4:12:2
2025-12-02 09:34:48 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:12:2
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B8315E0>
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B44CE40> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:48 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B937C40>
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:48 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:48 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:12:2'), (b'x-varnish', b'410914886'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=wULU0EuA1%2BQ41jySp6iC3qNst6MyHQT7Fqqa0zrqMOtavvisAu8GmXHppe5x%2BlCtVZNAgCaH9xhU9ELKaDLiaiqyQn1HsdMY5SHE04%2B4"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8c1769b75e73-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:49 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:12:2 "HTTP/1.1 200 OK"
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:49 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:49 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Steinsaltz on Mishneh Torah, Forbidden Foods 4:12:2 (he=True, en=False)
2025-12-02 09:34:49 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:49 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:49 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (88 chars)
2025-12-02 09:34:49 | INFO     | __main__:fetch_commentaries_for_base_texts:706 |   [10/10] Fetching: Steinsaltz on Mishneh Torah, Forbidden Foods 4:13:1
2025-12-02 09:34:49 | INFO     | __main__:fetch_text_from_sefaria:373 | 📥 Fetching from Sefaria: Steinsaltz on Mishneh Torah, Forbidden Foods 4:13:1
2025-12-02 09:34:49 | DEBUG    | __main__:fetch_text_from_sefaria:377 |   URL: https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:13:1
2025-12-02 09:34:49 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.started host='www.sefaria.org' port=443 local_address=None timeout=15.0 socket_options=None
2025-12-02 09:34:49 | DEBUG    | httpcore.connection:atrace:87 | connect_tcp.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B8984F0>
2025-12-02 09:34:49 | DEBUG    | httpcore.connection:atrace:87 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F81B04CD40> server_hostname='www.sefaria.org' timeout=15.0
2025-12-02 09:34:49 | DEBUG    | httpcore.connection:atrace:87 | start_tls.complete return_value=<httpcore._backends.anyio.AnyIOStream object at 0x000001F81B8985E0>
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.started request=<Request [b'GET']>
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:atrace:87 | send_request_headers.complete
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.started request=<Request [b'GET']>
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:atrace:87 | send_request_body.complete
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.started request=<Request [b'GET']>
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:atrace:87 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:49 GMT'), (b'Content-Type', b'application/json; charset=utf-8'), (b'Vary', b'Accept-Language, Cookie'), (b'Content-Language', b'en'), (b'url', b'/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:13:1'), (b'x-varnish', b'404904051'), (b'Age', b'0'), (b'Report-To', b'{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=yN6eZe7Whm6hnj0hY63vAwtXQOtrKVqX8fkxSrASd7Qfw7Zr%2BsljwL%2BjkLffJaW63%2FUT0KDElrPawZXfRkNNVPECz0F95NJUAZsfFuxO"}]}'), (b'access-control-allow-origin', b'*'), (b'strict-transport-security', b'max-age=2592000'), (b'cf-cache-status', b'DYNAMIC'), (b'Nel', b'{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}'), (b'Content-Encoding', b'gzip'), (b'CF-RAY', b'9a7b8c19aaf1c094-EWR'), (b'Cache-Status', b'node4.env2.dc1.us.techloq.com;detail=no-cache'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Referrer-Policy', b'no-referrer-when-downgrade')])
2025-12-02 09:34:49 | INFO     | httpx:_send_single_request:1740 | HTTP Request: GET https://www.sefaria.org/api/v3/texts/Steinsaltz%20on%20Mishneh%20Torah%2C%20Forbidden%20Foods%204:13:1 "HTTP/1.1 200 OK"
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.started request=<Request [b'GET']>
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:atrace:87 | receive_response_body.complete
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:atrace:87 | response_closed.started
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:atrace:87 | response_closed.complete
2025-12-02 09:34:49 | DEBUG    | __main__:fetch_text_from_sefaria:393 |   Found 1 version(s)
2025-12-02 09:34:49 | INFO     | __main__:fetch_text_from_sefaria:415 |   ✓ SUCCESS: Steinsaltz on Mishneh Torah, Forbidden Foods 4:13:1 (he=True, en=False)
2025-12-02 09:34:49 | DEBUG    | httpcore.connection:atrace:87 | close.started
2025-12-02 09:34:49 | DEBUG    | httpcore.connection:atrace:87 | close.complete
2025-12-02 09:34:49 | INFO     | __main__:fetch_commentaries_for_base_texts:718 |     ✓ Got text (24 chars)
2025-12-02 09:34:49 | INFO     | __main__:fetch_commentaries_for_base_texts:724 | 
✓ Total commentaries fetched: 40
2025-12-02 09:34:49 | INFO     | __main__:extract_citations_from_commentaries:736 | ================================================================================
2025-12-02 09:34:49 | INFO     | __main__:extract_citations_from_commentaries:737 | STAGE 3: EXTRACT CITATIONS FROM COMMENTARIES
2025-12-02 09:34:49 | INFO     | __main__:extract_citations_from_commentaries:738 | ================================================================================
2025-12-02 09:34:49 | INFO     | __main__:extract_citations_from_commentaries:739 |   Analyzing 40 commentary texts
2025-12-02 09:34:49 | DEBUG    | __main__:extract_citations_from_commentaries:776 |   Sending to Claude for citation extraction...
2025-12-02 09:34:49 | DEBUG    | anthropic._base_client:_build_request:493 | Request options: {'method': 'post', 'url': '/v1/messages', 'timeout': Timeout(connect=5.0, read=600, write=600, pool=600), 'files': None, 'idempotency_key': 'stainless-python-retry-e84777e3-6c93-4562-b849-11ae3d1ad8b2', 'json_data': {'max_tokens': 2000, 'messages': [{'role': 'user', 'content': 'Here are texts from commentaries discussing the topic:\n\n\nSOURCE: Yad Eitan on Mishneh Torah, Ritual Slaughter 1:1:1\nTEXT: אשר יצוד ציד חיה או עוף ושפך את דמו מלמד ששפיכת דם עוף כדם חיה. ותמה הכס"מ דבגמ\' יליף רב יהודה בשם ריב"פ איפכא מזה הפסוק דאין שחיטה לעוף מה"ת דשפך משמע שפיכה בעלמא וקאי רק על עוף דסליק מיניה ולא אחיה. ותירוצו דחוק כמ"ש הלח"מ וכרו"פ וגם תירוצם דחוק דאכתי מנ"ל לרבינו היקש דעוף לחיה מה שלא נאמר בגמ\'. אבל הדבר ברור שיצא זה לרבינו מהסוגיא דחולין (דף פ"ד) דאסיק מר בר ר"א אמר קרא חיה או עוף מה חיה אינה קודש אף עוף כו\' וה"נ מקשינן עוף לחיה לענין שחיטה. ואף לפמ"ש בס\' פאר הלכה דהך היקש דפ\' כסוי הדם צ"ל מיותר רק להא מילתא משום דהוי אפשר משאי אפשר מ"מ אפי\' דרשינן היקש זה לרבינו אפ"ה איכא יתורא להיקש דפ\' כסוי הדם דהא היקשא דכאן איכא למשמע אפי\' הוה כתיב חיה ועוף ואייתר או לההוא היקש דפ\' כה"ד. וכה"ג כתב בס\' הנזכר דההיא סוגיא אזלא למאן דלא בעא או לחלק ואייתר להך היקשא. וא"כ א"ש דהיקשא דרבינו בלאו או איכא \n\n============================================================\n\nSOURCE: Ohr Sameach on Mishneh Torah, Ritual Slaughter 1:1:1\nTEXT: ושפך את דמו מלמד ששפיכת דם העוף כשפיכת דם החיה והלכות שחיטה בכולן אחת הן. כן נראה שצ"ל, שזה שייך להלכה א\', והציון ב\' צ"ל קודם לפיכך, והכוונה דלא כמאן דאמר אין עיקור סימנים בעוף אם יש שחיטה לעוף מן התורה, וכן סתמא דתלמודא ריש פ"ב דמייתי דיש שחיטה לעוף מה"ת מדתנן הנוחר והמעקר פטור מלכסות וא"א אין כו\' נחירתו זו היא שחיטתו כו\' אלמא דיש עיקור סימנים בעוף אם יש שחיטה לעוף מה"ת. והא דאמר בגמרא דמ"ד אין שחיטה לעוף מה"ת יליף מדכתיב ושפך בשפיכה בעלמא וקאי על עוף משום דסליק מיניה, זהו כר\' יהודה דאמר דשחט חיה ועוף בעי לכל חדא כסוי בפני עצמה, ושפך את דמו קאי אחד מתרווייהו או עוף או חיה לכן לא הוי היקש גמור, אבל לרבנן דכסוי אחד לשניהן לחיה ועוף, א"כ ושפך את דמו משמע דם דתרווייהו כחדא מכסה בכסוי אחד הוי היקש גמור ועוף איתקש לחיה וטעון שחיטה מה"ת ודוק. ולפ"ז למאי דקיי"ל בס"ת שתפרו בפשתן דאיתקוש להלכותיו נ\n\n============================================================\n\nSOURCE: Tzafnat Pa\'neach on Mishneh Torah, Ritual Slaughter 1:1:1\nTEXT: מצות עשה כו\' הא למדת כו\' ובעוף כו\'. הנה מדברי רבינו נראה דס"ל דעוף אף דקיי"ל דישנו לשחיטה מה"ת מ"מ לא דמי לשאר שחיטות עיין בהך דקדושין דף נ"ז ע"ב דנקט שם מנין לרבות את העופות משמע דעופות אינם בשחיטה כבהמה ע"ש ברש"י ועיין בתוס\' זבחים ד\' ס"ח ע"א. אך רבינו לקמן פ"ב ה"א ס"ל דגם עוף אסור מה"ת בחולין בעזרה ועיין רש"י כריתות ד\' ז\' ע"ב דכתבו דעוף שאני ושם ד\' כ"ו ע"ב ובירושלמי נזיר פ"ד ע"ש גבי מליקה. אך כך דהנה מדברי רבינו לקמן ספ"ד דפסק כר"ע דבמדבר הותר בשר נחירה ס"ל כך דרק לנחור מותר אבל לשחוט כד"ת אסור במדבר רק קדשים בעזרה אבל חיה היה יכול לשוחטן גם במדבר וכן פסולי המוקדשים כן ובעופות כיון דבעזרה הוה מליקה וא"כ ממילא היה יכול לשוחטן אף במדבר בגבולין, ועיין בהך דזבחים ד\' ק"ז ע"א דצריך קרא לרבות שחיטת קדשים בעופות בחוץ ע"ש והנה רבינו ז"ל פסק כמ"ד דגבי מליקה אין חשש בעיקור סימנין כמבואר שם ספ"ו בהל\n\n============================================================\n\nSOURCE: Tzafnat Pa\'neach on Mishneh Torah, Ritual Slaughter 1:1:2\nTEXT: [השמטה במש"כ שם דברי רבינו שחיטת עכו"ם עושה פעולה לאיסור ולא כמו שנשחט מאליו. וא"כ לפ"ז י"ל דאם התחיל עכו"ם לשחוט מקצת הושט אף דמבואר בתוספתא חולין פ"ב דניקב הושט שחיטתה מטהרתה מ"מ כאן אם גמרו ישראל הוי שחיטת העכו"ם חסרון ומטמא כנבילה ולא הוי כהך דחולין דף י"ט ע"ב דבמקצת קנה לא הוי שם שחיטה כלל וכמש"כ וזהו כונת רבינו בהל\' אבות הטומאות פ"ב ה"י דעל טומאה זה אין חייבין עליה כרת אם נכנס למקדש אבל אם שחט העכו"ם את כל הושט הוי גם לרבינו נבילה דזה לא עדיף מנשחט מאליו וחיב עליו כרת אם נכנס למקדש. וזהו מה דדייק רבינו בפ"ד מהל\' שחיטה הי"ג אבל אם כו\' שאינו עושה אותו נבילה ומהו לשון נבילה אך לפמש"כ דאם שחט מקצת ושט וגמרו ישראל מטמא כנבילה מחמת השחיטה ולא מחמת הנקב וכמש"כ. ובמש"כ דרבינו והר"א ז"ל פליגי אם הם פועלים איזה דבר או הוי כמו מאליו י"ל דזה תליא בהך מחלוקת דסנהדרין דף ס\' ע"א גבי עכו"ם שגידף אם \n\n============================================================\n\nSOURCE: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:1:1\nTEXT: שֶׁנֶּאֱמַר וְזָבַחְתָּ וכו\'. וזביחה היא מילה נרדפת לשחיטה.\n\n============================================================\n\nSOURCE: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:1:2\nTEXT: וְנֶאֱמַר בִּבְכוֹר בַּעַל מוּם. בדינו של בכור בהמה טהורה שיש בו מום, הניתן לכהנים ונאכל כבשר חולין (הלכות בכורות א,ג).\n\n============================================================\n\nSOURCE: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:1:3\nTEXT: הָא לָמַדְתָּ שֶׁחַיָּה כַּבְּהֵמָה וכו\'. שבפסוק זה הושוו החיות צבי ואייל לבהמות בהמה טהורה.\n\n============================================================\n\nSOURCE: Tzafnat Pa\'neach on Mishneh Torah, Ritual Slaughter 1:10:1\nTEXT: כחוט השערה כו\'. ר"ל דבר שא"א לחלקו לשנים וראיה לזה מהך דחולין דף מ\' ע"ב כגון שהיה חצי קנה פגום כו\' מוכח דתיכף איתכשר ועיין תוס\' יבמות ד\' ל"ג ע"א ד"ה שחתך אצבעו והך דע"ז דף ל"ז ע"ב גבי כנפיו חופין את רובו ע"ש ברש"י ועיין ברש"י בכורות ד\' מ\' ע"ב גבי אזניו גדולות במראה ולא במדה ע"ש:\n\n============================================================\n\nSOURCE: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:10:1\nTEXT: וַחֲצִי הַשֵּׁנִי. בדיוק חצי, ולא רוב הסימן.\n\n============================================================\n\nSOURCE: Steinsaltz on Mishneh Torah, Ritual Slaughter 1:11:1\nTEXT: קָנֶה שֶׁהָיָה חֶצְיוֹ פָּסוּק. שהיה חתוך קודם לכן, ואין חתך כזה פוסל את הבהמה (ראה לקמן ג,יט).\n\n============================================================\n\nSOURCE: Turei Zahav on Shulchan Arukh, Yoreh De\'ah 1:1\nTEXT: בטור הביא ברייתא וזבחת כאשר צויתיך מלמד שנצטוה משה בע"פ כו\'. איכא למידק מהא דאיתא פ\' ד\' מיתות (דף צו) שבת וכבוד אב ואם נצטוו במרה דכתיב כאשר צוך ה\' אלהיך וא"ר יהודה כאשר צוך במרה וא"כ מאי שנא הך כאשר צויתיך מן כאשר צוך וי"ל דהא רש"י פי\' התם דמשנה תורה לא משה מעצמו היה שונה להם בערבות מואב אלא כמו שקבלה היה חוזר ומגיד להם וכל מה שכתוב בדברות האחרונות היה כתוב בלוחות וכן שמע בסיני עכ"ל וא"כ ל"ק מידי דודאי מה שאמר הקב"ה למשה בערבות מואב במשנה תורה וזבחת כאשר צויתיך ניחא לן לפרש על מה שלמד עמו בארבעים יום אחר מעמד הר סיני תורה שבע"פ משא"כ בענין כאשר צוך דכבוד אב ואם שהוא בי\' הדברות וכן שמע ממש בסיני לשון זה ע"כ לא אפשר לומר דקאי על מה שלמד עמו בע"פ במ\' יום דהא אחר זה היו אותן מ\' יום ע"כ הוכרחנו לומר דקאי על מרה: אפילו נשים. כן הוכיחו התוס\' ריש חולין מדתנן פרק כל הפסולין (זבחים דף לא) כל הפסולי\n\n============================================================\n\nSOURCE: Turei Zahav on Shulchan Arukh, Yoreh De\'ah 1:2\nTEXT: ועבדים. בטור כ\' עבדים משוחררים ותמה ב"י הא משוחרר הוא כישראל גמור וכבר צווחי קמאי ובתראי בענין זה ולי נראה דאע"פ שהוא משוחרר אינו כישראל גמור מצד הסברא שכן מצינו במדרש ילקוט פרשת אחרי מות סי\' תקצ"ט וז"ל בתוככם לרבות נשים ועבדים משוחררים הרי לפניך דעבד משוחרר צריך ריבויא כמו אשה א"כ אף במשנה דחשיב כאן נשים ועבדים י"ל דבמשוחררים קמיירי וילמוד סתום מן המפורש במקום אחר:\n\n============================================================\n\nSOURCE: Turei Zahav on Shulchan Arukh, Yoreh De\'ah 1:3\nTEXT: וי"א שאין לסמוך כו\'. הוא דעת א"ז וכן ס"ל לבעל העיטור בדברי הטור דבעילוף לא חיישינן כלל לא בתחלה ולא בסוף ולענין מומחה אין לסמוך אלא בדיעבד ולדידהו הא דאמרי\' בגמ\' רוב מצויין אצל שחיטה מומחין הן היינו דווקא בדיעבד וס"ל דבדיעבד אפי\' בדיקה לא בעי כמ"ש הטור בהדיא בשם בעל העיטור וקשה הא דאמר רבינא בלישנא קמא דלכתחלה בעינן מומחין ולא רצו שאר אמוראים להסכים עמו מטעם דרוב מצויין אצל שחיטה מומחין הן ולפי דעת הא"ז והעיטור שזכרנו היה להם להסכים עמו דהא האי רוב לא מהני אלא בדיעבד וא"ל דלרבינא בעינן בדיעבד בדיקה ואינהו ס"ל אפי\' בדיעבד לא בעי בדיקה וכזה כתב גם הב"י דנדו מסוף דברי רבינא ובתחלת דבריו לא פליגי עליה ק"ל א"כ לוקי מתני\' בהכי ונימא הכל שוחטין לכתחלה ביודעין שהן מומחין ושחיטתן כשרה קאי אאין יודעין וכשר בלא בדיקה. ונ"ל דמשמעות המשנה דבדיעבד דכשר צריך עוד להצטרף איזה דבר לאותו הכשר דהיינו לרבינא ב\n\n============================================================\n\nSOURCE: Turei Zahav on Shulchan Arukh, Yoreh De\'ah 1:4\nTEXT: בפני חכם ומומחים כו\'. ברמב"ם וטור לא כתוב ומומחה ונראה דרמ"א בא ללמדנו דתרתי בעינן ולא סגי ליטול קבלה מן המומחה בשחיטות לחוד רק מחכם בלא"ה ג"כ כי הוא יודע לנסותו היטב ואותן הנוטלים קבלה מן השוחטים שאינם חכמים בלאו הכי לא יפה הם עושים:\n\n============================================================\n\nSOURCE: Turei Zahav on Shulchan Arukh, Yoreh De\'ah 1:5\nTEXT: שיהיו שגורים בפיו. אע"פ דבשאר הוראות א"צ שידע המורה בע"פ כל ההוראות מ"מ בשחיטה שהיא מסורה לכל החמירו ונראה ראייה מלשון התלמוד באוקימתא דרבינא בלשון זה שיודעים בו שיודע לומר הלכות שחיטה האי לומר הוא לשון יתר לכאורה אלא דקמ"ל דצריך לומר ההלכות בעל פה וראינו רבים מתפרצים אין נותנים לב תמיד לחזור ההלכות ע"כ נהגו גדולים לחקור אחר השוחטים אף על פי שנטלו קבלה ולמוכיחים יונעם:\n\n============================================================\n\n\nExtract the EARLIER SOURCES they cite that are relevant to: behemah chezkat issur omedes - the presumption that an animal stands in a state of prohibition\n'}], 'model': 'claude-sonnet-4-20250514', 'system': 'You are a Torah scholar assistant that extracts earlier source citations from commentary texts.\n\nYou will be given texts from commentaries discussing a specific topic. Your job:\n1. Extract EARLIER SOURCES they cite (Gemara, Rishonim, base halachic texts)\n2. Count how many commentaries cite each source\n3. FILTER for relevance to the SPECIFIC topic\n\nCRITICAL - RELEVANCE FILTERING:\n- Only include sources that discuss THE SPECIFIC ASPECT of the query\n- If query is "chuppas niddah", DON\'T include sources about general chuppah\n- If query is "bitul chametz", DON\'T include sources about general chametz\n\nORIGINAL QUERY: beheima chezkas issur omedes\nINTERPRETED AS: behemah chezkat issur omedes - the presumption that an animal stands in a state of prohibition\n\nFor each commentary text, identify:\n- Which earlier sources it cites\n- Why those sources are relevant to THIS SPECIFIC TOPIC\n\nReturn JSON:\n{\n  "sources": [\n    {\n      "ref": "Gemara or Rishon reference",\n      "category": "Gemara/Rishonim/etc",\n      "citation_count": 2,\n      "relevance": "How this addresses the specific query"\n    }\n  ],\n  "summary": "Brief summary of the specific topic based on what the commentaries say"\n}\n\nIMPORTANT: If the commentary texts don\'t actually discuss the specific topic, return empty sources array.'}}
2025-12-02 09:34:49 | DEBUG    | anthropic._base_client:request:1045 | Sending HTTP Request: POST https://api.anthropic.com/v1/messages
2025-12-02 09:34:49 | DEBUG    | httpcore.connection:trace:47 | close.started
2025-12-02 09:34:49 | DEBUG    | httpcore.connection:trace:47 | close.complete
2025-12-02 09:34:49 | DEBUG    | httpcore.connection:trace:47 | connect_tcp.started host='api.anthropic.com' port=443 local_address=None timeout=5.0 socket_options=[(65535, 8, True), (6, 17, 60), (6, 16, 5), (6, 3, 60)]
2025-12-02 09:34:49 | DEBUG    | httpcore.connection:trace:47 | connect_tcp.complete return_value=<httpcore._backends.sync.SyncStream object at 0x000001F81B37B280>
2025-12-02 09:34:49 | DEBUG    | httpcore.connection:trace:47 | start_tls.started ssl_context=<ssl.SSLContext object at 0x000001F819E9CBC0> server_hostname='api.anthropic.com' timeout=5.0
2025-12-02 09:34:49 | DEBUG    | httpcore.connection:trace:47 | start_tls.complete return_value=<httpcore._backends.sync.SyncStream object at 0x000001F81B78F250>
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:trace:47 | send_request_headers.started request=<Request [b'POST']>
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:trace:47 | send_request_headers.complete
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:trace:47 | send_request_body.started request=<Request [b'POST']>
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:trace:47 | send_request_body.complete
2025-12-02 09:34:49 | DEBUG    | httpcore.http11:trace:47 | receive_response_headers.started request=<Request [b'POST']>
2025-12-02 09:34:56 | DEBUG    | httpcore.http11:trace:47 | receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Tue, 02 Dec 2025 14:34:56 GMT'), (b'Content-Type', b'application/json'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Content-Encoding', b'gzip'), (b'anthropic-ratelimit-input-tokens-limit', b'30000'), (b'anthropic-ratelimit-input-tokens-remaining', b'25000'), (b'anthropic-ratelimit-input-tokens-reset', b'2025-12-02T14:35:01Z'), (b'anthropic-ratelimit-output-tokens-limit', b'8000'), (b'anthropic-ratelimit-output-tokens-remaining', b'8000'), (b'anthropic-ratelimit-output-tokens-reset', b'2025-12-02T14:34:58Z'), (b'anthropic-ratelimit-requests-limit', b'50'), (b'anthropic-ratelimit-requests-remaining', b'49'), (b'anthropic-ratelimit-requests-reset', b'2025-12-02T14:34:50Z'), (b'retry-after', b'9'), (b'anthropic-ratelimit-tokens-limit', b'38000'), (b'anthropic-ratelimit-tokens-remaining', b'33000'), (b'anthropic-ratelimit-tokens-reset', b'2025-12-02T14:34:58Z'), (b'request-id', b'req_011CVi2VuVcBdxh6KDZihb6k'), (b'strict-transport-security', b'max-age=31536000; includeSubDomains; preload'), (b'anthropic-organization-id', b'73a09491-cda3-40b4-8544-d00ca1bc9331'), (b'x-envoy-upstream-service-time', b'6810'), (b'cf-cache-status', b'DYNAMIC'), (b'X-Robots-Tag', b'none'), (b'Server', b'cloudflare'), (b'CF-RAY', b'9a7b8c1b3b298be8-EWR')])
2025-12-02 09:34:56 | INFO     | httpx:_send_single_request:1025 | HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"
2025-12-02 09:34:56 | DEBUG    | httpcore.http11:trace:47 | receive_response_body.started request=<Request [b'POST']>
2025-12-02 09:34:56 | DEBUG    | httpcore.http11:trace:47 | receive_response_body.complete
2025-12-02 09:34:56 | DEBUG    | httpcore.http11:trace:47 | response_closed.started
2025-12-02 09:34:56 | DEBUG    | httpcore.http11:trace:47 | response_closed.complete
2025-12-02 09:34:56 | DEBUG    | anthropic._base_client:request:1083 | HTTP Response: POST https://api.anthropic.com/v1/messages "200 OK" Headers({'date': 'Tue, 02 Dec 2025 14:34:56 GMT', 'content-type': 'application/json', 'transfer-encoding': 'chunked', 'connection': 'keep-alive', 'content-encoding': 'gzip', 'anthropic-ratelimit-input-tokens-limit': '30000', 'anthropic-ratelimit-input-tokens-remaining': '25000', 'anthropic-ratelimit-input-tokens-reset': '2025-12-02T14:35:01Z', 'anthropic-ratelimit-output-tokens-limit': '8000', 'anthropic-ratelimit-output-tokens-remaining': '8000', 'anthropic-ratelimit-output-tokens-reset': '2025-12-02T14:34:58Z', 'anthropic-ratelimit-requests-limit': '50', 'anthropic-ratelimit-requests-remaining': '49', 'anthropic-ratelimit-requests-reset': '2025-12-02T14:34:50Z', 'retry-after': '9', 'anthropic-ratelimit-tokens-limit': '38000', 'anthropic-ratelimit-tokens-remaining': '33000', 'anthropic-ratelimit-tokens-reset': '2025-12-02T14:34:58Z', 'request-id': 'req_011CVi2VuVcBdxh6KDZihb6k', 'strict-transport-security': 'max-age=31536000; includeSubDomains; preload', 'anthropic-organization-id': '73a09491-cda3-40b4-8544-d00ca1bc9331', 'x-envoy-upstream-service-time': '6810', 'cf-cache-status': 'DYNAMIC', 'x-robots-tag': 'none', 'server': 'cloudflare', 'cf-ray': '9a7b8c1b3b298be8-EWR'})
2025-12-02 09:34:56 | DEBUG    | anthropic._base_client:request:1091 | request_id: req_011CVi2VuVcBdxh6KDZihb6k
2025-12-02 09:34:56 | DEBUG    | __main__:extract_citations_from_commentaries:787 |   Claude response: Looking through the provided commentary texts, I need to identify sources that specifically discuss "behemah chezkat issur omedes" - the presumption that an animal stands in a state of prohibition.

After carefully reviewing all the texts, I find that **none of the commentaries actually discuss this
2025-12-02 09:34:56 | DEBUG    | __main__:parse_claude_json:311 | ✓ Successfully parsed JSON
2025-12-02 09:34:56 | INFO     | __main__:extract_citations_from_commentaries:792 |   ✓ Extracted 0 sources:
2025-12-02 09:34:56 | INFO     | __main__:search_sources:933 | ================================================================================
2025-12-02 09:34:56 | INFO     | __main__:search_sources:934 | STAGE 4: FETCH TEXTS FOR EXTRACTED SOURCES
2025-12-02 09:34:56 | INFO     | __main__:search_sources:935 | ================================================================================
2025-12-02 09:34:56 | INFO     | __main__:search_sources:959 | ====================================================================================================
2025-12-02 09:34:56 | INFO     | __main__:search_sources:960 | SEARCH COMPLETE: Returning 0 sources
2025-12-02 09:34:56 | INFO     | __main__:search_sources:963 | ====================================================================================================
2025-12-02 18:48:28 | DEBUG    | httpcore.connection:trace:47 | close.started
2025-12-02 18:48:28 | DEBUG    | httpcore.connection:trace:47 | close.complete
2025-12-02 18:48:28 | DEBUG    | httpcore.connection:trace:47 | close.started
2025-12-02 18:48:28 | DEBUG    | httpcore.connection:trace:47 | close.complete
