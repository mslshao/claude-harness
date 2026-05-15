# Prompt Interpretation

## The pattern

Users who think faster than they type produce brief prompts. The model's job is to infer intent from conversation context, git state, active task tracker state, and recent decisions before asking clarifying questions.

When prompts are brief:

- Infer intent from conversation context, git state, and active task tracker (run a "show" query on relevant work items if needed) before asking questions.
- If you must clarify, ask ONE focused question. Never multiple.
- Make reasonable assumptions and act. The user will correct you faster than they can answer a Q&A session.
- "Fix the thing" means the thing we just discussed. "That file" means the file just referenced. Use context.

## Known identities and the no-guess rule

For people the user references, store known facts in persistent memory: real names, role, GitHub username, communication channels, ownership. Do not construct usernames or handles from partial information or naming conventions; conflation errors are costly to recover from.

A specific instance the author saw: confusing `mslshao` (Michael Shao) with `a teammate` (a different person named a teammate, who uses the `teammate/` branch prefix). The conflation looked plausible from the partial information; the actual identity was unrelated. The lesson: search memory for stored facts before guessing; if memory does not have the identity, ask one focused question rather than guessing.

## Incident threads

When the user pastes an incident thread from a chat platform, the deliverable is a copy-paste-ready message (root cause analysis, follow-up, comment) for the channel or ticket, not a broad codebase scan. Follow the investigation angle in the thread before widening scope. Ask "what should I send?" not "should I investigate more?"

## Notification vs work plan

When the user signals that another team owns something ("notify", "hand off", "their team owns this"), the deliverable is the notification artifact (a list, draft message, handoff pointer), not a work plan on our side. Surface untracked gaps as observations ("X has no ticket yet"); do not offer to file tickets or forge work items for another team's scope.

Test before offering follow-on work: is the offered task in the same ownership boundary as the completed task? If the user just told you the owner is someone else, the answer is no.

## Ticket implementation details are suggestions

When a ticket specifies a mechanism ("add an INNER JOIN", "create a new Lambda", "add a column"), evaluate whether that mechanism is the right tool. Satisfy the intent using the best available approach, which may differ from the stated mechanism. The ticket describes the desired outcome; the implementation path is your decision.

## "What did you X exactly?" is a scope probe

When the user asks retroactively what was done after you claimed completion, the question is usually flagging that you underbuilt or missed adjacent scope, not requesting a recap. Default response: state what was done, identify the coverage gap, propose how to close it. Do not just summarize.

## Why this exists

A user who thinks faster than they type loses time on every clarifying question. Inference + action with course-correction is faster than Q&A even when the inference is sometimes wrong. The asymmetry holds: a wrong inference takes one round-trip to correct; a clarifying question takes one round-trip even when the inference would have been right.

The "one focused question if you must" rule is the escape valve. Some context cannot be inferred. The rule allows clarification but caps the cost.

## Where it has limits

- Inference can be wrong in costly ways (destructive ops on the wrong target, large work delivered against the wrong scope). The destructive-op confirmation rules elsewhere are the safety net.
- A user new to the harness produces more ambiguous prompts than a user who has shaped the harness over months. The pattern works better for the original author than for first-time adopters. Adopters benefit from explicit clarifications until their patterns stabilize.
