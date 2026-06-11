# Report generation pipeline — `mcr-generation`

The `mcr-generation` service is a Celery worker that turns a meeting transcript (DOCX stored on S3) into a report — a structured Pydantic object for the built-in types (`DecisionRecord`, `DetailedSynthesis`), or raw markdown for custom reports — according to the requested report type. It exposes no HTTP API: it consumes Celery tasks dispatched by `mcr-core` and POSTs the result back.

## Input / Output

| | Type | Description |
|---|---|---|
| **In** `meeting_id` | `int` | Meeting identifier on the `mcr-core` side |
| **In** `transcription_object_filename` | `str` | S3 key of the transcription DOCX |
| **In** `report_type` | `ReportTypes` | `DECISION_RECORD`, `DETAILED_SYNTHESIS` or `CUSTOM_REPORT` |
| **In** `deliverable_id` | `int \| None` | Deliverable the result is reported against — the `task_success` / `task_failure` handlers POST to `/deliverables/{id}/success` or `/failure`. |
| **In** `owner_keycloak_uuid` | `str \| None` | Meeting owner; used on task prerun to fetch meeting context for Sentry. |
| **In** `notes_content` | `str \| None` | Human-written notes taken during the meeting (optional). Extracted by `NotesExtractor` into structured hints — `intent` and `next_meeting` seed the corresponding refiners; `topics` and `discussions` are injected as a human-priority hint into the reduce step. For `CUSTOM_REPORT`, a single `extract_all` call covers both inputs in one `asyncio.gather`: the union of `notes_facets` advertised by `CollectorSection`s, plus one LLM call per `CustomSection.instruction` (populating `ExtractedNotes.custom_section_facts`). |
| **In** `custom_prompt` | `str \| None` | End-user instruction. Required for `CUSTOM_REPORT`, ignored for the structured types. |
| **Out** | `BaseReport \| CustomMarkdownReport` | `DecisionRecord`, `DetailedSynthesis` (Pydantic) or `CustomMarkdownReport` (raw markdown). |

## Pipeline diagram

```mermaid
%%{init: {"flowchart": {"rankSpacing": 80, "nodeSpacing": 55}}}%%
flowchart TB
    accTitle: MCR report generation — overview
    accDescr {
      Overview: the Celery task downloads the transcript, splits it into chunks,
      optionally extracts hints from the notes, picks one of the three generators
      (shown as black boxes here), then POSTs the result back to mcr-core. Each
      generator is detailed in the diagrams below.
    }

    classDef io fill:#e1f5ff,stroke:#0277bd,color:#01579b
    classDef proc fill:#f3e5f5,stroke:#6a1b9a,color:#4a148c
    classDef llm fill:#fff3e0,stroke:#e65100,color:#bf360c
    classDef out fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20

    IN[/"meeting_id + deliverable_id<br/>+ transcription_object_filename + report_type<br/>+ notes_content? + custom_prompt? + owner_keycloak_uuid?"/]:::io
    IN --> TASK["generate_report_from_docx<br/>(Celery task)"]:::proc

    TASK --> FETCH["get_file_from_s3()"]:::proc
    FETCH --> S3[("S3 / Minio")]:::io
    S3 -->|"DOCX bytes"| CHUNK["chunk_docx_to_document_list()<br/>RecursiveCharacterTextSplitter"]:::proc
    CHUNK --> CHUNKS[/"list&lt;Chunk&gt;"/]:::io

    CHUNKS --> FACTORY{"create_report_generator(report_type)"}:::proc

    subgraph BRG["BaseReportGenerator (subclasses)"]
      direction TB
      GEN1["DecisionRecordGenerator()<br/>.generate(chunks, notes_content)"]:::proc
      GEN2["DetailedSynthesisGenerator()<br/>.generate(chunks, notes_content)"]:::proc
    end
    FACTORY -->|"DECISION_RECORD"| GEN1
    FACTORY -->|"DETAILED_SYNTHESIS"| GEN2
    FACTORY -->|"CUSTOM_REPORT"| GEN3["CustomReportGenerator(custom_prompt)<br/>.generate(chunks, notes_content)"]:::proc

    subgraph BR["BaseReport"]
      direction TB
      DR[/"DecisionRecord"/]:::out
      DS[/"DetailedSynthesis"/]:::out
    end
    GEN1 --> DR
    GEN2 --> DS
    GEN3 --> CMR[/"CustomMarkdownReport"/]:::out

    DR & DS & CMR -.->|"signal task_success"| POSTOK["POST /deliverables/{deliverable_id}/success<br/>→ mcr-core"]:::proc
    TASK -.->|"signal task_failure"| POSTKO["POST /deliverables/{deliverable_id}/failure<br/>→ mcr-core"]:::proc
```

