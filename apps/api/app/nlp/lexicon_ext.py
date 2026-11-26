"""Expanded vocabulary for the local extractor: common OPD/ward conditions and drugs beyond the v1 lexicon.

Curated by hand (no external download). Entries are general clinical vocabulary, not tuned to individual notes.
"""

from __future__ import annotations

# (pattern, ICD-10, description) — checked BEFORE the v1 list, so more specific phrases win.
EXTRA_CONDITIONS: list[tuple[str, str | None, str | None]] = [
    # Phrases that look like a condition but aren't one (code None = consume the span, record nothing).
    (r"\bst[- ](?:segment\s+)?(?:depression|elevation)s?\b", None, None),
    (r"iron[- ]deficiency an(?:a)?emia|\bida\b", "D50.9", "Iron deficiency anaemia"),
    (r"b12 deficiency|vitamin b12 (?:deficiency|low)|(?:b12|cobalamin) (?:is |also )?low", "E53.8", "Vitamin B12 deficiency"),
    (r"vitamin d deficiency|vit(?:amin)? d (?:deficiency|insufficiency)", "E55.9", "Vitamin D deficiency"),
    (r"hypokal(?:a)?emia|potassium (?:is |was )?low|low potassium", "E87.6", "Hypokalaemia"),
    (r"hyperkal(?:a)?emia", "E87.5", "Hyperkalaemia"),
    (r"\bbph\b|benign prostatic hyperplasia|prostatic enlargement", "N40.0", "Benign prostatic hyperplasia"),
    (r"\baki\b|acute kidney injury", "N17.9", "Acute kidney injury"),
    (r"kidney stone|renal (?:calculus|stone)|nephrolithiasis|urolithiasis", "N20.0", "Kidney stone"),
    (r"\bdka\b|diabetic ketoacidosis", "E10.10", "Diabetic ketoacidosis"),
    (r"duodenal ulcer", "K26.9", "Duodenal ulcer"),
    (r"gastric ulcer", "K25.9", "Gastric ulcer"),
    (r"peptic ulcer", "K27.9", "Peptic ulcer"),
    (r"dyspepsia", "K30", "Functional dyspepsia"),
    (r"gastritis", "K29.70", "Gastritis"),
    (r"\bibs\b|irritable bowel", "K58.9", "Irritable bowel syndrome"),
    (r"fatty liver|\bnafld\b|\bmasld\b|hepatic steatosis", "K76.0", "Fatty liver disease"),
    (r"hepatitis b|\bhbv\b", "B18.1", "Chronic hepatitis B"),
    (r"hepatitis c|\bhcv\b", "B18.2", "Chronic hepatitis C"),
    (r"\bhiv\b", "B20", "HIV disease"),
    (r"allergic rhinitis|hay fever", "J30.9", "Allergic rhinitis"),
    (r"sinusitis", "J32.9", "Chronic sinusitis"),
    (r"tonsillitis|pharyngitis", "J02.9", "Pharyngitis/tonsillitis"),
    (r"bronchitis", "J20.9", "Acute bronchitis"),
    (r"\burti\b|upper respiratory (?:tract )?infection", "J06.9", "Upper respiratory infection"),
    (r"tinea\s*\w*|ringworm|dermatophytosis", "B35.9", "Dermatophytosis (tinea)"),
    (r"eczema|atopic dermatitis", "L30.9", "Eczema"),
    (r"urticaria|hives", "L50.9", "Urticaria"),
    (r"\bacne\b", "L70.0", "Acne"),
    (r"cellulitis", "L03.90", "Cellulitis"),
    (r"scabies", "B86", "Scabies"),
    (r"osteoporosis", "M81.0", "Osteoporosis"),
    (r"low back pain|\blbp\b|lumbago", "M54.50", "Low back pain"),
    (r"sciatica", "M54.30", "Sciatica"),
    (r"frozen shoulder|adhesive capsulitis", "M75.00", "Frozen shoulder"),
    (r"vertigo|\bbppv\b", "R42", "Vertigo"),
    (r"insomnia", "G47.00", "Insomnia"),
    (r"\bpcos\b|polycystic ovar", "E28.2", "Polycystic ovary syndrome"),
    (r"glaucoma", "H40.9", "Glaucoma"),
    (r"cataract", "H26.9", "Cataract"),
    (r"conjunctivitis", "H10.9", "Conjunctivitis"),
    (r"otitis media", "H66.90", "Otitis media"),
    (r"\bdvt\b|deep vein thrombosis", "I82.409", "Deep vein thrombosis"),
    (r"pulmonary embolism|(?-i:\bPE\b)", "I26.99", "Pulmonary embolism"),
    (r"peripheral (?:arterial|vascular) disease|\bpad\b", "I73.9", "Peripheral arterial disease"),
    (r"\btia\b|transient isch(?:a)?emic attack", "G45.9", "Transient ischaemic attack"),
    (r"alzheimer'?s?", "G30.9", "Alzheimer's disease"),
    (r"typhoid|enteric fever", "A01.00", "Typhoid fever"),
    (r"chikungunya", "A92.0", "Chikungunya"),
    (r"covid(?:-?19)?", "U07.1", "COVID-19"),
    (r"sepsis", "A41.9", "Sepsis"),
    (r"hyperuric(?:a)?emia", "E79.0", "Hyperuricaemia"),
    (r"schizophrenia", "F20.9", "Schizophrenia"),
    (r"bipolar", "F31.9", "Bipolar disorder"),
    (r"alcohol (?:use disorder|dependence)", "F10.20", "Alcohol dependence"),
]

