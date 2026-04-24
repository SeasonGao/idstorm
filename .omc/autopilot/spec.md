# Spec: Dialogue Phase UX Optimization

## Goal
Enhance the dialogue phase with option-based interaction (clickable choices instead of free-text only) and a "proceed to next step" button for both auto and manual dimension advancement.

## Requirements

### 1. Option-Based Interaction
- Each assistant message that asks a question must include 3-5 selectable options
- Options are rendered as clickable chips below the assistant message
- Support both single-select and multi-select modes
- Free-text input remains available as fallback (existing textarea)
- Users can click options OR type freely
- Clicking an option sends it as a user message immediately (single-select)
- Multi-select requires a "确认" button to submit all selections

### 2. "Proceed to Next Step" Button
- Always visible in the input area when not streaming
- Clicking it force-advances to the next dialogue dimension
- Model still auto-detects saturation and advances normally
- When all 4 dimensions are complete, the button changes to "查看设计需求"

## Technical Design

### Backend Changes

**dialogue_engine.py:**
- Modify system prompt to instruct LLM to output `<<OPTIONS:{json}>>` at end of each response
- Parse options marker from full_content after streaming
- Strip markers from displayed content in done event
- Add `skip_to_next` parameter support: mark current dimension complete, advance, generate response for next dimension

**dialogue.py (router):**
- Add `skip_to_next: bool = False` to DialogueRequest
- Make `content` optional when skip_to_next is true
- Handle skip_to_next by advancing dimension and generating new response

### Frontend Changes

**types/index.ts:**
- Add `options` field to ChatMessage
- Add MessageOptions type

**useChat.ts:**
- Handle options in done event (extract and attach to message)
- Add skipToNext method
- On done, replace message content with clean version (markers stripped)

**MessageBubble.tsx:**
- Render OptionChips below assistant messages that have options

**OptionChips.tsx (new):**
- Renders clickable option chips
- Single-select: click to send immediately
- Multi-select: click to toggle, with confirm button
- "其他..." option reveals inline text input

**DialoguePage.tsx:**
- Add "进入下一步骤" button in input area
- Wire up option click → sendMessage
- Wire up skipToNext

## Files to Modify
- `backend/app/services/dialogue_engine.py`
- `backend/app/routers/dialogue.py`
- `frontend/src/types/index.ts`
- `frontend/src/hooks/useChat.ts`
- `frontend/src/components/dialogue/MessageBubble.tsx`
- `frontend/src/components/dialogue/DialoguePage.tsx`
- `frontend/src/components/dialogue/ChatInput.tsx`

## Files to Create
- `frontend/src/components/dialogue/OptionChips.tsx`
