# Academic Advisor & Degree Planning System (Project P02)
## Complete Functional Architecture, Feature Guide & Domain Context

---

## 1. Executive Summary & Problem Space

### What Is This Platform?
The **Academic Advisor & Degree Planning System** is an enterprise-grade, multi-tenant academic operations platform engineered for higher education institutions (universities and autonomous colleges). It serves as the single source of truth for:
1. **Academic Curricula & Prerequisite Rules**: Defining degree tracks, course catalogues, credit categories, and prerequisite requirement trees.
2. **Authoritative Degree Progress Audits**: Determining student graduation eligibility against pinned matriculation catalog editions.
3. **Non-Destructive Degree Planning & Simulation**: Enabling students to map out multi-semester schedules and simulate "what-if" major changes without altering their official records.
4. **Faculty Advising Governance**: Orchestrating advisor review queues, plan approvals, structured revision requests, and authorized academic overrides with an append-only audit trail.
5. **Early-Warning Student Risk Analytics**: Algorithmic identification of academic stagnation, credit velocity drops, and prerequisite failure cascades.
6. **Workforce & Career Competency Mapping**: Connecting academic course learning outcomes to industry skill frameworks to guide elective selection.

### Why Was It Built? (The Real-World University Problem)
In traditional universities, degree planning and academic advising suffer from critical structural failures:
* **The "Degree Audit Surprise"**: Students frequently discover in their final semester that a course taken three years earlier does not satisfy a specific sub-category requirement or that a prerequisite was inadvertently bypassed, delaying graduation.
* **The Prerequisite Web**: Modern technical degrees have intricate prerequisite graphs (e.g., Data Structures requires Programming II, which requires Programming I and Discrete Math; Operating Systems requires Data Structures and Computer Architecture). Paper catalogues or static PDFs cannot prevent students from enrolling in courses they are unqualified to take.
* **Fragile Academic Advising**: Faculty advisors manage caseloads of 50 to 100+ students with limited office hours. Communication happens over fragmented email threads, and informal verbal approvals for course substitutions leave no verifiable audit trail.
* **Catalog Year Inconsistency**: Universities regularly revise curricula (e.g., replacing an outdated Java course with Cloud Native Computing). If a revision is applied carelessly, students who matriculated under an older catalog edition can have their graduation requirements disrupted.
* **Transcript Contamination**: In existing student information systems, testing a "what-if" scenario (e.g., "What if I switch from Computer Science to Data Science?") often risks mutating or misallocating credits on the student's live academic transcript.

This platform solves these problems through mathematical rigor, catalog version immutability, deterministic rule evaluation, and strict multi-role governance.

---

## 2. Core Architectural Pillars (The "Why")

### 2.1 Multi-Tenancy & Institutional Isolation
* **What it is**: A shared multi-tenant database architecture where all data belongs to a specific institution (e.g., Apex Global University, Pacific Coast University, Metro Tech).
* **Why it exists**: Higher education systems, university consortia, and university branches require separate administrative domains. Courses, students, grading schemes, and faculty from one university must never leak into or interact with another university, while allowing the same application infrastructure to serve multiple campuses.

### 2.2 Immutable Published Curricula
* **What it is**: Once an academic curriculum version (e.g., *BS Computer Science 2024–2025*) is finalized and marked as `PUBLISHED`, its requirement groups, courses, and prerequisite rules are locked permanently against in-place edits or deletions.
* **Why it exists**: Legal and accreditation integrity. When a student matriculates, the university enters into an academic contract governed by that specific catalog edition. If department chairs could freely edit existing published curricula, students' graduation criteria would constantly shift. To make changes, administrators must clone the curriculum into a new draft version for the next academic year.