EXTRA_GENERICS = {
    # cardiovascular / renal
    "nebivolol", "labetalol", "nifedipine", "diltiazem", "verapamil", "prazosin", "clonidine", "hydralazine",
    "telmisartan-amlodipine", "olmesartan-amlodipine", "valsartan", "sacubitril-valsartan", "ivabradine", "digoxin",
    "amiodarone", "ranolazine", "trimetazidine", "fenofibrate", "ezetimibe", "eplerenone", "dabigatran",
    "enoxaparin", "torsemide", "metolazone", "potassium chloride", "sodium bicarbonate", "sevelamer", "calcitriol",
    # endocrine
    "glibenclamide", "voglibose", "acarbose", "saxagliptin", "canagliflozin", "liraglutide", "semaglutide",
    "dulaglutide", "insulin detemir", "insulin degludec", "carbimazole", "methimazole", "propylthiouracil",
    "hydrocortisone", "dexamethasone", "methylprednisolone", "cholecalciferol", "ergocalciferol", "vitamin e",
    "vitamin b12", "methylcobalamin", "ferrous sulphate", "ferrous fumarate", "ferrous ascorbate", "zinc",
    # respiratory / allergy
    "ipratropium", "levosalbutamol", "budesonide", "fluticasone", "formoterol", "salmeterol", "theophylline",
    "doxofylline", "cetirizine", "levocetirizine", "fexofenadine", "loratadine", "chlorpheniramine",
    "diphenhydramine", "dextromethorphan", "ambroxol", "acetylcysteine",
    # GI
    "esomeprazole", "lansoprazole", "famotidine", "ranitidine", "sucralfate", "itopride", "mosapride",
    "lactulose", "bisacodyl", "loperamide", "mesalamine", "ursodeoxycholic acid", "rifaximin",
    # anti-infectives
    "cefixime", "cefuroxime", "cefpodoxime", "cephalexin", "clarithromycin", "levofloxacin", "ofloxacin",
    "norfloxacin", "linezolid", "vancomycin", "piperacillin-tazobactam", "meropenem", "clindamycin",
    "cotrimoxazole", "fluconazole", "itraconazole", "terbinafine", "clotrimazole", "luliconazole", "ketoconazole",
    "acyclovir", "valacyclovir", "oseltamivir", "albendazole", "ivermectin", "artesunate", "chloroquine",
    "isoniazid", "rifampicin", "pyrazinamide", "ethambutol", "pyridoxine", "tenofovir", "permethrin",
    # neuro / psych / pain
    "pregabalin", "gabapentin", "duloxetine", "venlafaxine", "mirtazapine", "paroxetine", "citalopram",
    "clonazepam", "lorazepam", "diazepam", "quetiapine", "olanzapine", "risperidone", "haloperidol",
    "aripiprazole", "lithium", "valproate", "sodium valproate", "carbamazepine", "phenytoin", "lamotrigine",
    "topiramate", "donepezil", "memantine", "rivastigmine", "ropinirole", "pramipexole", "betahistine",
    "cinnarizine", "flunarizine", "naproxen", "aceclofenac", "etoricoxib", "mefenamic acid", "ketorolac",
    "morphine", "tapentadol", "thiocolchicoside", "baclofen", "tizanidine",
    # urology / others
    "tamsulosin", "silodosin", "finasteride", "dutasteride", "solifenacin", "tadalafil", "sildenafil",
    "letrozole", "clomiphene", "progesterone", "medroxyprogesterone", "tranexamic acid", "warfarin",
    "methotrexate", "leflunomide", "sulfasalazine", "azathioprine", "tacrolimus", "mycophenolate",
    "isotretinoin", "tretinoin", "adapalene", "benzoyl peroxide", "mupirocin", "fusidic acid", "minoxidil",
    "timolol", "latanoprost", "ondansetron", "metoclopramide",
}

