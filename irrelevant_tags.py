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
    "biography & autobiography / survival",
    "science, technology & medicine biographies",
    "science, technology & medicine autobiographies",
    "biography and true stories / true stories / true crime",
    "biography and true stories / biography: general / biography: historical",
    "autobiography: science",

    "business strategy", "business & management", "business",
    "business/economics", "economic history", "economics: professional & general",
    "business & economics",
    "business & economics / decision-making & problem solving",
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

    "car racing", "automobile racing", "motor sports", "formula 1 & grand prix",

    "children's general non-fiction",
    "reference works (children's / teenage)",
    "child: non-fiction 5+",

    "computing: professional & programming", "computers / information technology",
    "anf: computers and it", "computers / internet / general",
    "technology / general issues", "internet: general works",
    "computers / software development & engineering / quality assurance & testing",
    "computers / programming / open source",
    "computers / intelligence (ai) & semantics",
    "computers / machine theory",
    "business & economics / industries / computers & information technology",
    "computers - languages / programming",
    "computer programming / software development",
    "computer programming",

    "conjuring & magic",

    "emergency services", "accident & emergency nursing",

    "general cookery & recipes", "alcoholic drinks", "food & drink",
    "social science / agriculture & food", "cooking / health & healing / general",
    "cooking / essays & narratives",

    "crime & mystery", "crime & mystery fiction", "crime",
    "fiction/mystery & detective - traditional",
    "fiction/mystery & detective - general",
    "fiction/mystery & detective - international mystery & crime",
    "fiction / mystery & detective - hard-boiled",

    "dictionaries (single language)", "reference / dictionaries",

    "historical geology", "natural history",

    "earth sciences", "geography", "environment", "law / land use",
    "environment",
    "natural history", "natural history: plants",
    "nature / plants / flowers", "nature / plants / trees",
    "nature / ecology", "applied ecology", "nature / animals / mammals",
    "life sciences / zoology and animal sciences / animal behaviour",
    "science / life sciences / biophysics",
    "science / life sciences / biology",
    "science / life sciences / developmental biology",
    "science / physics / quantum theory",

    "entertainment & performing arts", "other performing arts",

    "family & relationships / death",
    "family & relationships / general",

    "fiction / romance / historical / 20th century",
    "fiction and related items / historical fiction",
    "fiction / historical / general", "fiction / historical / world war ii",
    "fiction: general & literary",
    "fiction / general",
    "general & literary fiction",
    "modern & contemporary fiction",

    "individual film directors", "film-makers",
    "performing arts / film /general",

    "great britain/british isles",

    "health & fitness / healthy living", "health & fitness / longetivity",
    "health & fitness / women's health", "health & fitness / pregnancy & childbirth",
    "health care issues",
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

    "history / africa / north", "history / africa / east",
    "history / middle east / iraq",
    "history / middle east / arabian peninsular",
    "history / asia / japan",
    "history / modern / 20th century",
    "history / modern / 21st century",
    "history & theory",

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


    "music / individual composer & musician", "rock & pop music",
    "composers & songwriters", "individual composers & musicians",
    "music styles & genres", "specific bands & groups",
    "music / history & criticism", "music / discography & buyer's guides",

    "new south wales",

    "philosophy", "philosophy & social aspects", "philosophy: logic",
    "ancient philosophy", "anf: philosophy",

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
    "political control & freedoms",
    "anf: society", "social discrimination & equal treatment",
    "espionage & secret services",
    "political consultants - humor", "political science - humor",
    "political satire",
    "political activism",

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

    "science / life sciences / evolution", "popular science",
    "science / general", "life sciences",
    "science / physics / quantum theory",
    "science / physics / general",
    "life sciences - general",
    "science - miscellanea",

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