### 2.3 Pure Deterministic Prerequisite Engine (No Dynamic Code Execution)
* **What it is**: Prerequisite rules are stored as structured JSON Abstract Syntax Trees (ASTs) supporting logical boolean operators (`AND`, `OR`), minimum grade thresholds, co-requisites, and credit milestones. Evaluation is performed by a sandboxed, deterministic pure-Python evaluator.
* **Why it exists**: Security and predictability. Systems that use dynamic script evaluation (`eval()` or Python scripting) are vulnerable to remote code execution and non-deterministic side effects. The rule engine uses Kleene 3-valued logic (`SATISFIED`, `IN_PROGRESS`, `UNSATISFIED`) so that current-semester enrollments can be correctly distinguished from permanently completed coursework.

### 2.4 Non-Destructive Multi-Semester Degree Planning
* **What it is**: Degree plans are virtual sandboxes where students can place courses into hypothetical future terms, experiment with heavy or light credit loads, and test alternate electives.
* **Why it exists**: Students need the freedom to explore graduation pathways without any danger of modifying official transcripts, earned credits, or registered course rosters.

### 2.5 Advisor Governance & Append-Only Override Audit Trails
* **What it is**: While students can create degree roadmaps, only assigned faculty advisors can officially approve or request changes to a primary plan. If an advisor grants a waiver (e.g., waiving a prerequisite due to industry experience, or approving an overload beyond 18 credits), the system records an immutable `OverrideEvent` with mandatory justification.
* **Why it exists**: Academic accreditation standards demand accountability. Overrides cannot be deleted or secretly edited; they permanently record who approved the exception, when, for what reason, and for which student.

---

## 3. The 5 Institutional Roles vs. The 3 Unified RBAC Tiers

One of the platform's most important design choices is the distinction between **Institutional Personas** (job functions) and **System Access Tiers** (macro routing).

### Why Are There 5 Institutional Roles?
Universities operate on clear administrative hierarchies:
1. **Student** (e.g., Alex Rivera): The primary consumer of the degree plan. Builds schedules, monitors graduation velocity, runs simulations, and tracks career skill acquisition.
2. **Faculty Academic Advisor** (e.g., Dr. Alice Chen): Faculty member responsible for a student caseload. Triages submitted plans, monitors academic risk scores, conducts advising meetings, and issues exception overrides.
3. **Programme Coordinator** (e.g., Dr. Cora Vance): Academic director managing a degree program (e.g., BS in Computer Science). Designs requirement groups, authors prerequisite rules, and models future curriculum versions.
4. **Head of Department / HOD** (e.g., Dr. Alan Sterling): Departmental executive overseeing all departmental programs, faculty workloads, cohort graduation pacing, course bottlenecks, and final curriculum publication sign-offs.
5. **System Administrator / Registrar** (e.g., Arthur Pendelton): Campus-wide administrator managing institutional tenancy, academic term dates, student-advisor bindings, user accounts, and platform configuration.

### Why Are There 3 Unified RBAC Tiers?
To avoid routing complexity, fragile permission checks, and permission sprawl across dozens of front-end pages, the platform normalizes the 5 operational roles into **3 Unified Access Tiers**:

```
[ Student ]                  ─────────►  STUDENT Tier
[ Faculty Advisor ]          ─────────►  MENTOR Tier
[ Coordinator / HOD / Admin ] ─────────►  MODERATOR Tier
```

* **`STUDENT` Tier**:
  * Authorized Pages: `/dashboard`, `/plan`, `/audit`, `/careers`, `/profile`
  * Focus: Personal degree progress, simulation sandbox, career skill gap analysis.
* **`MENTOR` Tier** (*Faculty Advisors*):
  * Authorized Pages: Inherits all Student pages + `/advising`
  * Focus: Student caseload roster, plan triage queue, risk profile monitoring, intervention logging.
* **`MODERATOR` Tier** (*Coordinators, HODs, System Admins*):
  * Authorized Pages: Inherits all Mentor pages + `/curriculum`, `/analytics`, `/admin`
  * Focus: Institutional governance, curriculum creation, department-wide metrics, system settings.

