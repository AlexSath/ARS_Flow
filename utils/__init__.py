from .color_palettes import *

GENES_OF_INTEREST = [
    "DNMT3A",
    "DNMT3AP1",
    "DNMT3L",
    "DNMT3B",
    "CD47",
    "CD55",
    "CD81",
    "CD151",
    "B2M",
    "KIT"
]

SCREEN_GENES = {
    "LX2 hits": [
        "SMAD3", # Daniel LX-2 screen hit
        "NFX1", # Daniel LX-2 screen hit
        "GPX4", # Daniel LX-2 screen hit
        "ESYT2", # Daniel LX-2 screen hit
        "LAMTOR1", # Daniel LX-2 screen hit
        "ZNF259", # Daniel LX-2 screen hit
        "PFKFB3", # Daniel LX-2 screen hit
        "C16orf87", # proposed renamed HDIP for HDAC-interacting protein, Daniel LX-2 screen hit
    ],
    "LX2 below thresh": [ # Daniel LX-2 screen below threshold
        "SMAD4", 
        "FOXO3",
        "HOXA3",
        "MEOX1", 
        "BRD2", 
        "MYH9",
        "CCN2", # aka Ctgf
        "TGFB1",
        "ZSCAN21",
        "ZNF559",
        "ZNF330",
    ],
    "LX2 screen enriched": [
        "MTHFD2", # Daniel screen enriched
        "ZNF567", # Daniel screen enriched
        "NUPL1", # Daniel screen enriched
    ],
}

FIBROSIS_GENES = [
    "TILAM",
    "POSTN",
    "JUNB",
    "GATA4",
    "GATA6",
    "TP73",
    "FOXC2",
    "SERPINE1",
    "ACTA1",
    "YAP1",
    "LTBP2",
    "WWTR1", # TAZ, another supposed mechanosensitive transcription factor
    "TGFBR1",
    "TGFBR2",
    "BRD3",
    "BRD4",
    "BRDT",
    "COL1A1",
    "SPI1", # see "PU.1 controls fibroblast..." (2019)
    "SMAD2",
]