#!/usr/bin/env python
"""
Bespoke Genuine-Data Seeding Script for Academic Advisor & Degree Planning System.
Generates an expansive, authentic university dataset including:
- University Institution & Multiple Academic Departments
- 8 Academic Terms (Historical completed, Active current, Future planning terms)
- 3 Degree Programmes (Computer Science, Data Science & AI, Software Engineering)
- 25+ Authentic Courses with comprehensive descriptions and credit categories
- Transparent Prerequisite Rule trees (Schema version 1, compound rules)
- Published Curriculums with Mandatory, Elective, and Capstone Requirement Groups
- Course Offerings across terms
- 10 Industry Skills & 4 Career Objectives with Course-Skill Mappings
- 5 Diverse Student Personas with full transcripts, CGPAs, and degree plans
- Advisor Triage Queue items, Versioned Snapshots, Review Decisions & Overrides
- Real Rule-Engine evaluated Student Risk Profiles
- Notification feeds for all users
- Dedicated Faculty Advisors, Curriculum Coordinator, and Registrar Superuser

Credentials for all generated accounts:
  Password: Password123!
"""

import os
import sys
from datetime import date, timedelta
from decimal import Decimal

# Configure Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from institutions.models import Institution, Department
from accounts.models import Role, InstitutionMembership, UserProfile, AdvisorAssignment
from curriculum.models import (
    Programme, DegreeType, CurriculumVersion, CurriculumStatus, CreditCategory,
    Course, RequirementGroup, RequirementGroupType, RequirementGroupCourse,
    PrerequisiteRule, CourseOffering, DeliveryMode
)
from academic_records.models import (
    AcademicTerm, TermSeason, StudentRecord, StudentRecordStatus,
    RepeatedCoursePolicy, TranscriptEntry, TranscriptEntryStatus, VerificationStatus,
    TransferCredit, Exemption
)
from planning.models import (
    Plan, PlanItem, PlanStatus, PlanVersion, PlanVersionStatus,
    PlanReviewDecision, ReviewAction, OverrideEvent, OverrideType
)
from advising.models import (
    StudentRiskProfile, OverallRiskLevel, RiskSeverity, RiskCategory
)
from advising.services import evaluate_student_risks
from degree_audit.services import run_degree_audit
from career_mapping.models import (
    Skill, SkillCategory, ProficiencyLevel, CareerObjective,
    CareerSkillRequirement, CourseSkillMapping, StudentCareerPreference
)
from notifications.models import (
    Notification, NotificationEventType, DeliveryStatus, ReadStatus
)

COMMON_PASSWORD = "Password123!"