Each branch is detailed in the two diagrams below: one for the structured types (`DECISION_RECORD` / `DETAILED_SYNTHESIS`), one for `CUSTOM_REPORT`.

## Reading the diagram

| Color | Meaning |
|---|---|
| 🟦 Blue (`io`) | Data flowing through (input/output, S3 file, list of chunks) |
| 🟪 Purple (`proc`) | Pure Python step (no LLM call) |
| 🟧 Orange (`llm`) | Step that calls an LLM via `instructor` (costs time and tokens) |
| 🟩 Green (`out`) | Final or stable intermediate structured object |

## DECISION_RECORD & DETAILED_SYNTHESIS — detail

Everything happens inside `.generate(chunks, notes_content)` of each `BaseReportGenerator` subclass. The shared steps — `_extract_notes(notes_content)` then `generate_header(chunks, extracted_notes)`, both inherited from the base class — precede the type-specific part: `MapReduceTopics` for `DECISION_RECORD`, `MapReduceDetailedDiscussions` + single-shot synthesis for `DETAILED_SYNTHESIS`. The header is passed as context (`meeting_subject` + `participants`) into the **map and reduce** prompts, which is why it must be computed before the map-reduce.

```mermaid
%%{init: {"flowchart": {"rankSpacing": 80, "nodeSpacing": 55}}}%%
flowchart TB
    accTitle: DECISION_RECORD & DETAILED_SYNTHESIS — detail
    accDescr {
      Both structured types share notes extraction and header construction (3
      refines), then diverge: DECISION_RECORD via MapReduceTopics, DETAILED_SYNTHESIS
      via MapReduceDetailedDiscussions followed by a single-shot synthesis. The
      header is passed as context to the map and reduce phases.
    }

    classDef io fill:#e1f5ff,stroke:#0277bd,color:#01579b
    classDef proc fill:#f3e5f5,stroke:#6a1b9a,color:#4a148c
    classDef llm fill:#fff3e0,stroke:#e65100,color:#bf360c
    classDef out fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20

    subgraph GEN[".generate(chunks, notes_content)"]
      direction TB

      subgraph INPUTS["inputs"]
        direction TB
        CHUNKS[/"chunks : list&lt;Chunk&gt;"/]:::io
        NC[/"notes_content?"/]:::io
      end

      NX["_extract_notes(notes_content)<br/>NotesExtractor.extract_all<br/>facets ← report_type"]:::llm
      EN[/"ExtractedNotes<br/>intent · next_meeting<br/>topics (DR) · discussions (DS)"/]:::out
      NX --> EN

      subgraph HEADER["generate_header(chunks, extracted_notes) — BaseReportGenerator"]
        direction TB
        RI["RefineIntent<br/>sequential init→refine"]:::llm
        RP["RefineParticipants<br/>sequential init→refine"]:::llm
        RN["RefineNextMeeting<br/>sequential init→refine"]:::llm
        HDR[("Header<br/>title · objective<br/>participants · next_meeting")]:::out
        RI --> HDR
        RP --> HDR
        RN --> HDR
      end

      subgraph DRB["DECISION_RECORD"]
        direction TB
        subgraph MRT["MapReduceTopics"]
          direction TB
          MT_MAP["map<br/>per chunk · ThreadPoolExecutor x4"]:::llm
          MT_RED["reduce<br/>dedup / merge (LLM)"]:::llm
          MT_MAP -->|"list&lt;MappedTopic&gt;"| MT_RED
        end
        DR["return DecisionRecord"]:::out
      end

      subgraph DSB["DETAILED_SYNTHESIS"]
        direction TB
        subgraph MRD["MapReduceDetailedDiscussions"]
          direction TB
          MD_MAP["map<br/>per chunk · ThreadPoolExecutor x4"]:::llm
          MD_RED["reduce<br/>dedup / merge (LLM)"]:::llm
          MD_MAP -->|"list&lt;MappedDetailedDiscussion&gt;"| MD_RED
        end
        subgraph SYN["DetailedDiscussionsSynthesizer"]
          direction TB
          SY["synthesize<br/>single-shot LLM"]:::llm
        end
        MD_RED -->|"list&lt;DetailedDiscussion&gt;"| SY
        DS["return DetailedSynthesis"]:::out
      end
    end

    NC --> NX
    CHUNKS --> RI & RP & RN
    EN -.->|"intent (init_hint)"| RI
    EN -.->|"next_meeting (init_hint)"| RN

    CHUNKS --> MT_MAP
    HDR -->|"meeting_subject + participants"| MT_MAP & MT_RED
    EN -.->|"topics (reduce hint)"| MT_RED
    MT_RED -->|"topics_with_decision + next_steps"| DR
    HDR -->|"header"| DR

    CHUNKS --> MD_MAP
    HDR -->|"meeting_subject + participants"| MD_MAP & MD_RED & SY
    EN -.->|"discussions (reduce hint)"| MD_RED
    MD_RED -->|"detailed_discussions"| DS
    SY -->|"discussions_summary · to_do_list · to_monitor_list"| DS
    HDR -->|"header"| DS
```

