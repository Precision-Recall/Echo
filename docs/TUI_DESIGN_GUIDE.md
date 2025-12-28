# Echo TUI Design & Implementation Guide

This document details the architecture, design choices, and implementation steps used to build the **Echo** Terminal User Interface (TUI). The design is explicitly inspired by the **Claude Code** CLI, featuring a distinct purple/pink aesthetic, split-pane layouts, and real-time streaming feedback.

## 1. Design Philosophy & References

The goal was to move beyond standard standard command-line logging to a "Premium Console Experience."

*   **Primary Inspiration**: [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview) CLI interface.
*   **Key Aesthetics**:
    *   **Theme**: Deep Purples (`#2E1065`), Pinks (`#D946EF`), and Violets (`#8B5CF6`).
    *   **Typography**: Bold headers, dimmed metadata, and clear distinction between "Thoughts" (internal monologue) and "Actions" (user-visible outputs).
    *   **Layout**: Split-screen to separate the "User Conversation" from the "Agent Brain" (Thinking Process).

## 2. Technology Stack

We utilized the **Rich** library for Python, widely considered the gold standard for beautiful terminal formatting.

*   **Library**: [`rich`](https://github.com/Textualize/rich)
*   **Key Modules Used**:
    *   `rich.layout`: For creating the responsive grid system (Header, Body, Footer, Sidebar).
    *   `rich.live`: For the non-blocking rendering loop that updates the UI 10+ times per second.
    *   `rich.panel`: For framing content with styled borders.
    *   `rich.console`: For standard formatted output.

## 3. Architecture

The TUI is built as a standalone module `src/utils/tui.py` that runs concurrently with the agent's logic.

### 3.1. The Layout System (`EchoTUI`)

We defined a flexible grid using `rich.Main` layout:

```python
self.layout.split(
    Layout(name="header", size=5),       # Fixed height banner
    Layout(name="body", ratio=1),        # Flexible body
    Layout(name="footer", size=3)        # Fixed height footer
)

# Split body into Main Interaction (Left) and Thinking Sidebar (Right)
self.layout["body"].split_row(
    Layout(name="main", ratio=2), 
    Layout(name="sidebar", ratio=1)
)
```

### 3.2. Asynchronous State Management

To ensure the UI doesn't freeze the Agent (which performs blocking network calls) or vice-versa, we used `asyncio` patterns:

1.  **The Live Loop**: The TUI runs its own `start()` methods that updates the screen frame-by-frame.
2.  **Concurrency**: We use `asyncio.TaskGroup` in `main.py` to run `tui.start()` and `agent.run()` as parallel tasks.
3.  **Thread-Safe Updates**: The UI methods (`add_log`, `add_thought`) append to internal lists (`self.MainLog`, `self.ThinkingLog`). The `Live` loop reads these lists on the next refresh cycle, avoiding race conditions on the stdout buffer.

### 3.3. Decoupling Logic ( callbacks)

To prevent circular dependencies between the `DesktopAgent` and the `TUI`, we used a **Callback Pattern**:

1.  **ThinkingLogger**: Modified to accept an optional `ui_callback`.
2.  **Main Injection**: `main.py` defines a bridging function:
    ```python
    def log_callback(type_, message):
        if type_ == "thought":
            tui.add_thought(message)
        else:
            tui.add_log(message)
    ```
3.  **Execution**: When the Agent logs an event, it calls the callback, which pushes data to the TUI instance.

## 4. Implementation Details

### Step 1: The Basic UI Utilities (`src/utils/ui.py`)
We first created a shared `Console` instance and theme definitions to ensure color consistency across the app. This handles the "Fast Mode" static prints.

### Step 2: The Advanced TUI Class (`src/utils/tui.py`)
This class encapsulates the entire visual state.
*   **Wave Animation**: A simple frame-counter modulo loop generates the `  ▂ ▃ ▄ ▅` animation string when `is_listening` is True.
*   **Panel Updates**: Helper methods (`update_sidebar`, `update_main`) regenerate the Rich Renderables based on the current log state.

### Step 3: Integration
In `main.py`, we detect `AgentMode.VOICE` and switch drivers:
*   **Fast Mode**: Uses standard `console.print` sequence.
*   **Voice Mode**: Instantiates `EchoTUI`, starts the `Live` context manager, and wraps the agent execution.

## 5. References & Resources

*   **Rich Library Documentation**: [https://rich.readthedocs.io/en/latest/](https://rich.readthedocs.io/en/latest/)
    *   *Specifically the [Layout Guide](https://rich.readthedocs.io/en/latest/layout.html) and [Live Display](https://rich.readthedocs.io/en/latest/live.html)*.
*   **Anthropic's Claude Code**: Visual inspiration for the "Thinking Block" and color scheme.
*   **Python Asyncio TaskGroups**: [Python 3.11+ Docs](https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup) for managing the parallel UI/Network tasks.
