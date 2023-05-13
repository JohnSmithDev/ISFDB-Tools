#!/usr/bin/env python3
"""
A list of tags/shelves/breadcrumbs/genres/sub-genres that are not relevant to
ISFDB.

NB: This will possibly not be used by any code elsewhere in this repo, but by
other projects that live elsewhere.  However, as it's very much tied to ISFDB,
it seems that this is a reasonable place for it to live.

TODO (maybe): Make this JSON for wider compatibility?  (So use " rather than ')

!!! Keep this all lower case and in alphabetic-ish order !!!
"""

ISFDB_IRRELEVANT_TAGS = {
    "advertising & society",

    "atlases"

    "biography: sport",
    "biography & autobiography / entertainment & performing arts",
    "biography & autobiography / general",
    "biography & autobiography / historical",
    "biography & autobiography / music",
    "biography & autobiography / military",
    "biography & autobiography / political",
    "biography & autobiography / presidents & heads of state",
    "biography & autobiography / personal memoirs",
    "biography & autobiography / mediacal (incl. patients)",
    "biography & autobiography / rich & famous",
    "biography & autobiography/science & technology",
    "biography & autobiography / sports",
    "biography & autobiography / survival",
    "biography & autobiography / women",
    "science, technology & medicine biographies",
    "science, technology & medicine autobiographies",
    "biography and true stories / true stories / true crime",
    "biography and true stories / biography: general / biography: historical",
    "autobiography: science",
    "business & industry biographies",
    "historical, political & military biographies",

    "business strategy", "business & management", "business",
    "business/economics", "economic history", "economics: professional & general",
    "business & economics",
    "business & economics/business mathematics",
    "business & economics / decision-making & problem solving",
    "business & ecomomics / economics / general",
    "business & ecomomics / entrepreneurship",
    "business & ecomomics / foreign exchange",
    "business & ecomomics / knowledge capital",
    "business & ecomomics / public finance",
    "business & ecomomics / research & development",
    "business innovation",
    "management: innovation",
    "anf: business and management",
    "popular economics",
    "macroeconomics",
    "entrepreneurship",

    "car racing", "automobile racing", "motor sports", "formula 1 & grand prix",

    "children's general non-fiction",
    "reference works (children's / teenage)",
    "child: non-fiction 5+",

    "computing: professional & programming", "computers / information technology",
    "anf: computers and it", "computers / internet / general",
    "technology / general issues",
    "technology & engineering",
    "technology & engineering/general",

    "internet: general works",
    "computers / software development & engineering / quality assurance & testing",
    "computers / programming / open source",
    "computers / intelligence (ai) & semantics",
    "computers / machine theory",
    "business & economics / industries / computers & information technology",

    "computers - languages / programming",
    "computer programming / software development",
    "computer programming",

    "conjuring & magic",

    "design / industrial",

    "emergency services", "accident & emergency nursing",

    "general cookery & recipes", "alcoholic drinks", "food & drink",
    "social science / agriculture & food", "cooking / health & healing / general",
    "cooking / essays & narratives",
    "cooking / methods / special appliances",
    "cooking / courses & dishes / soups & stews",

    "crime & mystery", "crime & mystery fiction", "crime",
    "fiction/mystery & detective - traditional",
    "fiction/mystery & detective - general",
    "fiction/mystery & detective - international mystery & crime",
    "fiction / mystery & detective - hard-boiled",

    "crime & criminology", "crime investigation & detection",
    "forensic science",

    "dictionaries (single language)", "reference / dictionaries",

    "historical geology", "natural history",

    "earth sciences", "geography", "environment", "law / land use",
    "environment",
    "natural history", "natural history: plants",
    "nature / plants / flowers", "nature / plants / trees",
    "nature / ecology", "applied ecology", "nature / animals / mammals",
    "life sciences / zoology and animal sciences / animal behaviour",
    "ecosystems & habitats",
    "nature / ecosystems & habitats / mountains",
    "nature / ecosystems & habitats / rivers",
    "the environment", "conservation of the environment",
    "pollution & threats to the environment",
    "botany & plant sciences", "zoology & animal sciences",
    "biology / life sciences", "mycology / fungi (non-medical)",
    "food & society",

    "entertainment & performing arts", "other performing arts",

    "family & relationships / death",
    "family & relationships / general",

    "fiction / romance / historical / 20th century",
    "fiction and related items / historical fiction",
    "historical romance", "sagas",
    "fiction / historical / general", "fiction / historical / world war ii",
    "fiction: general & literary",
    "fiction / general",
    "general & literary fiction",
    "modern & contemporary fiction",

    "individual film directors", "film-makers",
    "performing arts / film /general",

    "games & activities / quizzes",
    "games & activities / trivia",
    "games & activities/trivia",
    "games / trivia",
    "sport and leisure / hobbies",

    "great britain/british isles", "britain & ireland",

    "health & fitness / healthy living", "health & fitness / longetivity",
    "health & fitness / women's health", "health & fitness / pregnancy & childbirth",
    "health care issues",
    "health & well being",
    "medical / general", "medical / infectious diseases",
    "medical / clinical medicine", "health & fitness",
    "medicine: general issues",
    "popular medicine & health",
    "technology & medicine",


    "history", "historical events & topics", "general & world history",
    "anf: history",

    "historical periods", "history / general",
    "postwar 20th century history: 1945 to 2000", "history / world",
    "postwar 20th century history",
    "history / expeditions & discoveries",
    "history / essays",
    "20th century history: 1900 to 2000",
    "early modern history: 1500 to 1700",

    "british & irish history", "history / europe / great britain",
    "history / europe / ireland",
    "history / europe / great britain / 21st century",
    "humanities / history / history: earliest times to present day / early history: c. 500 to c. 1450/1500",
    "humanities / history / regional and national history / european history / british and irish history",

    "history / russia & the former soviet union",
    "european history", "history / europe / general",
    "history / europe / germany",

    "history / united states / general",
    "united states - social conditions - 21st century",
    "united states - social life and customs - 21st century",
    "travel / united states / general",

    "biography & autobiography / historical", "autobiography: historical",

    "history / asia / japan",

    "history / africa / north", "history / africa / east",
    "history / modern / 20th century",
    "history / middle east / iraq",
    "history / middle east / arabian peninsular",
    "history / middle east / turkey & ottoman empire",
    "history / asia / japan",
    "history / modern / 21st century",
    "history & theory",
    "literary collections / middle eastern",

    "history / military / world war ii",
    "history / military / naval",

    "housing & homelessness",

    "humor / form / essays",
    "humor / topic / internet & social media",
    "humor / topic / politics",
    "humor/topic - politics",
    "sport and leisure / humour",
    "humor / form / comic strips & cartoons", "humor / form / trivia",
    "humor / general",

    "industry & industrial studies",
    "mining industry", "mining technology & engineering",
    "energy industries & utilities",

    "information technology industries", "social networking", "social network",
    "internet advertising", "e-commerce", "internet - general",
    "business & economics / industries / computers & information technology",
    "computing and information technology / digital lifestyle",
    "computers / social aspects", "computing & information technology",
    "microcomputers - history",
    "computers / natural language processing",
    "computing and information technology / computer science / artifical intelligence",
    "science & technology",

    "international human rights law", "law / general", "legal history"

    "language arts & disciplines / grammar",
    "language arts & disciplines / vocabulary",
    "language / language: reference and general / writing and editing guides",
    "language: history & general works", "english language - etymology",
    "reference / word lists", "reference / language",
    "language / reference & general",
    "language learning: self study", "language learning: grammar",
    "language learning: reading skills",
    "grammar & vocabulary",
    "language / language teaching and learning (other than ELT) / " # note continuation
    "language teaching and learning material and coursework / grammar and vocabulary",

    "greater london",

    "management", "finance", "decision making",

    "military intelligence", "military - aviation", "military history",
    "wars & conflicts (other)", "history / military / united states",
    "history / military / general", "history / military / special forces",
    "military / korean war", "war & defence operations",
    "history / military / world war ii", "history / military / world war i",
    "aerospace & aviation technology", "post-ww2 conflicts",


    "music / individual composer & musician", "rock & pop music",
    "composers & songwriters", "individual composers & musicians",
    "music styles & genres", "specific bands & groups",
    "music / history & criticism", "music / discography & buyer's guides",

    "new south wales",

    "philosophy", "philosophy & social aspects", "philosophy: logic",
    "ancient philosophy", "anf: philosophy",
    "science / philosophy & social aspects",

    "poetry, drama & criticism",

    "police in mass media", "police & security services",

    "topic - politics",
    "government & constitution",
    "politics/intl relations", "political leaders & leadership",
    "politics & government", "political corruption",
    "international relations",
    "anf: politics and government",
    "society and social sciences / politics and government",
    "political science & theory",
    "political science",
    "political science/comparative politics",
    "political science / essays",
    "political science / general",
    "political science / history & theory",
    "political science / intelligence & espionage",
    "political science / political process / elections",
    "political science / political political economy",
    "political science / political process / political parties",
    "political science / political process / political parties",
    "political science / political ideologies / nationalism & patriotism",
    "political science / political economy",
    "political science / political freedom",
    "political science / public affairs & administration",
    "political science / terrorism",
    "political science / world / middle eastern",
    "political science / world / european",
    "social science / social work", "social work",
    "social science / developing & emerging countries",
    "political control & freedoms",
    "anf: society", "social discrimination & equal treatment",
    "espionage & secret services",
    "political consultants - humor", "political science - humor",
    "political satire",
    "political activism",
    "comparative politics",
    "politics, society & education",
    "social theory", "globalisation",
    "democracy",

    "great britain/politics and government",
    "american government", "government & constitution",

    "press & journalism", "media studies", "anf: media studies",
    "social science / media studies",

    "psychology", "sociology",
    "social psychology",
    "psychological testing & measurement", "popular psychology",
    "group or collective psychology", "sociology - general",
    "psychology / creative ability", "science / cognitive science",
    "philosophy: free will & determinism",
    "psychology / mental health",
    "psychology / cognitive psychology & cognition",

    "privacy & data protection",
    "social science / privacy & surveillance",
    "social science / criminology",

    "religion / religion", "religion: comparative",
    "history of religion",

    "contemporary romance",

    "popular science", "science: general issues", "mathematics & science",
    "popular mathematics", "probability & statistics",
    "anf: popular science and mathematics",
    "testing & measurement", "science / history", "science / ethics",
    "mathematics / general",

    "science / general",
    "science / life sciences / evolution",
    "science / life sciences / biophysics",
    "science / life sciences / biology",
    "science / life sciences / developmental biology",
    "science/math",
    "science - miscellanea",
    "science / physics / quantum theory",
    "science / physics / general",
    "science/research & methodology",
    "botany & plant sciences", "mycology / fungi (non-medical)", "biology / life sciences",
    "zoology & animal sciences", "science, technology & medicine",

    "life sciences",
    "life sciences - general",
    "natural history: general",
    "popular science",


    "self-help / general",

    "anf: skills for life",

    "social activists", "social movements",

    "society & culture", "cultural studies",
    "social science / anthropology / cultural & social",
    "social science / social classes",
    "social science / women's studies", "social science / feminism & feminist theory",
    "social science / sociology / general",
    "social & ethical issues",
    "society & culture: general",
    "corruption in society",
    "social & ethical issues", "social issues & processes",
    "social classes & economic disparity",
    "social & cultural history", "social & cultural studies",
    "social discrimination & inequality",
    "social mobility",

    "spiritualism", "self-help",
    "mind & spirit: mindfulness & meditation",

    "sports training & coaching", "sports books",
    "sports psychology", "the sports book awards",

    "teaching staff", "secondary schools", "classroom management",
    "teaching skills & techniques", "study & teaching",


    "television - history & criticism",
    "stage & screen / television",
    "performing arts / television / history & criticism",

    "thriller & adventure",

    "travel / general", "travel & holiday",

    "anf: transport", "transport industries",

    "true crime / espionage", "true crime / organized crime",
    "true crime",

    "virus / corona virus",

    "creative writing & creative writing guides",
    "usage & writing guides"
    }


# The 'relevant' tags are (probably) only going to be used when there are
# authors/works with both types; some TBD algorithm will determine which side
# wins out.
# Again, keep these in (roughly) alphabetic order
ISFDB_RELEVANT_TAGS = {
    "alternative history fiction",

    "fantasy",
    "af: fantasy",
    "fiction / fantasy / historical",
    "historical fantasy"

    "fairy tales",
    "fiction / fairy tales",

    "legends & mythology",
    "myths and legends",
    "myths & legends",

    "science fiction",

    "science fiction, fantasy & horror",
    "science fiction & fantasy",
    "sf, fantasy & horror",

    "speculative fiction",

    "urban fantasy",
    "fiction / fantasy / contemporary",
    "fiction / fantasy / urban"
    }