### How Powers Are Differentiated Within the "Moderator" Profile
Even though Coordinators, HODs, and System Administrators all share the top-level `MODERATOR` route clearance, their **dashboards, action buttons, and backend mutations** are strictly tailored to their institutional role:

| Capability / Domain | Programme Coordinator | Head of Department (HOD) | System Administrator |
| :--- | :--- | :--- | :--- |
| **Default Dashboard** | **Curriculum Authoring Hub**: Programme catalog, draft versions, prerequisite simulator. | **Executive Overview**: Department avg CGPA, cohort graduation trajectories, top course bottlenecks. | **System Control Center**: Academic terms, multi-institution settings, user provisioning. |
| **Curriculum Drafting** | Can create, clone, and edit draft curricula and prerequisite rules. | Can review draft curricula and grant official publication sign-off. | Oversees institutional curriculum catalogues. |
| **Department Analytics** | Scoped to their specific academic degree program. | Scoped to the entire department (all programs, all cohorts, all faculty). | Scoped institution-wide across all colleges and departments. |
| **Institutional Settings** | **Forbidden**: Cannot edit colleges, departments, or terms. | **Forbidden**: Cannot edit university multi-tenancy settings. | **Authorized**: Full control over institutions, campuses, and terms. |
| **Advisor Assignment** | Read-only view of advisor loads. | Oversees faculty advising allocations. | **Authorized**: Can reassign advisors to students. |
| **Django Admin Portal** | Blocked (`is_staff=False`). | Blocked (`is_staff=False`). | **Authorized**: Full administrative control (`is_superuser=True`). |
| **Perspective Switcher** | Fixed to Coordinator view. | Fixed to HOD executive view. | **Enabled**: Can toggle into Mentor or Student views to inspect operational backlogs. |

---

## 4. Comprehensive Feature Breakdown (Module by Module)

---

### Module 1: Institutions & Academic Structure
* **What it does**: Represents the university organizational hierarchy: `Institution` $\rightarrow$ `Department` $\rightarrow$ `AcademicTerm`.
* **Why it exists**: Every course, degree, student record, and prerequisite rule exists inside an institutional boundary. It ensures complete isolation between different colleges.
* **Key Details**:
  * **Institutions**: Represent distinct universities or colleges (e.g., Apex Global University). Each carries accreditation codes and operational settings.
  * **Departments**: Academic divisions (e.g., Computer Science, Mathematics, Humanities) that own courses and faculty.
  * **Academic Terms**: Semesters or quarters (e.g., Fall 2024, Spring 2025). Terms are marked as *Active*, *Past*, or *Future*, which directly drives prerequisite checking (determining whether a course is completed, currently in progress, or planned).

---

### Module 2: Curriculum Architecture & Immutability Engine
* **What it does**: Organizes degrees into structured, versioned curricula containing credit categories and requirement groups.
* **Why it exists**: A university degree is not a simple checklist of courses; it is a tree of requirements categorized by educational goals (e.g., General Education, Core Computing, Technical Electives, Capstones).
* **Key Details**:
  * **Programmes**: The degree awarded (e.g., *Bachelor of Science in Computer Science*).
  * **Curriculum Versions**: Pinned catalog editions (e.g., *Version 1.0 for Academic Year 2024–2025*).
  * **Lifecycle States**:
    * `DRAFT`: Actively being designed by Coordinators. Fully editable. Students cannot be enrolled.
    * `PUBLISHED`: Official catalog edition. Fully locked against edits or deletions. Active students are assigned here.
    * `ARCHIVED`: Historical catalog edition retained for compliance and transcript verification.
  * **Requirement Groups**: Sub-sections of a degree (e.g., *Mathematical Foundations*, *Computer Science Core*, *Senior Capstone Sequence*). Each group specifies:
    * Total credits required (e.g., 24 credits).
    * Minimum courses required.
    * Minimum allowable grade threshold (e.g., a grade of `C` or higher for core courses).

---

