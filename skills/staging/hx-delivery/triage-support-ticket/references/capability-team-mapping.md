# Capability → Team Mapping

| Capability | Description | Team | Domain |
|---|---|---|---|
| Stateless API | Lightweight API for model execution without session state | team-kernel team-models | Ecosystem |
| Transient API | Temporary session-based API for interactive model execution | team-kernel team-models team-policies | Ecosystem |
| Webhooks | Event-driven callbacks for notifying external systems of platform changes | team-policies | Ecosystem |
| API Docs | Interactive API reference documentation for developers integrating with the platform | team-policies | Ecosystem |
| API Versioning | Version management and deprecation strategy for public API endpoints | team-core | Ecosystem |
| Admin Portal | Web application for platform administrators to manage users, teams, licences, and configuration | team-policies | Experience |
| Developer Portal | Web application for model developers to build, test, and deploy pricing models | team-mdx team-policies | Experience |
| Modeller Portal | Web application for underwriters to price risks and manage policies and submissions | team-policies | Experience |
| Notifications | In-app notifications for platform events | team-portfolio | Experience |
| Search | Global search across policies and models, and other platform entities | team-policies | Experience |
| Data/Number Formats | Locale-aware formatting for currencies, dates, and numeric values within models | team-policies | Experience |
| Coding Assistance | AI-assisted creation of rating algorithms, data schemas, and UI views from natural language prompts | team-ai | AI |
| Import Models from Excel | Automated conversion of Excel-based pricing models into native hx models | team-ai | AI |
| Code Analysis/Profiling | AI-powered analysis of model code for errors, performance issues, and best practice adherence | team-ai | AI |
| Knowledge Support | Contextual AI assistant that answers questions about the hx platform and modelling concepts | team-ai | AI |
| Process Submissions | Automated extraction and structuring of data from submission documents | team-ai | AI |
| Populate Policies | AI-driven mapping of extracted submission data into policy fields | team-ai | AI |
| Multi-format file processing | Recursive extraction and format-specific intelligence | team-ai | AI |
| Address Cleansing | Standardisation of ingested address data | team-ai | AI |
| Human Review | Interactive viewing and editing with confidence scores | team-ai | AI |
| Semantic Node Mapping | LLM-based value exgtraction with citations and reasoning for why values were selected | team-ai | AI |
| Understanding Model Outputs | AI explanations of pricing model results to help underwriters interpret and justify decisions | team-ai | AI |
| Year on Year Comparison | Automated comparison of policy terms and pricing across renewal periods | team-ai | AI |
| Policy Wording Comparison | AI-powered diff and analysis of policy wording changes between versions | team-ai | AI |
| Benchmarking | Comparison of risk pricing against market benchmarks and portfolio history | team-ai | AI |
| Ingest Third Party Data | Automated ingestion and normalisation of external data sources for enriching risk assessments | team-ai | AI |
| IdP Integration | Single sign-on via external identity providers such as Okta, Azure AD, and SAML-based IdPs | team-policies | Governance & Compliance |
| User Management | View users imported from identity provider | team-policies | Governance & Compliance |
| Underwriter Teams & Roles | Grouping underwriters into teams with role-based permissions | team-policies | Governance & Compliance |
| Underwriter Model Access | Controlling which models each underwriter team can access | team-policies | Governance & Compliance |
| Underwriter Risk Privacy | Restricting visibility of policies between underwriter teams | team-policies | Governance & Compliance |
| Secret Management | Secure storage and rotation of credentials used by models at runtime | team-policies | Governance & Compliance |
| Host Whitelist Management | Controlling which external hosts models are permitted to make outbound requests to | team-policies | Governance & Compliance |
| API Key Management | Creation and revocation of API keys for external systems | team-policies | Governance & Compliance |
| License Usage | Tracking and reporting of licence seat consumption against entitlements | team-policies | Governance & Compliance |
| Event Log and Export | Centralised log of platform events with export capability for compliance reporting | team-core | Governance & Compliance |
| User Activity | Tracking of user sessions counts | team-policies | Governance & Compliance |
| Audit History | Audit trail of changes made to options by underwriters | team-kernel team-models | Governance & Compliance |
| Environment Usage | Monitoring and reporting of AWS consumption per environment | team-platform | Governance & Compliance |
| Model Version Release Requests | Approval workflow for promoting model versions to "Live" | team-policies | Governance & Compliance |
| Policy Delete Requests | Approval workflow for permanently deleting policy records | team-policies | Governance & Compliance |
| UAT Environments | Provisioning and management of user acceptance testing environments | team-platform | Governance & Compliance |
| Downtime Windows | Scheduling and communication of planned maintenance periods | team-platform | Governance & Compliance |
| Feature Flags | Toggling platform features on or off per tenant or environment | team-platform | Governance & Compliance |
| Uptime Page | Public status page showing real-time platform availability and incident history | team-platform | Governance & Compliance |
| Request & Approval Management | Routing and approving operational requests | team-core | Governance & Compliance |
| Email Ingestion | Automatically capturing submission documents from designated email inboxes | team-triage | Triage |
| Automated Data Extraction | Extracting structured data from unstructured submission documents using AI | team-triage | Triage |
| Submission Data Mapping | Mapping extracted fields to the schema expected by downstream pricing models | team-triage | Triage |
| Appetite Fit Assessment | Evaluating whether a submission falls within the insurer's risk appetite | team-triage | Triage |
| Territory & Jurisdiction Screening | Checking submissions against geographic and regulatory eligibility rules | team-triage | Triage |
| Technical Risk Score | Generating a preliminary risk score to inform prioritisation and pricing | team-triage | Triage |
| Referral | Routing submissions that exceed authority limits or require specialist review | team-triage | Triage |
| Indicative Pricing | Producing an early-stage price estimate before full actuarial analysis | team-triage | Triage |
| Submissions | Dashboard for viewing, filtering, and managing incoming submissions | team-triage | Triage |
| Automated Prioritisation | Rules-based ranking of submissions by urgency, value, and fit | team-triage | Triage |
| Policies | Central view for browsing, searching, and managing all policies | team-policies | Pricing |
| Corrections - Make a change to a policy without losing audit history |  | team-policies | Pricing |
| Custom Policy Lifecycles & Records | Custom tracking of policies through quoting, endorsement, and renewal stages | team-policies | Pricing |
| Renew Policies | Initiating and managing the renewal process for expiring policies | team-policies | Pricing |
| Explore Options | Running what-if scenarios to compare pricing under different terms and structures | team-policies | Pricing |
| Metadata and Tagging | Applying user-defined labels to policies for organisation and filtering | team-policies | Pricing |
| Exposure Rating | Pricing based on the insured's exposure measures such as revenue, payroll, or asset values | team-kernel team-models | Pricing |
| Experience Rating | Adjusting pricing based on the insured's historical loss experience | team-kernel team-models | Pricing |
| Credibility Rating / Rate Blending | Weighting exposure and experience rates using statistical credibility methods | team-kernel team-models | Pricing |
| CAT Modelling / Aggregation | Modelling catastrophe risk and aggregating exposures across a portfolio | team-kernel team-models | Pricing |
| Layering | Structuring coverage across excess and primary layers with per-layer pricing | team-kernel team-models | Pricing |
| Exposure Analysis | Analysing the distribution and concentration of insured exposures | team-kernel team-models | Pricing |
| Rate Change Analysis | Measuring and decomposing year-over-year changes in pricing | team-kernel team-models | Pricing |
| Peer Review | Workflow for a second actuary to review and approve pricing decisions | team-kernel team-models | Pricing |
| Trend Analysis | Identifying and projecting trends in loss frequency, severity, and development | team-kernel team-models | Pricing |
| Claims Development | Projecting ultimate claim costs from immature loss data using actuarial methods | team-kernel team-models | Pricing |
| Batch run orchestration | Scenario management, async job execition, and progress tracking | team-portfolio | Portfolio |
| Model version validation | Verifying that a new model version produces expected results across a portfolio before deployment | team-portfolio | Portfolio |
| Create from live/test policies | Building a portfolio from existing policies in either live or test environments | team-portfolio | Portfolio |
| Import Portfolio | Uploading portfolio data from external files for analysis | team-portfolio | Portfolio |
| Export snapshots | Exporting point-in-time portfolio data for external reporting or archival | team-portfolio | Portfolio |
| Tables | Tabular views of portfolio data with sorting, filtering, and column customisation | team-portfolio | Portfolio |
| Charting | Visual dashboards summarising portfolio metrics and key indicators including histograms, trends, rate adequacy visualisations, all with advanced filtering | team-portfolio | Portfolio |
| Custom Reporting Schemas | User-defined output schemas controlling which fields appear in portfolio reports | team-portfolio | Portfolio |
| Schema field mapping | Map between model version schemas and reporting schemas | team-portfolio | Portfolio |
| Dislocation analysis | Identifying pricing dislocations by re-rating a portfolio against a new model version | team-portfolio | Portfolio |
| Model Version selection | Choosing which model version to apply when running portfolio scenarios | team-portfolio | Portfolio |
| Async task orchestration | Background execution and orchestration of long-running operations | team-portfolio | Portfolio |
| Rates tables selection | Selecting which rate tables to apply when running portfolio scenarios | team-portfolio | Portfolio |
| Models | Creating, listing, and configuring pricing models within the platform | team-mdx | Decision Engine |
| Secrets | Managing encrypted credentials that models can access securely at runtime | team-mdx | Decision Engine |
| Libraries & Packages | Shared libraries and packages available for reuse across models | team-mdx | Decision Engine |
| Code Editor | Browser-based Python editor for writing and editing model code | team-mdx | Decision Engine |
| Code Editor Extensions | Plugin system for extending the code editor with custom tooling | team-mdx | Decision Engine |
| Code Editor Policies | Configuration rules governing editor behaviour such as linting and auto-formatting | team-mdx | Decision Engine |
| Version Control | Version history for model code with branching and diffing | team-mdx | Decision Engine |
| Model Import/Export | Importing and exporting models for migration or backup | team-mdx | Decision Engine |
| Unit Testing | Validate model logic with assertions against expected outputs | team-mdx | Decision Engine |
| Example Data | Sample input datasets for exercising models during development and testing | team-mdx | Decision Engine |
| Model Preview | Running a model interactively against test inputs to inspect outputs before deployment | team-mdx | Decision Engine |
| Stages | Model development stages including development, staging, and production | team-mdx | Decision Engine |
| Model Version Deployment | Promoting a model version from development through stages to production | team-models team-mdx | Decision Engine |
| Multiple Live Model Versions | Running multiple versions of a model concurrently in production | team-models team-mdx | Decision Engine |
| Data Schema Primitives | Typed node system for defining the shape of model data (structures, lists, values, files, triangles) | team-kernel team-models | Decision Engine |
| Node Modes | Input, output, and override modes governing data flow direction between users, algorithms, and the platform | team-kernel team-models | Decision Engine |
| Standard Nodes | Platform-injected data fields providing common concepts per Calculation Mode (e.g., inception date, premium currency) | team-kernel team-models | Decision Engine |
| Rating Algorithms | Synchronous, deterministic computation layer transforming inputs into pricing outputs | team-kernel team-models | Decision Engine |
| Parameter Table Access | Runtime lookup of tabular reference data as Pandas DataFrames | team-kernel team-models | Decision Engine |
| Policy Metadata Access | Reading policy, risk, model, and user context within model code | team-kernel team-models | Decision Engine |
| Error Reporting | Validation and fatal error mechanisms for surfacing issues during model execution | team-kernel team-models | Decision Engine |
| Asynchronous Tasks | Server-side background operations for non-deterministic work such as external API calls | team-kernel team-models | Decision Engine |
| Secret Access | Secure credential retrieval for use within asynchronous tasks | team-kernel team-models | Decision Engine |
| Layout Components | Hierarchical view structure (Root, Page, Section, Pane) providing progressive disclosure | team-kernel team-models | Decision Engine |
| Core Components | Platform-provided interactive components including collections, tables, selectors, charts, files, notes, and triangles | team-kernel team-models | Decision Engine |
| Custom Components | Developer-built JavaScript components extending the platform component library | team-kernel team-models | Decision Engine |
| Path-based Data Binding | Declarative binding of interface components to the data tree via path references | team-kernel team-models | Decision Engine |
| Conditional Rendering | Data-driven visibility and interactivity controls on interface elements | team-kernel team-models | Decision Engine |
| Calculation Modes | Named execution contexts each defining a data schema, algorithm, and interface for a business event type | team-kernel team-models | Decision Engine |
| Execution Modes | Configuration of how models are invoked including interactive and non-interactive modes | team-kernel team-models | Decision Engine |
| File Access & Manipulation | Reading and writing files within the model execution sandbox | team-kernel team-models | Decision Engine |
| Event-driven Tasks | Tasks triggered automatically by platform events such as policy creation | team-kernel team-models | Decision Engine |
| Exhibit Generation | Automated production of formatted documents and reports from model outputs | team-kernel team-models | Decision Engine |
| Decouple Parameter Tables | Managing rate tables independently from model versions for faster rate updates | team-rates-management-engineers | Decision Engine |
| Event Log | Audit trail of changes to rate tables including who changed what and when | team-rates-management-engineers | Decision Engine |
| Model-version mapping | Defining how data fields map to different model version schemas | team-kernel team-models | Decision Engine |
