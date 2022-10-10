"""Method to take CSV and format for upload to Mongo"""
import logging
from db.mongo_connector import MongoConnector
from db.consts import DB_SERVICES
from bson.objectid import ObjectId

# pylint: disable=R0902, R0912, R0913, R0914, R0915, E1101, E0611, W0108. W0702

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def log():
    """Logging Logger"""
    return logging.getLogger("upload_data")


# SCHEMA : [id, question, tag, frontend_tag]
QUESTIONS = [
    [
        1,
        """Is anyone scaring, threatening or hurting you or your children?""",
        [
            "Domestic Violence",
            "Shelter",
            "Family",
        ],
        "Family",
    ],
    [
        2,
        """Every family has fights.  What are fights like in your home?""",
        [
            "Domestic Violence",
            "Family",
            "Shelter",
        ],
        "Family",
    ],
    [
        3,
        """Do you ever skip or cut the dose of a medicine because of cost?""",
        [
            "Health Insurance",
            "Low Income",
        ],
        "Income",
    ],
    [
        4,
        """Do you and your family have health insurance?""",
        ["Health Insurance"],
        "Family",
    ],
    [
        5,
        """ Have you  NOT applied for AHCCCS, KidsCare, ACA insurance or other benefits? """,
        ["Health Insurance"],
        "Family",
    ],
    [
        6,
        """Are you pregnant?  If so, have you spoken to anyone about WIC?""",
        [
            "Family",
            "Health Insurance",
            "Public Benefits",
            "Low Income",
        ],
        "Women Health",
    ],
    [
        7,
        """If you have applied for assistance and been denied, have you filed an appeal?""",
        [
            "Pubic Benefits",
            "Social Security",
            "Low Income",
            "Child Support",
        ],
        "Income",
    ],
    [
        8,
        """Are you unemployed?""",
        ["Employment", "Public Benefits", "Low Income"],
        "Income",
    ],
    [
        9,
        """Do you always have enough food to eat?""",
        [
            "Public Benefits",
            "Food and Nutrition",
        ],
        "Food Insecurity",
    ],
    [
        10,
        """Are you receiving benefits from programs such as Cash Assistance or Food Stamps?""",
        [
            "Public Benefits",
            "Food and Nutrition",
            "Employment",
            "Low Income",
        ],
        "Income",
    ],
    [
        11,
        """In the last year, have you worried that food would run out before you got money to buy more?""",
        [
            "Public Benefits",
            "Food and Nutrition",
            "Employment",
            "Low Income",
        ],
        "Food Insecurity",
    ],
    [
        12,
        """Are you or anyone in your family >65, blind or disabled?""",
        [
            "Social Security",
            "Elder",
            "Disability",
        ],
        "Family",
    ],
    [
        13,
        """Have you applied for SSI /SSDI benefits?""",
        [
            "Social Security",
            "Public Benefits",
        ],
        "Income",
    ],
    [
        14,
        """Do you have concerns/problems with your home?""",
        [
            "Housing",
            "Public Benefits",
            "Shelter",
        ],
        "Home",
    ],
    [
        15,
        """Do you have any problems with your landlord?""",
        ["Housing", "Public Benefits"],
        "Home",
    ],
    [
        16,
        """Do you have mold, mice or roaches in your home?""",
        [
            "Housing",
            "Public Benefits",
        ],
        "Home",
    ],
    [
        17,
        """Was your home built before 1978?""",
        ["Housing", "Public Benefits"],
        "Home",
    ],
    [
        18,
        """Do you have peeling/chipping paint in your home?""",
        [
            "Housing",
            "Public Benefits",
        ],
        "Home",
    ],
    [
        19,
        """Do you have smoke and CO2 detectors?""",
        ["Housing", "Public Benefits"],
        "Home",
    ],
    [
        20,
        """How are your children doing in school?""",
        [
            "Education",
            "Family",
            "Adolescent",
            "Young Adult",
        ],
        "Children",
    ],
    [
        21,
        """Are they failing or struggling in any classes?""",
        [
            "Education",
            "Family",
            "Adolescent",
        ],
        "Children",
    ],
    [
        22,
        """Do they have problems getting along with other children or teachers?""",
        [
            "Education",
            "Family",
            "Adolescent",
            "Mental Health",
        ],
        "Children",
    ],
    [
        23,
        """How often do they miss school?""",
        ["Education", "Family", "Adolescent"],
        "Children",
    ],
    [
        24,
        """Does your child have a disability?""",
        [
            "Education",
            "Family",
            "Adolescent",
            "Disability",
            "Special Education",
        ],
        "Children",
    ],
    [
        25,
        """Has your child been evaluated for special education services?""",
        [
            "Education",
            "Family",
            "Adolescent",
            "Disability",
            "Special Education",
        ],
        "Children",
    ],
    [
        26,
        """Does your child have an Individual Education Program (IEP) or Section 504 plan?""",
        [
            "Education",
            "Family",
            "Adolescent",
            "Disability",
            "Special Education",
        ],
        "Children",
    ],
    [
        27,
        """Would you like to discuss any legal problems with an attorney at no cost?""",
        [
            "Legal Services",
            "Indigent",
        ],
        "",
    ],
    [28, """Identify as LBTQ?""", ["LGBTQ"], "Identity"],
    [29, """Identify as Indigent?""", ["Indigent"], "Identity"],
    [30, """Need transportation?""", ["Transportation"], "Income"],
]


def main():
    """
    Method to upload data from csv to Mongo and GeoCode with Google Maps API

    :return:
    """
    m = MongoConnector()
    collection = m.client.results.questions
    for doc in collection.find({}):
        collection.delete_one({"_id": ObjectId(doc["_id"])})
    data = QUESTIONS
    log().info("Size of Questions: %s", str(len(data)))
    clean_data = []
    for d in data:
        clean_data.append(
            {"id": d[0], "question": d[1], "tags": d[2], "main_tag": d[3]}
        )
    log().info(clean_data)
    ids = m.upload_results(
        db=DB_SERVICES["db"],
        collection="questions",
        data=clean_data,
        geo_index=False,
        key="id",
    )
    log().info(ids)


if __name__ == "__main__":
    main()