### Module 3: Prerequisite Engine & Dependency Graph
* **What it does**: Evaluates course eligibility and validates the entire curriculum graph for circular dependencies.
* **Why it exists**: To ensure students have the necessary knowledge before entering advanced coursework and to prevent universities from accidentally creating impossible circular degree requirements (e.g., Course A requires B, B requires C, and C requires A).
* **Key Details**:
  * **Prerequisite Rule Trees**: Evaluates complex logic such as:
    * Single course prerequisite: *Must complete CS-101 with at least a C-*.
    * Logical `AND`: *Must complete CS-201 AND MATH-201*.
    * Logical `OR`: *Must complete MATH-205 OR MATH-210*.
    * Minimum Credit Milestones: *Must have completed at least 60 credits (Junior standing)*.
  * **Co-requisites & Concurrent Enrollment**:
    * Co-requisite: *Must be enrolled in Physics I Lab at the same time as Physics I Lecture*.
    * Concurrent Enrollment: Allows a student to register for a follow-up course if the prerequisite is currently being taken in the immediately preceding term.
  * **Cycle Detection (Kahn's Algorithm)**: When a Coordinator designs a curriculum, the platform models all prerequisites as a Directed Acyclic Graph (DAG) and runs topological sorting. If any cycle is detected, publication is blocked with an explanation of the circular loop.

---

### Module 4: Academic Records, Transcripts & Articulation
* **What it does**: Maintains authoritative student transcript entries, transfer credits, test-out exemptions, and cumulative GPA.
* **Why it exists**: Serves as the ground truth of what a student has officially achieved.
* **Key Details**:
  * **Transcript Entries**: Official grades earned at the institution across completed and active semesters.
  * **Grading System**: Standardized on a 10.0 collegiate scale (with letter grades `A+` through `F`).
  * **Repeated Courses**: If a student retakes a course (e.g., after receiving a `D` or `F`), the system handles grade replacement rules according to institutional policy, updating the CGPA while preserving the historical attempt on the transcript.
  * **Transfer Articulation**: Records credits transferred from accredited external colleges, mapping external course codes to institutional equivalents.
  * **Course Exemptions**: Records official waivers for introductory coursework earned through AP exams, International Baccalaureate, or departmental placement examinations without inflating earned credit hours.

---

### Module 5: Authoritative Degree Progress Audit Engine
* **What it does**: Takes a student's complete academic record, compares it against their assigned curriculum catalog version, and generates an authoritative graduation audit.
* **Why it exists**: Eliminates manual graduation checks by providing an instant, mathematical breakdown of degree completion.
* **Key Details**:
  * **Single-Credit Allocation Algorithm**: In many universities, students attempt to "double-count" a single elective course toward two different requirement groups. The audit engine uses a deterministic, priority-ordered allocation algorithm:
    1. Core requirements are satisfied first.
    2. Mathematics and science requirements are satisfied second.
    3. General education requirements are satisfied third.
    4. Remaining eligible courses flow into Technical Electives and Free Electives.
    * Once a course's credits are consumed by one requirement group, they cannot be used to satisfy another.
  * **Audit Output**: Displays total credits earned vs. required (e.g., *106 / 120 credits*), overall CGPA vs. minimum graduation CGPA (e.g., *9.85 vs. 5.00*), and an itemized breakdown of every satisfied, in-progress, and unfulfilled requirement group.

---

### Module 6: Non-Destructive Multi-Semester Degree Planning
* **What it does**: An interactive roadmap builder where students and advisors place courses into future semesters up to graduation.
* **Why it exists**: Allows students to visualize their entire path to graduation and test different pacing strategies without fear of breaking their official records.
* **Key Details**:
  * **Primary vs. Alternative Plans**: Students can have one official *Primary Plan* submitted to their advisor, plus multiple *Alternative Plans* (e.g., "Fast-Track 3-Year Plan", "Cybersecurity Focus Plan").
  * **Live Rule Validation**: As courses are added to future terms, the prerequisite engine continuously checks if future prerequisite chains are respected (e.g., warning the student if they place *Machine Learning* in Term 6 without scheduling *Linear Algebra* in Term 5).
  * **Credit Pacing & Overload Warnings**: Flags semesters that drop below full-time enrollment (under 12 credits) or exceed standard maximum loads (over 18 credits).
  * **Plan Versioning & Snapshots**: Every time a plan is formally submitted or approved, an immutable snapshot (`PlanVersion`) is saved to preserve the agreement.

---

### Module 7: Automated Schedule Optimization (CP-SAT Solver)
* **What it does**: Uses constraint-satisfaction programming (Google OR-Tools CP-SAT) to automatically synthesize a mathematically optimal multi-semester graduation plan.
* **Why it exists**: Manually arranging 20–30 remaining courses across 4–6 semesters while juggling prerequisite trees, term offerings (Fall-only vs. Spring-only courses), and credit limits is a complex puzzle that often overwhelms students.
* **Key Details**:
  * **Hard Constraints (Must Be Satisfied)**:
    1. No course can be scheduled before its prerequisites are completed.
    2. Courses offered only in Fall cannot be placed in Spring terms.
    3. Total credits per semester must stay within allowed minimums and maximums (e.g., 12–18 credits).
    4. Co-requisites must be scheduled in the same term.
  * **Soft Objectives (Optimized For)**:
    1. Minimizes the total number of semesters needed to graduate.
    2. Balances credit workload evenly across terms (preventing 19-credit semesters followed by 12-credit semesters).
    3. Prioritizes foundational bottleneck courses early in the degree path.

---

### Module 8: Faculty Advisor Workflow & Governance
* **What it does**: Manages the review, feedback, approval, and exception lifecycle between students and their assigned faculty advisors.
* **Why it exists**: Ensures academic oversight and institutional accountability for degree planning.
* **Key Details**:
  * **Advising Caseload Roster**: Faculty advisors see their assigned students, filtered by academic standing, graduation year, or pending review status.
  * **Plan Review State Machine**:
    ```
    [ DRAFT ] ──(Student Submits)──► [ SUBMITTED ] ──(Advisor Reviews)──► [ APPROVED ]
                                            │
                                            └──(Changes Requested)──► [ REVISIONS_REQUESTED ]
    ```
  * **Advisor Notes**: Structured feedback attached to plan reviews explaining why a schedule was approved or what changes are required.
  * **Immutable Override Logging (`OverrideEvent`)**: When an advisor approves an exception (e.g., allowing a student to take 21 credits in their final semester, or waiving a prerequisite for an experienced transfer student), the advisor must provide a formal rationale. The system logs an immutable audit event recording the advisor's identity, timestamp, student ID, exception type, and justification.

---

### Module 9: Curriculum Change Impact Analyzer
* **What it does**: Simulates the institutional impact of changing a curriculum *before* the change is enacted.
* **Why it exists**: When a faculty committee proposes modifying a degree (e.g., making *Discrete Mathematics* a prerequisite for *Algorithms*, or increasing elective credits from 12 to 15), department chairs need to know: *How many currently enrolled students will have their graduation delayed by this change?*
* **Key Details**:
  * **Zero-Row Mutation Guarantee**: Runs entirely in read-only memory against active student records without altering any database rows.
  * **Impact Metrics**: Reports the exact count of students affected, lists specific students who would become blocked, identifies newly created prerequisite bottlenecks, and highlights students who would fall short of credit requirements.

---

### Module 10: Early-Warning Academic Risk Profiling
* **What it does**: Algorithmic evaluation of student transcripts to detect academic distress and graduation delay risks early.
* **Why it exists**: Students rarely drop out without warning; their transcripts display leading indicators semesters before academic disqualification. Traditional advising systems only catch issues after grades have plummeted.
* **Key Details**:
  * **Risk Tiers**: Classifies students as `LOW_RISK`, `MEDIUM_RISK`, `HIGH_RISK`, or `CRITICAL_RISK`.
  * **Deterministic Trigger Factors**:
    * *CGPA Stagnation or Drop*: Cumulative GPA falling near or below academic probation thresholds (< 6.00 / 10.00).
    * *Repeated Course Failure*: Failing the same foundational course multiple times (e.g., two failed attempts at *Calculus I*).
    * *Credit Velocity Deficit*: Completing fewer credits per semester than required to graduate within 4 years.
    * *Prerequisite Blocking*: Failing a core gateway course that unlocks 3 or more subsequent required courses.
  * **Intervention & Acknowledgment Logging**: Advisors can record formal risk acknowledgments, intervention plans, and tutoring referrals directly against the student's profile.

---

### Module 11: Career Competency Mapping & Recommendations
* **What it does**: Connects courses to industry skill competencies and specific career objectives.
* **Why it exists**: Students often struggle to choose electives that align with their professional career goals. This module bridges the gap between academic theory and industry hiring standards.
* **Key Details**:
  * **Career Objectives**: Defined target job profiles (e.g., *Full-Stack Cloud Architect*, *Machine Learning Engineer*, *Cybersecurity Specialist*, *DevOps Automation Engineer*).
  * **Skills Taxonomy**: Granular competencies categorized into domains (e.g., *Python Programming*, *Docker & Containers*, *Distributed Systems*, *Relational Database Architecture*).
  * **Course-Skill Mapping**: Catalogs which courses teach which skills and at what proficiency level (Beginner, Intermediate, Advanced).
  * **Skill Gap Analysis**: Compares a student's completed and planned courses against their selected career objective, visually highlighting acquired skills, skills currently in progress, and missing competencies.
  * **Curriculum-Grounded Recommendations**: Suggests specific elective courses that directly close the student's identified skill gaps while strictly respecting prerequisite eligibility.

---

### Module 12: Executive Analytics & Prerequisite Bottlenecks
* **What it does**: Aggregates academic performance across cohorts, departments, and programmes for executive decision-makers.
* **Why it exists**: Department chairs and university deans need high-level visibility into curriculum effectiveness, student retention, and institutional health.
* **Key Details**:
  * **Cohort Progress Tracking**: Pacing metrics showing the percentage of students in each class year (Freshman, Sophomore, Junior, Senior) who are on track for on-time graduation.
  * **Prerequisite Bottleneck Discovery**: Identifies "gateway" courses with high enrollment demand or high failure rates that are actively blocking large cohorts of students from progressing to higher-level courses.
  * **Formula-Safe CSV Exports**: When exporting reports to spreadsheet software, data fields are sanitized against CSV formula injection attacks (preventing malicious cells beginning with `=`, `+`, `-`, or `@`).

---

### Module 13: Intelligent AI Academic Assistant
* **What it does**: An in-app artificial intelligence assistant grounded in the university's specific curriculum rules and degree requirements using Retrieval-Augmented Generation (RAG).
* **Why it exists**: Provides students with instant, 24/7 answers to complex degree questions (e.g., *"What prerequisites do I need before taking Cloud Computing?"*, *"Can I take Distributed Systems in my Junior year?"*) without hallucinating policies or placing extra burden on busy advisors.
* **Key Details**:
  * **Curriculum-Grounded Context**: The assistant does not give generic advice; it retrieves the student's actual transcript, current catalog edition, completed prerequisites, and institutional policies before formulating a response.
  * **Advising vs. Faculty Triage**:
    * For students: Explains prerequisite paths, graduation requirements, and elective options.
    * For advisors: Summarizes student risk profiles, highlights unfulfilled requirements, and drafts suggested course recommendations.
  * **Safety Guardrails**: Transparently states that it is an informational advisor and that official graduation sign-offs require human faculty authorization.

---

### Module 14: In-App Notifications & Administrative Audit Trail
* **What it does**: Delivers targeted real-time alerts for academic milestones and records system-wide administrative changes.
* **Why it exists**: Keeps all participants informed without relying on easily missed email chains, and maintains institutional compliance.
* **Key Details**:
  * **Event-Driven Notifications**: Automatically generated when:
    * A student submits a degree plan for review.
    * An advisor approves a plan or requests revisions.
    * An override exception is granted.
    * Registration opens for an upcoming academic term.
  * **Deduplication Engine**: Prevents notification fatigue by deduplicating repetitive alerts.
  * **Administrative Audit Trail (`django_admin_log` & `PlanAuditLog`)**: Logs all administrative mutations, user creations, curriculum state changes, and plan approvals with timestamps, actor IDs, and IP provenance.

---

## 5. Summary of the Seeded Collegiate Dataset

To demonstrate realistic university operations, the platform comes pre-seeded with a comprehensive collegiate catalog and authentic student personas:

### The Course Catalogue (57 Authentic Courses)
Spanning 6 core departments:
* **Mathematics & Basic Sciences**: Single-Variable Calculus, Multivariable Calculus, Linear Algebra, Probability & Statistics, Discrete Mathematics, University Physics I & II, Engineering Chemistry.
* **Core Computing**: Programming Fundamentals, Object-Oriented Programming, Data Structures, Computer Architecture, Operating Systems, Database Management Systems, Algorithm Design & Analysis, Theory of Computation.
* **Software Engineering & Systems**: Software Engineering Principles, Cloud Architecture, Distributed Systems, Computer Networks, Information Security & Cryptography, Web Application Engineering.
* **Artificial Intelligence & Data Science**: Machine Learning, Deep Learning, Artificial Intelligence Principles, Big Data Analytics, Natural Language Processing.
* **General Education & Breadth**: Academic Writing & Composition, Professional Ethics in Computing, Macroeconomics, Technical Communication, Environmental Studies.
* **Capstones & Industry Practicum**: Senior Design Capstone Project I & II, Industry Internship Practicum.

### The 7 Student Personas (36 Subjects / 120+ Credits Each)
Every student profile models a full 8-semester collegiate degree path:
1. **Elena Rostova** (`student_elena`): *Graduating Honors Senior (CS)*. 32 completed courses, 4 planned in final semester, 9.85 CGPA, Degree Audit Passed.
2. **Alex Rivera** (`student_alex`): *Rising Junior (CS)*. 18 completed courses, 4 in progress, 14 planned, 9.20 CGPA. Plan submitted for advisor triage.
3. **Jordan Taylor** (`student_jordan`): *Senior Cybersecurity Specialist (CS)*. 26 completed courses, 4 in progress, 6 planned, 9.15 CGPA.
4. **Priya Sharma** (`student_priya`): *Junior Transfer Student (DS)*. 4 transfer courses articulated from external university, 2 test-out exemptions, 12 completed at AGU, 14 planned, 9.80 CGPA.
5. **Marcus Vance** (`student_marcus`): *Sophomore on Academic Warning (SE)*. 9 completed courses, course repeats in Calculus and Programming, 5.75 CGPA, active advisor risk intervention plan.
6. **David Kim** (`student_david`): *Senior DevOps Engineer (SE)*. 28 completed courses, 8 planned, 8.90 CGPA, on-track graduation trajectory.
7. **Chloe Bennett** (`student_chloe`): *First-Year Freshman (CS)*. 4 completed courses in first term, 32 planned across future terms, 9.50 CGPA.

---

## 6. Conclusion: Why This Architecture Matters

The Academic Advisor & Degree Planning System bridges the gap between static academic regulations and dynamic student scheduling. By combining:
* **Mathematical rule guarantees** (DAG cycle detection, Kleene 3-valued prerequisite logic),
* **Institutional safety invariants** (catalog version immutability, zero-mutation impact analysis, non-destructive sandboxing), and
* **Transparent governance** (5 distinct operational roles, 3 unified RBAC tiers, append-only override logs),

the platform ensures that universities can maintain total curriculum integrity while students navigate clear, personalized, and achievable pathways to on-time graduation.