## The three extraction strategies

| Strategy | Where | How it works | Why this choice |
|---|---|---|---|
| **Sequential refine** (no map) | Header (Intent, Participants, NextMeeting) | First chunk seeds the object; each subsequent chunk iteratively refines the same object via one LLM call. When notes are provided, `extracted_notes.intent` and `extracted_notes.next_meeting` replace the initial LLM extract as the seed: the refine loop then runs over **every** chunk against that notes-derived seed, saving one LLM call and grounding subsequent refines on what the notes author explicitly wrote. | The header is a single coherent object (one title, one participant list): we enrich it progressively rather than aggregating fragments. |
| **Parallel map-reduce** | Content (Topics, DetailedDiscussions) | Map: one LLM call per chunk in parallel (ThreadPoolExecutor, 4 workers) extracts candidate items. Reduce: one final LLM call dedupes and merges. When notes are provided, the corresponding `extracted_notes.topics` / `extracted_notes.discussions` is injected into the reduce prompt as a **human-priority signal**: the transcription remains the primary source but the notes take precedence on direct contradictions, and a topic absent from notes is not invalidated (notes are not exhaustive). The map phase is untouched. In Langfuse the two phases are traced as `section_topics_map` / `section_topics_reduce` and `section_detailed_discussions_map` / `section_detailed_discussions_reduce`. | Content is inherently multi-item (multiple topics, multiple discussions): we parallelise extraction and let the LLM handle final coherence. |
| **Single-shot synthesis** | DETAILED_SYNTHESIS only (`DetailedDiscussionsSynthesizer`) | One LLM call over the consolidated `Content` to produce `discussions_summary`, `to_do_list`, `to_monitor_list`. | These outputs are derivatives of already-reduced content — no need to revisit raw chunks. |

## Custom report flow

The `CUSTOM_REPORT` branch follows a different shape (detailed in the diagram below): the report structure itself is decided at runtime by a `Rewriter` LLM call that turns the raw user prompt into a `RewriterOutput` plan (an ordered list of `SectionSpec`s, each either a `CollectorSection` or a `CustomSection`).

