from pydantic import BaseModel, Field
from typing import Literal, Optional
from pathlib import Path
from loguru import logger
import hashlib
import json

# 1. The Schema for our Chunks
class ChunkMetadata(BaseModel):
    source_file: str
    title: str
    domain: Literal["medical", "fitness", "nutrition"]
    subdomain: str
    edition: Optional[str] = None
    publication_year: Optional[int] = None
    page_number: Optional[int] = None
    content_type: Literal["prose", "table", "figure", "algorithm"] = "prose"
    chunk_hash: str

# 2. The Registry (Auto-generated from _file_index.csv)
SOURCE_REGISTRY = {
    "PUSH PULL LEGS - JEFF NIPPARD - HYPERTROPHY PROGRAM.pdf": {
        "title": "PUSH PULL LEGS - JEFF NIPPARD - HYPERTROPHY PROGRAM",
        "domain": "fitness",
        "subdomain": "hypertrophy_program",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Appendices Glossary and Index.PDF": {
        "title": "ACE- T - Appendices Glossary and Index",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch1 - Exercise Science.PDF": {
        "title": "ACE- T - Ch1 - Exercise Science",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch10 - Flexibility.PDF": {
        "title": "ACE- T - Ch10 - Flexibility",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch11 - Programming for the Healthy Adult.PDF": {
        "title": "ACE- T - Ch11 - Programming for the Healthy Adult",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch12 - Special Populations and Health Concerns.PDF": {
        "title": "ACE- T - Ch12 - Special Populations and Health Concerns",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch13 - Principles of Adherence and Motivation.PDF": {
        "title": "ACE- T - Ch13 - Principles of Adherence and Motivation",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch14 - Communication and Teaching Techniques.PDF": {
        "title": "ACE- T - Ch14 - Communication and Teaching Techniques",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch16 - Muscuoskeletal Injuries.PDF": {
        "title": "ACE- T - Ch16 - Muscuoskeletal Injuries",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch17 - Emergency Procedures.PDF": {
        "title": "ACE- T - Ch17 - Emergency Procedures",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch2 - Human Anatomy.PDF": {
        "title": "ACE- T - Ch2 - Human Anatomy",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch3 - Biomechanics and Applied Kinesiology.PDF": {
        "title": "ACE- T - Ch3 - Biomechanics and Applied Kinesiology",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch4 - Nutrition.PDF": {
        "title": "ACE- T - Ch4 - Nutrition",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch5 - Health Screening.PDF": {
        "title": "ACE- T - Ch5 - Health Screening",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch6 - Testing and Evaluation.PDF": {
        "title": "ACE- T - Ch6 - Testing and Evaluation",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch7 Cardiorespiratory Fitness and Exercise.PDF": {
        "title": "ACE- T - Ch7 Cardiorespiratory Fitness and Exercise",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch8 - Musclar Strength and Endurance.PDF": {
        "title": "ACE- T - Ch8 - Musclar Strength and Endurance",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Ch9 - Strength Training Program Design.PDF": {
        "title": "ACE- T - Ch9 - Strength Training Program Design",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Intro and Table of Contents.PDF": {
        "title": "ACE- T - Intro and Table of Contents",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Review Answers.pdf": {
        "title": "ACE- T - Review Answers",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Review Ch1 to Ch9.PDF": {
        "title": "ACE- T - Review Ch1 to Ch9",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE-_T - Review Ch10 to Ch18.PDF": {
        "title": "ACE- T - Review Ch10 to Ch18",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE_PT4th_Manual_Ch1.pdf": {
        "title": "ACE PT4th Manual Ch1",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": "4th",
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE_T_Ch15_Basics_of_Behavior_Change_and_Health_Psychology.PDF": {
        "title": "ACE T Ch15 Basics of Behavior Change and Health Psychology",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACE_T_Ch18_Legal_Guidlines_and_Professional_Responsibilities.PDF": {
        "title": "ACE T Ch18 Legal Guidlines and Professional Responsibilities",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACSM Exercise Testing and Prescription (2018).pdf": {
        "title": "ACSM Exercise Testing and Prescription (2018)",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": 2018,
        "parser_strategy": "pymupdf"
    },
    "ACSM Resources for Personal Trainer-Thompson et al.pdf": {
        "title": "ACSM Resources for Personal Trainer-Thompson et al",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACSM_Cardiopulmonary_Exercise_testing_in_Children_and_Adolescents.pdf": {
        "title": "ACSM Cardiopulmonary Exercise testing in Children and Adolescents",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACSM_Personal_Trainer_2017_The_Crammer_s_Ultimate_Exam_Prep!_Alexa.pdf": {
        "title": "ACSM Personal Trainer 2017 The Crammer s Ultimate Exam Prep! Alexa",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": 2017,
        "parser_strategy": "pymupdf"
    },
    "ACSM_s Advanced Exercise Physiology.pdf": {
        "title": "ACSM s Advanced Exercise Physiology",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACSM_s Foundations of Strength Training and Conditioning.pdf": {
        "title": "ACSM s Foundations of Strength Training and Conditioning",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACSM_s_Advanced_Exercise_Physiology,_2e_Peter_A_Farrell,_Michael.pdf": {
        "title": "ACSM s Advanced Exercise Physiology, 2e Peter A Farrell, Michael",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACSM_s_Complete_Guide_to_Fitness_Health,_2nd_Edition_149253367X.pdf": {
        "title": "ACSM s Complete Guide to Fitness Health, 2nd Edition 149253367X",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": "2nd",
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACSM_s_Guidelines_for_Exercise_Testing_and_Prescription_9th_edition.pdf": {
        "title": "ACSM s Guidelines for Exercise Testing and Prescription 9th edition",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": "9th",
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACSM_s_Resources_for_the_Person_American_College_of_Sports_Medicine.pdf": {
        "title": "ACSM s Resources for the Person American College of Sports Medicine",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "ACSMs Guide to Exercise Testing and Prescription.pdf": {
        "title": "ACSMs Guide to Exercise Testing and Prescription",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Churchills Pocketbook of Differential Diagnosis.pdf": {
        "title": "Churchills Pocketbook of Differential Diagnosis",
        "domain": "medical",
        "subdomain": "diagnosis",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "Macleod\u2019s Clinical Diagnosis 2nd ed.pdf": {
        "title": "Macleod\u2019s Clinical Diagnosis 2nd ed",
        "domain": "medical",
        "subdomain": "diagnosis",
        "edition": "2nd",
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "Oxford Handbook of Clinical Diagnosis 3rd Ed.pdf": {
        "title": "Oxford Handbook of Clinical Diagnosis 3rd Ed",
        "domain": "medical",
        "subdomain": "diagnosis",
        "edition": "3rd",
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "Layne_Norton_PHAT___Power_Hypertrophy_Adaptive_Training.pdf": {
        "title": "Layne Norton PHAT   Power Hypertrophy Adaptive Training",
        "domain": "fitness",
        "subdomain": "hypertrophy",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "150 ECG Cases (Hampton) 5 ed (2019).pdf": {
        "title": "150 ECG Cases (Hampton) 5 ed (2019)",
        "domain": "medical",
        "subdomain": "cardiology",
        "edition": None,
        "publication_year": 2019,
        "parser_strategy": "unstructured"
    },
    "Goldberger's_Clinical_Electrocardiography_A_Simplified_Approach.pdf": {
        "title": "Goldberger's Clinical Electrocardiography A Simplified Approach",
        "domain": "medical",
        "subdomain": "cardiology",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "The-ECG-Made-Easy-9th-Edition.pdf": {
        "title": "The-ECG-Made-Easy-9th-Edition",
        "domain": "medical",
        "subdomain": "cardiology",
        "edition": "9th",
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "Oxford Handbook of Acute Medicine 4th Edition 2019.pdf": {
        "title": "Oxford Handbook of Acute Medicine 4th Edition 2019",
        "domain": "medical",
        "subdomain": "emergency",
        "edition": "4th",
        "publication_year": 2019,
        "parser_strategy": "unstructured"
    },
    "Oxford Handbook of Emergency Medicine 5th Edition 2020.pdf": {
        "title": "Oxford Handbook of Emergency Medicine 5th Edition 2020",
        "domain": "medical",
        "subdomain": "emergency",
        "edition": "5th",
        "publication_year": 2020,
        "parser_strategy": "unstructured"
    },
    "Allam's Clinical Examination - Dr. M. Allam (2020-2021) .pdf": {
        "title": "Allam's Clinical Examination - Dr. M. Allam (2020-2021)",
        "domain": "medical",
        "subdomain": "examination",
        "edition": None,
        "publication_year": 2020,
        "parser_strategy": "unstructured"
    },
    "Macleod\u2019s Clinical Examination 14thEd.pdf": {
        "title": "Macleod\u2019s Clinical Examination 14thEd",
        "domain": "medical",
        "subdomain": "examination",
        "edition": "14th",
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "Oxford Handbook of Clinical Examination.pdf": {
        "title": "Oxford Handbook of Clinical Examination",
        "domain": "medical",
        "subdomain": "examination",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "Oxford Handbook for the Foundation Programme 4th.pdf": {
        "title": "Oxford Handbook for the Foundation Programme 4th",
        "domain": "medical",
        "subdomain": "general_practice",
        "edition": "4th",
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "Oxford Handbook of General Practice 4th.pdf": {
        "title": "Oxford Handbook of General Practice 4th",
        "domain": "medical",
        "subdomain": "general_practice",
        "edition": "4th",
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "_ISSA_Certified_Nutritionist_Certification_Main_Course_Textbook.pdf": {
        "title": "ISSA Certified Nutritionist Certification Main Course Textbook",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "ISSA-Bodybuilding-Main-Course-Textbook.pdf": {
        "title": "ISSA-Bodybuilding-Main-Course-Textbook",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "ISSA-Certified-Nutritionist-Main-Course-Textbook.pdf": {
        "title": "ISSA-Certified-Nutritionist-Main-Course-Textbook",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "ISSA-Certified-Personal-Trainer-Main-Course-Textbook.pdf": {
        "title": "ISSA-Certified-Personal-Trainer-Main-Course-Textbook",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "ISSA-Corrective-Exercise-Specialist-Main-Course-Textbook.pdf": {
        "title": "ISSA-Corrective-Exercise-Specialist-Main-Course-Textbook",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "ISSA-Power-Lifting-Instructor-Maint-Text.pdf": {
        "title": "ISSA-Power-Lifting-Instructor-Maint-Text",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "ISSA-Specialist-in-Exercise-Therapy-Main-Course-Textbook.pdf": {
        "title": "ISSA-Specialist-in-Exercise-Therapy-Main-Course-Textbook",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "ISSA-Sports-Nutrition-Certification-Main-Course-Textbook.pdf": {
        "title": "ISSA-Sports-Nutrition-Certification-Main-Course-Textbook",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "ISSA-Transformation-Specialist-Main-Course-Textbook.pdf": {
        "title": "ISSA-Transformation-Specialist-Main-Course-Textbook",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "ISSA-Weight-Management-Specialist-Main-Text.pdf": {
        "title": "ISSA-Weight-Management-Specialist-Main-Text",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "ISSA-Yoga-Instructor-Main-Text.pdf": {
        "title": "ISSA-Yoga-Instructor-Main-Text",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "ISSA-Youth-Fitness-Certification-Main-Course-Textbook.pdf": {
        "title": "ISSA-Youth-Fitness-Certification-Main-Course-Textbook",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "Jeff Nippard - Squat Specialization Program.pdf": {
        "title": "Jeff Nippard - Squat Specialization Program",
        "domain": "fitness",
        "subdomain": "hypertrophy_program",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Jeff Nippard_s Bench Press Specialization Program.pdf": {
        "title": "Jeff Nippard s Bench Press Specialization Program",
        "domain": "fitness",
        "subdomain": "hypertrophy_program",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Jeff+Nippard_s+Fundamentals+Hypertrophy+Program.pdf": {
        "title": "Jeff+Nippard s+Fundamentals+Hypertrophy+Program",
        "domain": "fitness",
        "subdomain": "hypertrophy_program",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Jeff+Nippard_s+Upper+Lower+Strength+and+Size+Program.pdf": {
        "title": "Jeff+Nippard s+Upper+Lower+Strength+and+Size+Program",
        "domain": "fitness",
        "subdomain": "hypertrophy_program",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Jeff_Nippard_s_Arm_Hypertrophy_Program.pdf": {
        "title": "Jeff Nippard s Arm Hypertrophy Program",
        "domain": "fitness",
        "subdomain": "hypertrophy_program",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Jeff_Nippard_s_Back_Hypertrophy_Program.pdf": {
        "title": "Jeff Nippard s Back Hypertrophy Program",
        "domain": "fitness",
        "subdomain": "hypertrophy_program",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Jeff_Nippard_s_Chest_Hypertrophy_Program.pdf": {
        "title": "Jeff Nippard s Chest Hypertrophy Program",
        "domain": "fitness",
        "subdomain": "hypertrophy_program",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Jeff_Nippard_s_Forearm_Hypertrophy_Program.pdf": {
        "title": "Jeff Nippard s Forearm Hypertrophy Program",
        "domain": "fitness",
        "subdomain": "hypertrophy_program",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Jeff_Nippard_s_Glute_Hypertrophy_Program.pdf": {
        "title": "Jeff Nippard s Glute Hypertrophy Program",
        "domain": "fitness",
        "subdomain": "hypertrophy_program",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Jeff_Nippard_s_Neck_and_Trap_Guide.pdf": {
        "title": "Jeff Nippard s Neck and Trap Guide",
        "domain": "fitness",
        "subdomain": "hypertrophy_program",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Jeff_Nippard_s_Shoulder_Hypertrophy_Program.pdf": {
        "title": "Jeff Nippard s Shoulder Hypertrophy Program",
        "domain": "fitness",
        "subdomain": "hypertrophy_program",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "The Ultimate Recomp Guide - Jeff Nipard.pdf": {
        "title": "The Ultimate Recomp Guide - Jeff Nipard",
        "domain": "fitness",
        "subdomain": "hypertrophy_program",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Applied-Nutrition-for-Mixed-Sports-Companion-Slides-pdf.pdf": {
        "title": "Applied-Nutrition-for-Mixed-Sports-Companion-Slides-pdf",
        "domain": "nutrition",
        "subdomain": "weight_loss",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Guide_to_Flexible_Dieting.pdf": {
        "title": "Guide to Flexible Dieting",
        "domain": "nutrition",
        "subdomain": "weight_loss",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Lyle McDonald - The Rapid Fat Loss Handbook-1.pdf": {
        "title": "Lyle McDonald - The Rapid Fat Loss Handbook-1",
        "domain": "nutrition",
        "subdomain": "weight_loss",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Lyle McDonald - The Rapid Fat Loss Handbook.pdf": {
        "title": "Lyle McDonald - The Rapid Fat Loss Handbook",
        "domain": "nutrition",
        "subdomain": "weight_loss",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Lyle McDonald - The Ultimate Diet 2.0-2.pdf": {
        "title": "Lyle McDonald - The Ultimate Diet 2.0-2",
        "domain": "nutrition",
        "subdomain": "weight_loss",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "LYLE_McDONALD_-_Stubborn_Fat_Solution_Patch_1.1.pdf": {
        "title": "LYLE McDONALD - Stubborn Fat Solution Patch 1.1",
        "domain": "nutrition",
        "subdomain": "weight_loss",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "McDONALD__Lyle_2018_The_Womens_Book_-_Vol_1.pdf": {
        "title": "McDONALD  Lyle 2018 The Womens Book - Vol 1",
        "domain": "nutrition",
        "subdomain": "weight_loss",
        "edition": None,
        "publication_year": 2018,
        "parser_strategy": "pymupdf"
    },
    "The Protein Book.pdf": {
        "title": "The Protein Book",
        "domain": "nutrition",
        "subdomain": "weight_loss",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "The_Ketogenic_Diet.pdf": {
        "title": "The Ketogenic Diet",
        "domain": "nutrition",
        "subdomain": "weight_loss",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "The_Stubborn_Fat_Solution_by_Lyle_McDonald.pdf": {
        "title": "The Stubborn Fat Solution by Lyle McDonald",
        "domain": "nutrition",
        "subdomain": "weight_loss",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Davidson_s Essentials of Medicine.pdf": {
        "title": "Davidson s Essentials of Medicine",
        "domain": "medical",
        "subdomain": "internal_medicine",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "Davidson_s Principles and Practice of Medicine 24thEd.pdf": {
        "title": "Davidson s Principles and Practice of Medicine 24thEd",
        "domain": "medical",
        "subdomain": "internal_medicine",
        "edition": "24th",
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "Frameworks for internal medicine 2018.pdf": {
        "title": "Frameworks for internal medicine 2018",
        "domain": "medical",
        "subdomain": "internal_medicine",
        "edition": None,
        "publication_year": 2018,
        "parser_strategy": "unstructured"
    },
    "Harrison_s Manual of Medicine.pdf": {
        "title": "Harrison s Manual of Medicine",
        "domain": "medical",
        "subdomain": "internal_medicine",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "Harrison_s Principles of Internal Medicine Twenty First Edition.pdf": {
        "title": "Harrison s Principles of Internal Medicine Twenty First Edition",
        "domain": "medical",
        "subdomain": "internal_medicine",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "Hutchisone clinical methods-24th.pdf": {
        "title": "Hutchisone clinical methods-24th",
        "domain": "medical",
        "subdomain": "internal_medicine",
        "edition": "24th",
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "Kumar-and-Clark-Clinical Medicine.pdf": {
        "title": "Kumar-and-Clark-Clinical Medicine",
        "domain": "medical",
        "subdomain": "internal_medicine",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "The 5-Minute Clinical Consult 2023.pdf": {
        "title": "The 5-Minute Clinical Consult 2023",
        "domain": "medical",
        "subdomain": "internal_medicine",
        "edition": None,
        "publication_year": 2023,
        "parser_strategy": "unstructured"
    },
    "Mike Israetel -The Renaissance Diet 2.pdf": {
        "title": "Mike Israetel -The Renaissance Diet 2",
        "domain": "fitness",
        "subdomain": "nutrition",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Mike Mathews - Muscle Myths 1.1.pdf": {
        "title": "Mike Mathews - Muscle Myths 1.1",
        "domain": "fitness",
        "subdomain": "strength_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "CPT7_Study-Guide_Section1 .pdf": {
        "title": "CPT7 Study-Guide Section1",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "CPT7_Study-Guide_Section2.pdf": {
        "title": "CPT7 Study-Guide Section2",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "CPT7_Study-Guide_Section3.pdf": {
        "title": "CPT7 Study-Guide Section3",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "CPT7_Study-Guide_Section4.pdf": {
        "title": "CPT7 Study-Guide Section4",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "CPT7_Study-Guide_Section5.pdf": {
        "title": "CPT7 Study-Guide Section5",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "CPT7_Study-Guide_Section6.pdf": {
        "title": "CPT7 Study-Guide Section6",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "NASM CPT 7.pdf": {
        "title": "NASM CPT 7",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "NASM Essentials of Personal Fitness Training Sixth Edition.pdf": {
        "title": "NASM Essentials of Personal Fitness Training Sixth Edition",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "NASM Essentials Of Personal Fitness Training.pdf": {
        "title": "NASM Essentials Of Personal Fitness Training",
        "domain": "fitness",
        "subdomain": "personal_training",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "NSCA Strength Training.pdf": {
        "title": "NSCA Strength Training",
        "domain": "fitness",
        "subdomain": "strength_conditioning",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "NSCA_-_Developing_Agility_and_Quickness.pdf": {
        "title": "NSCA - Developing Agility and Quickness",
        "domain": "fitness",
        "subdomain": "strength_conditioning",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "NSCA_-_Developing_Power.pdf": {
        "title": "NSCA - Developing Power",
        "domain": "fitness",
        "subdomain": "strength_conditioning",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "NSCA_-_Developing_Speed.pdf": {
        "title": "NSCA - Developing Speed",
        "domain": "fitness",
        "subdomain": "strength_conditioning",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "NSCA_-_Developing_the_Core.pdf": {
        "title": "NSCA - Developing the Core",
        "domain": "fitness",
        "subdomain": "strength_conditioning",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "NSCA_-_Essentials_of_Personal_Training.pdf": {
        "title": "NSCA - Essentials of Personal Training",
        "domain": "fitness",
        "subdomain": "strength_conditioning",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "NSCA_-_Essentials_of_Strength_Training_and_Conditioning.pdf": {
        "title": "NSCA - Essentials of Strength Training and Conditioning",
        "domain": "fitness",
        "subdomain": "strength_conditioning",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "NSCA_-_Essentials_of_Tactical_Strength_and_Conditioning.pdf": {
        "title": "NSCA - Essentials of Tactical Strength and Conditioning",
        "domain": "fitness",
        "subdomain": "strength_conditioning",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "NSCA_-_Guide_to_Sport_and_Exercise_Nutrition.pdf": {
        "title": "NSCA - Guide to Sport and Exercise Nutrition",
        "domain": "fitness",
        "subdomain": "strength_conditioning",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "NSCA_-_Guide_to_Tests_and_Assessments.pdf": {
        "title": "NSCA - Guide to Tests and Assessments",
        "domain": "fitness",
        "subdomain": "strength_conditioning",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "NSCA_Essentials_Of_Strength_Training_And_Conditioning_3rd_Edition.pdf": {
        "title": "NSCA Essentials Of Strength Training And Conditioning 3rd Edition",
        "domain": "fitness",
        "subdomain": "strength_conditioning",
        "edition": "3rd",
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "nsca_training_load_chart.pdf": {
        "title": "nsca training load chart",
        "domain": "fitness",
        "subdomain": "strength_conditioning",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "NCLEX-RN.pdf": {
        "title": "NCLEX-RN",
        "domain": "medical",
        "subdomain": "nursing",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "Oxford-handbooks-in-nursing-Adam-Sheila-K._Baid-Heather_Creed-Fiona_Hargreaves-Jessica-Oxford-handbook-of-critical-care-nursing-Oxford-University-Press-2015.pdf": {
        "title": "Oxford-handbooks-in-nursing-Adam-Sheila-K. Baid-Heather Creed-Fiona Hargreaves-Jessica-Oxford-handbook-of-critical-care-nursing-Oxford-University-Press-2015",
        "domain": "medical",
        "subdomain": "nursing",
        "edition": None,
        "publication_year": 2015,
        "parser_strategy": "unstructured"
    },
    "Oxford Handbook of Practical Drug Therapy 2nd e.pdf": {
        "title": "Oxford Handbook of Practical Drug Therapy 2nd e",
        "domain": "medical",
        "subdomain": "pharmacology",
        "edition": "2nd",
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Oxford Handbook of Clinical Specialities 10 th.pdf": {
        "title": "Oxford Handbook of Clinical Specialities 10 th",
        "domain": "medical",
        "subdomain": "clinical_medicine",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "unstructured"
    },
    "Oxford_Handbook_of_Clinical_Medicine_11th_Edition_2024_ALGrawany0.pdf": {
        "title": "Oxford Handbook of Clinical Medicine 11th Edition 2024 ALGrawany0",
        "domain": "medical",
        "subdomain": "clinical_medicine",
        "edition": "11th",
        "publication_year": 2024,
        "parser_strategy": "unstructured"
    },
    "Y3T-E-BOOK-SECOND-EDITION.pdf": {
        "title": "Y3T-E-BOOK-SECOND-EDITION",
        "domain": "fitness",
        "subdomain": "bodybuilding",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    },
    "Y3TEBOOK_.pdf": {
        "title": "Y3TEBOOK",
        "domain": "fitness",
        "subdomain": "bodybuilding",
        "edition": None,
        "publication_year": None,
        "parser_strategy": "pymupdf"
    }
}

class MetadataTagger:
    def __init__(self):
        self.registry = SOURCE_REGISTRY

    def get_source_info(self, filename: str) -> dict:
        """Fetch the pre-defined metadata for a specific PDF."""
        # Clean the filename in case path artifacts are attached
        clean_name = Path(filename).name
        
        if clean_name not in self.registry:
            logger.warning(f"File '{clean_name}' not found in SOURCE_REGISTRY. Using fallback metadata.")
            return {
                "title": clean_name.replace(".pdf", "").replace(".PDF", ""),
                "domain": "medical",
                "subdomain": "unknown",
                "parser_strategy": "pymupdf"
            }

        return self.registry[clean_name]

    def create_chunk_hash(self, text_content: str, filename: str, page_num: int) -> str:
        """Creates a unique hash for deduplication during vector insertion."""
        unique_string = f"{filename}_{page_num}_{text_content}"
        return hashlib.sha256(unique_string.encode('utf-8')).hexdigest()