def seed_database():
    print("=" * 80)
    print("🎓 SEEDING GENUINE UNIVERSITY DATASET: Antigravity Global University (AGU)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # 1. INSTITUTION & DEPARTMENTS
    # -------------------------------------------------------------------------
    inst, _ = Institution.objects.get_or_create(
        code="AGU",
        defaults={
            "name": "Antigravity Global University & Institute of Technology",
            "domain": "agu.edu",
            "is_active": True,
        }
    )
    inst.name = "Antigravity Global University & Institute of Technology"
    inst.domain = "agu.edu"
    inst.is_active = True
    inst.save()
    print(f"✓ Institution: {inst.name} ({inst.code})")

    departments_data = [
        ("CS", "Department of Computer Science & Systems"),
        ("DS", "Department of Data Science & Artificial Intelligence"),
        ("SE", "Department of Software Engineering & DevOps"),
        ("MATH", "Department of Mathematics & Statistics"),
    ]
    depts = {}
    for code, name in departments_data:
        d, _ = Department.objects.get_or_create(
            institution=inst, code=code,
            defaults={"name": name}
        )
        depts[code] = d
    print(f"✓ Departments: {len(depts)} academic departments established")

    # -------------------------------------------------------------------------
    # 2. ACADEMIC TERMS (Timeline from 2024 to 2028)
    # -------------------------------------------------------------------------
    term_configs = [
        ("FA2024", "Fall 2024", TermSeason.FALL, 2024, "2024-09-01", "2024-12-20", False),
        ("SP2025", "Spring 2025", TermSeason.SPRING, 2025, "2025-01-15", "2025-05-15", False),
        ("FA2025", "Fall 2025", TermSeason.FALL, 2025, "2025-09-01", "2025-12-20", False),
        ("SP2026", "Spring 2026", TermSeason.SPRING, 2026, "2026-01-15", "2026-05-15", False),
        ("FA2026", "Fall 2026", TermSeason.FALL, 2026, "2026-09-01", "2026-12-20", True), # Active
        ("SP2027", "Spring 2027", TermSeason.SPRING, 2027, "2027-01-15", "2027-05-15", True),
        ("FA2027", "Fall 2027", TermSeason.FALL, 2027, "2027-09-01", "2027-12-20", True),
        ("SP2028", "Spring 2028", TermSeason.SPRING, 2028, "2028-01-15", "2028-05-15", True),
    ]
    terms = {}
    for code, name, season, year, start, end, is_act in term_configs:
        t, _ = AcademicTerm.objects.get_or_create(
            institution=inst,
            code=code,
            defaults={
                "name": name,
                "season": season,
                "year": year,
                "start_date": start,
                "end_date": end,
                "is_active": is_act,
            }
        )
        t.name = name
        t.is_active = is_act
        t.save()
        terms[code] = t
    print(f"✓ Academic Terms: {len(terms)} terms configured (FA2024 through SP2028)")

    # -------------------------------------------------------------------------
    # 3. CREDIT CATEGORIES
    # -------------------------------------------------------------------------
    credit_cats = {}
    cat_data = [
        ("GEN_ED", "General Education", "Core collegiate writing, humanities, and ethics breadth"),
        ("MATH_SCI", "Mathematics & Physical Sciences", "Formal mathematics, calculus, linear algebra, statistics"),
        ("MAJOR_CORE", "Computer Science Major Core", "Fundamental computation, data structures, systems, and algorithms"),
        ("TECH_ELEC", "Technical Electives", "Advanced upper-division domain specializations"),
        ("CAPSTONE", "Senior Capstone Experience", "Culminating design, engineering, and defense studio"),
    ]
    for code, name, desc in cat_data:
        cat, _ = CreditCategory.objects.get_or_create(
            institution=inst, code=code,
            defaults={"name": name, "description": desc}
        )
        credit_cats[code] = cat

    # -------------------------------------------------------------------------
    # 4. COURSES CATALOG (25+ Authentic, Rigorous Courses)
    # -------------------------------------------------------------------------
    courses_manifest = [
        # Mathematics & Quantitative Foundations
        ("MATH101", "Calculus I: Differential & Integral Theory", "4.00", "MATH_SCI",
         "Limits, continuous functions, derivatives, mean value theorem, fundamental theorem of calculus, and geometric applications.", None),
        ("MATH102", "Calculus II: Sequences, Series & Multivariable", "4.00", "MATH_SCI",
         "Techniques of integration, infinite series, Taylor polynomials, parametric equations, polar coordinates, and introductory vectors.",
         {"schema_version": 1, "type": "course_completed", "course_code": "MATH101", "min_grade": "C"}),
        ("MATH201", "Discrete Mathematics & Formal Proof", "3.00", "MATH_SCI",
         "Propositional logic, predicate calculus, methods of mathematical proof, set theory, induction, recurrence relations, and graph fundamentals.",
         {"schema_version": 1, "type": "course_completed", "course_code": "MATH101", "min_grade": "C"}),
        ("MATH205", "Linear Algebra & Computational Matrix Analysis", "3.00", "MATH_SCI",
         "Systems of linear equations, vector spaces, linear transformations, matrices, determinants, eigenvalues, eigenvectors, and singular value decomposition.",
         {"schema_version": 1, "type": "course_completed", "course_code": "MATH101", "min_grade": "C"}),
        ("STAT210", "Probability & Statistical Inference for Computing", "3.00", "MATH_SCI",
         "Axiomatic probability, random variables, expectation, standard distributions, central limit theorem, parameter estimation, and hypothesis testing.",
         {"schema_version": 1, "type": "course_completed", "course_code": "MATH102", "min_grade": "C"}),

        # General Education & Humanities
        ("ENG101", "Academic Writing & Scientific Discourse", "3.00", "GEN_ED",
         "Expository prose, critical analysis of research literature, peer review methodology, and persuasive scholarly argumentation.", None),
        ("PHIL220", "Ethics, Cyberlaw & Technological Responsibility", "3.00", "GEN_ED",
         "Philosophical frameworks applied to autonomous systems, algorithmic governance, digital privacy rights, intellectual property, and cybersecurity ethics.", None),

        # Core Computer Science
        ("CS101", "Introduction to Computer Science & Problem Solving", "4.00", "MAJOR_CORE",
         "Imperative and functional programming in Python. Recursion, algorithmic problem decomposition, basic data representation, and unit test suites.", None),
        ("CS102", "Object-Oriented Design & Data Abstraction", "4.00", "MAJOR_CORE",
         "Object-oriented software development in Java/C++. Inheritance, polymorphism, design patterns, encapsulation, exceptions, and memory management.",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS101", "min_grade": "C"}),
        ("CS201", "Data Structures & Algorithm Complexity", "4.00", "MAJOR_CORE",
         "Abstract data types: lists, stacks, queues, balanced search trees, binary heaps, hash tables, graphs. Asymptotic time/space complexity analysis (Big-O).",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS102", "min_grade": "C"}),
        ("CS202", "Computer Organization & Architecture", "3.00", "MAJOR_CORE",
         "Digital logic gates, instruction set architecture (RISC-V), pipelining, processor cache hierarchies, virtual memory, and assembly programming.",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS101", "min_grade": "C"}),
        ("CS301", "Operating Systems & Concurrency", "4.00", "MAJOR_CORE",
         "Process synchronization, thread scheduling, deadlocks, virtual memory architectures, file system internals, POSIX system calls, and device drivers.",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS201", "min_grade": "C"}),
        ("CS302", "Database Management Systems & Relational Theory", "4.00", "MAJOR_CORE",
         "Relational algebra, SQL, normal forms, B+ tree indexing, buffer management, transaction management (ACID), write-ahead logging, and query planning.",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS201", "min_grade": "C"}),
        ("CS305", "Theory of Computation & Automata", "3.00", "MAJOR_CORE",
         "Deterministic and non-deterministic finite automata, regular languages, context-free grammars, pushdown automata, Turing machines, decidability, NP-completeness.",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS201", "min_grade": "C"}),
        ("CS401", "Software Engineering Studio & Architecture", "4.00", "MAJOR_CORE",
         "Large-scale software design, microservices vs monoliths, continuous integration/deployment (CI/CD), version control workflows, automated regression testing.",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS201", "min_grade": "C"}),

        # Advanced Technical Electives
        ("CS405", "Cloud Computing, Microservices & Distributed DevOps", "4.00", "TECH_ELEC",
         "Cloud-native design, containerization with Docker and Kubernetes, serverless paradigms, distributed tracing, observability, and resilient multi-region architectures.",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS301", "min_grade": "C"}),
        ("CS410", "Artificial Intelligence & Autonomous Agents", "4.00", "TECH_ELEC",
         "Informed graph search (A*), constraint satisfaction, Markov decision processes, reinforcement learning, game-tree evaluation, and heuristic reasoning.",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS201", "min_grade": "C"}),
        ("CS420", "Computer Communication Networks & Protocols", "3.00", "TECH_ELEC",
         "Layered network architectures, TCP/IP protocol suite, congestion control, BGP routing, DNS, TLS transport security, and socket-level programming.",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS301", "min_grade": "C"}),
        ("CS430", "Information Security, Cryptography & Systems Defense", "3.00", "TECH_ELEC",
         "Symmetric/asymmetric cryptographic primitives (AES, RSA, ECC), digital signatures, authentication protocols, zero-trust network models, and vulnerability defense.",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS201", "min_grade": "C"}),
        ("DS201", "Foundations of Data Science & Exploratory Analytics", "3.00", "TECH_ELEC",
         "Tidy data paradigms, data wrangling, dimensionality reduction (PCA), exploratory statistical modeling, and interactive visualization using pandas/matplotlib.",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS101", "min_grade": "C"}),
        ("DS301", "Machine Learning & Deep Neural Architectures", "4.00", "TECH_ELEC",
         "Supervised and unsupervised learning, backpropagation, convolutional and recurrent neural nets, transformers, regularization, and model explainability.",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS201", "min_grade": "C"}),
        ("DS401", "Big Data Analytics & Distributed Processing Frameworks", "4.00", "TECH_ELEC",
         "Distributed data storage, Apache Spark RDDs and DataFrames, streaming ingestion (Kafka), and scalable distributed ML pipelines.",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS302", "min_grade": "C"}),

        # Capstone Sequence
        ("CS480", "Senior Capstone Design Studio I: Specification & Architecture", "3.00", "CAPSTONE",
         "Team-based engineering project initiation, stakeholder requirement gathering, formal architecture specification, and milestone prototyping.",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS401", "min_grade": "C"}),
        ("CS481", "Senior Capstone Design Studio II: Implementation & Defense", "3.00", "CAPSTONE",
         "Culminating project implementation, rigorous automated verification testing, production deployment, technical thesis, and faculty oral defense.",
         {"schema_version": 1, "type": "course_completed", "course_code": "CS480", "min_grade": "C"}),
    ]

    courses = {}
    for code, title, credits, cat_code, desc, _ in courses_manifest:
        c, _ = Course.objects.get_or_create(
            institution=inst,
            code=code,
            defaults={
                "title": title,
                "credits": Decimal(credits),
                "description": desc,
                "default_credit_category": credit_cats[cat_code],
                "is_active": True,
            }
        )
        c.title = title
        c.credits = Decimal(credits)
        c.description = desc
        c.default_credit_category = credit_cats[cat_code]
        c.is_active = True
        c.save()
        courses[code] = c
    print(f"✓ Courses Catalog: {len(courses)} collegiate courses established with descriptions & credit categories")

    # -------------------------------------------------------------------------
    # 5. COURSE OFFERINGS (Make courses available across terms)
    # -------------------------------------------------------------------------
    offering_count = 0
    for term_code, term_obj in terms.items():
        for code, course_obj in courses.items():
            # Offer math and foundational CS every term; electives alternated by season
            is_offered = True
            if code in ["CS405", "CS430", "DS401"] and term_obj.season == TermSeason.SPRING:
                is_offered = False
            elif code in ["CS410", "CS420", "DS301"] and term_obj.season == TermSeason.FALL:
                is_offered = False

            CourseOffering.objects.get_or_create(
                institution=inst,
                course=course_obj,
                academic_term=term_obj,
                defaults={
                    "academic_year": f"{term_obj.year}-{term_obj.year+1}",
                    "is_offered": is_offered,
                    "capacity": 45,
                    "delivery_mode": DeliveryMode.IN_PERSON,
                }
            )
            offering_count += 1
    print(f"✓ Course Offerings: {offering_count} term-course availability schedules generated")

    # -------------------------------------------------------------------------
    # 6. DEGREE PROGRAMMES & PUBLISHED CURRICULUMS
    # -------------------------------------------------------------------------
    programmes_data = [
        ("CS-BS", "Bachelor of Science in Computer Science", depts["CS"], DegreeType.BACHELOR,
         "Comprehensive theoretical foundation and modern software engineering systems curriculum accredited by ABET Computing Accreditation Commission."),
        ("DS-BS", "Bachelor of Science in Data Science & Artificial Intelligence", depts["DS"], DegreeType.BACHELOR,
         "Interdisciplinary programme combining computational mathematics, high-dimensional statistical inference, and deep machine learning architectures."),
        ("SE-BS", "Bachelor of Science in Software Engineering & Systems", depts["SE"], DegreeType.BACHELOR,
         "Rigorous curriculum focused on large-scale distributed architectures, quality assurance, cloud-native DevOps, and agile team studios."),
    ]
    programmes = {}
    curriculums = {}

    for p_code, p_name, p_dept, p_deg, p_desc in programmes_data:
        prog, _ = Programme.objects.get_or_create(
            institution=inst, code=p_code,
            defaults={"name": p_name, "department": p_dept.name, "degree_type": p_deg, "description": p_desc, "is_active": True}
        )
        prog.name = p_name
        prog.department = p_dept.name
        prog.description = p_desc
        prog.is_active = True
        prog.save()
        programmes[p_code] = prog

        curr, _ = CurriculumVersion.objects.get_or_create(
            institution=inst,
            programme=prog,
            version_number=1,
            defaults={
                "academic_year": "2024-2028",
                "status": CurriculumStatus.DRAFT,
                "total_credits_required": Decimal("120.00"),
                "min_cgpa_required": Decimal("5.000"),
            }
        )
        CurriculumVersion.objects.filter(id=curr.id).update(min_cgpa_required=Decimal("5.000"))
        curr.refresh_from_db()
        curriculums[p_code] = curr

    # Build Requirement Groups for CS-BS
    cs_curr = curriculums["CS-BS"]
    if cs_curr.status == CurriculumStatus.DRAFT:
        # Group 1: General Education (6 credits)
        g1, _ = RequirementGroup.objects.get_or_create(
            institution=inst, curriculum_version=cs_curr, name="General Education & Ethics",
            defaults={"group_type": RequirementGroupType.MANDATORY, "min_credits": Decimal("6.00"), "display_order": 1}
        )
        for c in ["ENG101", "PHIL220"]:
            RequirementGroupCourse.objects.get_or_create(requirement_group=g1, course=courses[c], defaults={"is_mandatory": True, "display_order": 1})

        # Group 2: Mathematics & Quantitative Foundations (17 credits)
        g2, _ = RequirementGroup.objects.get_or_create(
            institution=inst, curriculum_version=cs_curr, name="Mathematics & Scientific Foundations",
            defaults={"group_type": RequirementGroupType.MANDATORY, "min_credits": Decimal("17.00"), "display_order": 2}
        )
        for c in ["MATH101", "MATH102", "MATH201", "MATH205", "STAT210"]:
            RequirementGroupCourse.objects.get_or_create(requirement_group=g2, course=courses[c], defaults={"is_mandatory": True, "display_order": 2})

        # Group 3: Computer Science Core (29 credits)
        g3, _ = RequirementGroup.objects.get_or_create(
            institution=inst, curriculum_version=cs_curr, name="Computer Science Core Curriculum",
            defaults={"group_type": RequirementGroupType.MANDATORY, "min_credits": Decimal("29.00"), "display_order": 3}
        )
        for c in ["CS101", "CS102", "CS201", "CS202", "CS301", "CS302", "CS305", "CS401"]:
            RequirementGroupCourse.objects.get_or_create(requirement_group=g3, course=courses[c], defaults={"is_mandatory": True, "display_order": 3})

        # Group 4: Advanced Technical Electives (min 15 credits)
        g4, _ = RequirementGroup.objects.get_or_create(
            institution=inst, curriculum_version=cs_curr, name="Advanced Technical Electives",
            defaults={"group_type": RequirementGroupType.ELECTIVE, "min_credits": Decimal("15.00"), "display_order": 4}
        )
        for c in ["CS405", "CS410", "CS420", "CS430", "DS201", "DS301", "DS401"]:
            RequirementGroupCourse.objects.get_or_create(requirement_group=g4, course=courses[c], defaults={"is_mandatory": False, "display_order": 4})

        # Group 5: Senior Capstone Experience (6 credits)
        g5, _ = RequirementGroup.objects.get_or_create(
            institution=inst, curriculum_version=cs_curr, name="Senior Capstone Engineering Studio",
            defaults={"group_type": RequirementGroupType.MANDATORY, "min_credits": Decimal("6.00"), "display_order": 5}
        )
        for c in ["CS480", "CS481"]:
            RequirementGroupCourse.objects.get_or_create(requirement_group=g5, course=courses[c], defaults={"is_mandatory": True, "display_order": 5})

        # Attach Prerequisite Rules to CS-BS
        for code, title, credits, cat_code, desc, rule in courses_manifest:
            if rule:
                PrerequisiteRule.objects.get_or_create(
                    institution=inst,
                    curriculum_version=cs_curr,
                    course=courses[code],
                    defaults={"rule_json": rule, "description": f"Enforces minimum grade C in prerequisite for {code}"}
                )

        cs_curr.status = CurriculumStatus.PUBLISHED
        cs_curr.published_at = timezone.now()
        cs_curr.save()

    # Publish DS-BS and SE-BS curriculums as well
    for p_code in ["DS-BS", "SE-BS"]:
        c = curriculums[p_code]
        if c.status == CurriculumStatus.DRAFT:
            # Common core
            g_core, _ = RequirementGroup.objects.get_or_create(
                institution=inst, curriculum_version=c, name="Fundamental Core",
                defaults={"group_type": RequirementGroupType.MANDATORY, "min_credits": Decimal("24.00"), "display_order": 1}
            )
            for code in ["CS101", "CS102", "CS201", "MATH101", "ENG101", "MATH201"]:
                RequirementGroupCourse.objects.get_or_create(requirement_group=g_core, course=courses[code], defaults={"is_mandatory": True})
            c.status = CurriculumStatus.PUBLISHED
            c.published_at = timezone.now()
            c.save()

    print(f"✓ Degree Programmes: 3 accredited programmes published with official requirement groups & prerequisite rules")

    # -------------------------------------------------------------------------
    # 7. SKILLS & CAREER OBJECTIVES
    # -------------------------------------------------------------------------
    skills_data = [
        ("PYTHON_DEV", "Python Systems & Application Development", SkillCategory.TECHNICAL, "Idiomatic modern Python, typing, async I/O, poetry packaging, pytest"),
        ("JAVA_OOP", "Enterprise Java & Object-Oriented Design", SkillCategory.TECHNICAL, "JVM architecture, design patterns, spring boot, dependency injection"),
        ("DISTRIBUTED_SYS", "Distributed Systems, Consensus & RPC", SkillCategory.TECHNICAL, "Raft consensus, gRPC, fault tolerance, idempotency, event streams"),
        ("CLOUD_DEVOPS", "Cloud Architecture & Containerization", SkillCategory.TOOL, "Docker containerization, Kubernetes clusters, Terraform infrastructure-as-code, CI/CD"),
        ("DATABASE_ARCH", "Relational Database Theory & Query Optimization", SkillCategory.TECHNICAL, "PostgreSQL performance tuning, index strategies, transaction isolation levels"),
        ("ML_PYTORCH", "Deep Neural Networks & Machine Learning", SkillCategory.TECHNICAL, "PyTorch neural modeling, loss optimization, feature transformers, evaluation metrics"),
        ("CYBER_DEFENSE", "Cryptography & Secure Systems Architecture", SkillCategory.TECHNICAL, "Public key cryptography, TLS handshakes, OWASP mitigation, secure code auditing"),
        ("REST_API", "Production API Design & Microservices", SkillCategory.TECHNICAL, "RESTful architecture, OpenAPI specification, rate limiting, token authentication"),
        ("BIG_DATA", "Distributed Analytics & Apache Spark", SkillCategory.TOOL, "Spark SQL, distributed data partitions, Parquet formats, MapReduce optimizations"),
        ("AGILE_STUDIO", "Agile Engineering & Collaborative Code Review", SkillCategory.SOFT, "Scrum sprints, pull request reviews, automated CI gates, architectural documentation"),
    ]
    skills = {}
    for code, name, cat, desc in skills_data:
        sk, _ = Skill.objects.get_or_create(
            institution=inst, code=code,
            defaults={"name": name, "category": cat, "description": desc}
        )
        sk.name = name
        sk.category = cat
        sk.description = desc
        sk.save()
        skills[code] = sk

    # Course-Skill Mappings
    mappings = [
        ("CS101", "PYTHON_DEV", ProficiencyLevel.INTERMEDIATE, Decimal("0.90")),
        ("CS102", "JAVA_OOP", ProficiencyLevel.INTERMEDIATE, Decimal("0.85")),
        ("CS201", "PYTHON_DEV", ProficiencyLevel.ADVANCED, Decimal("0.75")),
        ("CS301", "DISTRIBUTED_SYS", ProficiencyLevel.INTERMEDIATE, Decimal("0.80")),
        ("CS302", "DATABASE_ARCH", ProficiencyLevel.ADVANCED, Decimal("0.95")),
        ("CS401", "AGILE_STUDIO", ProficiencyLevel.ADVANCED, Decimal("0.90")),
        ("CS401", "REST_API", ProficiencyLevel.INTERMEDIATE, Decimal("0.80")),
        ("CS405", "CLOUD_DEVOPS", ProficiencyLevel.ADVANCED, Decimal("0.95")),
        ("CS405", "DISTRIBUTED_SYS", ProficiencyLevel.ADVANCED, Decimal("0.85")),
        ("CS410", "ML_PYTORCH", ProficiencyLevel.INTERMEDIATE, Decimal("0.80")),
        ("CS430", "CYBER_DEFENSE", ProficiencyLevel.ADVANCED, Decimal("0.95")),
        ("DS301", "ML_PYTORCH", ProficiencyLevel.ADVANCED, Decimal("0.95")),
        ("DS401", "BIG_DATA", ProficiencyLevel.ADVANCED, Decimal("0.90")),
    ]
    for c_code, s_code, prof, weight in mappings:
        CourseSkillMapping.objects.get_or_create(
            institution=inst,
            course=courses[c_code],
            skill=skills[s_code],
            defaults={"proficiency_level": prof, "coverage_weight": weight}
        )

    # Career Objectives
    objectives_data = [
        ("SWE_CLOUD", "Cloud Infrastructure & Distributed Systems Engineer",
         "Designs high-availability distributed systems, containerized cloud microservices, and automated multi-region infrastructure pipelines.",
         [("CLOUD_DEVOPS", ProficiencyLevel.ADVANCED, True),
          ("DISTRIBUTED_SYS", ProficiencyLevel.ADVANCED, True),
          ("PYTHON_DEV", ProficiencyLevel.ADVANCED, False),
          ("REST_API", ProficiencyLevel.INTERMEDIATE, False)]),
        ("ML_ENGINEER", "Machine Learning & AI Research Engineer",
         "Architects deep learning neural networks, predictive models, and distributed training pipelines for production AI applications.",
         [("ML_PYTORCH", ProficiencyLevel.ADVANCED, True),
          ("PYTHON_DEV", ProficiencyLevel.ADVANCED, True),
          ("BIG_DATA", ProficiencyLevel.INTERMEDIATE, False)]),
        ("FULLSTACK_ARCH", "Enterprise Full-Stack Software Architect",
         "Oversees end-to-end software lifecycles, robust relational datastores, agile team code reviews, and high-throughput REST APIs.",
         [("JAVA_OOP", ProficiencyLevel.ADVANCED, True),
          ("DATABASE_ARCH", ProficiencyLevel.ADVANCED, True),
          ("REST_API", ProficiencyLevel.ADVANCED, True),
          ("AGILE_STUDIO", ProficiencyLevel.ADVANCED, False)]),
        ("CYBER_ANALYST", "Information Security & Systems Defense Specialist",
         "Protects mission-critical systems through cryptographic protocol engineering, zero-trust network defenses, and threat analysis.",
         [("CYBER_DEFENSE", ProficiencyLevel.ADVANCED, True),
          ("DISTRIBUTED_SYS", ProficiencyLevel.INTERMEDIATE, True),
          ("PYTHON_DEV", ProficiencyLevel.INTERMEDIATE, False)]),
    ]
    objectives = {}
    for code, title, desc, reqs in objectives_data:
        obj, _ = CareerObjective.objects.get_or_create(
            institution=inst, code=code,
            defaults={"title": title, "description": desc, "programme": programmes["CS-BS"], "is_active": True}
        )
        obj.title = title
        obj.description = desc
        obj.is_active = True
        obj.save()
        objectives[code] = obj

        for s_code, min_prof, is_crit in reqs:
            CareerSkillRequirement.objects.get_or_create(
                career_objective=obj,
                skill=skills[s_code],
                defaults={"min_proficiency": min_prof, "is_critical": is_crit, "display_order": 1}
            )

    print(f"✓ Skills & Careers: {len(skills)} competencies & {len(objectives)} career objectives established with requirement mappings")

    # -------------------------------------------------------------------------
    # 8. USER ACCOUNTS (Faculty, Advisors, Coordinators, Administrator & Students)
    # -------------------------------------------------------------------------
    def get_or_create_user(username, email, first, last, role_type, is_staff=False, is_super=False, phone="", pref=""):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "first_name": first, "last_name": last}
        )
        user.email = email
        user.first_name = first
        user.last_name = last
        user.is_staff = is_staff
        user.is_superuser = is_super
        user.is_active = True
        user.set_password(COMMON_PASSWORD)
        user.save()

        # Membership
        mem, _ = InstitutionMembership.objects.get_or_create(
            institution=inst,
            user=user,
            defaults={"role": role_type, "is_active": True}
        )
        mem.role = role_type
        mem.is_active = True
        mem.save()

        # Profile
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={"phone_number": phone, "preferred_name": pref or first}
        )
        profile.phone_number = phone
        profile.preferred_name = pref or first
        profile.save()

        return user, mem

    # Institutional Staff
    admin_user, admin_mem = get_or_create_user(
        "admin_super", "registrar@agu.edu", "Arthur", "Pendelton", Role.ADMIN,
        is_staff=True, is_super=True, phone="+1 (555) 019-2831", pref="Arthur"
    )
    coord_user, coord_mem = get_or_create_user(
        "coordinator_cora", "cora.vance@agu.edu", "Dr. Cora", "Vance", Role.COORDINATOR,
        is_staff=True, phone="+1 (555) 019-4820", pref="Dr. Vance"
    )
    advisor_alice, adv_alice_mem = get_or_create_user(
        "advisor_alice", "alice.chen@agu.edu", "Dr. Alice", "Chen", Role.ADVISOR,
        is_staff=True, phone="+1 (555) 019-3391", pref="Dr. Chen"
    )
    advisor_robert, adv_robert_mem = get_or_create_user(
        "advisor_robert", "robert.sterling@agu.edu", "Prof. Robert", "Sterling", Role.ADVISOR,
        is_staff=True, phone="+1 (555) 019-7712", pref="Prof. Sterling"
    )
    hod_user, hod_mem = get_or_create_user(
        "hod_alan", "alan.sterling@agu.edu", "Dr. Alan", "Sterling", Role.HOD,
        is_staff=True, phone="+1 (555) 019-3301", pref="Dr. Sterling"
    )

    # Student Personas
    students = {}
    students_meta = [
        ("student_elena", "elena.rostova@agu.edu", "Elena", "Rostova", "CS-BS", "FA2024", "SP2027", "9.85", "102.00", StudentRecordStatus.ACTIVE, advisor_alice, adv_alice_mem),
        ("student_alex", "alex.rivera@agu.edu", "Alex", "Rivera", "CS-BS", "FA2024", "SP2028", "9.20", "55.00", StudentRecordStatus.ACTIVE, advisor_alice, adv_alice_mem),
        ("student_marcus", "marcus.vance@agu.edu", "Marcus", "Vance", "SE-BS", "FA2025", "SP2028", "5.75", "26.00", StudentRecordStatus.ACTIVE, advisor_alice, adv_alice_mem),
        ("student_priya", "priya.sharma@agu.edu", "Priya", "Sharma", "DS-BS", "FA2026", "SP2028", "9.80", "36.00", StudentRecordStatus.ACTIVE, advisor_robert, adv_robert_mem),
        ("student_jordan", "jordan.taylor@agu.edu", "Jordan", "Taylor", "CS-BS", "FA2024", "SP2027", "9.15", "88.00", StudentRecordStatus.ACTIVE, advisor_alice, adv_alice_mem),
    ]

    for u_name, email, first, last, p_code, enrol_term, grad_term, gpa, credits_earned, rec_status, adv_user, adv_mem in students_meta:
        stu_u, stu_mem = get_or_create_user(u_name, email, first, last, Role.STUDENT)
        # Advisor Assignment
        AdvisorAssignment.objects.get_or_create(
            institution=inst,
            advisor=adv_mem,
            student=stu_mem,
            defaults={"is_active": True}
        )

        stu_rec, _ = StudentRecord.objects.get_or_create(
            institution=inst,
            student=stu_u,
            defaults={
                "programme": programmes[p_code],
                "pinned_curriculum": curriculums[p_code],
                "enrollment_term": terms[enrol_term],
                "expected_graduation_term": terms[grad_term],
                "repeated_course_policy": RepeatedCoursePolicy.BEST_GRADE,
                "status": rec_status,
                "cached_cgpa": Decimal(gpa),
                "cached_total_credits": Decimal(credits_earned),
            }
        )
        stu_rec.programme = programmes[p_code]
        stu_rec.pinned_curriculum = curriculums[p_code]
        stu_rec.enrollment_term = terms[enrol_term]
        stu_rec.expected_graduation_term = terms[grad_term]
        stu_rec.status = rec_status
        stu_rec.cached_cgpa = Decimal(gpa)
        stu_rec.cached_total_credits = Decimal(credits_earned)
        stu_rec.save()

        students[u_name] = {
            "user": stu_u,
            "membership": stu_mem,
            "record": stu_rec,
            "programme": programmes[p_code],
            "curriculum": curriculums[p_code],
        }

    print(f"✓ User Accounts: 4 Faculty/Staff & 5 Diverse Student Personas fully provisioned")

    # -------------------------------------------------------------------------
    # 9. TRANSCRIPTS & ACADEMIC HISTORIES
    # -------------------------------------------------------------------------
    def add_transcript(stu_record, c_code, term_code, grade, cr="4.00", status=TranscriptEntryStatus.COMPLETED):
        TranscriptEntry.objects.get_or_create(
            institution=inst,
            student_record=stu_record,
            course=courses[c_code],
            term=terms[term_code],
            defaults={
                "grade": grade,
                "credits_attempted": Decimal(cr),
                "credits_earned": Decimal(cr) if grade not in ["F", "W", "D-"] else Decimal("0.00"),
                "status": status,
                "verification_status": VerificationStatus.VERIFIED,
                "attempt_number": 1,
            }
        )

    # 9A. Elena Rostova: Senior Honors, 102 credits (All A's and A-'s)
    elena_rec = students["student_elena"]["record"]
    elena_courses = [
        ("MATH101", "FA2024", "A", "4.00"),
        ("CS101", "FA2024", "A", "4.00"),
        ("ENG101", "FA2024", "A", "3.00"),
        ("MATH102", "SP2025", "A", "4.00"),
        ("CS102", "SP2025", "A", "4.00"),
        ("PHIL220", "SP2025", "A-", "3.00"),
        ("MATH201", "FA2025", "A", "3.00"),
        ("CS201", "FA2025", "A", "4.00"),
        ("CS202", "FA2025", "A", "3.00"),
        ("MATH205", "SP2026", "A", "3.00"),
        ("CS301", "SP2026", "A", "4.00"),
        ("CS302", "SP2026", "A", "4.00"),
        ("STAT210", "SP2026", "A-", "3.00"),
        ("CS305", "FA2026", "A", "3.00"),
        ("CS401", "FA2026", "A", "4.00"),
        ("CS405", "FA2026", "A", "4.00"),
        ("CS480", "FA2026", "A", "3.00"),
    ]
    for c_code, t_code, gr, cr in elena_courses:
        add_transcript(elena_rec, c_code, t_code, gr, cr)

    # 9B. Alex Rivera: Junior, 55 credits (Solid high B+/A-)
    alex_rec = students["student_alex"]["record"]
    alex_courses = [
        ("MATH101", "FA2024", "A-", "4.00"),
        ("CS101", "FA2024", "A", "4.00"),
        ("ENG101", "FA2024", "B+", "3.00"),
        ("MATH102", "SP2025", "B+", "4.00"),
        ("CS102", "SP2025", "A-", "4.00"),
        ("PHIL220", "SP2025", "A", "3.00"),
        ("MATH201", "FA2025", "B+", "3.00"),
        ("CS201", "FA2025", "A", "4.00"),
        ("CS202", "FA2025", "B", "3.00"),
        ("CS301", "SP2026", "A-", "4.00"),
        ("CS302", "SP2026", "B+", "4.00"),
        # Current active term FA2026 in progress
        ("CS401", "FA2026", "IP", "4.00", TranscriptEntryStatus.IN_PROGRESS),
        ("MATH205", "FA2026", "IP", "3.00", TranscriptEntryStatus.IN_PROGRESS),
    ]
    for c_code, t_code, gr, cr, *st in alex_courses:
        status = st[0] if st else TranscriptEntryStatus.COMPLETED
        add_transcript(alex_rec, c_code, t_code, gr, cr, status)

    # 9C. Marcus Vance: Sophomore with Academic Risk (D+ in MATH101, Withdrew from CS102)
    marcus_rec = students["student_marcus"]["record"]
    add_transcript(marcus_rec, "CS101", "FA2025", "B-", "4.00")
    add_transcript(marcus_rec, "ENG101", "FA2025", "C+", "3.00")
    add_transcript(marcus_rec, "MATH101", "FA2025", "D+", "4.00") # Fails min C prerequisite!
    add_transcript(marcus_rec, "CS102", "SP2026", "W", "4.00", TranscriptEntryStatus.WITHDRAWN)
    add_transcript(marcus_rec, "PHIL220", "SP2026", "B", "3.00")

    # 9D. Priya Sharma: Junior Data Science with Transfer Credits
    priya_rec = students["student_priya"]["record"]
    add_transcript(priya_rec, "CS101", "FA2026", "A", "4.00")
    add_transcript(priya_rec, "MATH201", "FA2026", "A", "3.00")
    add_transcript(priya_rec, "DS201", "FA2026", "A", "3.00")
    # Transfer credits from Pacific Coast University
    TransferCredit.objects.get_or_create(
        institution=inst,
        student_record=priya_rec,
        course_code="MATH101",
        defaults={
            "course_title": "Calculus I (Transferred)",
            "source_institution": "Pacific Coast University",
            "credits": Decimal("4.00"),
            "grade": "CR",
            "is_verified": True,
            "verified_at": timezone.now() - timedelta(days=60),
        }
    )
    TransferCredit.objects.get_or_create(
        institution=inst,
        student_record=priya_rec,
        course_code="ENG101",
        defaults={
            "course_title": "Academic Writing (Transferred)",
            "source_institution": "Pacific Coast University",
            "credits": Decimal("3.00"),
            "grade": "CR",
            "is_verified": True,
            "verified_at": timezone.now() - timedelta(days=60),
        }
    )

    # 9E. Jordan Taylor: Senior with Official Advisor Override
    jordan_rec = students["student_jordan"]["record"]
    jordan_courses = [
        ("MATH101", "FA2024", "A-", "4.00"),
        ("CS101", "FA2024", "A", "4.00"),
        ("ENG101", "FA2024", "B+", "3.00"),
        ("MATH102", "SP2025", "B", "4.00"),
        ("CS102", "SP2025", "A", "4.00"),
        ("MATH201", "FA2025", "A", "3.00"),
        ("CS201", "FA2025", "A", "4.00"),
        ("CS301", "SP2026", "A-", "4.00"),
        ("CS302", "SP2026", "A", "4.00"),
        ("CS420", "FA2026", "A", "3.00"),
    ]
    for c_code, t_code, gr, cr in jordan_courses:
        add_transcript(jordan_rec, c_code, t_code, gr, cr)

    print("✓ Transcripts: Realistic collegiate histories, transfer evaluations, and in-progress entries populated")

    # Authoritatively synchronize CGPA and credits via deterministic degree audit
    for s_info in students.values():
        rec = s_info["record"]
        audit = run_degree_audit(rec)
        rec.cached_cgpa = audit.overall_cgpa
        rec.cached_total_credits = audit.total_credits_earned
        rec.save(update_fields=["cached_cgpa", "cached_total_credits"])
    print("✓ Degree Audits: Authoritatively computed 10-point CGPAs and progress synchronized across records")

    # -------------------------------------------------------------------------
    # 10. DEGREE PLANS, PLAN VERSIONS & ADVISOR TRIAGE
    # -------------------------------------------------------------------------
    # 10A. Alex Rivera: Submitted Degree Plan awaiting triage
    alex_plan, _ = Plan.objects.get_or_create(
        institution=inst,
        student_record=alex_rec,
        name="Alex's 4-Year Computer Science Pathway",
        defaults={
            "curriculum_version": curriculums["CS-BS"],
            "is_primary": True,
            "status": PlanStatus.SUBMITTED,
        }
    )
    alex_plan.status = PlanStatus.SUBMITTED
    alex_plan.save()

    PlanItem.objects.filter(plan=alex_plan).delete()
    # Term 1: SP2027
    PlanItem.objects.create(institution=inst, plan=alex_plan, course=courses["CS305"], planned_term=terms["SP2027"], term_index=1, position=0)
    PlanItem.objects.create(institution=inst, plan=alex_plan, course=courses["STAT210"], planned_term=terms["SP2027"], term_index=1, position=1)
    PlanItem.objects.create(institution=inst, plan=alex_plan, course=courses["CS405"], planned_term=terms["SP2027"], term_index=1, position=2)
    # Term 2: FA2027
    PlanItem.objects.create(institution=inst, plan=alex_plan, course=courses["CS480"], planned_term=terms["FA2027"], term_index=2, position=0)
    PlanItem.objects.create(institution=inst, plan=alex_plan, course=courses["CS410"], planned_term=terms["FA2027"], term_index=2, position=1)
    PlanItem.objects.create(institution=inst, plan=alex_plan, course=courses["CS420"], planned_term=terms["FA2027"], term_index=2, position=2)
    # Term 3: SP2028 (Graduation)
    PlanItem.objects.create(institution=inst, plan=alex_plan, course=courses["CS481"], planned_term=terms["SP2028"], term_index=3, position=0)
    PlanItem.objects.create(institution=inst, plan=alex_plan, course=courses["CS430"], planned_term=terms["SP2028"], term_index=3, position=1)

    # Freeze PlanVersion Snapshot
    PlanVersion.objects.filter(plan=alex_plan).delete()
    alex_ver = PlanVersion.objects.create(
        institution=inst,
        plan=alex_plan,
        version_number=1,
        status=PlanVersionStatus.SUBMITTED,
        submitted_by=students["student_alex"]["user"],
        submission_note="Ready for official faculty advising review. Targeted for Cloud Engineering career track.",
        snapshot_data={
            "plan_id": str(alex_plan.id),
            "plan_name": alex_plan.name,
            "student_username": "student_alex",
            "curriculum_version_number": 1,
            "items": [
                {"course_code": "CS305", "course_title": "Theory of Computation & Automata", "credits": "3.00", "term_code": "SP2027"},
                {"course_code": "STAT210", "course_title": "Probability & Statistical Inference for Computing", "credits": "3.00", "term_code": "SP2027"},
                {"course_code": "CS405", "course_title": "Cloud Computing, Microservices & Distributed DevOps", "credits": "4.00", "term_code": "SP2027"},
                {"course_code": "CS480", "course_title": "Senior Capstone Design Studio I", "credits": "3.00", "term_code": "FA2027"},
                {"course_code": "CS410", "course_title": "Artificial Intelligence & Autonomous Agents", "credits": "4.00", "term_code": "FA2027"},
                {"course_code": "CS420", "course_title": "Computer Communication Networks & Protocols", "credits": "3.00", "term_code": "FA2027"},
                {"course_code": "CS481", "course_title": "Senior Capstone Design Studio II", "credits": "3.00", "term_code": "SP2028"},
                {"course_code": "CS430", "course_title": "Information Security, Cryptography & Systems Defense", "credits": "3.00", "term_code": "SP2028"},
            ],
            "simulation": {
                "is_valid_for_submission": True,
                "total_planned_credits": "26.00",
                "total_cumulative_credits": "81.00",
                "projected_graduation_term": "SP2028",
                "hard_constraints": [],
                "warnings": [],
            }
        }
    )

    # 10B. Elena Rostova: Approved Degree Plan with Advisor Decision
    elena_plan, _ = Plan.objects.get_or_create(
        institution=inst,
        student_record=elena_rec,
        name="Elena's Honors Graduation Plan",
        defaults={"curriculum_version": curriculums["CS-BS"], "is_primary": True, "status": PlanStatus.APPROVED}
    )
    elena_plan.status = PlanStatus.APPROVED
    elena_plan.save()

    PlanItem.objects.filter(plan=elena_plan).delete()
    PlanItem.objects.create(institution=inst, plan=elena_plan, course=courses["CS481"], planned_term=terms["SP2027"], term_index=1, position=0)
    PlanItem.objects.create(institution=inst, plan=elena_plan, course=courses["CS430"], planned_term=terms["SP2027"], term_index=1, position=1)

    PlanVersion.objects.filter(plan=elena_plan).delete()
    elena_ver = PlanVersion.objects.create(
        institution=inst,
        plan=elena_plan,
        version_number=1,
        status=PlanVersionStatus.APPROVED,
        submitted_by=students["student_elena"]["user"],
        submission_note="Final semester clearance plan for honors graduation.",
        snapshot_data={"plan_name": elena_plan.name, "simulation": {"is_valid_for_submission": True}}
    )
    PlanReviewDecision.objects.create(
        institution=inst,
        plan=elena_plan,
        plan_version=elena_ver,
        reviewer=advisor_alice,
        action=ReviewAction.APPROVE,
        from_status=PlanStatus.SUBMITTED,
        to_status=PlanStatus.APPROVED,
        comments="Outstanding academic record and exemplary term balance. Approved for degree clearance.",
        idempotency_key=f"elena-review-{elena_plan.id}"
    )

    # 10C. Jordan Taylor: Plan with Official Prerequisite Override Event
    jordan_plan, _ = Plan.objects.get_or_create(
        institution=inst,
        student_record=jordan_rec,
        name="Jordan's Cybersecurity Defense Plan",
        defaults={"curriculum_version": curriculums["CS-BS"], "is_primary": True, "status": PlanStatus.APPROVED}
    )
    jordan_plan.status = PlanStatus.APPROVED
    jordan_plan.save()

    PlanItem.objects.filter(plan=jordan_plan).delete()
    PlanItem.objects.create(institution=inst, plan=jordan_plan, course=courses["CS430"], planned_term=terms["SP2027"], term_index=1, position=0)
    PlanItem.objects.create(institution=inst, plan=jordan_plan, course=courses["CS480"], planned_term=terms["SP2027"], term_index=1, position=1)

    PlanVersion.objects.filter(plan=jordan_plan).delete()
    jordan_ver = PlanVersion.objects.create(
        institution=inst,
        plan=jordan_plan,
        version_number=1,
        status=PlanVersionStatus.APPROVED,
        submitted_by=students["student_jordan"]["user"],
        submission_note="Cybersecurity defense plan.",
        snapshot_data={"plan_name": jordan_plan.name, "simulation": {"is_valid_for_submission": True}}
    )

    # Advisor Override Recorded
    OverrideEvent.objects.create(
        institution=inst,
        plan=jordan_plan,
        plan_version=jordan_ver,
        actor=advisor_alice,
        override_type=OverrideType.PREREQUISITE_OVERRIDE,
        justification="Approved prerequisite override for CS430 Information Security based on student's verified NSA/CISA summer fellowship and demonstrated cryptographic proficiency.",
        metadata={"course_code": "CS430", "approved_prereq_waived": "MATH201"}
    )

    # 10D. Marcus Vance: Draft Plan with Academic Risk
    marcus_plan, _ = Plan.objects.get_or_create(
        institution=inst,
        student_record=marcus_rec,
        name="Marcus's Academic Recovery Roadmap",
        defaults={"curriculum_version": curriculums["SE-BS"], "is_primary": True, "status": PlanStatus.DRAFT}
    )
    marcus_plan.status = PlanStatus.DRAFT
    marcus_plan.save()

    PlanItem.objects.filter(plan=marcus_plan).delete()
    PlanItem.objects.create(institution=inst, plan=marcus_plan, course=courses["MATH101"], planned_term=terms["SP2027"], term_index=1, position=0)
    PlanItem.objects.create(institution=inst, plan=marcus_plan, course=courses["CS102"], planned_term=terms["SP2027"], term_index=1, position=1)

    print("✓ Degree Plans: Active submitted snapshots in advisor triage, approved senior plans, and override events configured")

    # -------------------------------------------------------------------------
    # 11. STUDENT RISK PROFILES (Transparent Rule-Engine Evaluations)
    # -------------------------------------------------------------------------
    for u_name, s_data in students.items():
        # Evaluate transparent academic rules
        evaluate_student_risks(s_data["record"], save=True, assessed_by=advisor_alice)
    print("✓ Student Risk Profiles: Rule-based risk indicators deterministically evaluated & cached for all students")

    # -------------------------------------------------------------------------
    # 12. STUDENT CAREER PREFERENCES
    # -------------------------------------------------------------------------
    StudentCareerPreference.objects.get_or_create(
        institution=inst,
        student_record=alex_rec,
        career_objective=objectives["SWE_CLOUD"],
        defaults={"priority": 1, "target_term": terms["SP2028"], "notes": "Targeting cloud infrastructure and distributed systems engineering."}
    )
    StudentCareerPreference.objects.get_or_create(
        institution=inst,
        student_record=elena_rec,
        career_objective=objectives["FULLSTACK_ARCH"],
        defaults={"priority": 1, "target_term": terms["SP2027"], "notes": "Targeting enterprise systems architect positions."}
    )
    StudentCareerPreference.objects.get_or_create(
        institution=inst,
        student_record=priya_rec,
        career_objective=objectives["ML_ENGINEER"],
        defaults={"priority": 1, "target_term": terms["SP2028"], "notes": "Targeting generative AI and deep neural models research."}
    )
    StudentCareerPreference.objects.get_or_create(
        institution=inst,
        student_record=jordan_rec,
        career_objective=objectives["CYBER_ANALYST"],
        defaults={"priority": 1, "target_term": terms["SP2027"], "notes": "Targeting defense and zero-trust cybersecurity operations."}
    )

    # -------------------------------------------------------------------------
    # 13. REAL NOTIFICATIONS FOR ALL ACCOUNTS
    # -------------------------------------------------------------------------
    # Notifications for Advisor Alice
    Notification.objects.get_or_create(
        institution=inst,
        recipient=advisor_alice,
        event_type=NotificationEventType.PLAN_SUBMITTED,
        deduplication_key=f"notif-plan-sub-{alex_plan.id}",
        defaults={
            "subject": "New Degree Plan Submitted: Alex Rivera",
            "preview": "Alex Rivera has submitted their 4-Year Computer Science Pathway for faculty advisor triage.",
            "delivery_status": DeliveryStatus.DELIVERED,
            "read_status": ReadStatus.UNREAD,
        }
    )
    Notification.objects.get_or_create(
        institution=inst,
        recipient=advisor_alice,
        event_type=NotificationEventType.PREREQUISITE_RISK,
        deduplication_key=f"notif-risk-marcus-{marcus_rec.id}",
        defaults={
            "subject": "Academic Warning Alert: Marcus Vance",
            "preview": "Marcus Vance has a prerequisite bottleneck in MATH101 (grade D+). Advising intervention required.",
            "delivery_status": DeliveryStatus.DELIVERED,
            "read_status": ReadStatus.UNREAD,
        }
    )

    # Notifications for Student Alex
    Notification.objects.get_or_create(
        institution=inst,
        recipient=students["student_alex"]["user"],
        event_type=NotificationEventType.PLAN_SUBMITTED,
        deduplication_key=f"notif-stu-sub-{alex_plan.id}",
        defaults={
            "subject": "Degree Plan Submitted Successfully",
            "preview": "Your graduation plan has been placed in Dr. Alice Chen's advising review queue.",
            "delivery_status": DeliveryStatus.DELIVERED,
            "read_status": ReadStatus.UNREAD,
        }
    )
    Notification.objects.get_or_create(
        institution=inst,
        recipient=students["student_alex"]["user"],
        event_type=NotificationEventType.REGISTRATION_REMINDER,
        deduplication_key="notif-reg-reminder-fa2026",
        defaults={
            "subject": "Spring 2027 Course Registration Period",
            "preview": "Early registration for Spring 2027 opens in 14 days. Verify that your planned courses have no prerequisite conflicts.",
            "delivery_status": DeliveryStatus.DELIVERED,
            "read_status": ReadStatus.READ,
        }
    )

    # Notifications for Student Elena
    Notification.objects.get_or_create(
        institution=inst,
        recipient=students["student_elena"]["user"],
        event_type=NotificationEventType.PLAN_APPROVED,
        deduplication_key=f"notif-elena-app-{elena_plan.id}",
        defaults={
            "subject": "Official Degree Plan Approved",
            "preview": "Dr. Alice Chen has formally approved your Honors Graduation Plan for Spring 2027 clearance.",
            "delivery_status": DeliveryStatus.DELIVERED,
            "read_status": ReadStatus.READ,
        }
    )

    # Notifications for Student Marcus
    Notification.objects.get_or_create(
        institution=inst,
        recipient=students["student_marcus"]["user"],
        event_type=NotificationEventType.PREREQUISITE_RISK,
        deduplication_key="notif-marcus-warn-math101",
        defaults={
            "subject": "Academic Alert: Prerequisite Requirement Unfulfilled",
            "preview": "A minimum grade of C is required in MATH101 to enroll in MATH102. Please schedule an advising appointment.",
            "delivery_status": DeliveryStatus.DELIVERED,
            "read_status": ReadStatus.UNREAD,
        }
    )

    print(f"✓ Notifications: Genuine institutional alerts, review notifications, and registration reminders delivered")
    print("=" * 80)
    print("🚀 GENUINE DATASET SEEDING COMPLETE!")
    print("=" * 80)
    print("\nAUTHENTICATION CREDENTIALS SUMMARY (Password for all accounts: Password123!)")
    print("-" * 80)
    print("1. SYSTEM ADMINISTRATOR & REGISTRAR")
    print("   Username: admin_super")
    print("   Role:     System Administrator & Registrar (Django Superuser)")
    print("   Features: Full system access, Django Admin (/admin/), system audit logs")
    print()
    print("2. HEAD OF DEPARTMENT (HOD)")
    print("   Username: hod_alan")
    print("   Role:     Head of Department (HOD) - Computer Science & Systems")
    print("   Features: Department-wide academic performance, risk distribution, curriculum oversight")
    print()
    print("3. PROGRAMME COORDINATOR")
    print("   Username: coordinator_cora")
    print("   Role:     Director of Undergraduate Studies (COORDINATOR)")
    print("   Features: Curriculum Workspace, degree pathway editor, prerequisite trees, cohort analytics")
    print()
    print("4. FACULTY ACADEMIC ADVISORS")
    print("   Username: advisor_alice")
    print("   Role:     Senior Faculty Advisor (ADVISOR)")
    print("   Features: Triage Queue (Alex's submitted plan), override modal, risk profile indicators")
    print()
    print("   Username: advisor_robert")
    print("   Role:     Data Science & Transfer Advisor (ADVISOR)")
    print("   Features: Priya's transfer student advising, career competency reviews")
    print()
    print("5. STUDENT PERSONAS & DIVERSE SCENARIOS (1–10 GPA SCALE)")
    print("   a) Elena Rostova (Honors Senior - Cloud Track)")
    print("      Username: student_elena")
    print("      Stats:    60 Completed Credits | 9.85 / 10.00 CGPA | LOW Risk")
    print("      Plan:     'Elena's Honors Graduation Plan' (Status: APPROVED)")
    print()
    print("   b) Alex Rivera (Proactive Junior - Review Queue Scenario)")
    print("      Username: student_alex")
    print("      Stats:    40 Completed Credits (+7 IP) | 9.20 / 10.00 CGPA | On Track")
    print("      Plan:     'Alex's 4-Year Computer Science Pathway' (Status: SUBMITTED - in triage queue)")
    print()
    print("   c) Marcus Vance (Sophomore - At Risk / Academic Warning)")
    print("      Username: student_marcus")
    print("      Stats:    14 Completed Credits | 5.75 / 10.00 CGPA | CRITICAL Risk")
    print("      Issue:    D+ in MATH101, Withdrew from CS102, active prerequisite bottleneck")
    print()
    print("   d) Priya Sharma (Data Science Junior - Transfer Credit Student)")
    print("      Username: student_priya")
    print("      Stats:    10 Institutional + 7 Transfer Credits | 9.80 / 10.00 CGPA")
    print("      Program:  B.S. in Data Science & Artificial Intelligence (DS-BS)")
    print()
    print("   e) Jordan Taylor (Senior - Advisor Prerequisite Override)")
    print("      Username: student_jordan")
    print("      Stats:    37 Completed Credits | 9.15 / 10.00 CGPA | Cybersecurity Focus")
    print("      Special:  Official recorded Advisor Override for CS430 (NSA Fellowship waiver)")
    print("-" * 80)

if __name__ == "__main__":
    seed_database()
