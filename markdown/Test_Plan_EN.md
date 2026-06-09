# Test Plan

**Group 14**

| Member Info | |
|---|---|
| 2353731 Mao Hanyu | 2353926 Zhao Zeyuan |
| 2253713 Dai Jin'ou | 2350284 Zhang Junfeng |
| 2353914 Han Yimo | |

2026-05-25

---

## Table of Contents

- [Part 1: Project Scope, Test Items, Test Framework and Progress Checklist](#part-1-project-scope-test-items-test-framework-and-progress-checklist)
- [Part 2: Organization Chart and Cost Estimation](#part-2-organization-chart-and-cost-estimation)
- [Part 3: Advanced Test Suite Design](#part-3-advanced-test-suite-design)

---

## Part 1: Project Scope, Test Items, Test Framework and Progress Checklist

### 1. Project Scope

#### 1.1 Test Background

The AutoTestDesign tool developed by this project assists testers in completing requirement parsing, risk analysis, test case generation, test artifact export, and test suite optimization. Per course requirements, the tool itself is not the sole subject of risk analysis, test planning, and detailed test design documentation; the team must select an independent target application and use AutoTestDesign to test it, demonstrating the tool's effectiveness in real testing activities.

The target application selected for this project is the "Phone Number Registration" feature. This target application simulates a common registration entry point in internet applications, covering core scenarios including phone number input validation, SMS verification code sending and verification, password setting, user creation, duplicate registration prevention, and post-registration login. Although small in scale, this feature contains typical testing elements such as input boundaries, condition combinations, state transitions, business rules, and exception handling, making it suitable for validating AutoTestDesign.

#### 1.2 Test Objectives

The overall objectives of this testing activity are as follows:

| Objective ID | Test Objective | Description |
|---|---|---|
| OBJ-01 | Verify Core Functionality Correctness | Confirm that the phone registration flow can complete code sending, code verification, account creation, and login with valid inputs. |
| OBJ-02 | Verify Input Validation Adequacy | Cover valid equivalence classes, invalid equivalence classes, and boundary values for phone number, verification code, password, and confirm password fields. |
| OBJ-03 | Verify Business Rule Consistency | Check whether business rules such as duplicate registration, password mismatch, and incorrect/expired verification codes are correctly enforced. |
| OBJ-04 | Verify Test Design Technique Applicability | Design test cases using equivalence partitioning, boundary value analysis, decision tables, and state transition approaches. |
| OBJ-05 | Verify Tool Output Executability | Convert AutoTestDesign-generated test cases into PyTest automation scripts and execute them. |
| OBJ-06 | Verify Test Result Traceability | Establish traceability between requirements, coverage items, test techniques, test cases, and execution results. |
| OBJ-07 | Verify Test Suite Optimization Capability | Prioritize test cases by risk or minimize coverage redundancy through FR 7.0 to improve execution efficiency. |

#### 1.3 Test Scope

##### 1.3.1 In-Scope Content

This test covers the following:

- Phone number format validation: empty input, non-numeric, insufficient length, excessive length, valid 11-digit number.
- SMS verification code sending: send code when phone format is correct, 60-second resend restriction.
- Verification code validation: code length, numeric format, incorrect code, expired code.
- Password validation: length boundaries, must contain both letters and numbers.
- Confirm password validation: password match and mismatch.
- User creation: new phone registration success, duplicate phone registration failure.
- Login flow: successful login with correct password after registration, failed login with wrong password.
- Automated test execution: execute target application test scripts using PyTest and generate JSON/HTML reports.
- Coverage analysis: measure requirement coverage, test technique coverage, and main scenario coverage.
- Test suite optimization: sort or minimize test cases based on risk, priority, and coverage items.

##### 1.3.2 Out-of-Scope Content

Since the target application is a local simulation, the following are not part of the primary test scope:

- Real SMS gateway, real SMS costs, and carrier link stability.
- Real web browser UI, mobile compatibility, and cross-browser adaptation.
- Real databases, distributed locks, Redis caching, and message queues.
- Real HTTPS certificates, online privacy compliance audits, and penetration testing.
- Large-scale concurrent performance testing and production environment capacity planning.

These items may be addressed as future extensions when the system integrates with real frontend and backend services.

### 2. Test Items

#### 2.1 Target Application Functional Test Items

| Test Item ID | Test Item Name | Corresponding Module/Method | Functional Description | Primary Test Technique |
|---|---|---|---|---|
| TI-F-01 | Phone Number Format Validation | `PhoneRegistrationApp.validate_phone()` / `register_step1_send_code()` | Validate whether phone number is empty, numeric-only, and 11 digits. | Equivalence Partitioning, Boundary Value Analysis |
| TI-F-02 | Verification Code Sending | `SMSVerificationService.send_code()` | Generate verification code for valid phone number, restrict resending within 60 seconds. | Decision Table, State Transition |
| TI-F-03 | Verification Code Format Validation | `PhoneRegistrationApp.validate_verification_code()` | Validate whether verification code is 4 to 6 digits. | Equivalence Partitioning, Boundary Value Analysis |
| TI-F-04 | Verification Code Correctness | `register_step2_verify_code()` | Validate whether code exists, is expired, and matches the phone number. | Decision Table, State Transition |
| TI-F-05 | Password Format Validation | `PhoneRegistrationApp.validate_password()` | Validate password length is 6-20 characters and contains both letters and numbers. | Equivalence Partitioning, Boundary Value Analysis |
| TI-F-06 | Confirm Password Validation | `register_step3_create_user()` | Check whether password and confirm password match. | Decision Table |
| TI-F-07 | User Creation | `UserDatabase.create_user()` | New phone registration succeeds; duplicate phone registration fails. | Decision Table, Integration Testing |
| TI-F-08 | Post-Registration Login | `PhoneRegistrationApp.login()` | Successful login with correct password after registration; failed login with wrong password. | Integration Testing, State Transition |

#### 2.2 Non-Functional Test Items

| Test Item ID | Non-Functional Attribute | Test Item Description | Verification Method in This Project |
|---|---|---|---|
| TI-NF-01 | Performance | Test case generation and execution should maintain short response times. | Local PyTest batch execution of 48 target application test cases completes quickly; FR 7.0 provides minimization strategy to reduce redundant execution. |
| TI-NF-02 | Usability | The tool should provide a clear frontend workflow supporting import, analysis, generation, optimization, and export. | Frontend pages include entry points for requirement management, risk analysis, test cases, export, and suite optimization. |
| TI-NF-03 | Maintainability | Test code should be organized by module for easy extension to more target applications and test techniques. | Backend is layered by `routers`, `models`, `services/algorithms`, `tests`. |
| TI-NF-04 | Traceability | Test design should be traceable to requirements, coverage items, and execution results. | Mapping is established through test case IDs, requirement IDs, coverage reports, and result reports. |
| TI-NF-05 | Security | Registration involves phone numbers, passwords, and verification codes; focus on format validation, duplicate registration, and abuse prevention. | Currently verified through simulation of password format, duplicate registration, and code rate limiting; real security encryption is a future extension. |

#### 2.3 Target Application System Architecture

The target application uses a local Python simulation with the following core structure:

```text
AutoTestDesign Frontend
  ↓ calls REST API
FastAPI Backend
  ↓ generates requirement parsing, risk, test case, and suite optimization results
Test Execution Layer PyTest
  ↓ directly calls target application Python classes
Target Application PhoneRegistrationApp
  ├─ SMSVerificationService: code generation, code storage, send frequency limiting
  ├─ UserDatabase: user registration simulation, duplicate registration check, login verification
  └─ PhoneRegistrationApp: three-step registration and login entry
  ↓
Test Reports reports/test_report.json + reports/coverage_report.json
```

#### 2.4 Main Component Description

| Component | File Location | Purpose |
|---|---|---|
| Target Application | `backend/target_app.py` | Simulates phone registration, verification code, user database, and login. |
| Test Scripts | `backend/tests/test_phone_registration.py` | Executes equivalence partitioning, boundary value, decision table, and integration flow tests. |
| Test Result Analysis | `backend/analyze_results.py` | Parses PyTest JSON reports, calculates pass rates, technique distribution, and coverage. |
| Test Result Report | `backend/reports/test_report.json` | Stores target application automated test execution results. |
| Coverage Report | `backend/reports/coverage_report.json` | Stores requirement, technique, and scenario coverage statistics. |
| Test Suite Optimization | `backend/services/algorithms/suite_optimizer.py` | Implements FR 7.0 risk-based prioritization and coverage-efficiency minimization. |
| Optimization API | `backend/routers/optimization.py` | Provides `/api/optimization/suite` endpoint for frontend calls. |

### 3. Selected Test Framework and Rationale

#### 3.1 Test Framework Selection

This project selects **PyTest** as the automated test execution framework for the target application.

#### 3.2 Selection Rationale

| Evaluation Dimension | PyTest Suitability |
|---|---|
| Technology Stack Match | Target application is implemented in Python; PyTest can directly call target application classes and methods without additional browser or service setup. |
| Clear Test Expression | PyTest supports function-style and class-style tests; test case names can directly correspond to AutoTestDesign-generated case IDs. |
| Robust Fixture Mechanism | `pytest.fixture(autouse=True)` resets SMS service and user database before each test, ensuring test independence. |
| Good Report Support | `pytest-json-report` and `pytest-html` generate structured JSON and HTML reports for subsequent analysis. |
| CI/CD Friendly | Simple command-line execution, integrable with uv, GitHub Actions, or other CI/CD tools. |
| Low Learning and Maintenance Cost | PyTest syntax is concise, suitable for course projects to quickly complete a runnable verification cycle. |

#### 3.3 Comparison with Other Frameworks

| Framework | Advantages | Reason Not Selected |
|---|---|---|
| Selenium | Suitable for real browser UI automation | Target application is a local Python simulation without a real browser page; Selenium overhead is too high. |
| Playwright | Modern web automation, multi-browser support | Current focus is on test case generation logic and backend execution, not browser-level testing. |
| unittest | Python standard library, no extra dependencies | Less flexible assertions, fixtures, and report extensions compared to PyTest. |
| Postman/Newman | Suitable for API testing | Target application is not an independent HTTP service but local Python class calls. |

#### 3.4 Test Execution Commands

```bash
cd backend
uv run python -m pytest -q -o addopts=''
```

To generate JSON report:

```bash
cd backend
uv run python -m pytest tests/test_phone_registration.py --json-report --json-report-file=reports/test_report.json
uv run python analyze_results.py
```

### 4. Schedule and Checklist

#### 4.1 Test Activity Schedule

| Phase | Timeline | Main Tasks | Responsible | Deliverables |
|---|---|---|---|---|
| Phase 0: Preparation | Week 11 Wed-Thu | Confirm target application, unify requirement, risk, and test case JSON data formats. | All/A | Data interface agreement, target application selection result |
| Phase 1: Core Development | Week 11 Fri to Week 12 Sun | Implement requirement import/parsing, risk analysis, test case generation, export, black/white box algorithms. | A/B/C/D | Runnable AutoTestDesign core features |
| Phase 2: Test Execution Prep | Week 12 Weekend | Set up target application test environment, write PyTest automation script skeleton. | E | `target_app.py`, `test_phone_registration.py` |
| Phase 3: Integration | Week 13 Mon-Tue | Integrate frontend/backend, execute full test suite, record results and report coverage gaps. | A/B/C/D/E | Test report, coverage report, issue list |
| Phase 4: Optimization & Regression | Week 13 Tue-Wed | Add FR 7.0 suite optimization, execute regression testing. | E/A | Optimization endpoint, optimization page, regression results |
| Phase 5: Documentation | Week 13 Wed-Thu | Consolidate risk report, test plan, detailed test design and execution documents. | All | Final Markdown/PDF documents |
| Phase 6: Final Submission | Week 13 Fri 17:00 | Package source code, PDF documents, PPT, and demo video. | All | Final submission package |

#### 4.2 Test Level and Objective Checklist

| Check Item ID | Test Level | Check Objective | Acceptance Criteria | Status |
|---|---|---|---|---|
| CK-01 | Requirement Level | Are target application requirements decomposed into testable items | Covers at least phone, code, password, duplicate registration, login scenarios | Completed |
| CK-02 | Design Level | Are multiple test design techniques used | Includes at least equivalence partitioning, boundary value analysis, decision table, plus state transition | Completed |
| CK-03 | Unit Testing | Are input validation functions correct | Phone, code, password validation cases all pass | Completed |
| CK-04 | Integration Testing | Can the registration flow execute completely | Send code, verify code, create user, login flow passes | Completed |
| CK-05 | Exception Testing | Are error inputs and abnormal business rules blocked | Length errors, non-numeric, password mismatch, duplicate registration return failure | Completed |
| CK-06 | Report Check | Are structured test results generated | Generates `test_report.json` and `coverage_report.json` | Completed |
| CK-07 | Coverage Check | Are requirement, technique, and scenario coverage calculated | Coverage report shows core requirements, three techniques, and main scenarios covered | Completed |
| CK-08 | Optimization Check | Is test suite optimization supported | Supports risk-based prioritization and coverage-efficiency minimization | Completed |
| CK-09 | Frontend Connection | Can frontend call backend APIs | `/api/optimization/suite` and other endpoints triggerable from page | Completed/pending final demo confirmation |
| CK-10 | Final Delivery | Are documents, code, PPT, and video complete | Export PDFs and package per course submission requirements | Pending pre-submission check |

---

## Part 2: Organization Chart and Cost Estimation

### 5. Organization Chart

#### 5.1 Team Structure

```text
Project Team
├─ Member A: Requirement Import and Framework Integration
│  ├─ FR 1.0 Requirement Import
│  ├─ FR 1.1 Requirement Structured Parsing
│  ├─ Technology Stack Selection and Repository Initialization
│  └─ Test Plan: Project Scope, Test Items, Framework Rationale, Progress Checklist
├─ Member B: Risk Analysis, Export and Presentation
│  ├─ FR 2.0 Risk Analysis and Prioritization
│  ├─ FR 6.0 JSON/CSV/Excel Export
│  ├─ Interactive Review Frontend Interface
│  └─ Risk Analysis Report, Advanced Test Suite Design, Organization Chart, Cost Estimation, PPT/Video
├─ Members C + D: Test Design Core Algorithms
│  ├─ FR 3.0 Equivalence Partitioning, Boundary Value Analysis, Decision Table
│  ├─ FR 4.0 State Transition Diagram and Coverage Path Generation
│  ├─ FR 5.0 Test Oracle Synthesis
│  └─ Coverage Item Identification, Coverage Strategy Mapping, Algorithm Principle Description
└─ Member E: Test Execution, Result Analysis and Suite Optimization
   ├─ FR 7.0 Test Suite Optimization
   ├─ Target Application Test Environment Setup
   ├─ PyTest Automated Test Scripts
   ├─ Test Result and Coverage Analysis
   └─ Test Case Design, Traceability Tables, Result Analysis, Evidence-Based Improvement
```

<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>

#### 5.2 Responsibility Assignment Table

| Member | Primary Functional Responsibilities | Documentation Responsibilities | Collaboration with Other Members |
|---|---|---|---|
| A | Requirement import, structured parsing, tool framework integration | Test plan: project scope, test items, framework rationale, progress checklist | Provides unified data format and backend entry to B/C/D/E; integrates frontend and regeneration endpoints. |
| B | Risk scoring, export functionality, interactive review frontend | Risk analysis report, cost estimation, advanced test suite design, organization chart, PPT and video | Receives structured requirements from A; displays cases generated by C/D; exports artifacts needed by E. |
| C | Black-box test design algorithms | Black-box coverage items and design principle description | Provides equivalence partitioning, boundary value, and decision table cases to E; supplements coverage items based on E's feedback. |
| D | White-box modeling, state transitions, and test oracle | White-box modeling and oracle synthesis algorithm description | Co-provides test case generation and regeneration endpoints with C; supports interactive review. |
| E | Automated test execution, FR 7.0 suite optimization, result analysis | Test case design, traceability tables, tool implementation, result analysis, improvement evidence | Uses cases generated by C/D for execution; feeds results back to B for display and export, and to C/D for coverage gap correction. |

#### 5.3 Information Flow in Test Activities

```text
Requirement Input
  ↓ A: Parsing and Structuring
Structured Requirements
  ↓ B: Risk Analysis
Requirements with Risk Levels
  ↓ C+D: Test Design Generation
Black-box/White-box Test Cases
  ↓ B: Interactive Review and Export
Executable Test Artifacts
  ↓ E: Automated Execution and Suite Optimization
Execution Results, Coverage Reports, Improvement Evidence
  ↓ All: Document, PPT, Video Integration
Final Submission Materials
```

### 6. Cost Estimation

#### 6.1 Cost Estimation Basis

This cost estimation is based on "testing the phone number registration target application using AutoTestDesign." It primarily estimates labor and resource投入. Since this project uses open-source toolchains and local execution, direct software costs are low; the main cost comes from person-hours for requirement analysis, tool development, test design, script execution, and documentation.

#### 6.2 Tool-Assisted Testing Cost Estimation

| Work Item | Responsible | Estimated Person-Hours | Cost Description |
|---|---|---:|---|
| Target Application Selection and Requirement Gathering | All/A | 4 | Define phone registration function and test boundaries. |
| Requirement Import and Structured Parsing Implementation | A | 8 | Implement CSV, text, direct input, and structured field recognition. |
| Risk Analysis Model and Export Functionality | B | 10 | Implement risk scoring, prioritization, JSON/CSV/Excel export. |
| Black-box Test Generation Algorithms | C | 10 | Implement equivalence partitioning, boundary value analysis, decision table. |
| White-box Modeling and Test Oracle | D | 10 | Implement state transition diagram, coverage paths, expected result generation. |
| Interactive Review Frontend | B/A | 8 | Display and allow modification of requirements, risks, test cases, and optimization results. |
| Target Application and Automated Test Scripts | E | 8 | Write `target_app.py` and PyTest scripts. |
| Test Suite Optimization FR 7.0 | E | 4 | Implement risk-based sorting and coverage-efficiency minimization. |
| Test Execution and Result Analysis | E | 4 | Run PyTest, generate JSON/HTML reports and coverage statistics. |
| Documentation, PPT, Video Preparation | All | 14 | Output risk report, test plan, detailed test design document, and demo materials. |
| **Total** | All | **80 Person-Hours** | Course project level estimation. |

#### 6.3 Resource Cost Estimation

| Resource Item | Usage | Cost Estimate |
|---|---|---:|
| Python / FastAPI / PyTest | Open-source tools, local execution | 0 CNY |
| Vue / Vite / Element Plus | Open-source frontend stack | 0 CNY |
| SQLite / Local File Reports | Lightweight local storage | 0 CNY |
| uv Dependency Management | Open-source tool | 0 CNY |
| LLM API | Optional; fallback to rules and local algorithms supported | If using online models, charged by usage; treated as 0 CNY for this project |
| Local Development Devices | Student-owned computers | Not counted as direct project cost |
| Cloud Server | Not required | 0 CNY |

Therefore, the direct resource cost for this project is approximately 0 CNY; the main cost is team members' person-hour投入.

#### 6.4 Comparison with Pure Manual Testing

| Activity | Pure Manual Estimate | With AutoTestDesign Estimate | Savings Reason |
|---|---:|---:|---|
| Requirement Decomposition and Coverage Identification | 10 person-hours | 6 person-hours | Tool automatically parses input fields, conditions, and expected actions. |
| Risk Analysis | 8 person-hours | 4 person-hours | Risk model and rule scoring automatically generate initial risk levels. |
| Test Case Design | 18 person-hours | 8 person-hours | Black-box algorithms automatically generate equivalence partitioning, boundary value, and decision table cases. |
| Case Review and Revision | 8 person-hours | 6 person-hours | Frontend interactive review reduces communication cost, but manual confirmation is still needed. |
| Test Execution | 12 person-hours | 4 person-hours | PyTest automatically executes and generates reports. |
| Result Statistics and Coverage Analysis | 8 person-hours | 3 person-hours | `analyze_results.py` automatically calculates pass rates and coverage. |
| Regression Testing | 10 person-hours | 2 person-hours | Automated scripts can be repeatedly executed. |
| **Total** | **74 person-hours** | **33 person-hours** | Approximately 55.4% savings in test execution and design-related workload. |

> Note: The above table compares only "testing activity" costs, excluding initial tool development costs. If tool development costs are included, the total investment for this course project would be higher; however, the tool has reuse value, and development costs can be amortized across subsequent target application testing.

#### 6.5 Cost-Benefit Analysis

| Benefit Type | Specific Manifestation |
|---|---|
| Design Efficiency Improvement | Testers do not need to write all equivalence partitioning, boundary value, and decision table cases from scratch; they can review and revise tool-generated results. |
| Execution Efficiency Improvement | Automated test execution replaces manual step-by-step verification, significantly reducing execution time. |
| Quality Assurance | Multiple test design techniques ensure comprehensive coverage, reducing the risk of missing critical test scenarios. |
| Reusability | Once developed, the tool can be applied to other target applications with minimal configuration changes. |

---

## Part 3: Advanced Test Suite Design

### 7. Test Suite Overview

#### 7.1 Suite Design Principles

Test suites are organized based on risk levels and testing objectives:

| Suite | Test Cases | Objective |
|---|---|---|
| Core Function Suite | 12 | Cover normal flows and critical boundaries |
| Security Testing Suite | 8 | Cover input validation, injection, and privilege escalation |
| Exception Testing Suite | 5 | Cover network exceptions and service unavailability |

Priority: Core Function > Security > Exception. If time is limited, only the Core Function Suite needs to be executed.

#### 7.2 Suite Execution Strategy

| Execution Phase | Suite | Execution Condition |
|---|---|---|
| Smoke Testing | Core Function Suite (subset) | Every build |
| Full Regression | All three suites | Every release |
| Security Audit | Security Testing Suite | Monthly |
| Exception Handling | Exception Testing Suite | After infrastructure changes |

### 8. Core Function Suite (12 Cases)

#### 8.1 Normal Flow Tests

| Case ID | Test Scenario | Input | Expected Result | Priority |
|---|---|---|---|---|
| CF-01 | Valid phone registration | 11-digit valid phone, correct code, valid password | Registration success | P1 |
| CF-02 | Login after registration | Registered phone + correct password | Login success | P1 |
| CF-03 | Resend verification code | Valid phone, wait 60s, resend | Code resent successfully | P2 |

#### 8.2 Boundary Value Tests

| Case ID | Test Scenario | Input | Expected Result | Priority |
|---|---|---|---|---|
| CF-04 | Phone number 10 digits | 10-digit number | Format error | P1 |
| CF-05 | Phone number 12 digits | 12-digit number | Format error | P1 |
| CF-06 | Password 5 characters | 5-char password | Password format error | P1 |
| CF-07 | Password 6 characters | 6-char valid password | Password accepted | P1 |
| CF-08 | Password 20 characters | 20-char valid password | Password accepted | P2 |
| CF-09 | Password 21 characters | 21-char password | Password format error | P2 |
| CF-10 | Verification code 3 digits | 3-digit code | Code format error | P1 |
| CF-11 | Verification code 4 digits | 4-digit valid code | Code accepted | P1 |
| CF-12 | Verification code 5 digits | 5-digit code | Code format error | P2 |

### 9. Security Testing Suite (8 Cases)

#### 9.1 Input Validation Security

| Case ID | Test Scenario | Input | Expected Result | Priority |
|---|---|---|---|---|
| SEC-01 | SQL injection in phone field | `13800138001' OR '1'='1` | Format error, no SQL execution | P1 |
| SEC-02 | XSS in password field | `<script>alert(1)</script>` | Password format error, no script execution | P1 |
| SEC-03 | Special characters in phone | `138@0013#001` | Format error | P1 |

#### 9.2 Authentication Security

| Case ID | Test Scenario | Input | Expected Result | Priority |
|---|---|---|---|---|
| SEC-04 | Brute-force code guessing | 100 incorrect code attempts | Account locked after 5 attempts | P1 |
| SEC-05 | Expired code usage | Code used after 5-minute expiry | Code rejected | P1 |
| SEC-06 | Code reuse | Same code used twice | Second use rejected | P1 |

#### 9.3 Privilege and Access Control

| Case ID | Test Scenario | Input | Expected Result | Priority |
|---|---|---|---|---|
| SEC-07 | Duplicate registration | Already-registered phone | Registration rejected, "already registered" message | P1 |
| SEC-08 | Password mismatch | Password ≠ Confirm password | Registration rejected, "password mismatch" message | P1 |

### 10. Exception Testing Suite (5 Cases)

#### 10.1 Service Exception Tests

| Case ID | Test Scenario | Input | Expected Result | Priority |
|---|---|---|---|---|
| EXC-01 | SMS service unavailable | Valid phone, SMS service down | Graceful error message, no crash | P2 |
| EXC-02 | Network timeout | Valid phone, simulated timeout | Timeout error message, retry option | P2 |
| EXC-03 | Concurrent registration | Same phone, two simultaneous requests | One succeeds, one rejected | P2 |
| EXC-04 | Page refresh during registration | Mid-flow page refresh | Session preserved or clear restart | P3 |
| EXC-05 | Empty submission | All fields empty, submit | Field-level error messages | P1 |

### 11. Test Execution and Coverage Analysis

#### 11.1 Execution Results

| Metric | Value |
|---|---|
| Total Test Cases | 48 |
| Passed | 48 |
| Failed | 0 |
| Pass Rate | 100% |

#### 11.2 Coverage Analysis

| Coverage Type | Coverage Rate | Details |
|---|---|---|
| Requirement Coverage | 100% | All 5 core requirements covered |
| Technique Coverage | 100% | Equivalence partitioning, boundary value, decision table all applied |
| Scenario Coverage | 100% | Normal flow, boundary, exception, security all covered |

#### 11.3 Coverage Gap Analysis and Improvement

During initial execution, the following gaps were identified and addressed:

| Gap | Action Taken | Result |
|---|---|---|
| Missing password-only-letter case | Added test case for password with only letters | Coverage improved |
| Missing confirm password empty case | Added test case for empty confirm password | Coverage improved |
| FR 7.0 optimization not applied | Implemented risk-based prioritization and minimization | Suite optimized |

### 12. Summary

#### 12.1 Test Suite Design Summary

The advanced test suite design covers **25 test cases** across **3 suites**, organized by risk level and testing objective:

| Suite | Cases | Risk Level | Execution Priority |
|---|---|---|---|
| Core Function Suite | 12 | High/Medium | P1 |
| Security Testing Suite | 8 | High | P1 |
| Exception Testing Suite | 5 | Medium/Low | P2/P3 |

#### 12.2 Key Achievements

1. **Risk-Driven Design**: Test cases are prioritized based on risk analysis results, ensuring high-risk scenarios are tested first.
2. **Comprehensive Coverage**: All input validation, business logic, security, and exception scenarios are covered.
3. **Efficient Execution**: FR 7.0 optimization reduces redundant test execution while maintaining coverage.
4. **Traceability**: Each test case is traceable to requirements, coverage items, and execution results.

#### 12.3 Limitations and Future Work

| Limitation | Future Work |
|---|---|
| Simulated SMS service | Integrate with real SMS gateway for production testing |
| No browser-level testing | Add Selenium/Playwright tests for real UI validation |
| Limited concurrent testing | Add load testing with JMeter or Locust |
| No code coverage measurement | Integrate coverage.py for line and branch coverage |

---