```mermaid
%%{init: {"flowchart": {"rankSpacing": 80, "nodeSpacing": 55}}}%%
flowchart TB
    accTitle: CUSTOM_REPORT — detail of .generate()
    accDescr {
      Everything runs inside .generate(chunks, notes_content) of CustomReportGenerator
      (which delegates to generate_async). Rewriter.rewrite turns self.raw_prompt into
      a plan; _extract_notes_for_plan extracts notes according to the plan;
      _render_section renders each section in parallel (a predefined collector reusing
      the primitives, or GenericMapReducePipeline); _assemble_markdown produces the
      CustomMarkdownReport.
    }

    classDef io fill:#e1f5ff,stroke:#0277bd,color:#01579b
    classDef proc fill:#f3e5f5,stroke:#6a1b9a,color:#4a148c
    classDef llm fill:#fff3e0,stroke:#e65100,color:#bf360c
    classDef out fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20

    subgraph GEN[".generate(chunks, notes_content)"]
      direction TB

      subgraph INPUTS["inputs"]
        direction TB
        CHUNKS[/"chunks : list&lt;Chunk&gt;"/]:::io
        NC[/"notes_content?"/]:::io
        RAW[/"self.raw_prompt<br/>(custom_prompt, via constructor)"/]:::io
      end

      subgraph RWB["Rewriter"]
        direction TB
        RW["rewrite(self.raw_prompt)<br/>(LLM call)"]:::llm
      end
      PLAN[/"RewriterOutput<br/>title + 1..6 SectionSpec"/]:::out

      subgraph NOTESB["_extract_notes_for_plan(plan, notes_content)"]
        direction TB
        FACETS["∪ collector.notes_facets<br/>+ list of CustomSection.instruction"]:::proc
        NX["NotesExtractor.extract_all<br/>(single asyncio.gather)"]:::llm
        FACETS -.->|"if notes_content<br/>+ facets ∪ instructions non-empty"| NX
      end
      EN[/"ExtractedNotes<br/>facets… + custom_section_facts"/]:::out

      subgraph RENDER["_render_section per section (asyncio.gather)"]
        direction TB
        subgraph COLL["CollectorSection → METADATA_COLLECTORS[id].collect()"]
          direction TB
          C_TITLE["title<br/>= RefineIntent"]:::llm
          C_PART["participants<br/>= RefineParticipants"]:::llm
          C_NEXT["next_meeting<br/>= RefineNextMeeting"]:::llm
          C_TOP["topics<br/>= RefineIntent + RefineParticipants<br/>+ MapReduceTopics"]:::llm
          C_DISC["detailed_discussions<br/>= RefineIntent + RefineParticipants<br/>+ MapReduceDetailedDiscussions"]:::llm
        end
        subgraph GMR["CustomSection → GenericMapReducePipeline"]
          direction TB
          G_MAP["map<br/>map_one per chunk · asyncio.gather · semaphore 4"]:::llm
          G_RED["reduce → markdown<br/>(no # / ## headings)"]:::llm
          G_MAP -->|"list&lt;str&gt; facts"| G_RED
        end
      end
      BODIES[/"bodies : list&lt;str&gt;"/]:::out

      MD["_assemble_markdown(title, sections, bodies)<br/># title + ## heading per section"]:::proc
      CMR["return CustomMarkdownReport"]:::out
    end

    RAW --> RW
    RW --> PLAN
    PLAN --> FACETS
    NC --> NX
    NX --> EN

    PLAN -->|"CollectorSection"| COLL
    PLAN -->|"CustomSection"| G_MAP
    CHUNKS --> COLL
    CHUNKS --> G_MAP
    EN -.->|"intent · next_meeting<br/>topics · discussions"| COLL
    EN -.->|"custom_section_facts[instruction]<br/>(reduce hint)"| G_RED

    COLL --> BODIES
    G_RED --> BODIES
    PLAN -->|"title + headings"| MD
    BODIES --> MD
    MD --> CMR
```

