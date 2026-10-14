# Dispatch Prompt Contract

The other dispatch docs answer *who* runs the work. This one answers *what the prompt must carry* once the target is chosen. It applies to every dispatch: subagent, workflow stage, or peer session.

The clauses below are not stylistic. Each one exists because its absence produced a measured defect, and each defect was of the same shape: the agent did competent work against a default assumption the prompt never overrode. An agent inherits nothing from the dispatching session except the prompt text. Anything the dispatcher knows and does not write down is not a shared premise; it is a coin flip.

## 1. State claims: name the source that establishes them

**Clause**: "Read the full comment history oldest to newest, not just the description. Cite the comment date or the PR that establishes each state claim. A claim sourced only from the description is the defect."

**Why**: an agent asked to describe the current state of a tracked item reads the description and skips the comments, every time, unless told otherwise. A description records the state at the moment it was written; the comments carry everything that happened since.

**Measured**: a 26-item sweep wrote a "state as of today" paragraph onto each ticket in a handoff. Five of the 26 were wrong, all in the same direction (understating progress). The worst was a top-priority blocker whose comment told its inheritor that no code change existed and no PR had been opened, when the fix had merged six days earlier and was recorded in four comments directly above it on the same ticket. It was caught by luck: a different agent, on unrelated research, happened to read a full history. No designed check caught it.

**Note the compounding failure.** The dispatching session had hit the identical description-before-comments trap itself earlier the same afternoon, on a different tracker, and had written the lesson up. Writing up a trap does not inoculate the next dispatch against it. Only putting the clause in the prompt does. That gap is exactly why this rule sits in the dispatch contract instead of in a memory file, and why the harness backs it with a pre-dispatch hook that fires when a prompt asks for the state of a tracked item without a read-the-comments instruction.

## 2. Cross-boundary verification names the artifact class

**Clause**: state what evidence the dispatcher will check, in the vocabulary of the artifact actually being produced.

**Why**: the standing rule is that a subagent's summary is not evidence and the artifact itself must be checked. On the day above, that rule was applied to every code change and to zero of the 26 ticket writes, because "check the diff" reads as being about code. The rule was not forgotten; it was scoped away by its own phrasing.

A dispatch that produces ticket comments, wiki pages, Slack drafts, or config edits needs its verification clause written in those nouns. "I will re-read the posted comment against the ticket's history" is a contract. "Verify your work" is not.

Corollary for a staged hook (2026-10-07): a brief that names a staged hook gives the staged copy's hash and the live hook's hash. Both are read with `sha256sum` when the brief is written, so the worker can tell whether that copy is already installed. On 2026-10-06 a brief told a worker to fold a change into a staged copy that had been installed hours earlier, and built as written it would have reverted two installed changes.

## 3. Sweeps carry a value bar, not just a filter

**Clause**: name the bar that makes an item worth acting on, not only the predicate that makes it match.

**Why**: a filter-only brief returns everything that matches, and the dispatcher then owns a triage problem it did not budget for. A sweep briefed to find untracked defects surfaced 107 raw candidates. The agent deviated from its brief, correctly, by applying a value bar (a cited file or a real incident, and no existing ticket) and presenting a tiered choice instead. Handing the operator a 107-row promote-everything question would have been a bad question, and the brief, not the agent, was what made it likely.

Corollary for the ownership predicate: say exactly how "already tracked" is tested. A substring match on a tracker key both over- and under-counts; a bracketed key in the title is a testable rule.

## 4. Destructive verbs must be named in this round's directive

**Clause**: if the agent may force-push, rebase, delete a branch, merge, deploy, or drop, the prompt says so in the words the human used this round.

**Why**: conditional permission ("handle it if needed") does not pre-authorize an irreversible operation, and neither does a directive from an earlier round. Before dispatching, check that the destructive verb in the prompt is one the human actually authorized for this dispatch. Absent that, the prompt says explicitly that the agent stops and reports instead.

The mirror-image failure is on the dispatcher's side: an offer where one word authorizes two different blast radii ("reply `approve` and I will do both, or `approve` for just the first") cannot be disambiguated by the reply. Give each scope its own verb.

## 5. Approval gates belong to the acting agent

**Clause**: relay the human's decision as context. Never add that the agent's own approval gate is unnecessary.

**Why**: the dispatcher's approval is not the agent's approval, and this holds whether the "agent" is a subagent or a peer session. The gate belongs to whoever holds the specific mutation. Pre-empting it contradicts the very rule being relayed, and it costs seconds to keep: in the instance that produced this clause, the human answered the redundant-looking question immediately.

See `../patterns/multi-session-orchestration.md` for the peer-session form of the same rule, which is where it was first violated.

## 6. Critiques get a file path, not a paste

**Clause**: write the artifact under review to a file and pass the path.

**Why**: an artifact pasted into the prompt gets reviewed as the dispatcher's description of the artifact, not as the artifact. Per-character checks (dash scans, exact word counts, vocabulary scans) silently cannot run. A coherence critic once opened its report by saying the revised draft was not in its inputs, reviewed from the prompt brief anyway, and left three of six checks unclosed. That framing correlation is the precise thing an independent reviewer exists to break.

## 7. Completion has a terminal shape, and "completed" is not it

**Clause**: require a terminal RESULT block, and state what it must contain (the paths touched, the identifier produced, the acceptance criteria addressed).

**Why**: a completion status on the task notification means the process ended, not that the work shipped. A result that stops mid-thought, omits its expected block, or lacks an identifier it was supposed to produce probably hit a turn limit. Inspect the artifact before reporting done.

Recovery order, when the block is missing: resume the same agent (its context is intact) with what is missing and the definition of done; only when it is no longer resumable, cold-dispatch the same agent type with a self-contained prompt describing what the previous agent actually did according to the artifact, not according to its prose.

## The shape behind all seven

Every clause converts an assumption the dispatcher holds into text the agent can act on. The recurring defect is not that the model reasons badly. It is that the dispatching session knows something (comments carry the state; this sweep needs a bar; that verb was not authorized; the human already said yes, but not to this) and ships a prompt that does not say it. The agent then defaults, competently and confidently, to something else.

The test before sending: what does this agent need to know that only I know right now? If the answer is not in the prompt, the prompt is not finished.