EXTRA_ALIASES = {
    "thyroxine": "levothyroxine", "eltroxin": "levothyroxine", "jalra": "vildagliptin", "galvus": "vildagliptin",
    "duolin": "ipratropium-levosalbutamol", "montair": "montelukast", "allegra": "fexofenadine", "zyrtec": "cetirizine",
    "okacet": "cetirizine", "rantac": "ranitidine", "omez": "omeprazole", "razo": "rabeprazole", "nexpro": "esomeprazole",
    "taxim": "cefixime", "azee": "azithromycin", "zifi": "cefixime", "oflox": "ofloxacin", "flagyl": "metronidazole",
    "metrogyl": "metronidazole", "septran": "cotrimoxazole", "combiflam": "ibuprofen-paracetamol", "voveran": "diclofenac",
    "ultracet": "tramadol-paracetamol", "lyrica": "pregabalin", "nexito": "escitalopram", "urimax": "tamsulosin",
    "uprise": "cholecalciferol", "d-rise": "cholecalciferol", "shelcal": "calcium-vitamin d", "neurobion": "vitamin b12",
    "mecobalamin": "methylcobalamin", "ipravent": "ipratropium", "budecort": "budesonide", "levolin": "levosalbutamol",
    "mixtard": "insulin", "human mixtard": "insulin", "huminsulin": "insulin", "actrapid": "insulin",
    "tresiba": "insulin degludec", "levemir": "insulin detemir", "ozempic": "semaglutide", "jardiance": "empagliflozin",
    "forxiga": "dapagliflozin", "xarelto": "rivaroxaban", "eliquis": "apixaban", "pradaxa": "dabigatran",
    "clexane": "enoxaparin", "lmwh": "enoxaparin", "plavix": "clopidogrel", "brilinta": "ticagrelor",
    "storvas": "atorvastatin", "crestor": "rosuvastatin", "concor": "bisoprolol", "nebicard": "nebivolol",
    "cilacar": "cilnidipine", "aldactone": "spironolactone", "dytor": "torsemide", "zyloric": "allopurinol",
    "febuget": "febuxostat", "hcqs": "hydroxychloroquine", "folvite": "folic acid", "wysolone": "prednisolone",
    "omnacortil": "prednisolone", "dexona": "dexamethasone", "emeset": "ondansetron", "perinorm": "metoclopramide",
    "cremaffin": "lactulose", "dulcolax": "bisacodyl", "udiliv": "ursodeoxycholic acid", "udca": "ursodeoxycholic acid",
    "kcl": "potassium chloride", "inh": "isoniazid", "rif": "rifampicin", "vit d3": "cholecalciferol",
    "vitamin d3": "cholecalciferol", "vit e": "vitamin e", "vit b12": "vitamin b12", "b12": "vitamin b12",
    "iron": "ferrous sulphate", "ferrous sulfate": "ferrous sulphate",
}

# Words that may precede a dose but are never drugs (stops the unknown-drug heuristic misfiring).
NON_DRUG_WORDS = {
    "dose", "doses", "total", "daily", "about", "after", "before", "patient", "weight", "height", "level", "levels",
    "intake", "units", "insulin", "sugar", "sugars", "glucose", "calorie", "calories", "protein", "sodium", "salt",
    "fluid", "fluids", "water", "volume", "output", "urine", "blood", "loss", "gain", "weekly", "monthly", "morning",
    "evening", "night", "every", "least", "maximum", "minimum", "upto", "around", "approx", "approximately",
    "creatinine", "hemoglobin", "haemoglobin", "albumin", "potassium", "calcium", "vitamin", "platelets", "count",
}