The orchestrator (`CustomReportGenerator`) serialises `rewriter → notes extraction` because the set of facets and the list of custom instructions are both unknown until the plan exists. A single `extract_all` call then parallelises N facet extractions and M custom-instruction extractions in one `asyncio.gather` (the shared `NotesExtractor._semaphore` caps concurrency at 4). The short-circuit kicks in only when **both** facets and custom_instructions are empty (e.g. a plan with only a `participants` `CollectorSection` and no `CustomSection`). When the LLM extract for a custom instruction returns no fact (notes silent on that topic), the corresponding `notes_facts` is `[]` and the generic pipeline runs without the writer-notes block (`NOTES_SECTION_TEMPLATE`, headed `## Notes du rédacteur`) in its reduce prompt.

Each `MetadataCollector` advertises a `notes_facets: ClassVar[frozenset[NotesFacet]]` so the orchestrator can compute the union without inspecting collector internals:

| Collector | `notes_facets` | Wired-in hints |
|---|---|---|
| `title` | `{INTENT}` | `RefineIntent.init_hint = notes.intent` |
| `next_meeting` | `{NEXT_MEETING}` | `RefineNextMeeting.init_hint = notes.next_meeting` |
| `topics` | `{INTENT, TOPICS}` | inner `RefineIntent.init_hint = notes.intent`, `MapReduceTopics.notes_hint = notes.topics` |
| `detailed_discussions` | `{INTENT, DISCUSSIONS}` | inner `RefineIntent.init_hint = notes.intent`, `MapReduceDetailedDiscussions.notes_hint = notes.discussions` |
| `participants` | `∅` | none — notes are not used here |

## Going further

Pointers to key files if you want to dive into the code:

- **Celery task**: `app/services/report_generation_task_service.py` — entry point + success/failure handlers that POST back to `mcr-core`.
- **Generator factory**: `app/services/report_generator/__init__.py` — dispatch via `match` on `ReportTypes`.
- **Base class + shared header**: `app/services/report_generator/base_report_generator.py`.
- **Map-reduce**: `app/services/sections/topics/map_reduce_topics.py`, `app/services/sections/detailed_discussions/map_reduce_detailed_discussions.py`.
- **Refine**: `app/services/sections/base/init_then_refine.py` defines the generic `BaseInitThenRefine[T]` that owns the loop, prompt rendering and Langfuse span. `init_then_refine(chunks, init_hint=None)` accepts an optional `init_hint`: when set, the initial LLM extract on `chunks[0]` is skipped and the seed is `init_hint` itself, then every chunk is refined against it. The three concrete refiners (`app/services/sections/{intent,participants,next_meeting}/refine_*.py`) only declare four class attributes (`response_model`, two prompt templates, `section_name`). `RefineParticipants` returns an internal chain-of-thought wrapper; `BaseReportGenerator.generate_header` finalises it via `.to_public()`.
- **Shared LLM client**: `app/services/utils/llm_helpers.py` — `call_llm_with_structured_output()` (Instructor + exponential retry + Langfuse observability).
- **Custom report orchestrator**: `app/services/report_generator/custom_report_generator.py` — async `generate` (rewriter → plan-driven notes extraction → per-section `asyncio.gather` → markdown assembly).
- **Rewriter**: `app/services/rewriter/rewriter.py` — turns the raw prompt into a `RewriterOutput` plan; the prompt advertises each collector's `description`.
- **Metadata collectors**: `app/services/metadata_collectors/` — `MetadataCollector` adapters and the `METADATA_COLLECTORS` registry; each declares its `notes_facets`.
- **Generic pipeline**: `app/services/generic_pipeline/generic_map_reduce_pipeline.py` — async map-reduce producing markdown for `CustomSection`s.
- **Notes extraction**: `app/services/notes/notes_extractor.py` (+ `facets.py`) — `extract_all` runs facet and custom-instruction extractions in a single `asyncio.gather` (semaphore-capped at 4).
- **Output schemas**: `app/schemas/base.py` (`BaseReport`, `DecisionRecord`, `DetailedSynthesis`, `Header`) and `app/schemas/custom_prompt.py` (`RewriterOutput`, `CollectorSection`, `CustomSection`).
