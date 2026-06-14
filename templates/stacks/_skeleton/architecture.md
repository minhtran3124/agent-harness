# Architecture Profile — Active Stack

This file is the **active stack architecture profile** for this project.
Agents should read it before implementing, debugging, or reviewing.

---

## Generic Architecture Outline (fill in for your project)

When adopting this harness for an application project, replace this file's content
with your stack profile, or run `/bootstrap-xia2` to generate one. Prompts to answer:

**Layers / Responsibilities**
- What are the named layers (e.g. entry point, business logic, data access)?
- What is each layer allowed to do, and what is explicitly off-limits?

**Request / Data Flow**
- How does a request enter the system and travel through the layers to a response?
- Where does auth, validation, and error handling live?

**Key Patterns**
- What cross-cutting patterns does the codebase enforce (e.g. DI, factory, soft-delete)?

**Infrastructure**
- What persistence, cache, messaging, and hosting components are in use?
